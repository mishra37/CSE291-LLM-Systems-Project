"""Build the ten authored long-generation tasks and their readable rubrics.

python -m workloads.build_long_generation --tokenizer /path/to/qwen-tokenizer.json
Requires workloads/requirements-authoring.txt; no model or judge calls.
"""
import argparse
import hashlib
import json
from pathlib import Path

from runner.llama_client import chatml
from workloads.generate_long_context import MODEL, REVISION, TOKENIZER_SHA256, TOKENIZER_URL

SYSTEM = "Complete the writing task in English. Follow the requested content and length requirements. Return only the finished response."

# Original task prompts. Technical reference notes are paraphrases for evaluators.
SPECS = [
    {
        "title": "From a domain name to a server address", "subtype": "technical_explanation", "budget": 512,
        "opening": "Explain DNS resolution to a beginner who has just typed www.example.com into a browser.",
        "requirements": [
            "Explain the purpose of DNS and what address information the browser needs.",
            "Describe the roles of a recursive resolver and root, top-level-domain, and authoritative name servers during a cache miss.",
            "Explain how a cached answer and its TTL can change a later lookup.",
            "Walk through the example and distinguish DNS resolution from fetching the webpage itself.",
        ],
        "notes": [
            "DNS stores resource records; address lookup is one use. A recursive resolver can follow referrals to authoritative data, while cached records can avoid those steps.",
            "TTL bounds ordinary cache reuse. DNS supplies resolution information; HTTP transfers the webpage. Do not require every query to contact the root.",
        ],
        "critical": ["Claims DNS itself downloads the webpage.", "Claims every lookup must traverse the full hierarchy despite a usable cached answer."],
        "sources": [{"title": "RFC 1034: DNS concepts, sections 3.6 and 5", "url": "https://www.rfc-editor.org/rfc/rfc1034.html"}],
    },
    {
        "title": "When a database index helps", "subtype": "technical_explanation", "budget": 1024,
        "opening": "Explain database indexes to a developer using PostgreSQL and a large events table with a user_id column.",
        "requirements": [
            "Explain how an index can help find rows without inspecting every table row, using an intuitive analogy.",
            "Show a small CREATE INDEX example on user_id and a SELECT example filtering by user_id; explain their relationship.",
            "Explain why an index costs storage and can add work when indexed data changes.",
            "Describe a situation where the planner may prefer a sequential scan, and explain why indexing every column is not a universal solution.",
        ],
        "notes": [
            "An index is an auxiliary access structure. PostgreSQL chooses an index when estimated useful; a scan can be preferable when much of a table is needed.",
            "Indexes consume space and need maintenance as indexed data changes. A valid example is CREATE INDEX events_user_idx ON events (user_id), paired with a WHERE user_id = constant query.",
        ],
        "critical": ["Claims indexes always improve every query or are always chosen.", "Claims indexes have no storage or write-maintenance cost."],
        "sources": [
            {"title": "PostgreSQL 18: Index introduction", "url": "https://www.postgresql.org/docs/18/indexes-intro.html"},
            {"title": "PostgreSQL 18: Indexes", "url": "https://www.postgresql.org/docs/18/indexes.html"},
        ],
    },
    {
        "title": "HTTP cache reuse and validation", "subtype": "technical_explanation", "budget": 512,
        "opening": "Explain HTTP response caching to a beginner using a browser that repeatedly requests the same public image.",
        "requirements": [
            "Describe a cache hit and a cache miss and why reuse can save work.",
            "Explain freshness and the difference between reusing a fresh response and validating a stored response.",
            "Explain the practical distinction between unqualified Cache-Control: no-cache and Cache-Control: no-store for an ordinary response.",
            "Give a concrete first-request and later-request example, including why caching does not guarantee permanently current content.",
        ],
        "notes": [
            "Fresh stored responses may be reused subject to cache rules. Validation checks whether a stored response can still be used.",
            "Unqualified no-cache requires successful validation before reuse; it does not generally prohibit storage. No-store ordinarily forbids storage. An expired response is not necessarily deleted immediately.",
        ],
        "critical": ["Equates no-cache with a general prohibition on storing responses.", "Claims cached content is guaranteed to stay current indefinitely."],
        "sources": [{"title": "RFC 9111: HTTP Caching, sections 4 and 5.2.2", "url": "https://www.rfc-editor.org/rfc/rfc9111.html"}],
    },
    {
        "title": "Sorting records while preserving ties", "subtype": "technical_explanation", "budget": 1024,
        "opening": "Write a beginner-friendly explanation of sorting records in Python 3. Use [('A', 2), ('B', 1), ('C', 2)] as the running example.",
        "requirements": [
            "Compare sorted() and list.sort(), including whether the original list changes and what each returns.",
            "Explain a key function and show a small Python snippet sorting the records by their second element.",
            "Show the complete ascending result and explain what stable sorting means for A and C.",
            "Explain reverse=True and show the complete descending result, including the order of equal-key records.",
        ],
        "notes": [
            "sorted() returns a new list; list.sort() mutates its list and returns None. key selects the comparison value. Python sorting preserves original order among equal keys, including reverse sorting.",
            "Ascending: [('B', 1), ('A', 2), ('C', 2)]. Descending: [('A', 2), ('C', 2), ('B', 1)]. A key such as lambda item: item[1] is sufficient.",
        ],
        "critical": ["Claims list.sort() returns the sorted list or sorted() mutates the input list.", "Reverses A and C when sorting by the second element, contradicting stability."],
        "sources": [{"title": "Python 3.13 Sorting HOWTO", "url": "https://docs.python.org/3.13/howto/sorting.html"}],
    },
    {
        "title": "From C source to an executable", "subtype": "technical_explanation", "budget": 1024,
        "opening": "Explain a typical native C build using the Clang/LLVM toolchain to a beginner. Use a small program that adds two integers as an illustration; no runnable full program is required.",
        "requirements": [
            "Describe preprocessing, tokenization, parsing, and semantic checks at a high level.",
            "Explain the purpose of an intermediate representation and optimization without implying that all compilers use identical stages.",
            "Distinguish machine-code generation, an object file, and the linker's role in producing an executable.",
            "Follow the example through the pipeline and distinguish a syntax/type error from an unresolved-symbol link error and from a runtime error.",
        ],
        "notes": [
            "A typical Clang build preprocesses source, parses and checks it, generates LLVM IR, optionally optimizes, and emits target code. Assembly may use an integrated assembler.",
            "Linking combines object code and libraries and resolves symbols. A successful build does not prove the program has no runtime bugs. Tools may combine stages rather than write each intermediate file.",
        ],
        "critical": ["Treats object files as universally complete executables with no linking needed.", "Claims successful compilation proves a program is free of runtime errors."],
        "sources": [{"title": "Clang: Assembling a Complete Toolchain", "url": "https://clang.llvm.org/docs/Toolchain.html"}],
    },
    {
        "title": "The lighthouse message", "subtype": "story", "budget": 512,
        "opening": "Write a complete short story in third person about Mara, a lighthouse keeper considering leaving her post.",
        "requirements": [
            "Have Mara discover a message inside a damaged lantern before a storm arrives.",
            "Make the message influence a practical decision she makes during the storm.",
            "Include a brief exchange of dialogue with another person and a concrete obstacle Mara must overcome.",
            "End after the immediate danger has passed, with Mara choosing to stay at the lighthouse; make that decision follow from the events.",
        ],
        "critical": ["Mara leaves permanently at the end instead of choosing to stay.", "The response is only an outline or stops before resolving the immediate danger."],
    },
    {
        "title": "A lunar greenhouse", "subtype": "story", "budget": 1024,
        "opening": "Write a complete science-fiction story in third person about Ivo, a maintenance apprentice at a lunar greenhouse, and Nia, its botanist.",
        "requirements": [
            "Introduce a cooling-system failure that threatens the plants and establish a specific time pressure.",
            "Show Ivo and Nia disagreeing over a repair, then making a joint plan through dialogue.",
            "Make their solution depend on a previously introduced tool or observation, and show one attempted repair that fails.",
            "Resolve the cooling problem with a believable cost or compromise and end with an image of one surviving seedling.",
        ],
        "critical": ["An unintroduced miraculous device resolves the entire conflict without an established cause.", "The cooling problem has no resolution or the final seedling image is absent."],
    },
    {
        "title": "The last train's passenger", "subtype": "story", "budget": 512,
        "opening": "Write a complete realistic story in first person, narrated by Ren, a station attendant closing a small railway station for the night.",
        "requirements": [
            "Introduce a stranded passenger carrying a violin case and explain why they cannot simply board another train.",
            "Have Ren face a choice between finishing the shift on time and helping the passenger.",
            "Use dialogue to reveal that Ren's initial assumption about the passenger was mistaken.",
            "Resolve how the passenger will leave safely and end with Ren accepting the personal inconvenience of helping.",
        ],
        "critical": ["The passenger's immediate predicament remains unresolved.", "The central narrator becomes another person without explanation."],
    },
    {
        "title": "A map after the flood", "subtype": "story", "budget": 1024,
        "opening": "Write a complete adventure story in third person about Sora, a village mapmaker, and Tavi, a courier navigating a forest after a flood.",
        "requirements": [
            "Establish a delivery that matters to the village and show that a familiar bridge has been washed away.",
            "Introduce an old map with one misleading detail and one useful clue before either affects the route.",
            "Show Sora and Tavi disagreeing about a route, testing an observation, and revising their plan together.",
            "Bring them to the destination without restoring the bridge by coincidence, and end with Sora correcting the map based on what they learned.",
        ],
        "critical": ["The delivery is left unresolved or succeeds only because the bridge inexplicably reappears.", "The misleading detail never affects the journey and no map correction occurs."],
    },
    {
        "title": "The imperfect loaf", "subtype": "story", "budget": 512,
        "opening": "Write a complete realistic story in third person about Jules, an apprentice baker entering a neighborhood baking contest.",
        "requirements": [
            "Introduce a flaw in Jules's loaf and show why it matters personally rather than only competitively.",
            "Have another contestant need help while Jules still has time to work on the loaf.",
            "Show Jules choosing to help, with a concrete cost to the presentation and a short exchange of dialogue.",
            "Reveal that Jules does not win first prize, then end with a specific sign of earned community appreciation.",
        ],
        "critical": ["Jules wins first prize despite the explicit ending requirement.", "The response never reveals the contest outcome."],
    },
]


def build(tokenizer):
    tasks = []
    for index, spec in enumerate(SPECS, 1):
        low, high = (200, 280) if spec["budget"] == 512 else (450, 600)
        requirements = [{"id": f"r{i}", "description": text} for i, text in enumerate(spec["requirements"], 1)]
        prompt = (f"{spec['opening']}\n\nWrite {low}-{high} words. Develop the ideas or events rather than giving an outline.\n"
                  + "\n".join(f"{i}. {r['description']}" for i, r in enumerate(requirements, 1)))
        criteria = [{"id": r["id"], "description": r["description"], "max_score": 2,
                     "requirement_id": r["id"]} for r in requirements]
        technical = spec["subtype"] == "technical_explanation"
        criteria += [
            {"id": "correctness", "description": "Material claims and worked examples are accurate." if technical else
             "Characters, setting, causal events, and ending remain internally consistent.", "max_score": 2},
            {"id": "coherence", "description": "The response is organized, understandable, and has a complete ending or conclusion.", "max_score": 2},
            {"id": "development", "description": "The requested length is used for substantive development, without padding or excessive repetition.", "max_score": 2},
        ]
        task = {
            "schema_version": 1, "task_id": f"long_gen-v1-{index:03d}", "type": "long_gen",
            "subtype": spec["subtype"], "title": spec["title"], "system": SYSTEM, "prompt": prompt,
            "requirements": requirements, "execution": {"model_calls": 1, "tool_calls": 0},
            "generation": {"max_tokens": spec["budget"], "temperature": 0.0, "ignore_eos": False},
            "evaluation": {
                "method": "rubric", "rubric_version": "1", "criteria": criteria,
                "score_scale": {"0": "Unmet, absent, or materially wrong.", "1": "Partially met; substantive omissions or weaknesses remain.",
                                "2": "Fully met; no material omission or error for this criterion."},
                "word_count": {"min": low, "max": high, "method": "len(text.split())", "scope": "entire response including headings and code"},
                "pass_rule": {"minimum_total": 12, "maximum_total": 14, "minimum_each_criterion": 1,
                              "required_full_score": ["correctness"], "word_range_required": True,
                              "execution_complete_required": True, "critical_failures_allowed": 0},
                "critical_failures": spec["critical"],
                "reference_notes": spec.get("notes", ["No single reference story. Accept any plot and wording satisfying the explicit prompt and consistency criteria."]),
                "reference_sources": spec.get("sources", []),
                "review_protocol": "Score every criterion with evidence from the response. Record critical errors. Judge after the timed run without scheduler labels. Missing judgments are pending, not passes.",
            },
            "source": {"dataset": "llmsys-authored-writing", "version": "1", "split": "development",
                       "question_id": f"writing-{index:03d}", "title": spec["title"],
                       "authoring": "Original prompts and rubrics authored with the project assistant; no AWS model generation.",
                       "reference_checked_on": "2026-11-03" if technical else None},
        }
        n_tokens = len(tokenizer.encode(chatml(SYSTEM, [("user", prompt)]), add_special_tokens=False).ids)
        task["length"] = {"prompt_tokens": n_tokens, "context_limit": 4096,
                          "reserved_output_tokens": spec["budget"], "safety_margin_tokens": 128,
                          "tokenizer_model": MODEL, "tokenizer_revision": REVISION,
                          "tokenizer_sha256": TOKENIZER_SHA256, "tokenizer_library": "tokenizers==0.22.1", "server_verified": False}
        if n_tokens + spec["budget"] + 128 > 4096:
            raise ValueError("Task exceeds context budget")
        tasks.append(task)
    return tasks


def write_outputs(tasks, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / "long_generation.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tasks), encoding="utf-8", newline="\n")
    parts = ["# Long generation: 10 writing tasks\n",
             "Five technical explanations and five stories. Each uses one model call and no tools. Flag issues by task ID.\n",
             f"**Shared system instruction:** {SYSTEM}\n",
             "Only the system instruction and prompt are sent to the model. Rubrics, reference notes, and sources are evaluator-only. Temperature is 0 and natural EOS is enabled. Output caps are maxima, not forced generation lengths.\n",
             "## Scoring rules fixed before experiments\n",
             "Each task has seven criteria worth 0 (unmet), 1 (partially met), or 2 (fully met). A quality pass requires valid execution, 12/14 total, at least 1 on every criterion, 2 on correctness/consistency, the stated word range, and no critical failure. Count words with `len(text.split())`, including headings and code.\n",
             "Report completion rate, per-criterion scores, total score, length compliance, and quality pass rate separately. Failed execution cannot pass quality. Unjudged completed outputs remain pending; do not silently drop them. Human or LLM judging has not been run. These authored rubrics are operational criteria, not universal measures of writing quality.\n",
             "Input counts use the pinned upstream Qwen tokenizer and ChatML. AWS inference, deployed-tokenizer verification, and actual response-length checks remain pending.\n",
             "## Index\n", "| Task | Topic | Kind | Input tokens | Output cap | Words |", "|---|---|---|---:|---:|---|"]
    for t in tasks:
        w = t["evaluation"]["word_count"]
        parts.append(f"| [{t['task_id']}](#{t['task_id']}) | {t['title']} | {t['subtype']} | {t['length']['prompt_tokens']} | {t['generation']['max_tokens']} | {w['min']}-{w['max']} |")
    for t in tasks:
        e = t["evaluation"]
        parts += [f"\n## {t['task_id']}\n", f"**{t['title']}**\n", f"### Prompt\n\n{t['prompt']}\n", "### Evaluation rubric\n"]
        parts += [f"- **{c['id']} (0-2):** {c['description']}" for c in e["criteria"]]
        parts += ["\n**Critical failures (any one prevents a pass):**\n"]
        parts += [f"- {error}" for error in e["critical_failures"]]
        parts += ["\n**Reference notes:**\n"]
        parts += [f"- {note}" for note in e["reference_notes"]]
        if e["reference_sources"]:
            parts += ["\n**Sources checked for the reference notes:**\n"]
            parts += [f"- [{ref['title']}]({ref['url']})" for ref in e["reference_sources"]]
    (out / "long_generation_review.md").write_text("\n".join(parts) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", type=Path, required=True, help=TOKENIZER_URL)
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).parent / "tasks/v1")
    args = parser.parse_args()
    if hashlib.sha256(args.tokenizer.read_bytes()).hexdigest() != TOKENIZER_SHA256:
        parser.error("Use the pinned Qwen tokenizer file")
    from tokenizers import Tokenizer
    tasks = build(Tokenizer.from_file(str(args.tokenizer)))
    write_outputs(tasks, args.out_dir)
    print(f"Wrote {len(tasks)} tasks; prompt tokens: {[t['length']['prompt_tokens'] for t in tasks]}")
