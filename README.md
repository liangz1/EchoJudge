# RAG evaluation datasets and EchoJudge

## RAG evaluation datasets: human_feedback.yaml

Humans may want to provide 3 types of feedback:
1. rating+reason to existing records
1. pick a preferred answer from 2+ model's response: the simplest task. sometimes I just want to say "this one Bricky is better than bard, that one bard is the best". I can quickly label many records.
1. Manually write a preferred answer (in practice, I may improve based on the currently best response. If all responses are pretty bad, I actually don't want to write a good one from scratch.)

Requirements for human_feedback.yaml template:
1. Support all 3 forms of feedback (many fields can be optional though)
1. Unify Human feedback and AI feedback.

Design for my yaml template, each entry has:
1. 1 user input
1. 1+ responses, each has
    1. 1 responder (RAG_app_version or human) & their answer
    1. 1 or 2 judges (llm_judge and/or human), each judge has
        1. 1+ criteria, each with rating+reason. Example criteria:
            1. answer
            1. retrieval
            1. code_syntax
            1. guardrail
    1. 0+ ranking pairs from 1 or 2 judges (llm_judge and/or human) in format: `llm_judge/human: responder1 > responder2`

RAG_app_versions can be:
`bricky_version1, lakesense_version123, bard_gemini_pro_1201, ChatGPT_GPT4_0612...`

## EchoJudge
At its core, EchoJudge is an LLM Judge that aligns with human feedback, emulating human preferences extracted from human_feedback.yaml datasets to deliver consistent ratings. This alignment ensures that similar questions receive similar reward scores, suitable for regression tests. EchoJudge is for developers seeking to refine and test their RAG applications with both human-guided AI feedback. 

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
