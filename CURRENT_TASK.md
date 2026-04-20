# Current Task

Last updated: 2026-04-21

## Task

Run and recover the `d4ff8ca no-conf base` attribution experiment, while synchronizing the project documentation with the latest b1/e5 attribution results.

## Goal

Determine whether the strong `KGN-main internal kgnv2base` result comes from the broader KGN-main code path itself or from T2-specific confidence changes.

The current attribution question is:

- At `d4ff8ca`, with `--conf_branch`, `--conf_weight`, and `--conf_fusion` all disabled, does b1/e5 behave closer to official `paper2-clean` baseline or closer to `KGN-main internal kgnv2base`?

## In Scope

- Track the cloud `d4ff8ca no-conf base` b1/e5 training run.
- Record and recover the final training/test state.
- If no test was chained, run the no-conf model_best test later.
- Update documentation with the latest experiment attribution facts.
- Keep all b1/e5 results labeled as short-budget attribution, not final thesis-scale results.

## Out Of Scope

- No algorithm code changes.
- No training or testing.
- No cloud execution.
- No hook, MCP, skill, or Claude setup.
- No changes to `data/`, `exp/`, `pretrained_weights/`, or `KGN-Pro-main/`.
- No checkpoint, tarball, dataset, or log submission.

## Current Cloud State

- Cloud workspace: `/root/autodl-tmp/KGN-main`.
- Cloud branch: `diag-t2-d4ff8ca-base-ablation @ d4ff8ca`.
- Screen session: `37818.d4ff8ca_base (Detached)`.
- Running training exp_id: `diag_t2_d4ff8ca_base_no_conf_b1_single_r512_e5_val1_p20`.
- Expected test exp_id: `diag_t2_d4ff8ca_base_no_conf_b1_best_test_d02_a30`.
- Old stale T2 repeat training processes were killed; the intended remaining long job is the no-conf base training.

## Completion Criteria

- Cloud no-conf b1/e5 training completion is confirmed.
- `model_best.pth` is evaluated with no `--conf_branch` and no `--conf_fusion`.
- The resulting metrics are recorded against:
  - official `paper2-clean baseline`
  - `KGN-main internal kgnv2base`
  - `T2 cloud repeat`
  - `T2 local repeat`
- Documentation no longer says T3.1 is pending first cloud validation; it says T3.1 has recovery signal but is not verified effective.
- Documentation does not mislabel `KGN-main kgnv2base` as official baseline.

## After Completion

If no-conf base is weak, T2 evidence against the official clean baseline becomes stronger.
If no-conf base is strong, run a stricter `paper2-clean + T2-only` migration experiment before writing T2 as an independent single-variable gain.
