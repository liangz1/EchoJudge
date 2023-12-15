# EchoJudge
At its core, EchoJudge is an LLM Judge that aligns with human feedback, emulating human preferences extracted from human_feedback.yaml datasets to deliver consistent ratings. This alignment ensures that similar questions receive similar reward scores, suitable for regression tests. EchoJudge is for developers seeking to refine and test their RAG applications with both human-guided AI feedback. 

## RAG evaluation datasets for EchoJudge: human_feedback.yaml

Humans may want to provide 3 types of feedback:
1. rating+reason to existing records
1. pick a preferred answer from 2+ model's response: the simplest task. sometimes I just want to say "this one Bricky is better than bard, that one bard is the best". I can quickly label many records.
1. Manually write a preferred answer (in practice, I may improve based on the currently best response. If all responses are pretty bad, I actually don't want to write a good one from scratch.)

Requirements for human_feedback.yaml template:
1. Support all 3 forms of feedback (many fields can be optional though)
1. Unify Human feedback and AI feedback.

Design for my yaml template

♊️ Prompt to generate the Pydantic code: (Gemini Pro did better than GPT-4)
```
Each QAEntry has:
1. 1 user_input: str, required.
2. 1 or more response entries ResponseEntry, each has
    1. responder_name: str, required
    2. response_text: str, required
    3. 0 or more Judges, each Judge has
        1. name: str, "llm_judge" or "human"
        2. 1 or more Criteria, each has
            1. name: str, required
            2. rating: int, required
            3. reason: str, required
            4. tags: a list of Tag, where Tag: str
3. 0 or more RankingPair from a certain judge in the format:
    1. judge_name: str, required
    2. candidates: NamedTuple(candidate_1=responder_name_X, candidate_2=responder_name_Y)
    3. preference: str, value: responder_name_X or responder_name_Y
```

Example criteria:
1. answer
1. retrieval
1. code_syntax
1. guardrail
            
RAG_app_versions can be:
`bricky_version1, lakesense_version123, bard_gemini_pro_1201, ChatGPT_GPT4_0612...`

## EchoJudge

Proposal:
```python
echo_judge = EchoJudge(persist_dir="path/to/dir")
traces = Trace.from_csv(question_column="col1", answer_column="col2")
trace = traces[0]
trace = Trace(question="", answer="")
trace = echo_judge.evaluate(trace)
trace.score == -1/ 0/ 1
trace.reason == "..."

# You can run the loop to make sure the judge converge
echo_judge.align(trace)
echo_judge.evaluate(trace)

echo_judge.persist()

# You can always rerun the alignment loop, and if already aligned, no-op.
```
