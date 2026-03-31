import pdb
import numpy as np

import _init_paths

from detectors.base_detector import BaseDetector
from detectors.detector_factory import detector_factory
from pose_recover.pnp_solver_factory import PnPSolverFactory
from pose_recover.Base import BasePnPSolver

class KeypointGraspNet():
    def __init__(self, opt, kpt_detector:BaseDetector, pnp_solver:BasePnPSolver):
        self.opt = opt
        self.kpt_detector = kpt_detector
        self.pnp_solver = pnp_solver
    
    def set_cam_intrinsic_mat(self, intrinsic_mat):
        """Set the camera intrinsic matrix for pose recovery
        Args:
            intrincis (3, 3)
        """
        self.pnp_solver.set_camera_intrinsic_matrix(intrinsic_mat)
    
    def generate(self, input, return_all=False):
        """Generate grasps

        Args:
            input (np.ndarray or Dict):         The RGB-D image, or dictionary containing the preprocessed input and dataset information
        
        Outputs:
            quaternions (N, 4):                 Quaternion representaiton of grasp pose rotations. In (x, y, z, w) format
            locations (N, 3):                   The translation to the middle point between gripper tips.
            widths (N,):                        The predicted open width. Might want to increment a little as the PS dataset annotation tends to be tight
            kpts (N, 4, 2):                     The keypoint coordinates
            scores (N):                         The center confidence score by network
        """
        # first make sure the intrinsic matrix is initialized
        assert self.pnp_solver.assert_cam_intrinsic(), \
            "Please use the set_cam_intrinsic_mat API to provide KGN with the camera intrinsic matrix."

        # get information based on input mode
        if isinstance(input, np.ndarray):
            # then assumes input is RGB-D
            detector_input = input
            if self.opt.input_mod == "RGD":
                detector_input = detector_input[:, :, np.array([True, True, False, True])]
            elif self.opt.input_mod == "RGBD":
                detector_input = detector_input
            elif self.opt.input_mod == "RGB":
                detector_input = detector_input[:, :, :3]
            elif self.opt.input_mod == "D":
                detector_input = detector_input[:, :, 3:4]
            else:
                raise NotImplementedError

            depth_this = input[:,:,3]
        else:
            detector_input = input
            depth_this = input["depth"]
            depth_this = depth_this.cpu().detach().numpy().squeeze()
            

        # generate the keypoints
        if not self.opt.test_oracle_kpts:
            kpts, centers, widths_gen, scales, scores, confidences, detect_stats = self._generate_kpts(detector_input)
        else:
            kpts, centers, widths_gen = self._generate_kpts_gt(detector_input)
            scales = None
            scores = np.array([], dtype=np.float32)
            confidences = np.array([], dtype=np.float32)
            detect_stats = {
                "decoded_candidates": int(kpts.shape[0]),
                "score_filtered_candidates": int(kpts.shape[0]),
            }


        # generate the grasps
        N_grasps = kpts.shape[0]
        locations = []
        quaternions = []
        reproj_errors = []
        widths = []
        scores_keep = []
        kpts_keep = []
        centers_keep = []
        scales_keep = []
        analysis = {
            "decoded_candidates": int(detect_stats["decoded_candidates"]),
            "score_filtered_candidates": int(detect_stats["score_filtered_candidates"]),
            "pnp_attempted": 0,
            "pnp_failed": 0,
            "scale_refine_failed": 0,
            "reproj_filtered": 0,
            "accepted_candidates": 0,
            "accepted_scores": [],
            "accepted_confidences": [],
            "accepted_reprojection_errors": [],
            "accepted_scales": [],
        }

        for i in range(N_grasps):
            analysis["pnp_attempted"] += 1
            
            # first determine the 3d keypoint distances used in the pnp algorithm
            if self.opt.open_width_canonical is not None:
                proj_width = self.opt.open_width_canonical
            elif self.opt.min_open_width is not None:
                proj_width = widths_gen[i] if widths_gen[i] > self.opt.min_open_width \
                    else self.opt.min_open_width
            else:
                proj_width =  widths_gen[i]    

            if self.opt.scale_kpts_mode:
                # get scale
                scale = scales[i]
                # proj width
                proj_width = scale * widths_gen[i] * self.opt.scale_coeff_k
                # proj_width = 1
            
            self.pnp_solver.set_open_width(open_width=proj_width)

            # predict the poses
            try:
                location, quaternion, projected_points, reprojectionError = \
                    self.pnp_solver.solve_pnp(
                        kpts[i, :, :],
                        centers[i, :, :]
                    )
            except:
                location = None
                quaternion = None
            
            # skip if the grasp pose recovery failed
            if location is None or quaternion is None:
                analysis["pnp_failed"] += 1
                continue
        
            # if scale prediction mode
            if self.opt.sep_scale_branch:
                location = location / np.linalg.norm(location) * scales[i]

            # refine scale
            if self.opt.refine_scale:
                # fetch depth

                H, W = depth_this.shape
                center_this = centers[i].reshape(2)

                # refine based on depth
                quaternion, location, succ_refine = self.refine(quaternion, location, center_this, depth_this)
                if not succ_refine:
                    analysis["scale_refine_failed"] += 1
                    continue

            # filter based on reprojection error
            if self.opt.reproj_error_th is None or reprojectionError < self.opt.reproj_error_th:
                locations.append(location)
                quaternions.append(quaternion)
                widths.append(widths_gen[i])
                scores_keep.append(scores[i])
                kpts_keep.append(kpts[i, :, :])
                reproj_errors.append(reprojectionError)
                centers_keep.append(centers[i])
                if confidences.size > 0:
                    analysis["accepted_confidences"].append(confidences[i])
                if self.opt.scale_kpts_mode:
                    scales_keep.append(scale)
                    analysis["accepted_scales"].append(scale)
                analysis["accepted_scores"].append(scores[i])
                analysis["accepted_reprojection_errors"].append(reprojectionError)
            else:
                analysis["reproj_filtered"] += 1

        analysis["accepted_candidates"] = len(locations)
        
        if not return_all:
            return np.array(quaternions), np.array(locations), np.array(widths), np.stack(kpts_keep) if len(kpts_keep) > 0 else np.array([]), np.array(scores_keep)
        else:
            return np.array(quaternions), np.array(locations), np.array(widths),\
                np.stack(kpts_keep) if len(kpts_keep) > 0 else np.array([]), \
                np.array(scores_keep), \
                np.array(reproj_errors), np.array(centers_keep), analysis
                

    def _generate_kpts(self, input):
        ########## get the keypoint prediction
        ret = self.kpt_detector.run(input)

        ########## stack the results
        # only one class, so index zero. 
        # Get an array of (N_grasp, 13) results,
        # where the 13 = 2 (center coord) + 8 (kpts coord) + 1 (width) + 1 (score) + 1(ori_cls) + 1(scale)
        dets = np.array(ret["results"][1], dtype=np.float32)
        if dets.size == 0:
            empty_kpts = np.zeros((0, 4, 2), dtype=np.float32)
            empty_centers = np.zeros((0, 1, 2), dtype=np.float32)
            empty_scores = np.zeros((0,), dtype=np.float32)
            empty_confidences = np.zeros((0,), dtype=np.float32)
            empty_widths = np.zeros((0,), dtype=np.float32)
            detect_stats = {
                "decoded_candidates": 0,
                "score_filtered_candidates": 0,
            }
            if self.opt.sep_scale_branch:
                return empty_kpts, empty_centers, empty_widths, np.zeros((0,), dtype=np.float32), empty_scores, empty_confidences, detect_stats
            return empty_kpts, empty_centers, empty_widths, None, empty_scores, empty_confidences, detect_stats

        kpts_2d_pred = dets[:, 2:10].reshape(-1, 4, 2)
        centers_2d_pred = dets[:, :2].reshape(-1, 1, 2)
        widths_pred = dets[:, 10]
        raw_scores = dets[:, 11]
        next_col = 13
        if self.opt.sep_scale_branch:
            scales = dets[:, next_col]
            next_col += 1
        else:
            scales = None
        if self.opt.conf_branch and dets.shape[1] >= next_col + 2:
            confidences = dets[:, next_col]
            rank_scores = dets[:, next_col + 1]
        else:
            confidences = np.zeros((dets.shape[0],), dtype=np.float32)
            rank_scores = raw_scores

        # filter by scores
        scores = rank_scores
        score_mask = scores > self.opt.center_thresh
        kpts_2d_pred = kpts_2d_pred[score_mask]
        widths_pred = widths_pred[score_mask]
        centers_2d_pred = centers_2d_pred[score_mask]
        scores = scores[score_mask]
        confidences = confidences[score_mask]
        detect_stats = {
            "decoded_candidates": int(dets.shape[0]),
            "score_filtered_candidates": int(score_mask.sum()),
        }

        # the scales
        if self.opt.sep_scale_branch:
            scales = scales[score_mask]
            return kpts_2d_pred, centers_2d_pred, widths_pred, scales, scores, confidences, detect_stats
        else:
            return kpts_2d_pred, centers_2d_pred, widths_pred, None, scores, confidences, detect_stats


    def _generate_kpts_gt(self, input):
        """Generate GT keypoints
        It assumes that the input contains required information.
        """
        kpts_2d_gt = input["oracle_kpts_2d_noise"][0]
        centers_2d_gt = (kpts_2d_gt[:, 0:1, :] + kpts_2d_gt[:, 1:2, :]) / 2
        widths_gt = input["oracle_widths"][0]
        return kpts_2d_gt, centers_2d_gt, widths_gt

    def refine(self, quat, loc, center_pred, depth_map):
        """Refine a single grasp based on center prediction and depth map
        
        Args:
            quat (4, ):         quaternion of the grasp in camera frame
            loc (3, ):          location of the grasp in camera frame
            center_pred (2, ):  The predicted center of the grasp on image. (x, y) following OpenCV coord
            depth_matp (H, W):  The depth map
        Return:
            quat (4):           Refined quaternion
            loc (3,):           Refined location
            succ (bool):        Refinement is successful or not. If not, then the returned quaternion and location would be the same as before
                                Example failure case: The depth value at the center location is empty (0), which happens a lot in the real-world data
        """
        H, W = depth_map.shape

        # fetch the depth at the center
        center_pred = np.rint(center_pred).astype(int)
        center_pred[0] = center_pred[0] if center_pred[0] <= W-1 else W-1
        center_pred[1] = center_pred[1] if center_pred[1] <= H-1 else H-1
        depth_this = depth_map[center_pred[1], center_pred[0]]

        # corner case
        if depth_this == 0:
            return quat, loc, False

        # here we only refine location
        loc = loc / np.linalg.norm(loc) * depth_this

        return quat, loc, True
    

    @staticmethod
    def buildFromArgs(opt):
        """Create an KGN instance from arguments"""
        # detector
        Detector = detector_factory["grasp_pose"]
        detector = Detector(opt)

        # PnP Solver
        PNPSolver = PnPSolverFactory[opt.pnp_type] 
        pnp_solver = PNPSolver(
            kpt_type=opt.kpt_type,
            use_center=opt.use_center
        )

        # KGN
        kgn = KeypointGraspNet(opt, detector, pnp_solver)         

        return kgn
        
