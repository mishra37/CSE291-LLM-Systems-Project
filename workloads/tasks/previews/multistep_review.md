# Two multistep task previews

These are examples for discussion, not the full 40-task collection. All data is
fictional. No model responses have been generated and no agent tool runtime has
been integrated. `multistep.jsonl` stores the proposed inputs, tool fixtures,
step instructions, and evaluator-only answers.

The runner will prescribe the tool order. The model must interpret each result
and produce its own responses. These are scripted agent workflows, not autonomous
tool selection. Intermediate model replies remain in the conversation alongside
all earlier tool results. Each result is revealed only after its tool finishes.

For illustration, each tool has an added two-second delay. Delay is an experiment
setting, not part of the correct answer. Each model call has a maximum of 128
output tokens, temperature 0, and natural EOS stopping. Actual outputs, latency,
and tokenizer/context-fit checks remain to be measured.

| Task | Model calls | Tool calls | Added tool time | Final check |
|---|---:|---:|---:|---|
| [Regional net sales](#multistep-preview-sales-001) | 5 | 4 | 8 seconds | Integer arithmetic and region identity |
| [Follow a recorded error chain](#multistep-preview-logs-001) | 3 | 2 | 4 seconds | Trace IDs and explicit causal links |

## multistep-preview-sales-001

**User task:**

> For October 2026, find the combined net sales for North, South, West, and East.
> Net sales equal gross sales minus refunds. Identify the region with the highest
> net sales and its net amount. All amounts are whole US dollars. Return only a
> JSON object with `total_net_sales_usd`, `largest_region`, and
> `largest_region_net_sales_usd`.

### Model call 1

The model receives the task and is asked to briefly state the calculation and
which regional inputs are still needed. No sales figures are available yet.

**Tool call 1:** `get_region_sales(region="North", period="2026-10")`

After a two-second delay, the tool returns:

```json
{"region":"North","period":"2026-10","gross_sales_usd":150,"refunds_usd":30}
```

### Model call 2

The model receives North's result and is asked to update the running net total
and list the regions still missing. It must not give a final answer yet.

**Tool call 2:** `get_region_sales(region="South", period="2026-10")`

```json
{"region":"South","period":"2026-10","gross_sales_usd":200,"refunds_usd":20}
```

### Model call 3

The model receives South's result and updates its running total and current
highest-net-sales region, retaining North's earlier result.

**Tool call 3:** `get_region_sales(region="West", period="2026-10")`

```json
{"region":"West","period":"2026-10","gross_sales_usd":175,"refunds_usd":25}
```

### Model call 4

The model receives West's result, updates its running calculation, and notes
that East's figures are still missing.

**Tool call 4:** `get_region_sales(region="East", period="2026-10")`

```json
{"region":"East","period":"2026-10","gross_sales_usd":100,"refunds_usd":10}
```

### Model call 5

The model receives East's result and produces its final JSON using all four tool
results. The expected answer below is for the evaluator, not part of the prompt:

```json
{"total_net_sales_usd":540,"largest_region":"South","largest_region_net_sales_usd":180}
```

The independently calculated regional net amounts are North 120, South 180,
West 150, and East 90. Their sum is 540. South is the unique maximum.

**Completion:** all five model calls and four successful tool calls finish with
valid terminal responses and no context truncation. A wrong intermediate
calculation does not cancel the remaining scheduled steps; record it separately.

**Correctness:** parse the final JSON and compare the three required fields.
Object key order and whitespace do not matter. Dollar amounts must be JSON
integers, and the region must be `South`. Invalid JSON, extra fields, wrong
amounts, or a different region fail the strict final-answer check. Report the
number of correct required fields separately as diagnostic partial credit.

## multistep-preview-logs-001

**User task:**

> Investigate request `req-742`, starting at gateway event `E-201`. Follow each
> `cause_event_id` until an event has no recorded cause. Report that originating
> event's component and error code, plus the ordered event-ID chain from the
> gateway to the origin. Ignore events from other requests. Return only a JSON
> object with `origin_component`, `origin_error_code`, and `event_chain`.

This task asks for the origin of an explicitly recorded chain. It does not ask
the model to infer the deeper real-world cause of a database problem from timestamps.

### Model call 1

The model receives the task and states what trace information is needed. No log
events are available yet.

**Tool call 1:** `read_log_bundle(bundle="application", request_id="req-742")`

This tool returns the relevant bundle including neighboring events. The model
must filter by request ID. After a two-second delay it returns:

```json
{"bundle":"application","events":[
  {"event_id":"E-201","request_id":"req-742","component":"gateway","error_code":"UPSTREAM_FAILURE","cause_event_id":"E-202"},
  {"event_id":"E-202","request_id":"req-742","component":"checkout","error_code":"DB_REQUEST_FAILED","cause_event_id":"D-301"},
  {"event_id":"E-203","request_id":"req-915","component":"gateway","error_code":"NOT_FOUND","cause_event_id":null}
]}
```

### Model call 2

The model receives those events and identifies which cause is still unresolved.
`E-201` points to `E-202`, which points to `D-301`. The contents of `D-301` are
not available yet.

**Tool call 2:** `read_log_bundle(bundle="database", request_id="req-742")`

```json
{"bundle":"database","events":[
  {"event_id":"D-302","request_id":"req-888","component":"database","error_code":"SYNTAX_ERROR","cause_event_id":null},
  {"event_id":"D-301","request_id":"req-742","component":"database","error_code":"POOL_EXHAUSTED","cause_event_id":null}
]}
```

### Model call 3

The model combines both bundles, follows the explicit links for `req-742`, and
returns its final JSON. Evaluator-only expected answer:

```json
{"origin_component":"database","origin_error_code":"POOL_EXHAUSTED","event_chain":["E-201","E-202","D-301"]}
```

**Completion:** all three model calls and two successful tool calls finish with
valid terminal responses and no context truncation.

**Correctness:** parse the JSON and compare the three required fields. The event
chain must be in the requested gateway-to-origin order. Merely selecting the
database component, the first error displayed, or an unrelated request's error
does not pass. Invalid JSON or extra fields also fail the strict check. Record
per-field matches separately.

## What these examples let us measure

During each tool delay, request FIFO can run another task's ready model call;
task FIFO keeps the admitted task's capacity reserved. Returning requests may
queue again under request FIFO. The history grows after every model response
and tool result. Both policies must process the same scheduled steps and data.

Report completion rate, final-answer accuracy among completed tasks, and fully
correct completed tasks divided by all offered tasks. Missing and failed tasks
stay in the overall denominator. Tool exceptions are execution failures, not
wrong answers. A completed but incorrect response is a quality failure.

The final answers and full fixture collection must never be sent as the initial
model prompt. Only the initial task and the current step's visible tool result
are added as the workflow advances. Tool lookups do not depend on the model's
proposed actions in this scripted version.
