# Bugs And Risks

This file records known project risks and deferred issues. It is not a bug tracker
for every experiment failure; keep it focused on risks that future Codex/agent
sessions must not forget.

Last updated: 2026-04-21

## Current High-Risk Misstatements

- Do not say T3.1 is verified effective. It is implemented and shows recovery-style positive signal relative to `ctrl_t2off`, but it has not beaten the strong internal baseline.
- Do not call `KGN-main internal kgnv2base` the official `paper2-clean` baseline.
- Do not describe `paper2-clean baseline` vs `KGN-main T2` as a strict single-variable T2 ablation.
- Do not use the cloud T2 repeat `model_last.pth` as the final main thesis conclusion without noting it is a short-budget b1/e5 attribution checkpoint and may not have the cleanest training closure.
- Do not say KGN-Pro-main is a complete implementation of the KGN-Pro paper.
- Do not call smoke training an effectiveness result.
- Do not treat early P3 best, P4-lite-v2, or "fine-tune 3 epochs without pose_reg" as the latest verified mainline.
- Do not mix `model_best.pth` and `model_last.pth` as strict same-class evidence without explicitly saying which one was used.
- Do not write b1/e5 quick attribution numbers as final full-budget thesis results.

## Engineering Risks

### `opts.py --pnp_type` default mismatch

Observation:

- `opts.py` has a `--pnp_type` default that should be checked against available choices.

Current decision:

- Do not prioritize this before T3.1 verification unless it blocks a real command path.

### Trainer `save_result` decode signature risk

Observation:

- The trainer-side `save_result` path may still use an old `grasp_pose_decode(...)` calling pattern.
- Standard `src/test.py` evaluation uses the detector path and is the current main evaluation route.

Current decision:

- Do not prioritize this before T3.1 validation unless `main.py --test` or trainer-side result saving becomes necessary.

### Untracked `src/lib/third_party/__init__.py`

Observation:

- `src/lib/third_party/__init__.py` is currently an untracked empty file.

Current decision:

- Do not delete or submit it unless a dedicated small fix decides it is needed.

## Experiment Risks

- Different training budgets must not be mixed in one main comparison table.
- Different datasets must not be mixed in one main comparison table.
- Different inference parameters must not be mixed in one main comparison table.
- `b1/e5` is high-variance and should be treated as a fast attribution budget.
- `model_best.pth` and `model_last.pth` can differ materially and must be labeled separately.
- `paper2-clean baseline` and `KGN-main` do not share a bit-identical code path; candidate generation, detector/test flow, dataset reading fixes, and analysis hooks may differ even when `--conf_branch` is off.
- `conf_fusion` is P3 inference behavior. Turning it off tests P3-off/nofusion; it does not remove all P1/P2/T2-era code path differences.
- Smoke train/test only proves that the link runs; it does not prove algorithmic improvement.
- Cloud-generated `ps_grasp_multi_1k` data is not trusted and should not be used as the current formal data source.
- Current trusted cloud data is the local-uploaded `ps_grasp_single_1k`.
- Formal T3.1 validation still needs controlled training, testing, and result analysis against a strong baseline.

## Current Attribution Risks

- `paper2-clean baseline b1/e5` around `0.1013 / 0.0922 / 0.4920` is the official-clean fast baseline.
- `KGN-main internal kgnv2base b1/e5` around `0.1995 / 0.2240 / 0.7670` is a strong internal baseline whose source is still being attributed.
- `T2 cloud repeat model_last + P3 on` around `0.1837 / 0.1998 / 0.7530` supports that T2 is strong against official clean, but it is not yet the strictest single-variable proof.
- `T2 cloud repeat model_last + P3 off` around `0.1618 / 0.1483 / 0.6840` shows P3 helps this checkpoint, but nofusion still remains above paper2-clean.
- The current `d4ff8ca no-conf base` experiment is needed before deciding whether `paper2-clean + T2-only` migration is necessary.

## KGN-Pro-main Migration Risks

- `KGN-Pro-main` is reference-only.
- Do not submit `KGN-Pro-main/`.
- Do not migrate `KGN-Pro-main` as a whole.
- Do not directly copy these main-chain files into KGN-main:
  - `KGN-Pro-main/src/test.py`
  - `KGN-Pro-main/src/keypoint_graspnet.py`
  - `KGN-Pro-main/src/lib/pose_recover/`
  - `KGN-Pro-main/src/lib/trains/base_trainer.py`
- `KGN-Pro-main` training side contains useful EPro-PnP / MonteCarloPoseLoss / w2d ideas, but its test and inference chains remain largely KGNv2-style.

## File Safety Risks

- Never delete dirty worktree files without explicit user confirmation.
- Never run cleanup commands such as `rm -rf` unless explicitly requested and scoped.
- Never submit:
  - `data/`
  - `exp/`
  - `pretrained_weights/`
  - `KGN-Pro-main/`
  - `*.tar`
  - `*.tar.gz`
  - checkpoints
  - large logs
  - credentials
- Never compress the whole cloud `exp/grasp_pose/`; compress only one `<exp_id>` directory.

## Security Risks

- Do not record tokens, passwords, cookies, SSH private keys, Codex auth files, GitHub credentials, or full sensitive config files in project documentation.
- `/home/xyk/.codex` and `/root/.codex` are auth/history/config locations, not project files.
- The repository root `.codex` is currently an ignored zero-byte ordinary file and should not be treated as the Codex auth directory.
