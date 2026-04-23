from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from multiprocessing import reduction
from re import S

import torch
import numpy as np

from models.losses import FocalLoss, RegL1Loss, RegLoss, RegWeightedL1Loss
from models.prob_pose_aux_loss import ProbPoseAuxLoss
from models.decode import grasp_pose_decode
from models.utils import _sigmoid, flip_tensor, flip_lr_off, flip_lr, _transpose_and_gather_feat
from utils.debugger import Debugger
from utils.post_process import grasp_pose_post_process
from utils.oracle_utils import gen_oracle_map
from .base_trainer import BaseTrainer


class ConfLoss(torch.nn.Module):
    """Geometry-aware heteroscedastic confidence / uncertainty loss.

    The branch still predicts one scalar log-variance for each orientation class at each
    center. Compared with the original lightweight version, the detached supervision target
    is no longer the raw center-to-keypoint offset error. Instead, it reconstructs the 2D
    keypoints in the output-resolution plane and supervises confidence with the detached
    geometry error between predicted and GT 2D correspondences for the matched grasp.
    """

    def __init__(self, opt):
        super(ConfLoss, self).__init__()
        self.output_res = opt.output_res
        self.ori_num = opt.ori_num
        if hasattr(opt, 'num_grasp_kpts'):
            self.num_kpts = opt.num_grasp_kpts
        else:
            self.num_kpts = opt.heads['kpts_center_offset'] // (2 * self.ori_num)

    def _select_orientation_offsets(self, kpts_tensor, ori_clses):
        batch_size, max_grasps = ori_clses.shape
        kpts_tensor = kpts_tensor.view(
            batch_size, max_grasps, self.ori_num, self.num_kpts, 2
        )
        gather_index = ori_clses.view(batch_size, max_grasps, 1, 1, 1).expand(
            batch_size, max_grasps, 1, self.num_kpts, 2
        )
        return kpts_tensor.gather(2, gather_index).squeeze(2)

    def forward(self, conf_map, reg_map, kpts_center_output, batch):
        conf_pred = _transpose_and_gather_feat(conf_map, batch['ind'])
        ori_clses = batch['ori_clses'].long().unsqueeze(2)
        conf_pred = conf_pred.gather(2, ori_clses).squeeze(2)
        conf_pred = torch.clamp(conf_pred, min=-5., max=5.)

        ct_int_x = (batch['ind'] % self.output_res).float()
        ct_int_y = torch.div(batch['ind'], self.output_res, rounding_mode='floor').float()
        ct_int = torch.stack([ct_int_x, ct_int_y], dim=2)

        if reg_map is not None and 'reg' in batch:
            reg_pred = _transpose_and_gather_feat(reg_map, batch['ind'])
            reg_gt = batch['reg']
        else:
            reg_pred = torch.zeros_like(ct_int)
            reg_gt = torch.zeros_like(ct_int)

        center_pred = ct_int + reg_pred
        center_gt = ct_int + reg_gt

        kpts_center_pred = _transpose_and_gather_feat(kpts_center_output, batch['ind'])
        kpts_center_target = batch['kpts_center_offset']
        kpts_center_mask = batch['kpts_center_mask'].float()

        ori_clses_flat = batch['ori_clses'].long()
        pred_offsets = self._select_orientation_offsets(kpts_center_pred, ori_clses_flat)
        target_offsets = self._select_orientation_offsets(kpts_center_target, ori_clses_flat)
        offset_mask = self._select_orientation_offsets(kpts_center_mask, ori_clses_flat).float()

        kpt_pred = center_pred.unsqueeze(2) + pred_offsets
        kpt_gt = center_gt.unsqueeze(2) + target_offsets

        coord_valid_count = offset_mask.sum(dim=(2, 3))
        valid_mask = (coord_valid_count > 0).float()
        geom_err = (
            torch.abs(kpt_pred - kpt_gt) * offset_mask
        ).sum(dim=(2, 3)) / (coord_valid_count + 1e-4)

        # Keep the confidence branch as an auxiliary head in this first cut.
        geom_err = geom_err.detach()

        loss = (torch.exp(-conf_pred) * geom_err + conf_pred) * valid_mask
        loss = loss.sum() / (valid_mask.sum() + 1e-4)

        conf_mean = (conf_pred * valid_mask).sum() / (valid_mask.sum() + 1e-4)
        conf_geom_proxy_mean = (geom_err * valid_mask).sum() / (valid_mask.sum() + 1e-4)
        return loss, conf_mean, conf_geom_proxy_mean


class GraspPoseLoss_clf(torch.nn.Module):
    def __init__(self, opt):
        super(GraspPoseLoss_clf, self).__init__()
        self.opt = opt

        # grasp width
        self.crit_w = RegWeightedL1Loss() 

        # center loss
        self.crit_hm = FocalLoss()
        self.crit_reg = RegL1Loss() if opt.reg_loss == 'l1' else \
            RegLoss() if opt.reg_loss == 'sl1' else None

        self.crit_kpts_center = RegWeightedL1Loss() if not opt.dense_kpts else \
            torch.nn.L1Loss(reduction='sum')
        self.crit_hm_kpts = FocalLoss()
        
        # the scale loss
        if opt.sep_scale_branch:
            self.crit_scale = RegWeightedL1Loss()

        # the lightweight confidence / uncertainty loss
        if opt.conf_branch:
            self.crit_conf = ConfLoss(opt)

        if opt.prob_pose_loss:
            self.crit_prob_pose = ProbPoseAuxLoss(opt)
            self.prob_pose_forward_calls = 0
            self.prob_pose_warmup_iters = max(0, int(opt.prob_pose_warmup_iters))
            self.prob_pose_ramp_iters = max(1, int(opt.prob_pose_ramp_iters))
            
        """CenterNet version
        self.crit = FocalLoss()
        self.crit_hm_hp = torch.nn.MSELoss() if opt.mse_loss else FocalLoss()
        self.crit_kp = RegWeightedL1Loss() if not opt.dense_kpts else \
            torch.nn.L1Loss(reduction='sum')
        self.crit_reg = RegL1Loss() if opt.reg_loss == 'l1' else \
            RegLoss() if opt.reg_loss == 'sl1' else None
        self.opt = opt
        """ 

    def forward(self, outputs, batch):

        opt = self.opt
        hm_loss, w_loss, off_loss = 0, 0, 0
        scale_loss = 0
        conf_loss = 0
        conf_mean = 0
        conf_geom_proxy_mean = 0
        prob_pose_loss = 0
        prob_pose_valid_count = 0
        prob_pose_cost_mean = 0
        prob_pose_raw_loss = 0
        prob_pose_high_cost_rate = 0
        prob_pose_skip_rate = 0
        prob_pose_no_valid_rate = 0
        prob_pose_invalid_raw_rate = 0
        prob_pose_too_large_raw_rate = 0
        prob_pose_target_valid_total = 0
        prob_pose_target_selected_count = 0
        prob_pose_target_select_cost_mean = 0
        prob_pose_target_geom_cost_mean = 0
        prob_pose_target_conf_quality_mean = 0
        prob_pose_target_mode_id = 0
        prob_pose_active_weight = 0

        kpts_center_loss, hm_kpts_loss, kpts_offset_loss = 0, 0, 0

        for s in range(opt.num_stacks):
            output = outputs[s]
            output['hm'] = _sigmoid(output['hm'])
            if opt.kpts_refine and not opt.mse_loss:
                output['hm_kpts'] = _sigmoid(output['hm_kpts'])

            if opt.eval_oracle_hmkpts:
                output['hm_kpts'] = batch['hm_kpts']
            if opt.eval_oracle_hm:
                output['hm'] = batch['hm']
            if opt.eval_oracle_kps:
                if opt.dense_kpts:
                    output['kpts'] = batch['dense_kpts']
                else:
                    raise NotImplementedError("Haven't check what does gen_oracle_map mean")
                    output['kpts'] = torch.from_numpy(gen_oracle_map(
                        batch['kpts'].detach().cpu().numpy(),
                        batch['ind'].detach().cpu().numpy(),
                        opt.output_res, opt.output_res)).to(opt.device)
            if opt.eval_oracle_kpts_offset:
                output['kpts_offset'] = torch.from_numpy(gen_oracle_map(
                    batch['kpts_offset'].detach().cpu().numpy(),
                    batch['kpts_ind'].detach().cpu().numpy(),
                    opt.output_res, opt.output_res)).to(opt.device)
            
            # The center branch losses
            hm_loss += self.crit_hm(output['hm'], batch['hm']) / opt.num_stacks

                
            kpts_center_loss += self.crit_kpts_center(output['kpts_center_offset'], batch['kpts_center_mask'],
                                    batch['ind'], batch['kpts_center_offset']) / opt.num_stacks

            if opt.reg_offset and opt.off_weight > 0:
                off_loss += self.crit_reg(output['reg'], batch['reg_mask'],
                                          batch['ind'], batch['reg']) / opt.num_stacks
            
            # The open width prediction loss
            if opt.w_weight > 0:
                w_loss += self.crit_w(output['w'], batch['w_mask'],
                                         batch['ind'], batch['w']) / opt.num_stacks
            
            # The keypoints refinement branch loss
            if opt.kpts_refine and opt.off_weight > 0:
                kpts_offset_loss += self.crit_reg(
                    output['kpts_offset'], batch['kpts_mask'],
                    batch['kpts_ind'], batch['kpts_offset']) / opt.num_stacks
            if opt.kpts_refine and opt.hm_kpts_weight > 0:
                hm_kpts_loss += self.crit_hm_kpts(
                    output['hm_kpts'], batch['hm_kpts']) / opt.num_stacks
            
            # The scale loss
            if opt.sep_scale_branch and opt.scale_weight > 0:
                scale_loss += self.crit_scale(
                    output['scales'], batch['scales_mask'],
                    batch['ind'], batch['scales']
                ) / opt.num_stacks

            # The confidence / uncertainty loss.
            # It learns a per-grasp scalar uncertainty from the detached reconstructed
            # 2D keypoint geometry error, so the first cut does not perturb the existing
            # keypoint branch behavior or the inference-time fusion logic.
            if opt.conf_branch and opt.conf_weight > 0:
                conf_loss_this, conf_mean_this, conf_geom_proxy_mean_this = self.crit_conf(
                    output['conf'], output.get('reg', None), output['kpts_center_offset'], batch
                )
                conf_loss += conf_loss_this / opt.num_stacks
                conf_mean += conf_mean_this / opt.num_stacks
                conf_geom_proxy_mean += conf_geom_proxy_mean_this / opt.num_stacks

            if opt.prob_pose_loss and opt.prob_pose_weight > 0:
                if self.training:
                    self.prob_pose_forward_calls += 1
                if self.prob_pose_forward_calls <= self.prob_pose_warmup_iters:
                    active_prob_pose_weight = 0.0
                else:
                    ramp_progress = (
                        self.prob_pose_forward_calls - self.prob_pose_warmup_iters
                    ) / float(self.prob_pose_ramp_iters)
                    active_prob_pose_weight = opt.prob_pose_weight * min(
                        max(ramp_progress, 0.0), 1.0
                    )
                if active_prob_pose_weight > 0:
                    prob_pose_loss_this, prob_pose_valid_count_this, prob_pose_cost_mean_this, \
                        prob_pose_raw_loss_this, prob_pose_high_cost_rate_this, \
                        prob_pose_skip_rate_this, prob_pose_no_valid_rate_this, \
                        prob_pose_invalid_raw_rate_this, prob_pose_too_large_raw_rate_this, \
                        prob_pose_target_valid_total_this, prob_pose_target_selected_count_this, \
                        prob_pose_target_select_cost_mean_this, \
                        prob_pose_target_geom_cost_mean_this, \
                        prob_pose_target_conf_quality_mean_this, \
                        prob_pose_target_mode_id_this = \
                        self.crit_prob_pose(
                            output.get('reg', None),
                            output['kpts_center_offset'],
                            batch,
                            conf_map=output.get('conf', None),
                        )
                else:
                    zero_loss = output['hm'].sum() * 0
                    zero_stat = output['hm'].sum().detach() * 0
                    prob_pose_loss_this = zero_loss
                    prob_pose_valid_count_this = zero_stat
                    prob_pose_cost_mean_this = zero_stat
                    prob_pose_raw_loss_this = zero_stat
                    prob_pose_high_cost_rate_this = zero_stat
                    prob_pose_skip_rate_this = zero_stat
                    prob_pose_no_valid_rate_this = zero_stat
                    prob_pose_invalid_raw_rate_this = zero_stat
                    prob_pose_too_large_raw_rate_this = zero_stat
                    prob_pose_target_valid_total_this = zero_stat
                    prob_pose_target_selected_count_this = zero_stat
                    prob_pose_target_select_cost_mean_this = zero_stat
                    prob_pose_target_geom_cost_mean_this = zero_stat
                    prob_pose_target_conf_quality_mean_this = zero_stat
                    prob_pose_target_mode_id_this = output['hm'].new_tensor(
                        float(getattr(self.crit_prob_pose, 'target_mode_id', 0))
                    ).detach()
                prob_pose_loss += prob_pose_loss_this / opt.num_stacks
                prob_pose_valid_count += prob_pose_valid_count_this / opt.num_stacks
                prob_pose_cost_mean += prob_pose_cost_mean_this / opt.num_stacks
                prob_pose_raw_loss += prob_pose_raw_loss_this / opt.num_stacks
                prob_pose_high_cost_rate += prob_pose_high_cost_rate_this / opt.num_stacks
                prob_pose_skip_rate += prob_pose_skip_rate_this / opt.num_stacks
                prob_pose_no_valid_rate += prob_pose_no_valid_rate_this / opt.num_stacks
                prob_pose_invalid_raw_rate += prob_pose_invalid_raw_rate_this / opt.num_stacks
                prob_pose_too_large_raw_rate += prob_pose_too_large_raw_rate_this / opt.num_stacks
                prob_pose_target_valid_total += (
                    prob_pose_target_valid_total_this / opt.num_stacks
                )
                prob_pose_target_selected_count += (
                    prob_pose_target_selected_count_this / opt.num_stacks
                )
                prob_pose_target_select_cost_mean += (
                    prob_pose_target_select_cost_mean_this / opt.num_stacks
                )
                prob_pose_target_geom_cost_mean += (
                    prob_pose_target_geom_cost_mean_this / opt.num_stacks
                )
                prob_pose_target_conf_quality_mean += (
                    prob_pose_target_conf_quality_mean_this / opt.num_stacks
                )
                prob_pose_target_mode_id += prob_pose_target_mode_id_this / opt.num_stacks
                prob_pose_active_weight += (
                    output['hm'].new_tensor(active_prob_pose_weight) / opt.num_stacks
                )


        loss = opt.hm_weight * hm_loss + opt.w_weight * w_loss + \
            opt.off_weight * off_loss + opt.kpts_center_weight * kpts_center_loss + \
            opt.hm_kpts_weight * hm_kpts_loss + opt.off_weight * kpts_offset_loss + \
            opt.scale_weight * scale_loss + opt.conf_weight * conf_loss + \
            prob_pose_active_weight * prob_pose_loss
        
        
        loss_stats = {'loss': loss, 'hm_loss': hm_loss, 'w_loss': w_loss,
                    'kpts_center_loss': kpts_center_loss,'reg_loss(center_offset)': off_loss,
                    'hm_kpts_loss': hm_kpts_loss, 'kpts_offset_loss': kpts_offset_loss,
                    "scale_loss": scale_loss,
                    "conf_loss": conf_loss,
                    "conf_mean": conf_mean,
                    "conf_geom_proxy_mean": conf_geom_proxy_mean,
                    "prob_pose_loss": prob_pose_loss,
                    "prob_pose_valid_count": prob_pose_valid_count,
                    "prob_pose_cost_mean": prob_pose_cost_mean,
                    "prob_pose_raw_loss": prob_pose_raw_loss,
                    "prob_pose_high_cost_rate": prob_pose_high_cost_rate,
                    "prob_pose_skip_rate": prob_pose_skip_rate,
                    "prob_pose_no_valid_rate": prob_pose_no_valid_rate,
                    "prob_pose_invalid_raw_rate": prob_pose_invalid_raw_rate,
                    "prob_pose_too_large_raw_rate": prob_pose_too_large_raw_rate,
                    "prob_pose_target_valid_total": prob_pose_target_valid_total,
                    "prob_pose_target_selected_count": prob_pose_target_selected_count,
                    "prob_pose_target_select_cost_mean": prob_pose_target_select_cost_mean,
                    "prob_pose_target_geom_cost_mean": prob_pose_target_geom_cost_mean,
                    "prob_pose_target_conf_quality_mean": prob_pose_target_conf_quality_mean,
                    "prob_pose_target_mode_id": prob_pose_target_mode_id,
                    "prob_pose_active_weight": prob_pose_active_weight
                    }

                       
        return loss, loss_stats


class GraspPoseTrainer(BaseTrainer):
    def __init__(self, opt, model, optimizer=None):
        super(GraspPoseTrainer, self).__init__(opt, model, optimizer=optimizer)

    def _get_losses(self, opt):
        loss_states = ['loss', 'hm_loss', 'w_loss', 'kpts_center_loss',
                   'reg_loss(center_offset)']

        # The options to get the keypoint refinement losses
        if self.opt.kpts_refine:
            loss_states.append('hm_kpts_loss')
            loss_states.append('kpts_offset_loss')

        # The scale loss
        if self.opt.sep_scale_branch:
            loss_states.append("scale_loss")

        if self.opt.conf_branch:
            loss_states.append("conf_loss")
            loss_states.append("conf_mean")
            loss_states.append("conf_geom_proxy_mean")
        if self.opt.prob_pose_loss:
            loss_states.append("prob_pose_loss")
            loss_states.append("prob_pose_valid_count")
            loss_states.append("prob_pose_cost_mean")
            loss_states.append("prob_pose_raw_loss")
            loss_states.append("prob_pose_high_cost_rate")
            loss_states.append("prob_pose_skip_rate")
            loss_states.append("prob_pose_no_valid_rate")
            loss_states.append("prob_pose_invalid_raw_rate")
            loss_states.append("prob_pose_too_large_raw_rate")
            loss_states.append("prob_pose_target_valid_total")
            loss_states.append("prob_pose_target_selected_count")
            loss_states.append("prob_pose_target_select_cost_mean")
            loss_states.append("prob_pose_target_geom_cost_mean")
            loss_states.append("prob_pose_target_conf_quality_mean")
            loss_states.append("prob_pose_target_mode_id")
            loss_states.append("prob_pose_active_weight")

        loss = GraspPoseLoss_clf(opt)
        return loss_states, loss

    def debug(self, batch, output, iter_id):
        opt = self.opt
        reg = output['reg'] if opt.reg_offset else None
        hm_kpts = output['hm_kpts'] if opt.kpts_refine else None
        kpts_offset = output['kpts_offset'] if opt.kpts_refine else None
        dets = grasp_pose_decode(
            self.opt,
            output['hm'], output['w'], output['kpts_center_offset'],
            reg=reg, hm_kpts=hm_kpts, kpts_offset=kpts_offset, 
            scales=output["scales"] if "scales" in output.keys() else None, 
            K=self.opt.K)
        dets = dets.detach().cpu().numpy().reshape(1, -1, dets.shape[2])

        dets[:, :, :10] *= opt.input_res / opt.output_res
        dets_gt = batch['meta']['gt_det'].numpy().reshape(1, -1, dets.shape[2])
        dets_gt[:, :, :10] *= opt.input_res / opt.output_res
        for i in range(1):
            debugger = Debugger(
                dataset=opt.dataset, ipynb=(opt.debug == 3), theme=opt.debugger_theme,
                kpt_type=self.opt.kpt_type
            )
            img = batch['input'][i].detach().cpu().numpy().transpose(1, 2, 0)
            img = np.clip(((
                img * opt.std + opt.mean) * 255.), 0, 255).astype(np.uint8)
            # img = img[:,:,::-1] # bgr
            img = img[:, :, :3][:, :, ::-1] # RGBD to bgr
            pred = debugger.gen_colormap(
                output['hm'][i].detach().cpu().numpy())
            gt = debugger.gen_colormap(batch['hm'][i].detach().cpu().numpy())
            debugger.add_blend_img(img, pred, 'pred_hm')
            debugger.add_blend_img(img, gt, 'gt_hm')

            debugger.add_img(img, img_id='out_pred')
            for k in range(len(dets[i])):
                if dets[i, k, 11] > opt.center_thresh:
                    debugger.add_ps_grasp_kpts(dets[i, k, 2:10], img_id='out_pred')

            debugger.add_img(img, img_id='out_gt')
            for k in range(len(dets_gt[i])):
                if dets_gt[i, k, 11] > opt.center_thresh:
                    debugger.add_ps_grasp_kpts(dets_gt[i, k, 2:10], img_id='out_gt')

            if opt.kpts_refine:
                pred = debugger.gen_colormap_hp(
                    output['hm_kpts'][i].detach().cpu().numpy())
                gt = debugger.gen_colormap_hp(
                    batch['hm_kpts'][i].detach().cpu().numpy())
                debugger.add_blend_img(img, pred, 'pred_hmkpts')
                debugger.add_blend_img(img, gt, 'gt_hmkpts')

            if opt.debug == 4:
                debugger.save_all_imgs(
                    opt.debug_dir, prefix='{}'.format(iter_id))
            else:
                debugger.show_all_imgs(pause=True)

    def save_result(self, output, batch, results):
        reg = output['reg'] if self.opt.reg_offset else None
        hm_kpts = output['hm_kpts'] if self.opt.kpts_refine else None
        kpts_offset = output['kpts_offset'] if self.opt.kpts_refine else None
        dets = grasp_pose_decode(
            output['hm'], output['w'], output['kpts_center_offset'],
            reg=reg, hm_kpts=hm_kpts, kpts_offset=kpts_offset, 
            scales=output["scales"] if "scales" in output.keys() else None, 
            K=self.opt.K)
        dets = dets.detach().cpu().numpy().reshape(1, -1, dets.shape[2])

        dets_out = grasp_pose_post_process(
            dets.copy(), batch['meta']['c'].cpu().numpy(),
            batch['meta']['s'].cpu().numpy(),
            output['hm'].shape[2], output['hm'].shape[3])


        results[batch['meta']['img_id'].cpu().numpy()[0]] = dets_out[0]
