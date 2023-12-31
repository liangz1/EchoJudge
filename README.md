# EchoJudge
At its core, EchoJudge is an LLM Judge that aligns with human feedback, emulating human preferences extracted from human_feedback.yaml datasets to deliver consistent ratings. This alignment ensures that similar questions receive similar reward scores, suitable for regression tests. EchoJudge is for developers seeking to refine and test their RAG applications with both human-guided AI feedback. 

Pitch sketch:

**Detailed Problem Description (WHAT)**
What are the pain points in current RAG development or decision-making processes that EchoJudge aims to address?

1. There is no convenient UI for RAG app developers and domain experts to view, grade, comment, and express preference to conversations in RAG usage logs. People currently use spreadsheets, google docs, jsonl files to store the human feedback data. After an update, there is no easy way to parse, recompile, and access them programatically.
2. It's hard to run regression tests on manually identified issues, represented by one or more examples showing why the answer is good or bad. On one hand, genai metrics like "helpfulness", "context_relevancy" are not sufficient to capture the key parts that need to be distinguished for each identified issue. On the other hand, the judge also needs domain knowledge to tell whether the answer is good. LLM judge without ground-truth domain knowledge cannot judge correctly.

**Target Audience (WHO)**: RAG developers and domain experts.

**Importance of the Problem (WHY)**: Without addressing the pain points, developers cannot efficiently:
1. Collect human feedback from domain experts and themselves, maintain and iterate on the curated records.
2. Use human feedback to assess and have a global view the quality of the RAG app.
3. Use human feedback as a guidance to improve the quality of the RAG app, and verify the fix, and run the regression tests.

**Expected Impact/Benefit (Impact)**: 

**Unique Selling Proposition**:
This solution is simple:
1. UI: Just open the yaml file in VSCode.
2. Design and implementation: A couple of python classes.
3. Easy onboarding: Any existing RAG app can onboard this tool by mapping their usage log columns to the required yaml fields.

**Examples or Use Cases**: Onboarding Bricky (Databricks Help assistant) usage logs.
```python
traces_human = ...load from "bricky_human_feedback.yaml"
# Show traces before calling the EchoJudge

judge = EchoJudge()
judge.align(traces_human)
traces_ai = judge.evaluate(traces_human, responder=["bricky"])

# Show traces after calling the EchoJudge

# You can evaluate multiple responders
traces_ai_2 = judge.evaluate(traces_human, responders=["bricky", "gemini_pro", "gpt_4"])

# You can write the new traces_ai_2 to "bricky_human_feedback.yaml" without losing existing information, just added ai grading results.

# You can check the scores:
human_scores = Trace.aggregate(judge="human", responders=["bricky", "gemini_pro", "gpt_4"])
human_scores == {"bricky": 0.4, "gemini_pro": 0.8, "gpt_4": 0.7}
ai_scores = Trace.aggregate(judge="ai", responders=["bricky", "gemini_pro", "gpt_4"])
ai_scores == {"bricky": 0.35, "gemini_pro": 0.85, "gpt_4": 0.75}

# You can open "bricky_human_feedback.yaml" in VSCode to see the details
```

## RAG evaluation datasets for EchoJudge: human_feedback.yaml

Humans may want to provide 3 types of feedback:
1. rating+reason to existing records
1. pick a preferred answer from 2+ model's response: the simplest task. sometimes I just want to say "this one Bricky is better than bard, that one bard is the best". I can quickly label many records.
1. Manually write a preferred answer (in practice, I may improve based on the currently best response. If all responses are pretty bad, I actually don't want to write a good one from scratch.)

Requirements for human_feedback.yaml template:
1. Support all 3 forms of feedback (many fields can be optional though)
1. Unify Human feedback and AI feedback.


## EchoJudge

Proposal:
```python
echo_judge = EchoJudge(persist_dir="path/to/dir")

echo_judge.align(trace)
echo_judge.evaluate(trace)

echo_judge.persist()

# You can always rerun the alignment loop, and if already aligned, no-op.
```

Low-hanging fruit

Dataset parser

1. Golden dataset ingestion from csv: The source csv should be allowed to have duplicate records/questions, while the yaml golden dataset may not want to have duplicate records.
