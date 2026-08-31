# Generic LIBERO Skill

This source bundle turns LIBERO into a policy-selectable PAOS Skill. The first
profile, `lingbot_va`, reuses the official LIBERO benchmark node and the existing
`lerobot_runner` LingBot-VA adapter; inference code and model weights are not copied
into the Skill.

```text
PAOS Agent
  -> Gateway
     -> benchmark.controller/describe (Query) -> libero_benchmark
     -> benchmark.controller/run (Session)    -> libero_benchmark
     -> policy.runner/serve (Session)          -> lerobot_runner

libero_benchmark -- proprio/image/policy_command --> lerobot_runner
libero_benchmark <-- JointCommand action --------- lerobot_runner
```

`bench_endpoint` is intentionally not part of this profile. LIBERO benchmark 1.0.0
contains the canonical Query/Session endpoint in the same process as the simulator.

## Versions and source runtime

The checked-in local locks describe reproducible source launchers used for developer
validation:

- Gateway 1.1.0 (Session-capable)
- LIBERO benchmark 1.0.0 (`benchmark.controller`)
- lerobot-inference 1.0.2 plus the `policy.runner` Session integration
- dora-rs 0.4.1

The profile depends on PAOS Runtime support for profile `startup_timeout_s` (validated
with runtime commit `aa3d6a6`). This is an existing runtime feature; the Skill does
not patch PAOS or Forge core. Formal registry publishing should replace the local
source locks with independently released Node artifacts without changing the graph.

Set the source runtime variables before starting:

```bash
export FORGE_GATEWAY_ROOT=/path/to/forge_gateway
export FORGE_GATEWAY_PYTHON=/path/to/gateway-python
export LIBERO_BENCHMARK_ROOT=/path/to/benchmark/libero
export LIBERO_BENCHMARK_PYTHON=/path/to/libero-python
export LEROBOT_RUNNER_PYTHON=/path/to/lerobot-runner-python
```

Install the three deterministic local source launchers once (cache hits are
idempotent and never overwrite a different artifact):

```bash
python scripts/install_source_nodes.py
```

The LIBERO Python environment must provide LIBERO, robosuite, MuJoCo, EGL/OpenGL,
dora-rs 0.4.1, forge-msgs 1.2.0, forge-tool 1.0.0, and NumPy 1.26.4 (NumPy 2.5 is
incompatible with the current Numba/LIBERO stack). The policy environment must
provide the pinned `lerobot-inference` dependencies and an NVIDIA GPU suitable for
LingBot-VA. Set `CUDA_VISIBLE_DEVICES` before `paos skill start` when selecting a GPU.

## LingBot-VA models

Models larger than 1GB are external prerequisites and are never placed in the Skill
or Node archives. Download the two official Hugging Face repositories at fixed
revisions:

```bash
python scripts/download_lingbot_va.py --model-root "$HOME/.cache/phyagentos/models/lingbot-va"
```

The downloader uses Hugging Face cache metadata, resumes interrupted downloads, and
reuses complete local files. For a network-free cache check use
`--local-files-only`. Then export the printed paths:

```bash
export LINGBOT_VA_MODEL_DIR=/path/to/lingbot_va_libero_long
export LINGBOT_VA_BASE_DIR=/path/to/lingbot_va_base_frozen
```

Sources are `lerobot/lingbot_va_libero_long` at
`73e0be23b134a7c4dfc2d82f6ff27ba0bfdc0932` and `robbyant/lingbot-va-base`
at `68b7bc1b35da6ddc67ea94c4ceb58d768fbb3f9c`. Existing TOS copies are retained as
handoff backups only; installation and startup do not depend on TOS.

## Use

Install or stage the bundle and verify discovery:

```bash
paos skill list
paos skill inspect libero
paos skill start libero --profile lingbot_va
paos skill status libero
```

Through the PAOS Agent/Tool bridge, first query `libero.benchmark.describe`, then
start `libero.policy`, then start `libero.benchmark.run`. A minimal two-episode plan
is:

```json
{
  "task_ids": [0, 1],
  "init_state_ids": [0],
  "num_runs": 1,
  "seed": 0
}
```

The profile freezes `suite=libero_10`, `control_mode=relative`,
`layout_mode=per_episode`, and `num_steps_wait=10`. The benchmark owns success,
success rate, termination, and the result file. `num_steps` is diagnostic because
real LingBot-VA runs have demonstrated run-to-run variation.

After the last invocation:

```bash
paos skill stop libero
```

## Troubleshooting

- `BENCH_NOT_READY`: initialization is still in progress; wait and query describe
  again. The 900-second profile startup budget covers model and simulator loading.
- HTTP 503 or `FORGE_ENDPOINT_BUSY`: an invocation already occupies the endpoint;
  do not queue or duplicate it. Reconcile its status/result.
- `unknown`: the outcome is ambiguous and may already have GPU/result side effects;
  never rerun blindly.
- model path errors: rerun the downloader with `--local-files-only --verify-only`
  and export both resolved directories.
