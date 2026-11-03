# Long generation: 10 writing tasks

Five technical explanations and five stories. Each uses one model call and no tools. Flag issues by task ID.

**Shared system instruction:** Complete the writing task in English. Follow the requested content and length requirements. Return only the finished response.

Only the system instruction and prompt are sent to the model. Rubrics, reference notes, and sources are evaluator-only. Temperature is 0 and natural EOS is enabled. Output caps are maxima, not forced generation lengths.

## Scoring rules fixed before experiments

Each task has seven criteria worth 0 (unmet), 1 (partially met), or 2 (fully met). A quality pass requires valid execution, 12/14 total, at least 1 on every criterion, 2 on correctness/consistency, the stated word range, and no critical failure. Count words with `len(text.split())`, including headings and code.

Report completion rate, per-criterion scores, total score, length compliance, and quality pass rate separately. Failed execution cannot pass quality. Unjudged completed outputs remain pending; do not silently drop them. Human or LLM judging has not been run. These authored rubrics are operational criteria, not universal measures of writing quality.

Input counts use the pinned upstream Qwen tokenizer and ChatML. AWS inference, deployed-tokenizer verification, and actual response-length checks remain pending.

## Index

| Task | Topic | Kind | Input tokens | Output cap | Words |
|---|---|---|---:|---:|---|
| [long_gen-v1-001](#long_gen-v1-001) | From a domain name to a server address | technical_explanation | 146 | 512 | 200-280 |
| [long_gen-v1-002](#long_gen-v1-002) | When a database index helps | technical_explanation | 165 | 1024 | 450-600 |
| [long_gen-v1-003](#long_gen-v1-003) | HTTP cache reuse and validation | technical_explanation | 158 | 512 | 200-280 |
| [long_gen-v1-004](#long_gen-v1-004) | Sorting records while preserving ties | technical_explanation | 171 | 1024 | 450-600 |
| [long_gen-v1-005](#long_gen-v1-005) | From C source to an executable | technical_explanation | 181 | 1024 | 450-600 |
| [long_gen-v1-006](#long_gen-v1-006) | The lighthouse message | story | 154 | 512 | 200-280 |
| [long_gen-v1-007](#long_gen-v1-007) | A lunar greenhouse | story | 172 | 1024 | 450-600 |
| [long_gen-v1-008](#long_gen-v1-008) | The last train's passenger | story | 158 | 512 | 200-280 |
| [long_gen-v1-009](#long_gen-v1-009) | A map after the flood | story | 181 | 1024 | 450-600 |
| [long_gen-v1-010](#long_gen-v1-010) | The imperfect loaf | story | 166 | 512 | 200-280 |

## long_gen-v1-001

**From a domain name to a server address**

### Prompt

Explain DNS resolution to a beginner who has just typed www.example.com into a browser.

Write 200-280 words. Develop the ideas or events rather than giving an outline.
1. Explain the purpose of DNS and what address information the browser needs.
2. Describe the roles of a recursive resolver and root, top-level-domain, and authoritative name servers during a cache miss.
3. Explain how a cached answer and its TTL can change a later lookup.
4. Walk through the example and distinguish DNS resolution from fetching the webpage itself.

### Evaluation rubric

- **r1 (0-2):** Explain the purpose of DNS and what address information the browser needs.
- **r2 (0-2):** Describe the roles of a recursive resolver and root, top-level-domain, and authoritative name servers during a cache miss.
- **r3 (0-2):** Explain how a cached answer and its TTL can change a later lookup.
- **r4 (0-2):** Walk through the example and distinguish DNS resolution from fetching the webpage itself.
- **correctness (0-2):** Material claims and worked examples are accurate.
- **coherence (0-2):** The response is organized, understandable, and has a complete ending or conclusion.
- **development (0-2):** The requested length is used for substantive development, without padding or excessive repetition.

**Critical failures (any one prevents a pass):**

- Claims DNS itself downloads the webpage.
- Claims every lookup must traverse the full hierarchy despite a usable cached answer.

**Reference notes:**

- DNS stores resource records; address lookup is one use. A recursive resolver can follow referrals to authoritative data, while cached records can avoid those steps.
- TTL bounds ordinary cache reuse. DNS supplies resolution information; HTTP transfers the webpage. Do not require every query to contact the root.

**Sources checked for the reference notes:**

- [RFC 1034: DNS concepts, sections 3.6 and 5](https://www.rfc-editor.org/rfc/rfc1034.html)

## long_gen-v1-002

**When a database index helps**

### Prompt

Explain database indexes to a developer using PostgreSQL and a large events table with a user_id column.

Write 450-600 words. Develop the ideas or events rather than giving an outline.
1. Explain how an index can help find rows without inspecting every table row, using an intuitive analogy.
2. Show a small CREATE INDEX example on user_id and a SELECT example filtering by user_id; explain their relationship.
3. Explain why an index costs storage and can add work when indexed data changes.
4. Describe a situation where the planner may prefer a sequential scan, and explain why indexing every column is not a universal solution.

### Evaluation rubric

- **r1 (0-2):** Explain how an index can help find rows without inspecting every table row, using an intuitive analogy.
- **r2 (0-2):** Show a small CREATE INDEX example on user_id and a SELECT example filtering by user_id; explain their relationship.
- **r3 (0-2):** Explain why an index costs storage and can add work when indexed data changes.
- **r4 (0-2):** Describe a situation where the planner may prefer a sequential scan, and explain why indexing every column is not a universal solution.
- **correctness (0-2):** Material claims and worked examples are accurate.
- **coherence (0-2):** The response is organized, understandable, and has a complete ending or conclusion.
- **development (0-2):** The requested length is used for substantive development, without padding or excessive repetition.

**Critical failures (any one prevents a pass):**

- Claims indexes always improve every query or are always chosen.
- Claims indexes have no storage or write-maintenance cost.

**Reference notes:**

- An index is an auxiliary access structure. PostgreSQL chooses an index when estimated useful; a scan can be preferable when much of a table is needed.
- Indexes consume space and need maintenance as indexed data changes. A valid example is CREATE INDEX events_user_idx ON events (user_id), paired with a WHERE user_id = constant query.

**Sources checked for the reference notes:**

- [PostgreSQL 18: Index introduction](https://www.postgresql.org/docs/18/indexes-intro.html)
- [PostgreSQL 18: Indexes](https://www.postgresql.org/docs/18/indexes.html)

## long_gen-v1-003

**HTTP cache reuse and validation**

### Prompt

Explain HTTP response caching to a beginner using a browser that repeatedly requests the same public image.

Write 200-280 words. Develop the ideas or events rather than giving an outline.
1. Describe a cache hit and a cache miss and why reuse can save work.
2. Explain freshness and the difference between reusing a fresh response and validating a stored response.
3. Explain the practical distinction between unqualified Cache-Control: no-cache and Cache-Control: no-store for an ordinary response.
4. Give a concrete first-request and later-request example, including why caching does not guarantee permanently current content.

### Evaluation rubric

- **r1 (0-2):** Describe a cache hit and a cache miss and why reuse can save work.
- **r2 (0-2):** Explain freshness and the difference between reusing a fresh response and validating a stored response.
- **r3 (0-2):** Explain the practical distinction between unqualified Cache-Control: no-cache and Cache-Control: no-store for an ordinary response.
- **r4 (0-2):** Give a concrete first-request and later-request example, including why caching does not guarantee permanently current content.
- **correctness (0-2):** Material claims and worked examples are accurate.
- **coherence (0-2):** The response is organized, understandable, and has a complete ending or conclusion.
- **development (0-2):** The requested length is used for substantive development, without padding or excessive repetition.

**Critical failures (any one prevents a pass):**

- Equates no-cache with a general prohibition on storing responses.
- Claims cached content is guaranteed to stay current indefinitely.

**Reference notes:**

- Fresh stored responses may be reused subject to cache rules. Validation checks whether a stored response can still be used.
- Unqualified no-cache requires successful validation before reuse; it does not generally prohibit storage. No-store ordinarily forbids storage. An expired response is not necessarily deleted immediately.

**Sources checked for the reference notes:**

- [RFC 9111: HTTP Caching, sections 4 and 5.2.2](https://www.rfc-editor.org/rfc/rfc9111.html)

## long_gen-v1-004

**Sorting records while preserving ties**

### Prompt

Write a beginner-friendly explanation of sorting records in Python 3. Use [('A', 2), ('B', 1), ('C', 2)] as the running example.

Write 450-600 words. Develop the ideas or events rather than giving an outline.
1. Compare sorted() and list.sort(), including whether the original list changes and what each returns.
2. Explain a key function and show a small Python snippet sorting the records by their second element.
3. Show the complete ascending result and explain what stable sorting means for A and C.
4. Explain reverse=True and show the complete descending result, including the order of equal-key records.

### Evaluation rubric

- **r1 (0-2):** Compare sorted() and list.sort(), including whether the original list changes and what each returns.
- **r2 (0-2):** Explain a key function and show a small Python snippet sorting the records by their second element.
- **r3 (0-2):** Show the complete ascending result and explain what stable sorting means for A and C.
- **r4 (0-2):** Explain reverse=True and show the complete descending result, including the order of equal-key records.
- **correctness (0-2):** Material claims and worked examples are accurate.
- **coherence (0-2):** The response is organized, understandable, and has a complete ending or conclusion.
- **development (0-2):** The requested length is used for substantive development, without padding or excessive repetition.

**Critical failures (any one prevents a pass):**

- Claims list.sort() returns the sorted list or sorted() mutates the input list.
- Reverses A and C when sorting by the second element, contradicting stability.

**Reference notes:**

- sorted() returns a new list; list.sort() mutates its list and returns None. key selects the comparison value. Python sorting preserves original order among equal keys, including reverse sorting.
- Ascending: [('B', 1), ('A', 2), ('C', 2)]. Descending: [('A', 2), ('C', 2), ('B', 1)]. A key such as lambda item: item[1] is sufficient.

**Sources checked for the reference notes:**

- [Python 3.13 Sorting HOWTO](https://docs.python.org/3.13/howto/sorting.html)

## long_gen-v1-005

**From C source to an executable**

### Prompt

Explain a typical native C build using the Clang/LLVM toolchain to a beginner. Use a small program that adds two integers as an illustration; no runnable full program is required.

Write 450-600 words. Develop the ideas or events rather than giving an outline.
1. Describe preprocessing, tokenization, parsing, and semantic checks at a high level.
2. Explain the purpose of an intermediate representation and optimization without implying that all compilers use identical stages.
3. Distinguish machine-code generation, an object file, and the linker's role in producing an executable.
4. Follow the example through the pipeline and distinguish a syntax/type error from an unresolved-symbol link error and from a runtime error.

### Evaluation rubric

- **r1 (0-2):** Describe preprocessing, tokenization, parsing, and semantic checks at a high level.
- **r2 (0-2):** Explain the purpose of an intermediate representation and optimization without implying that all compilers use identical stages.
- **r3 (0-2):** Distinguish machine-code generation, an object file, and the linker's role in producing an executable.
- **r4 (0-2):** Follow the example through the pipeline and distinguish a syntax/type error from an unresolved-symbol link error and from a runtime error.
- **correctness (0-2):** Material claims and worked examples are accurate.
- **coherence (0-2):** The response is organized, understandable, and has a complete ending or conclusion.
- **development (0-2):** The requested length is used for substantive development, without padding or excessive repetition.

**Critical failures (any one prevents a pass):**

- Treats object files as universally complete executables with no linking needed.
- Claims successful compilation proves a program is free of runtime errors.

**Reference notes:**

- A typical Clang build preprocesses source, parses and checks it, generates LLVM IR, optionally optimizes, and emits target code. Assembly may use an integrated assembler.
- Linking combines object code and libraries and resolves symbols. A successful build does not prove the program has no runtime bugs. Tools may combine stages rather than write each intermediate file.

**Sources checked for the reference notes:**

- [Clang: Assembling a Complete Toolchain](https://clang.llvm.org/docs/Toolchain.html)

## long_gen-v1-006

**The lighthouse message**

### Prompt

Write a complete short story in third person about Mara, a lighthouse keeper considering leaving her post.

Write 200-280 words. Develop the ideas or events rather than giving an outline.
1. Have Mara discover a message inside a damaged lantern before a storm arrives.
2. Make the message influence a practical decision she makes during the storm.
3. Include a brief exchange of dialogue with another person and a concrete obstacle Mara must overcome.
4. End after the immediate danger has passed, with Mara choosing to stay at the lighthouse; make that decision follow from the events.

### Evaluation rubric

- **r1 (0-2):** Have Mara discover a message inside a damaged lantern before a storm arrives.
- **r2 (0-2):** Make the message influence a practical decision she makes during the storm.
- **r3 (0-2):** Include a brief exchange of dialogue with another person and a concrete obstacle Mara must overcome.
- **r4 (0-2):** End after the immediate danger has passed, with Mara choosing to stay at the lighthouse; make that decision follow from the events.
- **correctness (0-2):** Characters, setting, causal events, and ending remain internally consistent.
- **coherence (0-2):** The response is organized, understandable, and has a complete ending or conclusion.
- **development (0-2):** The requested length is used for substantive development, without padding or excessive repetition.

**Critical failures (any one prevents a pass):**

- Mara leaves permanently at the end instead of choosing to stay.
- The response is only an outline or stops before resolving the immediate danger.

**Reference notes:**

- No single reference story. Accept any plot and wording satisfying the explicit prompt and consistency criteria.

## long_gen-v1-007

**A lunar greenhouse**

### Prompt

Write a complete science-fiction story in third person about Ivo, a maintenance apprentice at a lunar greenhouse, and Nia, its botanist.

Write 450-600 words. Develop the ideas or events rather than giving an outline.
1. Introduce a cooling-system failure that threatens the plants and establish a specific time pressure.
2. Show Ivo and Nia disagreeing over a repair, then making a joint plan through dialogue.
3. Make their solution depend on a previously introduced tool or observation, and show one attempted repair that fails.
4. Resolve the cooling problem with a believable cost or compromise and end with an image of one surviving seedling.

### Evaluation rubric

- **r1 (0-2):** Introduce a cooling-system failure that threatens the plants and establish a specific time pressure.
- **r2 (0-2):** Show Ivo and Nia disagreeing over a repair, then making a joint plan through dialogue.
- **r3 (0-2):** Make their solution depend on a previously introduced tool or observation, and show one attempted repair that fails.
- **r4 (0-2):** Resolve the cooling problem with a believable cost or compromise and end with an image of one surviving seedling.
- **correctness (0-2):** Characters, setting, causal events, and ending remain internally consistent.
- **coherence (0-2):** The response is organized, understandable, and has a complete ending or conclusion.
- **development (0-2):** The requested length is used for substantive development, without padding or excessive repetition.

**Critical failures (any one prevents a pass):**

- An unintroduced miraculous device resolves the entire conflict without an established cause.
- The cooling problem has no resolution or the final seedling image is absent.

**Reference notes:**

- No single reference story. Accept any plot and wording satisfying the explicit prompt and consistency criteria.

## long_gen-v1-008

**The last train's passenger**

### Prompt

Write a complete realistic story in first person, narrated by Ren, a station attendant closing a small railway station for the night.

Write 200-280 words. Develop the ideas or events rather than giving an outline.
1. Introduce a stranded passenger carrying a violin case and explain why they cannot simply board another train.
2. Have Ren face a choice between finishing the shift on time and helping the passenger.
3. Use dialogue to reveal that Ren's initial assumption about the passenger was mistaken.
4. Resolve how the passenger will leave safely and end with Ren accepting the personal inconvenience of helping.

### Evaluation rubric

- **r1 (0-2):** Introduce a stranded passenger carrying a violin case and explain why they cannot simply board another train.
- **r2 (0-2):** Have Ren face a choice between finishing the shift on time and helping the passenger.
- **r3 (0-2):** Use dialogue to reveal that Ren's initial assumption about the passenger was mistaken.
- **r4 (0-2):** Resolve how the passenger will leave safely and end with Ren accepting the personal inconvenience of helping.
- **correctness (0-2):** Characters, setting, causal events, and ending remain internally consistent.
- **coherence (0-2):** The response is organized, understandable, and has a complete ending or conclusion.
- **development (0-2):** The requested length is used for substantive development, without padding or excessive repetition.

**Critical failures (any one prevents a pass):**

- The passenger's immediate predicament remains unresolved.
- The central narrator becomes another person without explanation.

**Reference notes:**

- No single reference story. Accept any plot and wording satisfying the explicit prompt and consistency criteria.

## long_gen-v1-009

**A map after the flood**

### Prompt

Write a complete adventure story in third person about Sora, a village mapmaker, and Tavi, a courier navigating a forest after a flood.

Write 450-600 words. Develop the ideas or events rather than giving an outline.
1. Establish a delivery that matters to the village and show that a familiar bridge has been washed away.
2. Introduce an old map with one misleading detail and one useful clue before either affects the route.
3. Show Sora and Tavi disagreeing about a route, testing an observation, and revising their plan together.
4. Bring them to the destination without restoring the bridge by coincidence, and end with Sora correcting the map based on what they learned.

### Evaluation rubric

- **r1 (0-2):** Establish a delivery that matters to the village and show that a familiar bridge has been washed away.
- **r2 (0-2):** Introduce an old map with one misleading detail and one useful clue before either affects the route.
- **r3 (0-2):** Show Sora and Tavi disagreeing about a route, testing an observation, and revising their plan together.
- **r4 (0-2):** Bring them to the destination without restoring the bridge by coincidence, and end with Sora correcting the map based on what they learned.
- **correctness (0-2):** Characters, setting, causal events, and ending remain internally consistent.
- **coherence (0-2):** The response is organized, understandable, and has a complete ending or conclusion.
- **development (0-2):** The requested length is used for substantive development, without padding or excessive repetition.

**Critical failures (any one prevents a pass):**

- The delivery is left unresolved or succeeds only because the bridge inexplicably reappears.
- The misleading detail never affects the journey and no map correction occurs.

**Reference notes:**

- No single reference story. Accept any plot and wording satisfying the explicit prompt and consistency criteria.

## long_gen-v1-010

**The imperfect loaf**

### Prompt

Write a complete realistic story in third person about Jules, an apprentice baker entering a neighborhood baking contest.

Write 200-280 words. Develop the ideas or events rather than giving an outline.
1. Introduce a flaw in Jules's loaf and show why it matters personally rather than only competitively.
2. Have another contestant need help while Jules still has time to work on the loaf.
3. Show Jules choosing to help, with a concrete cost to the presentation and a short exchange of dialogue.
4. Reveal that Jules does not win first prize, then end with a specific sign of earned community appreciation.

### Evaluation rubric

- **r1 (0-2):** Introduce a flaw in Jules's loaf and show why it matters personally rather than only competitively.
- **r2 (0-2):** Have another contestant need help while Jules still has time to work on the loaf.
- **r3 (0-2):** Show Jules choosing to help, with a concrete cost to the presentation and a short exchange of dialogue.
- **r4 (0-2):** Reveal that Jules does not win first prize, then end with a specific sign of earned community appreciation.
- **correctness (0-2):** Characters, setting, causal events, and ending remain internally consistent.
- **coherence (0-2):** The response is organized, understandable, and has a complete ending or conclusion.
- **development (0-2):** The requested length is used for substantive development, without padding or excessive repetition.

**Critical failures (any one prevents a pass):**

- Jules wins first prize despite the explicit ending requirement.
- The response never reveals the contest outcome.

**Reference notes:**

- No single reference story. Accept any plot and wording satisfying the explicit prompt and consistency criteria.
