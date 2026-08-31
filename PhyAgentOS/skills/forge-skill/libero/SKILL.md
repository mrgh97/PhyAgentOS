---
name: libero
description: Run a LIBERO benchmark with a profile-selected policy and reconcile the benchmark-owned result.
metadata: {"PhyAgentOS":{"always":false,"requires":{"runtime":["libero"]}}}
---

# Generic LIBERO Benchmark

This Skill orchestrates the live Tool endpoints. It does not drive the simulator,
infer episode success, or calculate benchmark scores.

For the `lingbot_va` profile the stable tools are:

- `libero.policy`: Session `policy.runner/serve`, holding the resident policy node.
- `libero.benchmark.describe`: Query `benchmark.controller/describe`.
- `libero.benchmark.run`: Session `benchmark.controller/run`.

## Required order

1. Read live context for all three tools and require them to be ready.
2. Start `libero.policy` once. Retain its invocation ID and confirm the Session is
   running. An accepted response is admission, not benchmark completion.
3. Query `libero.benchmark.describe`. Never guess task IDs, init-state IDs, defaults,
   or limits from memory.
4. Construct arguments from the user's request and the live capabilities. Start
   `libero.benchmark.run` once and retain its invocation ID.
5. Reconcile status and result until the benchmark Session reaches a terminal phase
   and its result is available. Do not treat acceptance or a progress event as final.
6. After the last batch, stop the policy Session. Stop the Skill runtime to terminate
   the node process and release GPU memory.

Use Session controls for both long-lived operations: `stop` is valid; `cancel` is
not. A benchmark stop is applied at an episode boundary and may return a partial
result.

## Safety and result ownership

- On `BENCH_NOT_READY`, wait and query live context/describe again. Do not modify the
  RuntimeManager.
- On `FORGE_ENDPOINT_BUSY` or Gateway HTTP 503 concurrency exhaustion, do not queue a
  second execution. Reconcile the active invocation.
- On transport loss or `unknown`, never blindly invoke the same evaluation again:
  GPU and result side effects may already exist. Reconcile status/result first.
- Do not decide episode success, recompute success rate, alter the score, or aggregate
  metrics across invocations. Those values are owned by `libero_benchmark`.

Report at least: terminal status, primary metric when present, success rate,
successes/total episodes when present, completed/total episodes, and result file.
For every episode report task ID, init-state ID, run index, episode seed, success,
termination, and `num_steps` when the result file exposes them.

`num_steps` is diagnostic only. Real LingBot-VA autorun self-consistency testing has
shown run-to-run nondeterminism in this field; it must not be used to decide whether
the Skill integration is equivalent. The benchmark-owned primary metric, episode
identity/seed, success, and termination remain the acceptance fields.
