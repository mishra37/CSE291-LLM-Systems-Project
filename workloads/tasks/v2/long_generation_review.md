# Revised v2 tasks

Generated from v1 by `workloads/build_v2.py`. Reference answers, fixtures, and scoring rules are unchanged.

## long_gen-v2-001

Parent: `long_gen-v1-001`

**System:** Complete the writing task in English. Meet all content requirements within the stated word range. Plan the length before writing and return only the finished response. Do not include a preface, an outline, or a word-count note.

Explain DNS resolution to a beginner who has just typed www.example.com into a browser.

Write 200-280 words. Develop the ideas or events rather than giving an outline.
1. Explain the purpose of DNS and what address information the browser needs.
2. Describe the roles of a recursive resolver and root, top-level-domain, and authoritative name servers during a cache miss.
3. Explain how a cached answer and its TTL can change a later lookup.
4. Walk through the example and distinguish DNS resolution from fetching the webpage itself.

Length requirement: 200-280 words TOTAL, including any headings and code. Aim for about 240 words, budgeting roughly 60 words per content requirement. Combine related points and avoid repeating the introduction in a conclusion. For a story, leave room for the required ending. Before finishing, check the total length and shorten or develop the response as needed to stay within the range. Return only the finished response.

**Output maximum:** 512 tokens; **input:** 260 upstream tokens.

### Evaluator-only reference / rubric (not sent to the model)

```json
{
  "method": "rubric",
  "rubric_version": "1",
  "criteria": [
    {
      "id": "r1",
      "description": "Explain the purpose of DNS and what address information the browser needs.",
      "max_score": 2,
      "requirement_id": "r1"
    },
    {
      "id": "r2",
      "description": "Describe the roles of a recursive resolver and root, top-level-domain, and authoritative name servers during a cache miss.",
      "max_score": 2,
      "requirement_id": "r2"
    },
    {
      "id": "r3",
      "description": "Explain how a cached answer and its TTL can change a later lookup.",
      "max_score": 2,
      "requirement_id": "r3"
    },
    {
      "id": "r4",
      "description": "Walk through the example and distinguish DNS resolution from fetching the webpage itself.",
      "max_score": 2,
      "requirement_id": "r4"
    },
    {
      "id": "correctness",
      "description": "Material claims and worked examples are accurate.",
      "max_score": 2
    },
    {
      "id": "coherence",
      "description": "The response is organized, understandable, and has a complete ending or conclusion.",
      "max_score": 2
    },
    {
      "id": "development",
      "description": "The requested length is used for substantive development, without padding or excessive repetition.",
      "max_score": 2
    }
  ],
  "score_scale": {
    "0": "Unmet, absent, or materially wrong.",
    "1": "Partially met; substantive omissions or weaknesses remain.",
    "2": "Fully met; no material omission or error for this criterion."
  },
  "word_count": {
    "min": 200,
    "max": 280,
    "method": "len(text.split())",
    "scope": "entire response including headings and code"
  },
  "pass_rule": {
    "minimum_total": 12,
    "maximum_total": 14,
    "minimum_each_criterion": 1,
    "required_full_score": [
      "correctness"
    ],
    "word_range_required": true,
    "execution_complete_required": true,
    "critical_failures_allowed": 0
  },
  "critical_failures": [
    "Claims DNS itself downloads the webpage.",
    "Claims every lookup must traverse the full hierarchy despite a usable cached answer."
  ],
  "reference_notes": [
    "DNS stores resource records; address lookup is one use. A recursive resolver can follow referrals to authoritative data, while cached records can avoid those steps.",
    "TTL bounds ordinary cache reuse. DNS supplies resolution information; HTTP transfers the webpage. Do not require every query to contact the root."
  ],
  "reference_sources": [
    {
      "title": "RFC 1034: DNS concepts, sections 3.6 and 5",
      "url": "https://www.rfc-editor.org/rfc/rfc1034.html"
    }
  ],
  "review_protocol": "Score every criterion with evidence from the response. Record critical errors. Judge after the timed run without scheduler labels. Missing judgments are pending, not passes."
}
```

## long_gen-v2-002

Parent: `long_gen-v1-002`

**System:** Complete the writing task in English. Meet all content requirements within the stated word range. Plan the length before writing and return only the finished response. Do not include a preface, an outline, or a word-count note.

Explain database indexes to a developer using PostgreSQL and a large events table with a user_id column.

Write 450-600 words. Develop the ideas or events rather than giving an outline.
1. Explain how an index can help find rows without inspecting every table row, using an intuitive analogy.
2. Show a small CREATE INDEX example on user_id and a SELECT example filtering by user_id; explain their relationship.
3. Explain why an index costs storage and can add work when indexed data changes.
4. Describe a situation where the planner may prefer a sequential scan, and explain why indexing every column is not a universal solution.

Length requirement: 450-600 words TOTAL, including any headings and code. Aim for about 525 words, budgeting roughly 131 words per content requirement. Combine related points and avoid repeating the introduction in a conclusion. For a story, leave room for the required ending. Before finishing, check the total length and shorten or develop the response as needed to stay within the range. Return only the finished response.

**Output maximum:** 1024 tokens; **input:** 280 upstream tokens.

### Evaluator-only reference / rubric (not sent to the model)

```json
{
  "method": "rubric",
  "rubric_version": "1",
  "criteria": [
    {
      "id": "r1",
      "description": "Explain how an index can help find rows without inspecting every table row, using an intuitive analogy.",
      "max_score": 2,
      "requirement_id": "r1"
    },
    {
      "id": "r2",
      "description": "Show a small CREATE INDEX example on user_id and a SELECT example filtering by user_id; explain their relationship.",
      "max_score": 2,
      "requirement_id": "r2"
    },
    {
      "id": "r3",
      "description": "Explain why an index costs storage and can add work when indexed data changes.",
      "max_score": 2,
      "requirement_id": "r3"
    },
    {
      "id": "r4",
      "description": "Describe a situation where the planner may prefer a sequential scan, and explain why indexing every column is not a universal solution.",
      "max_score": 2,
      "requirement_id": "r4"
    },
    {
      "id": "correctness",
      "description": "Material claims and worked examples are accurate.",
      "max_score": 2
    },
    {
      "id": "coherence",
      "description": "The response is organized, understandable, and has a complete ending or conclusion.",
      "max_score": 2
    },
    {
      "id": "development",
      "description": "The requested length is used for substantive development, without padding or excessive repetition.",
      "max_score": 2
    }
  ],
  "score_scale": {
    "0": "Unmet, absent, or materially wrong.",
    "1": "Partially met; substantive omissions or weaknesses remain.",
    "2": "Fully met; no material omission or error for this criterion."
  },
  "word_count": {
    "min": 450,
    "max": 600,
    "method": "len(text.split())",
    "scope": "entire response including headings and code"
  },
  "pass_rule": {
    "minimum_total": 12,
    "maximum_total": 14,
    "minimum_each_criterion": 1,
    "required_full_score": [
      "correctness"
    ],
    "word_range_required": true,
    "execution_complete_required": true,
    "critical_failures_allowed": 0
  },
  "critical_failures": [
    "Claims indexes always improve every query or are always chosen.",
    "Claims indexes have no storage or write-maintenance cost."
  ],
  "reference_notes": [
    "An index is an auxiliary access structure. PostgreSQL chooses an index when estimated useful; a scan can be preferable when much of a table is needed.",
    "Indexes consume space and need maintenance as indexed data changes. A valid example is CREATE INDEX events_user_idx ON events (user_id), paired with a WHERE user_id = constant query."
  ],
  "reference_sources": [
    {
      "title": "PostgreSQL 18: Index introduction",
      "url": "https://www.postgresql.org/docs/18/indexes-intro.html"
    },
    {
      "title": "PostgreSQL 18: Indexes",
      "url": "https://www.postgresql.org/docs/18/indexes.html"
    }
  ],
  "review_protocol": "Score every criterion with evidence from the response. Record critical errors. Judge after the timed run without scheduler labels. Missing judgments are pending, not passes."
}
```

## long_gen-v2-003

Parent: `long_gen-v1-003`

**System:** Complete the writing task in English. Meet all content requirements within the stated word range. Plan the length before writing and return only the finished response. Do not include a preface, an outline, or a word-count note.

Explain HTTP response caching to a beginner using a browser that repeatedly requests the same public image.

Write 200-280 words. Develop the ideas or events rather than giving an outline.
1. Describe a cache hit and a cache miss and why reuse can save work.
2. Explain freshness and the difference between reusing a fresh response and validating a stored response.
3. Explain the practical distinction between unqualified Cache-Control: no-cache and Cache-Control: no-store for an ordinary response.
4. Give a concrete first-request and later-request example, including why caching does not guarantee permanently current content.

Length requirement: 200-280 words TOTAL, including any headings and code. Aim for about 240 words, budgeting roughly 60 words per content requirement. Combine related points and avoid repeating the introduction in a conclusion. For a story, leave room for the required ending. Before finishing, check the total length and shorten or develop the response as needed to stay within the range. Return only the finished response.

**Output maximum:** 512 tokens; **input:** 272 upstream tokens.

### Evaluator-only reference / rubric (not sent to the model)

```json
{
  "method": "rubric",
  "rubric_version": "1",
  "criteria": [
    {
      "id": "r1",
      "description": "Describe a cache hit and a cache miss and why reuse can save work.",
      "max_score": 2,
      "requirement_id": "r1"
    },
    {
      "id": "r2",
      "description": "Explain freshness and the difference between reusing a fresh response and validating a stored response.",
      "max_score": 2,
      "requirement_id": "r2"
    },
    {
      "id": "r3",
      "description": "Explain the practical distinction between unqualified Cache-Control: no-cache and Cache-Control: no-store for an ordinary response.",
      "max_score": 2,
      "requirement_id": "r3"
    },
    {
      "id": "r4",
      "description": "Give a concrete first-request and later-request example, including why caching does not guarantee permanently current content.",
      "max_score": 2,
      "requirement_id": "r4"
    },
    {
      "id": "correctness",
      "description": "Material claims and worked examples are accurate.",
      "max_score": 2
    },
    {
      "id": "coherence",
      "description": "The response is organized, understandable, and has a complete ending or conclusion.",
      "max_score": 2
    },
    {
      "id": "development",
      "description": "The requested length is used for substantive development, without padding or excessive repetition.",
      "max_score": 2
    }
  ],
  "score_scale": {
    "0": "Unmet, absent, or materially wrong.",
    "1": "Partially met; substantive omissions or weaknesses remain.",
    "2": "Fully met; no material omission or error for this criterion."
  },
  "word_count": {
    "min": 200,
    "max": 280,
    "method": "len(text.split())",
    "scope": "entire response including headings and code"
  },
  "pass_rule": {
    "minimum_total": 12,
    "maximum_total": 14,
    "minimum_each_criterion": 1,
    "required_full_score": [
      "correctness"
    ],
    "word_range_required": true,
    "execution_complete_required": true,
    "critical_failures_allowed": 0
  },
  "critical_failures": [
    "Equates no-cache with a general prohibition on storing responses.",
    "Claims cached content is guaranteed to stay current indefinitely."
  ],
  "reference_notes": [
    "Fresh stored responses may be reused subject to cache rules. Validation checks whether a stored response can still be used.",
    "Unqualified no-cache requires successful validation before reuse; it does not generally prohibit storage. No-store ordinarily forbids storage. An expired response is not necessarily deleted immediately."
  ],
  "reference_sources": [
    {
      "title": "RFC 9111: HTTP Caching, sections 4 and 5.2.2",
      "url": "https://www.rfc-editor.org/rfc/rfc9111.html"
    }
  ],
  "review_protocol": "Score every criterion with evidence from the response. Record critical errors. Judge after the timed run without scheduler labels. Missing judgments are pending, not passes."
}
```

## long_gen-v2-004

Parent: `long_gen-v1-004`

**System:** Complete the writing task in English. Meet all content requirements within the stated word range. Plan the length before writing and return only the finished response. Do not include a preface, an outline, or a word-count note.

Write a beginner-friendly explanation of sorting records in Python 3. Use [('A', 2), ('B', 1), ('C', 2)] as the running example.

Write 450-600 words. Develop the ideas or events rather than giving an outline.
1. Compare sorted() and list.sort(), including whether the original list changes and what each returns.
2. Explain a key function and show a small Python snippet sorting the records by their second element.
3. Show the complete ascending result and explain what stable sorting means for A and C.
4. Explain reverse=True and show the complete descending result, including the order of equal-key records.

Length requirement: 450-600 words TOTAL, including any headings and code. Aim for about 525 words, budgeting roughly 131 words per content requirement. Combine related points and avoid repeating the introduction in a conclusion. For a story, leave room for the required ending. Before finishing, check the total length and shorten or develop the response as needed to stay within the range. Return only the finished response.

**Output maximum:** 1024 tokens; **input:** 286 upstream tokens.

### Evaluator-only reference / rubric (not sent to the model)

```json
{
  "method": "rubric",
  "rubric_version": "1",
  "criteria": [
    {
      "id": "r1",
      "description": "Compare sorted() and list.sort(), including whether the original list changes and what each returns.",
      "max_score": 2,
      "requirement_id": "r1"
    },
    {
      "id": "r2",
      "description": "Explain a key function and show a small Python snippet sorting the records by their second element.",
      "max_score": 2,
      "requirement_id": "r2"
    },
    {
      "id": "r3",
      "description": "Show the complete ascending result and explain what stable sorting means for A and C.",
      "max_score": 2,
      "requirement_id": "r3"
    },
    {
      "id": "r4",
      "description": "Explain reverse=True and show the complete descending result, including the order of equal-key records.",
      "max_score": 2,
      "requirement_id": "r4"
    },
    {
      "id": "correctness",
      "description": "Material claims and worked examples are accurate.",
      "max_score": 2
    },
    {
      "id": "coherence",
      "description": "The response is organized, understandable, and has a complete ending or conclusion.",
      "max_score": 2
    },
    {
      "id": "development",
      "description": "The requested length is used for substantive development, without padding or excessive repetition.",
      "max_score": 2
    }
  ],
  "score_scale": {
    "0": "Unmet, absent, or materially wrong.",
    "1": "Partially met; substantive omissions or weaknesses remain.",
    "2": "Fully met; no material omission or error for this criterion."
  },
  "word_count": {
    "min": 450,
    "max": 600,
    "method": "len(text.split())",
    "scope": "entire response including headings and code"
  },
  "pass_rule": {
    "minimum_total": 12,
    "maximum_total": 14,
    "minimum_each_criterion": 1,
    "required_full_score": [
      "correctness"
    ],
    "word_range_required": true,
    "execution_complete_required": true,
    "critical_failures_allowed": 0
  },
  "critical_failures": [
    "Claims list.sort() returns the sorted list or sorted() mutates the input list.",
    "Reverses A and C when sorting by the second element, contradicting stability."
  ],
  "reference_notes": [
    "sorted() returns a new list; list.sort() mutates its list and returns None. key selects the comparison value. Python sorting preserves original order among equal keys, including reverse sorting.",
    "Ascending: [('B', 1), ('A', 2), ('C', 2)]. Descending: [('A', 2), ('C', 2), ('B', 1)]. A key such as lambda item: item[1] is sufficient."
  ],
  "reference_sources": [
    {
      "title": "Python 3.13 Sorting HOWTO",
      "url": "https://docs.python.org/3.13/howto/sorting.html"
    }
  ],
  "review_protocol": "Score every criterion with evidence from the response. Record critical errors. Judge after the timed run without scheduler labels. Missing judgments are pending, not passes."
}
```

## long_gen-v2-005

Parent: `long_gen-v1-005`

**System:** Complete the writing task in English. Meet all content requirements within the stated word range. Plan the length before writing and return only the finished response. Do not include a preface, an outline, or a word-count note.

Explain a typical native C build using the Clang/LLVM toolchain to a beginner. Use a small program that adds two integers as an illustration; no runnable full program is required.

Write 450-600 words. Develop the ideas or events rather than giving an outline.
1. Describe preprocessing, tokenization, parsing, and semantic checks at a high level.
2. Explain the purpose of an intermediate representation and optimization without implying that all compilers use identical stages.
3. Distinguish machine-code generation, an object file, and the linker's role in producing an executable.
4. Follow the example through the pipeline and distinguish a syntax/type error from an unresolved-symbol link error and from a runtime error.

Length requirement: 450-600 words TOTAL, including any headings and code. Aim for about 525 words, budgeting roughly 131 words per content requirement. Combine related points and avoid repeating the introduction in a conclusion. For a story, leave room for the required ending. Before finishing, check the total length and shorten or develop the response as needed to stay within the range. Return only the finished response.

**Output maximum:** 1024 tokens; **input:** 296 upstream tokens.

### Evaluator-only reference / rubric (not sent to the model)

```json
{
  "method": "rubric",
  "rubric_version": "1",
  "criteria": [
    {
      "id": "r1",
      "description": "Describe preprocessing, tokenization, parsing, and semantic checks at a high level.",
      "max_score": 2,
      "requirement_id": "r1"
    },
    {
      "id": "r2",
      "description": "Explain the purpose of an intermediate representation and optimization without implying that all compilers use identical stages.",
      "max_score": 2,
      "requirement_id": "r2"
    },
    {
      "id": "r3",
      "description": "Distinguish machine-code generation, an object file, and the linker's role in producing an executable.",
      "max_score": 2,
      "requirement_id": "r3"
    },
    {
      "id": "r4",
      "description": "Follow the example through the pipeline and distinguish a syntax/type error from an unresolved-symbol link error and from a runtime error.",
      "max_score": 2,
      "requirement_id": "r4"
    },
    {
      "id": "correctness",
      "description": "Material claims and worked examples are accurate.",
      "max_score": 2
    },
    {
      "id": "coherence",
      "description": "The response is organized, understandable, and has a complete ending or conclusion.",
      "max_score": 2
    },
    {
      "id": "development",
      "description": "The requested length is used for substantive development, without padding or excessive repetition.",
      "max_score": 2
    }
  ],
  "score_scale": {
    "0": "Unmet, absent, or materially wrong.",
    "1": "Partially met; substantive omissions or weaknesses remain.",
    "2": "Fully met; no material omission or error for this criterion."
  },
  "word_count": {
    "min": 450,
    "max": 600,
    "method": "len(text.split())",
    "scope": "entire response including headings and code"
  },
  "pass_rule": {
    "minimum_total": 12,
    "maximum_total": 14,
    "minimum_each_criterion": 1,
    "required_full_score": [
      "correctness"
    ],
    "word_range_required": true,
    "execution_complete_required": true,
    "critical_failures_allowed": 0
  },
  "critical_failures": [
    "Treats object files as universally complete executables with no linking needed.",
    "Claims successful compilation proves a program is free of runtime errors."
  ],
  "reference_notes": [
    "A typical Clang build preprocesses source, parses and checks it, generates LLVM IR, optionally optimizes, and emits target code. Assembly may use an integrated assembler.",
    "Linking combines object code and libraries and resolves symbols. A successful build does not prove the program has no runtime bugs. Tools may combine stages rather than write each intermediate file."
  ],
  "reference_sources": [
    {
      "title": "Clang: Assembling a Complete Toolchain",
      "url": "https://clang.llvm.org/docs/Toolchain.html"
    }
  ],
  "review_protocol": "Score every criterion with evidence from the response. Record critical errors. Judge after the timed run without scheduler labels. Missing judgments are pending, not passes."
}
```

## long_gen-v2-006

Parent: `long_gen-v1-006`

**System:** Complete the writing task in English. Meet all content requirements within the stated word range. Plan the length before writing and return only the finished response. Do not include a preface, an outline, or a word-count note.

Write a complete short story in third person about Mara, a lighthouse keeper considering leaving her post.

Write 200-280 words. Develop the ideas or events rather than giving an outline.
1. Have Mara discover a message inside a damaged lantern before a storm arrives.
2. Make the message influence a practical decision she makes during the storm.
3. Include a brief exchange of dialogue with another person and a concrete obstacle Mara must overcome.
4. End after the immediate danger has passed, with Mara choosing to stay at the lighthouse; make that decision follow from the events.

Length requirement: 200-280 words TOTAL, including any headings and code. Aim for about 240 words, budgeting roughly 60 words per content requirement. Combine related points and avoid repeating the introduction in a conclusion. For a story, leave room for the required ending. Before finishing, check the total length and shorten or develop the response as needed to stay within the range. Return only the finished response.

**Output maximum:** 512 tokens; **input:** 268 upstream tokens.

### Evaluator-only reference / rubric (not sent to the model)

```json
{
  "method": "rubric",
  "rubric_version": "1",
  "criteria": [
    {
      "id": "r1",
      "description": "Have Mara discover a message inside a damaged lantern before a storm arrives.",
      "max_score": 2,
      "requirement_id": "r1"
    },
    {
      "id": "r2",
      "description": "Make the message influence a practical decision she makes during the storm.",
      "max_score": 2,
      "requirement_id": "r2"
    },
    {
      "id": "r3",
      "description": "Include a brief exchange of dialogue with another person and a concrete obstacle Mara must overcome.",
      "max_score": 2,
      "requirement_id": "r3"
    },
    {
      "id": "r4",
      "description": "End after the immediate danger has passed, with Mara choosing to stay at the lighthouse; make that decision follow from the events.",
      "max_score": 2,
      "requirement_id": "r4"
    },
    {
      "id": "correctness",
      "description": "Characters, setting, causal events, and ending remain internally consistent.",
      "max_score": 2
    },
    {
      "id": "coherence",
      "description": "The response is organized, understandable, and has a complete ending or conclusion.",
      "max_score": 2
    },
    {
      "id": "development",
      "description": "The requested length is used for substantive development, without padding or excessive repetition.",
      "max_score": 2
    }
  ],
  "score_scale": {
    "0": "Unmet, absent, or materially wrong.",
    "1": "Partially met; substantive omissions or weaknesses remain.",
    "2": "Fully met; no material omission or error for this criterion."
  },
  "word_count": {
    "min": 200,
    "max": 280,
    "method": "len(text.split())",
    "scope": "entire response including headings and code"
  },
  "pass_rule": {
    "minimum_total": 12,
    "maximum_total": 14,
    "minimum_each_criterion": 1,
    "required_full_score": [
      "correctness"
    ],
    "word_range_required": true,
    "execution_complete_required": true,
    "critical_failures_allowed": 0
  },
  "critical_failures": [
    "Mara leaves permanently at the end instead of choosing to stay.",
    "The response is only an outline or stops before resolving the immediate danger."
  ],
  "reference_notes": [
    "No single reference story. Accept any plot and wording satisfying the explicit prompt and consistency criteria."
  ],
  "reference_sources": [],
  "review_protocol": "Score every criterion with evidence from the response. Record critical errors. Judge after the timed run without scheduler labels. Missing judgments are pending, not passes."
}
```

## long_gen-v2-007

Parent: `long_gen-v1-007`

**System:** Complete the writing task in English. Meet all content requirements within the stated word range. Plan the length before writing and return only the finished response. Do not include a preface, an outline, or a word-count note.

Write a complete science-fiction story in third person about Ivo, a maintenance apprentice at a lunar greenhouse, and Nia, its botanist.

Write 450-600 words. Develop the ideas or events rather than giving an outline.
1. Introduce a cooling-system failure that threatens the plants and establish a specific time pressure.
2. Show Ivo and Nia disagreeing over a repair, then making a joint plan through dialogue.
3. Make their solution depend on a previously introduced tool or observation, and show one attempted repair that fails.
4. Resolve the cooling problem with a believable cost or compromise and end with an image of one surviving seedling.

Length requirement: 450-600 words TOTAL, including any headings and code. Aim for about 525 words, budgeting roughly 131 words per content requirement. Combine related points and avoid repeating the introduction in a conclusion. For a story, leave room for the required ending. Before finishing, check the total length and shorten or develop the response as needed to stay within the range. Return only the finished response.

**Output maximum:** 1024 tokens; **input:** 287 upstream tokens.

### Evaluator-only reference / rubric (not sent to the model)

```json
{
  "method": "rubric",
  "rubric_version": "1",
  "criteria": [
    {
      "id": "r1",
      "description": "Introduce a cooling-system failure that threatens the plants and establish a specific time pressure.",
      "max_score": 2,
      "requirement_id": "r1"
    },
    {
      "id": "r2",
      "description": "Show Ivo and Nia disagreeing over a repair, then making a joint plan through dialogue.",
      "max_score": 2,
      "requirement_id": "r2"
    },
    {
      "id": "r3",
      "description": "Make their solution depend on a previously introduced tool or observation, and show one attempted repair that fails.",
      "max_score": 2,
      "requirement_id": "r3"
    },
    {
      "id": "r4",
      "description": "Resolve the cooling problem with a believable cost or compromise and end with an image of one surviving seedling.",
      "max_score": 2,
      "requirement_id": "r4"
    },
    {
      "id": "correctness",
      "description": "Characters, setting, causal events, and ending remain internally consistent.",
      "max_score": 2
    },
    {
      "id": "coherence",
      "description": "The response is organized, understandable, and has a complete ending or conclusion.",
      "max_score": 2
    },
    {
      "id": "development",
      "description": "The requested length is used for substantive development, without padding or excessive repetition.",
      "max_score": 2
    }
  ],
  "score_scale": {
    "0": "Unmet, absent, or materially wrong.",
    "1": "Partially met; substantive omissions or weaknesses remain.",
    "2": "Fully met; no material omission or error for this criterion."
  },
  "word_count": {
    "min": 450,
    "max": 600,
    "method": "len(text.split())",
    "scope": "entire response including headings and code"
  },
  "pass_rule": {
    "minimum_total": 12,
    "maximum_total": 14,
    "minimum_each_criterion": 1,
    "required_full_score": [
      "correctness"
    ],
    "word_range_required": true,
    "execution_complete_required": true,
    "critical_failures_allowed": 0
  },
  "critical_failures": [
    "An unintroduced miraculous device resolves the entire conflict without an established cause.",
    "The cooling problem has no resolution or the final seedling image is absent."
  ],
  "reference_notes": [
    "No single reference story. Accept any plot and wording satisfying the explicit prompt and consistency criteria."
  ],
  "reference_sources": [],
  "review_protocol": "Score every criterion with evidence from the response. Record critical errors. Judge after the timed run without scheduler labels. Missing judgments are pending, not passes."
}
```

## long_gen-v2-008

Parent: `long_gen-v1-008`

**System:** Complete the writing task in English. Meet all content requirements within the stated word range. Plan the length before writing and return only the finished response. Do not include a preface, an outline, or a word-count note.

Write a complete realistic story in first person, narrated by Ren, a station attendant closing a small railway station for the night.

Write 200-280 words. Develop the ideas or events rather than giving an outline.
1. Introduce a stranded passenger carrying a violin case and explain why they cannot simply board another train.
2. Have Ren face a choice between finishing the shift on time and helping the passenger.
3. Use dialogue to reveal that Ren's initial assumption about the passenger was mistaken.
4. Resolve how the passenger will leave safely and end with Ren accepting the personal inconvenience of helping.

Length requirement: 200-280 words TOTAL, including any headings and code. Aim for about 240 words, budgeting roughly 60 words per content requirement. Combine related points and avoid repeating the introduction in a conclusion. For a story, leave room for the required ending. Before finishing, check the total length and shorten or develop the response as needed to stay within the range. Return only the finished response.

**Output maximum:** 512 tokens; **input:** 272 upstream tokens.

### Evaluator-only reference / rubric (not sent to the model)

```json
{
  "method": "rubric",
  "rubric_version": "1",
  "criteria": [
    {
      "id": "r1",
      "description": "Introduce a stranded passenger carrying a violin case and explain why they cannot simply board another train.",
      "max_score": 2,
      "requirement_id": "r1"
    },
    {
      "id": "r2",
      "description": "Have Ren face a choice between finishing the shift on time and helping the passenger.",
      "max_score": 2,
      "requirement_id": "r2"
    },
    {
      "id": "r3",
      "description": "Use dialogue to reveal that Ren's initial assumption about the passenger was mistaken.",
      "max_score": 2,
      "requirement_id": "r3"
    },
    {
      "id": "r4",
      "description": "Resolve how the passenger will leave safely and end with Ren accepting the personal inconvenience of helping.",
      "max_score": 2,
      "requirement_id": "r4"
    },
    {
      "id": "correctness",
      "description": "Characters, setting, causal events, and ending remain internally consistent.",
      "max_score": 2
    },
    {
      "id": "coherence",
      "description": "The response is organized, understandable, and has a complete ending or conclusion.",
      "max_score": 2
    },
    {
      "id": "development",
      "description": "The requested length is used for substantive development, without padding or excessive repetition.",
      "max_score": 2
    }
  ],
  "score_scale": {
    "0": "Unmet, absent, or materially wrong.",
    "1": "Partially met; substantive omissions or weaknesses remain.",
    "2": "Fully met; no material omission or error for this criterion."
  },
  "word_count": {
    "min": 200,
    "max": 280,
    "method": "len(text.split())",
    "scope": "entire response including headings and code"
  },
  "pass_rule": {
    "minimum_total": 12,
    "maximum_total": 14,
    "minimum_each_criterion": 1,
    "required_full_score": [
      "correctness"
    ],
    "word_range_required": true,
    "execution_complete_required": true,
    "critical_failures_allowed": 0
  },
  "critical_failures": [
    "The passenger's immediate predicament remains unresolved.",
    "The central narrator becomes another person without explanation."
  ],
  "reference_notes": [
    "No single reference story. Accept any plot and wording satisfying the explicit prompt and consistency criteria."
  ],
  "reference_sources": [],
  "review_protocol": "Score every criterion with evidence from the response. Record critical errors. Judge after the timed run without scheduler labels. Missing judgments are pending, not passes."
}
```

## long_gen-v2-009

Parent: `long_gen-v1-009`

**System:** Complete the writing task in English. Meet all content requirements within the stated word range. Plan the length before writing and return only the finished response. Do not include a preface, an outline, or a word-count note.

Write a complete adventure story in third person about Sora, a village mapmaker, and Tavi, a courier navigating a forest after a flood.

Write 450-600 words. Develop the ideas or events rather than giving an outline.
1. Establish a delivery that matters to the village and show that a familiar bridge has been washed away.
2. Introduce an old map with one misleading detail and one useful clue before either affects the route.
3. Show Sora and Tavi disagreeing about a route, testing an observation, and revising their plan together.
4. Bring them to the destination without restoring the bridge by coincidence, and end with Sora correcting the map based on what they learned.

Length requirement: 450-600 words TOTAL, including any headings and code. Aim for about 525 words, budgeting roughly 131 words per content requirement. Combine related points and avoid repeating the introduction in a conclusion. For a story, leave room for the required ending. Before finishing, check the total length and shorten or develop the response as needed to stay within the range. Return only the finished response.

**Output maximum:** 1024 tokens; **input:** 296 upstream tokens.

### Evaluator-only reference / rubric (not sent to the model)

```json
{
  "method": "rubric",
  "rubric_version": "1",
  "criteria": [
    {
      "id": "r1",
      "description": "Establish a delivery that matters to the village and show that a familiar bridge has been washed away.",
      "max_score": 2,
      "requirement_id": "r1"
    },
    {
      "id": "r2",
      "description": "Introduce an old map with one misleading detail and one useful clue before either affects the route.",
      "max_score": 2,
      "requirement_id": "r2"
    },
    {
      "id": "r3",
      "description": "Show Sora and Tavi disagreeing about a route, testing an observation, and revising their plan together.",
      "max_score": 2,
      "requirement_id": "r3"
    },
    {
      "id": "r4",
      "description": "Bring them to the destination without restoring the bridge by coincidence, and end with Sora correcting the map based on what they learned.",
      "max_score": 2,
      "requirement_id": "r4"
    },
    {
      "id": "correctness",
      "description": "Characters, setting, causal events, and ending remain internally consistent.",
      "max_score": 2
    },
    {
      "id": "coherence",
      "description": "The response is organized, understandable, and has a complete ending or conclusion.",
      "max_score": 2
    },
    {
      "id": "development",
      "description": "The requested length is used for substantive development, without padding or excessive repetition.",
      "max_score": 2
    }
  ],
  "score_scale": {
    "0": "Unmet, absent, or materially wrong.",
    "1": "Partially met; substantive omissions or weaknesses remain.",
    "2": "Fully met; no material omission or error for this criterion."
  },
  "word_count": {
    "min": 450,
    "max": 600,
    "method": "len(text.split())",
    "scope": "entire response including headings and code"
  },
  "pass_rule": {
    "minimum_total": 12,
    "maximum_total": 14,
    "minimum_each_criterion": 1,
    "required_full_score": [
      "correctness"
    ],
    "word_range_required": true,
    "execution_complete_required": true,
    "critical_failures_allowed": 0
  },
  "critical_failures": [
    "The delivery is left unresolved or succeeds only because the bridge inexplicably reappears.",
    "The misleading detail never affects the journey and no map correction occurs."
  ],
  "reference_notes": [
    "No single reference story. Accept any plot and wording satisfying the explicit prompt and consistency criteria."
  ],
  "reference_sources": [],
  "review_protocol": "Score every criterion with evidence from the response. Record critical errors. Judge after the timed run without scheduler labels. Missing judgments are pending, not passes."
}
```

## long_gen-v2-010

Parent: `long_gen-v1-010`

**System:** Complete the writing task in English. Meet all content requirements within the stated word range. Plan the length before writing and return only the finished response. Do not include a preface, an outline, or a word-count note.

Write a complete realistic story in third person about Jules, an apprentice baker entering a neighborhood baking contest.

Write 200-280 words. Develop the ideas or events rather than giving an outline.
1. Introduce a flaw in Jules's loaf and show why it matters personally rather than only competitively.
2. Have another contestant need help while Jules still has time to work on the loaf.
3. Show Jules choosing to help, with a concrete cost to the presentation and a short exchange of dialogue.
4. Reveal that Jules does not win first prize, then end with a specific sign of earned community appreciation.

Length requirement: 200-280 words TOTAL, including any headings and code. Aim for about 240 words, budgeting roughly 60 words per content requirement. Combine related points and avoid repeating the introduction in a conclusion. For a story, leave room for the required ending. Before finishing, check the total length and shorten or develop the response as needed to stay within the range. Return only the finished response.

**Output maximum:** 512 tokens; **input:** 280 upstream tokens.

### Evaluator-only reference / rubric (not sent to the model)

```json
{
  "method": "rubric",
  "rubric_version": "1",
  "criteria": [
    {
      "id": "r1",
      "description": "Introduce a flaw in Jules's loaf and show why it matters personally rather than only competitively.",
      "max_score": 2,
      "requirement_id": "r1"
    },
    {
      "id": "r2",
      "description": "Have another contestant need help while Jules still has time to work on the loaf.",
      "max_score": 2,
      "requirement_id": "r2"
    },
    {
      "id": "r3",
      "description": "Show Jules choosing to help, with a concrete cost to the presentation and a short exchange of dialogue.",
      "max_score": 2,
      "requirement_id": "r3"
    },
    {
      "id": "r4",
      "description": "Reveal that Jules does not win first prize, then end with a specific sign of earned community appreciation.",
      "max_score": 2,
      "requirement_id": "r4"
    },
    {
      "id": "correctness",
      "description": "Characters, setting, causal events, and ending remain internally consistent.",
      "max_score": 2
    },
    {
      "id": "coherence",
      "description": "The response is organized, understandable, and has a complete ending or conclusion.",
      "max_score": 2
    },
    {
      "id": "development",
      "description": "The requested length is used for substantive development, without padding or excessive repetition.",
      "max_score": 2
    }
  ],
  "score_scale": {
    "0": "Unmet, absent, or materially wrong.",
    "1": "Partially met; substantive omissions or weaknesses remain.",
    "2": "Fully met; no material omission or error for this criterion."
  },
  "word_count": {
    "min": 200,
    "max": 280,
    "method": "len(text.split())",
    "scope": "entire response including headings and code"
  },
  "pass_rule": {
    "minimum_total": 12,
    "maximum_total": 14,
    "minimum_each_criterion": 1,
    "required_full_score": [
      "correctness"
    ],
    "word_range_required": true,
    "execution_complete_required": true,
    "critical_failures_allowed": 0
  },
  "critical_failures": [
    "Jules wins first prize despite the explicit ending requirement.",
    "The response never reveals the contest outcome."
  ],
  "reference_notes": [
    "No single reference story. Accept any plot and wording satisfying the explicit prompt and consistency criteria."
  ],
  "reference_sources": [],
  "review_protocol": "Score every criterion with evidence from the response. Record critical errors. Judge after the timed run without scheduler labels. Missing judgments are pending, not passes."
}
```
