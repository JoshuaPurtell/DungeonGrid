# Lantern Lite Communication Premium/Penalty

Observed: 2026-04-26

## Question

Does enabling communication improve GPT-4.1-mini performance on Lantern Lite?

We define:

```text
communication premium/penalty = communication condition - no-communication condition
```

Positive deltas are a communication premium. Negative deltas are a communication penalty.

## Eval Setup

- Runner: NanoCoop `starter-agent`
- Model: `gpt-4.1-mini`
- Backend: DungeonGrid through NanoCoop's `DungeonGridReActPolicy`
- Quest/layout: `lantern_crypt_lite`
- Heroes: 2
- Warden: deterministic/scripted Warden
- Seeds: 1-10
- Max steps: 200
- Episodes: 10 with communication, 10 without communication
- Parallelism: `--workers 10` per condition, both conditions launched concurrently
- Timeout metadata: `NANOCOOP_TIMEOUT_SECONDS=0`

Communication condition:

```yaml
env:
  communication_protocol:
    mode: pure_decentralized
```

No-communication condition:

```yaml
env:
  communication_protocol:
    mode: no_message
```

Temporary run artifacts from this local run:

- `/tmp/nanocoop_lantern_lite_comm_10x200`
- `/tmp/nanocoop_lantern_lite_no_comm_10x200`

## Aggregate Results

| condition | success | mean reward | median reward | mean steps | delivered messages |
|---|---:|---:|---:|---:|---:|
| communication | 4/10 = 40% | 6.6420 | 5.3250 | 147.2 | 342 |
| no communication | 8/10 = 80% | 8.3455 | 9.0050 | 127.6 | 0 |

Communication premium/penalty:

```text
mean score delta:    -1.7035
median score delta:  -1.9700
success-rate delta:  -0.4000
success-count delta: -4 / 10
```

At 200 steps, this run shows a substantial communication penalty.

## Paired Seed Results

| seed | comm reward | no-comm reward | score delta | comm success | no-comm success | success delta | comm msgs |
|---:|---:|---:|---:|---|---|---:|---:|
| 1 | 8.065 | 7.435 | +0.630 | true | true | 0 | 18 |
| 2 | 9.045 | 9.200 | -0.155 | true | true | 0 | 24 |
| 3 | 5.175 | 9.280 | -4.105 | false | true | -1 | 37 |
| 4 | 5.355 | 9.610 | -4.255 | false | true | -1 | 73 |
| 5 | 8.990 | 9.505 | -0.515 | true | true | 0 | 29 |
| 6 | 5.295 | 8.720 | -3.425 | false | true | -1 | 18 |
| 7 | 9.635 | 6.285 | +3.350 | true | false | +1 | 7 |
| 8 | 5.015 | 5.165 | -0.150 | false | false | 0 | 34 |
| 9 | 4.915 | 9.445 | -4.530 | false | true | -1 | 64 |
| 10 | 4.930 | 8.810 | -3.880 | false | true | -1 | 38 |

## Secondary Metrics

| metric | communication | no communication |
|---|---:|---:|
| mean achievement count | 13.9 | 15.6 |
| mean quest achievement count | 4.2 | 5.3 |
| mean invalid actions | 13.1 | 24.7 |
| mean survival | 0.3 | 0.9 |
| mean LLM calls | 176.5 | 194.9 |

Communication reduced invalid actions, but no-communication completed more often and had much higher survival.

## Interpretation

The 80-step, 5-seed probe showed a small positive communication premium, but the larger 200-step, 10-seed run flips into a penalty. The likely failure mode is over-communication: the communication prompt successfully produced many messages, but messages cost AP, and the agents appear to lose tempo and survival in longer runs.

The current result should be read as a prompt/protocol interaction, not proof that communication is intrinsically bad. Better follow-up probes:

- cap or budget message use;
- reward only timely, causally useful messages;
- compare free/zero-AP messages against AP-cost messages;
- test a prompt that says "message only after new information or before handoff/extraction";
- inspect failed communication transcripts for message loops or delayed objective/extraction actions.

## GPT-4.1-nano Comparison

After the GPT-4.1-mini run, the same 10-seed, 200-step protocol was run with `gpt-4.1-nano`.

Temporary run artifacts from this local run:

- `/tmp/nanocoop_lantern_lite_gpt41_nano_comm_10x200`
- `/tmp/nanocoop_lantern_lite_gpt41_nano_no_comm_10x200`

Aggregate results:

| condition | success | mean reward | median reward | mean steps | delivered messages | rejected messages |
|---|---:|---:|---:|---:|---:|---:|
| communication | 0/10 = 0% | 1.8450 | 1.2850 | 186.3 | 60 | 0 |
| no communication | 0/10 = 0% | 3.0215 | 2.7550 | 163.3 | 0 | 53 |

Estimated API cost using GPT-4.1-nano pricing (`$0.10/1M` input, `$0.025/1M` cached input, `$0.40/1M` output):

| condition | non-cached input | cached input | output | estimated cost |
|---|---:|---:|---:|---:|
| communication | 8.91M | 10.03M | 0.13M | $1.19 |
| no communication | 6.14M | 6.35M | 0.09M | $0.81 |
| total | 15.05M | 16.38M | 0.22M | $2.00 |

Communication premium/penalty:

```text
mean score delta:    -1.1765
median score delta:  -1.2675
success-rate delta:   0.0000
success-count delta:  0 / 10
```

Paired seed results:

| seed | comm reward | no-comm reward | score delta | comm success | no-comm success | success delta | comm msgs | no-comm rejected msgs |
|---:|---:|---:|---:|---|---|---:|---:|---:|
| 1 | 2.865 | 4.605 | -1.740 | false | false | 0 | 11 | 0 |
| 2 | 2.990 | 2.705 | +0.285 | false | false | 0 | 5 | 0 |
| 3 | 2.865 | 3.995 | -1.130 | false | false | 0 | 15 | 0 |
| 4 | 2.740 | 4.130 | -1.390 | false | false | 0 | 19 | 0 |
| 5 | 1.050 | 4.440 | -3.390 | false | false | 0 | 0 | 0 |
| 6 | 1.160 | 1.300 | -0.140 | false | false | 0 | 2 | 0 |
| 7 | 1.050 | 2.630 | -1.580 | false | false | 0 | 0 | 0 |
| 8 | 1.160 | 1.050 | +0.110 | false | false | 0 | 2 | 53 |
| 9 | 1.160 | 2.805 | -1.645 | false | false | 0 | 2 | 0 |
| 10 | 1.410 | 2.555 | -1.145 | false | false | 0 | 4 | 0 |

Secondary metrics:

| metric | communication | no communication |
|---|---:|---:|
| mean achievement count | 4.4 | 5.3 |
| mean quest achievement count | 1.2 | 1.4 |
| mean invalid actions | 129.8 | 68.0 |
| mean survival | 0.8 | 0.4 |
| mean LLM calls | 325.5 | 231.8 |

The nano run did not produce any successes in either condition. The main finding is model capability rather than communication efficacy: `gpt-4.1-nano` appears below the Lantern Lite task threshold with this ReAct harness. Communication still shows a reward penalty, and the no-communication condition revealed a prompt/protocol mismatch: nano attempted 53 messages despite being instructed not to, and the protocol rejected them.

## GPT-5.4-nano Comparison

The same 200-step protocol was run with `gpt-5.4-nano`, using 20 seeds per condition.

Temporary run artifacts from this local run:

- `/tmp/nanocoop_lantern_lite_gpt54_nano_comm_20x200`
- `/tmp/nanocoop_lantern_lite_gpt54_nano_no_comm_20x200`

Aggregate results:

| condition | success | mean reward | median reward | mean steps | delivered messages | rejected messages |
|---|---:|---:|---:|---:|---:|---:|
| communication | 2/20 = 10% | 5.2343 | 4.9100 | 179.15 | 2393 | 0 |
| no communication | 12/20 = 60% | 7.3980 | 7.4300 | 137.70 | 0 | 0 |

Estimated API cost using GPT-5.4-nano pricing (`$0.20/1M` input, `$0.02/1M` cached input, `$1.25/1M` output):

| condition | non-cached input | cached input | output | estimated cost |
|---|---:|---:|---:|---:|
| communication | 22.55M | 18.33M | 0.64M | $5.68 |
| no communication | 11.98M | 14.67M | 0.35M | $3.13 |
| total | 34.53M | 33.00M | 1.00M | $8.81 |

Communication premium/penalty:

```text
mean score delta:    -2.1637
median score delta:  -2.3000
success-rate delta:  -0.5000
success-count delta: -10 / 20
```

Paired seed results:

| seed | comm reward | no-comm reward | score delta | comm success | no-comm success | success delta | comm msgs |
|---:|---:|---:|---:|---|---|---:|---:|
| 1 | 6.270 | 9.970 | -3.700 | false | true | -1 | 147 |
| 2 | 4.410 | 9.950 | -5.540 | false | true | -1 | 128 |
| 3 | 3.190 | 4.205 | -1.015 | false | false | 0 | 119 |
| 4 | 5.985 | 9.900 | -3.915 | false | true | -1 | 108 |
| 5 | 6.085 | 9.370 | -3.285 | false | true | -1 | 144 |
| 6 | 4.475 | 8.620 | -4.145 | false | true | -1 | 145 |
| 7 | 5.025 | 5.585 | -0.560 | false | false | 0 | 67 |
| 8 | 4.795 | 4.305 | +0.490 | false | false | 0 | 128 |
| 9 | 5.530 | 9.240 | -3.710 | false | true | -1 | 148 |
| 10 | 5.755 | 6.970 | -1.215 | false | false | 0 | 76 |
| 11 | 4.550 | 5.605 | -1.055 | false | false | 0 | 86 |
| 12 | 5.065 | 5.855 | -0.790 | false | false | 0 | 145 |
| 13 | 7.580 | 7.300 | +0.280 | true | true | 0 | 140 |
| 14 | 4.165 | 8.065 | -3.900 | false | true | -1 | 93 |
| 15 | 4.205 | 6.155 | -1.950 | false | false | 0 | 123 |
| 16 | 4.240 | 8.015 | -3.775 | false | true | -1 | 113 |
| 17 | 4.570 | 7.435 | -2.865 | false | true | -1 | 65 |
| 18 | 6.360 | 6.385 | -0.025 | false | false | 0 | 146 |
| 19 | 7.655 | 7.605 | +0.050 | true | true | 0 | 129 |
| 20 | 4.775 | 7.425 | -2.650 | false | true | -1 | 143 |

Secondary metrics:

| metric | communication | no communication |
|---|---:|---:|
| mean achievement count | 12.4 | 14.45 |
| mean quest achievement count | 4.6 | 5.1 |
| mean invalid actions | 24.15 | 30.1 |
| mean survival | 0.5 | 0.825 |
| mean LLM calls | 297.85 | 253.75 |

GPT-5.4-nano is above GPT-4.1-nano on this task, but the communication condition is strongly worse than no-communication under the current prompt/protocol. The most visible issue is extreme over-messaging: 2393 delivered messages across 20 communication episodes, about 120 delivered messages per episode. This likely dominates AP tempo and explains the lower survival and lower completion rate despite slightly fewer invalid actions.

## GPT-4.1-nano No-Communication Cost Probe

To diagnose experiment cost and wall-clock time, a fresh 5-seed GPT-4.1-nano no-communication probe was run with the same 200-step Lantern Lite setup.

Temporary run artifact:

- `/tmp/nanocoop_lantern_lite_gpt41_nano_no_comm_5x200_cost_probe`

Pricing used:

- non-cached input: `$0.10 / 1M`
- cached input: `$0.025 / 1M`
- output: `$0.40 / 1M`

Per-episode cost:

| seed | success | reward | steps | LLM calls | non-cached input | cached input | output | cost |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 101 | false | 4.125 | 186 | 259 | 760,447 | 660,608 | 11,380 | $0.0971 |
| 102 | false | 2.880 | 130 | 170 | 559,842 | 348,160 | 6,312 | $0.0672 |
| 103 | false | 3.080 | 200 | 236 | 624,690 | 617,856 | 12,474 | $0.0829 |
| 104 | false | 3.105 | 193 | 278 | 739,995 | 692,480 | 11,517 | $0.0959 |
| 105 | false | 2.630 | 134 | 197 | 688,601 | 415,872 | 6,460 | $0.0818 |

Totals:

| non-cached input | cached input | output | cost |
|---:|---:|---:|---:|
| 3.37M | 2.73M | 48.1K | $0.4249 |

Summary:

- mean cost per episode: `$0.0850`
- median cost per episode: `$0.0829`
- mean LLM calls per episode: `228.0`
- mean env steps per episode: `168.6`

All five probe episodes failed. Cost and wall-clock time are dominated by long failed rollouts with many model calls. Immediate harness levers to test:

- reduce `max_steps` or add early-stop conditions when repeated invalid actions/low progress indicate a stuck rollout;
- lower `max_tool_rounds` from 6 for nano-scale models;
- reduce `max_tokens` from 768 when using GPT-4.1-nano;
- simplify the system prompt/rules bundle, especially repeated compact rules;
- make no-communication configs remove message actions from legal candidates instead of relying only on prompt/protocol rejection.

## GPT-4.1-nano No-Communication Prompt/Context Iteration

After adding private notes, message-history search, rules-on-demand prompt text, safer partial-plan continuation through empty reveals, and anti-frivolous-tool-call prompting, the same 5-seed no-communication probe was rerun.

Temporary run artifacts:

- `/tmp/react_dungeongrid_gpt41_nano_lantern_lite_no_comm_5x200_after_prompt.yaml`
- `/tmp/nanocoop_lantern_lite_gpt41_nano_no_comm_5x200_after_prompt`

Aggregate comparison:

| condition | success | mean reward | median reward | mean steps | mean LLM calls | non-cached input | cached input | output | estimated cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline 5-seed probe | 0/5 | 3.164 | 3.080 | 168.6 | 228.0 | 3.37M | 2.73M | 48.1K | $0.4250 |
| prompt/context iteration | 0/5 | 2.431 | 2.555 | 162.4 | 249.6 | 3.37M | 1.98M | 36.2K | $0.4006 |

Per-seed comparison:

| seed | baseline reward | new reward | baseline calls | new calls | baseline cost | new cost |
|---:|---:|---:|---:|---:|---:|---:|
| 101 | 4.125 | 1.060 | 259 | 290 | $0.0971 | $0.0864 |
| 102 | 2.880 | 3.745 | 170 | 356 | $0.0672 | $0.1156 |
| 103 | 3.080 | 3.745 | 236 | 181 | $0.0829 | $0.0641 |
| 104 | 3.105 | 2.555 | 278 | 138 | $0.0959 | $0.0519 |
| 105 | 2.630 | 1.050 | 197 | 283 | $0.0818 | $0.0826 |

Tool-use observations:

- Private memory calls fell from 352 `private_plan` calls to 206 `private_notes` calls.
- The new message-history search tool was called 43 times despite no communication being enabled.
- Estimated cost fell by about 5.7%, mostly from lower cached input and lower output tokens.
- Non-cached input was essentially flat, while LLM calls rose about 9.5%.
- Reward decreased on this small sample, so this iteration is not clearly better yet.

Interpretation:

The rules-on-demand/private-notes direction reduced some repeated context and output, but adding message-history search created a new tool-call attractor in a no-communication condition. The next likely cost win is condition-aware tool gating: disable message-history search and message actions entirely when `communication_protocol.mode: no_message`, then rerun this same 5-seed probe.

## GPT-4.1-nano No-Communication Compact Observation Iteration

After compressing observation rendering for equipment, party roster, visible teammates, adjacent tiles, visible entities, visible objects, and visible rooms, the same 5-seed no-communication probe was rerun.

Temporary run artifacts:

- `/tmp/react_dungeongrid_gpt41_nano_lantern_lite_no_comm_5x200_compact_obs.yaml`
- `/tmp/nanocoop_lantern_lite_gpt41_nano_no_comm_5x200_compact_obs`

Aggregate comparison:

| condition | success | mean reward | median reward | mean steps | mean LLM calls | non-cached input | cached input | output | estimated cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline 5-seed probe | 0/5 | 3.164 | 3.080 | 168.6 | 228.0 | 3.37M | 2.73M | 48.1K | $0.4250 |
| prompt/context iteration | 0/5 | 2.431 | 2.555 | 162.4 | 249.6 | 3.37M | 1.98M | 36.2K | $0.4006 |
| compact observation iteration | 0/5 | 3.801 | 4.140 | 182.8 | 250.4 | 2.35M | 1.94M | 37.5K | $0.2981 |

Per-seed comparison:

| seed | baseline reward | prompt/context reward | compact obs reward | baseline cost | prompt/context cost | compact obs cost |
|---:|---:|---:|---:|---:|---:|---:|
| 101 | 4.125 | 1.060 | 4.455 | $0.0971 | $0.0864 | $0.0507 |
| 102 | 2.880 | 3.745 | 5.130 | $0.0672 | $0.1156 | $0.0786 |
| 103 | 3.080 | 3.745 | 4.140 | $0.0829 | $0.0641 | $0.0619 |
| 104 | 3.105 | 2.555 | 2.665 | $0.0959 | $0.0519 | $0.0579 |
| 105 | 2.630 | 1.050 | 2.615 | $0.0818 | $0.0826 | $0.0490 |

Tool-use observations:

- Private memory calls fell again, from 352 baseline / 206 prompt-context to 133 compact-observation calls.
- Message-history search still fired 48 times in `no_message`, confirming that condition-aware tool gating remains important.
- Non-cached input dropped about 30.5% versus baseline.
- Estimated cost dropped about 29.9% versus baseline.
- Reward improved versus both prior 5-seed probes, though all five episodes still failed completion.

Interpretation:

Compact current-state rendering is a clear win on this small probe: it improved score while materially lowering non-cached input and cost. The next cleanup should remove the message-history search tool and message action surface in no-communication runs; that should reduce unnecessary tool calls without weakening the compact observation format.

## GPT-4.1-nano No-Communication Cache-Ordered Prompt Iteration

After reordering the observation prompt into stable-to-volatile sections (`quest_reference`, `party_reference`, `current_turn`, `local_board`, `recent_context`) and moving action/plan-safety boilerplate into the system action basics, the same 5-seed no-communication probe was rerun.

Temporary run artifacts:

- `/tmp/react_dungeongrid_gpt41_nano_lantern_lite_no_comm_5x200_cache_order.yaml`
- `/tmp/nanocoop_lantern_lite_gpt41_nano_no_comm_5x200_cache_order`

Aggregate comparison:

| condition | success | mean reward | median reward | mean steps | mean LLM calls | non-cached input | cached input | output | estimated cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline 5-seed probe | 0/5 | 3.164 | 3.080 | 168.6 | 228.0 | 3.37M | 2.73M | 48.1K | $0.4250 |
| compact observation iteration | 0/5 | 3.801 | 4.140 | 182.8 | 250.4 | 2.35M | 1.94M | 37.5K | $0.2981 |
| cache-ordered prompt iteration | 0/5 | 4.093 | 4.130 | 171.2 | 400.6 | 3.65M | 3.27M | 57.5K | $0.4695 |

Per-seed comparison:

| seed | compact obs reward | cache-order reward | compact obs calls | cache-order calls | compact obs cost | cache-order cost |
|---:|---:|---:|---:|---:|---:|---:|
| 101 | 4.455 | 5.245 | 186 | 338 | $0.0507 | $0.0861 |
| 102 | 5.130 | 4.080 | 308 | 290 | $0.0786 | $0.0676 |
| 103 | 4.140 | 2.805 | 262 | 470 | $0.0619 | $0.1019 |
| 104 | 2.665 | 4.130 | 270 | 429 | $0.0579 | $0.0987 |
| 105 | 2.615 | 4.205 | 226 | 476 | $0.0490 | $0.1152 |

Tool-use observations:

- Message-history search rose from 48 compact-observation calls to 167 cache-order calls.
- Private notes rose from 133 compact-observation calls to 599 cache-order calls.
- Mean LLM calls rose from 250.4 to 400.6.
- Estimated cost rose from `$0.2981` to `$0.4695`, worse than the original baseline.
- Reward improved slightly versus compact observation, but the token/cost regression is too large for this to be a good cost optimization.

Interpretation:

Stable-to-volatile reordering alone did not produce better cache economics in this ReAct harness. The sectioned prompt appears to have encouraged more non-action tool use, especially message history and private notes. The compact-observation format remains the best current cost/performance point. The next iteration should prioritize condition-aware tool gating before further cache-prefix ordering experiments.

## GPT-4.1-nano No-Communication Tool-Policy Iteration

After adding a stricter tool-use policy and hiding `dungeongrid_message_history_search` when `communication_protocol.mode: no_message`, the same 5-seed no-communication probe was rerun.

Temporary run artifacts:

- `/tmp/react_dungeongrid_gpt41_nano_lantern_lite_no_comm_5x200_tool_policy.yaml`
- `/tmp/nanocoop_lantern_lite_gpt41_nano_no_comm_5x200_tool_policy`

Aggregate comparison:

| condition | success | mean reward | median reward | mean steps | mean LLM calls | non-cached input | cached input | output | estimated cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| compact observation iteration | 0/5 | 3.801 | 4.140 | 182.8 | 250.4 | 2.35M | 1.94M | 37.5K | $0.2981 |
| cache-ordered prompt iteration | 0/5 | 4.093 | 4.130 | 171.2 | 400.6 | 3.65M | 3.27M | 57.5K | $0.4695 |
| strict tool-policy iteration | 0/5 | 1.100 | 1.050 | 200.0 | 181.4 | 1.24M | 1.49M | 25.7K | $0.1720 |

Per-seed comparison:

| seed | cache-order reward | tool-policy reward | cache-order calls | tool-policy calls | cache-order cost | tool-policy cost |
|---:|---:|---:|---:|---:|---:|---:|
| 101 | 5.245 | 1.050 | 338 | 180 | $0.0861 | $0.0328 |
| 102 | 4.080 | 1.300 | 290 | 177 | $0.0676 | $0.0345 |
| 103 | 2.805 | 1.050 | 470 | 180 | $0.1019 | $0.0337 |
| 104 | 4.130 | 1.050 | 429 | 184 | $0.0987 | $0.0356 |
| 105 | 4.205 | 1.050 | 476 | 186 | $0.1152 | $0.0354 |

Tool-use observations:

- Message-history search fell from 167 cache-order calls to 0.
- Private notes fell from 599 cache-order calls to 16.
- Mean LLM calls fell from 400.6 to 181.4.
- Estimated cost fell to `$0.1720`, the cheapest run so far.
- Reward collapsed to `1.100`, indicating the prompt/tool policy overcorrected and likely suppressed useful deliberation or planning.

Interpretation:

Hard tool gating works mechanically, but the strict prompt made the nano policy too inert. The useful direction is not "almost no tools"; it is condition-aware tools plus a softer policy that still permits rules/notes when they improve route/objective progress. The best current operating point remains compact observation, not cache-order plus strict tool policy.

### Revert confirmation

The strict tool-policy/gating code was reverted and the same 5-seed probe was rerun to confirm reward behavior recovered.

Temporary run artifacts:

- `/tmp/react_dungeongrid_gpt41_nano_lantern_lite_no_comm_5x200_revert_confirm.yaml`
- `/tmp/nanocoop_lantern_lite_gpt41_nano_no_comm_5x200_revert_confirm`

| condition | success | mean reward | median reward | mean steps | mean LLM calls | message-history calls | private-note calls | estimated cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| strict tool-policy iteration | 0/5 | 1.100 | 1.050 | 200.0 | 181.4 | 0 | 16 | $0.1720 |
| revert confirmation | 0/5 | 3.630 | 3.800 | 180.6 | 436.0 | 133 | 581 | $0.5127 |

The revert restored reward to the expected range, confirming the strict tool-policy patch caused the collapse. It also restored high tool/cost behavior, so the safer next path is not to reintroduce the strict policy; instead, tune tool schemas/availability in a narrower way or return to the compact-observation checkpoint.
