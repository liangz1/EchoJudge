from pydantic import BaseModel, Field, validator
from typing import List, Optional
import ast
import pandas as pd
import uuid
import yaml


class LongStr(BaseModel):
    text: str

def long_str_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data.text, style='>')

yaml.add_representer(LongStr, long_str_representer)

class Criterion(BaseModel):
    name: str = Field(..., description="Name of the criterion being evaluated")
    rating: int = Field(..., description="Rating for the criterion: 1 for good, -1 for bad, 0 for no signal")
    reason: str = Field(..., description="Explanation for the rating")
    tags: List[str] = Field(description="List of tags associated with the criterion", default=[])

    @classmethod
    def retrieval(cls):
        return cls(
            name="retrieval",
            rating=0,
            reason="we don't know what is retrieved",
        )

    @classmethod
    def answer(cls):
        return cls(
            name="answer",
            rating=1,
            reason="helpful",
        )

class Grading(BaseModel):
    judge_name: str = Field(
        ...,
        description="Name of the judge (ai or human)"
    )
    criteria: List[Criterion] = Field(..., description="List of criteria evaluated by the judge")
    
    @classmethod
    def example(cls):
        return cls(
            judge_name="human",
            criteria=[
                Criterion.retrieval(),
                Criterion.answer(),
            ],
        )

class Response(BaseModel):
    responder_name: str = Field(..., description="Name of the responder who provided the response")
    response_text: LongStr = Field(..., description="Text of the response")
    source: List[str] = Field(description="List of strings for retrieved source doc IDs", default=[])
    gradings: List[Grading] = Field(description="List of gradings to the response", default=[Grading.example()])

    @classmethod
    def example(cls, responder_name):
        return cls(
            responder_name=responder_name,
            response_text=LongStr(text=\
                "placeholder\n"
                "answer " + uuid.uuid4().hex[:6]
            ),
            source=["(placeholder) https://github.com/liangz1/EchoJudge/tree/main"],
            gradings=[Grading.example()]
        )
    
class CandidatePair(BaseModel):
    candidate_1: str
    candidate_2: str

class Preference(BaseModel):
    judge_name: str = Field(
        ...,
        description="Name of the judge (ai or human)",
    )
    candidates: CandidatePair
    preferred_candidate: str

    @validator('preferred_candidate')
    def validate_preferred_candidate(cls, v, values, **kwargs):
        if 'candidates' in values and v not in [values['candidates'].candidate_1, values['candidates'].candidate_2]:
            raise ValueError(f"preferred_candidate must be either '{values['candidates'].candidate_1}' or '{values['candidates'].candidate_2}'")
        return v

    @classmethod
    def example(cls):
        return cls(
            judge_name="human",
            candidates=CandidatePair(
                candidate_1="(placeholder) bot_v1",
                candidate_2="(placeholder) bot_v2",
            ),
            preferred_candidate="(placeholder) bot_v1",
        )

class Trace(BaseModel):
    trace_id: int
    user_input: str = Field(..., description="User input that prompted the responses")
    responses: List[Response] = Field(description="List of responses to the user input", default=[Response.example("bot_v1"), Response.example("bot_v2")])
    preferences: List[Preference] = Field(description="List of preferences from judges", default=[Preference.example()])

    def validate(self):
        for preference in self.preferences:
            # Check if candidate_1, candidate_2 exist in responders
            responders = [response.responder_name for response in self.responses]
            if preference.candidates.candidate_1 not in responders:
                raise ValueError(f"candidate_1: {preference.candidates.candidate_1} not found in responders: {responders}")
            if preference.candidates.candidate_2 not in responders:
                raise ValueError(f"candidate_2: {preference.candidates.candidate_2} not found in responders: {responders}")
        return v

    @classmethod
    def example(cls):
        return cls(
            trace_id=0,
            user_input="(placeholder) What is EchoJudge?",
        )

    @classmethod
    def from_dict(cls, serialized):
        for i, response in enumerate(serialized["responses"]):
            response_text = response["response_text"]
            serialized["responses"][i]["response_text"] = {"text": response_text}
        return cls(**serialized)
    
    def dict_for_yaml_print(self):
        serialized = self.dict()
        for i, response in enumerate(self.responses):
            # reapply LongStr for printing ">-" in yaml dump
            serialized["responses"][i]["response_text"] = response.response_text
        return serialized

    @classmethod
    def from_usage_log(cls, trace_id, user_input, responder_name, response_text, source=[]):
        return cls(
            trace_id=trace_id,
            user_input=user_input,
            responses=[
                Response(
                    responder_name=responder_name,
                    response_text=LongStr(text=response_text),
                    source=source,
                ),
                Response.example("gemini_pro"),
                 Response.example("gpt_4"),
            ],
        )


class Traces(BaseModel):
    traces: List[Trace] = Field(description="List of Traces", default=[])

    def write_to_yaml_file(self, path: str):
        traces_for_dump = [t.dict_for_yaml_print() for t in self.traces]
        with open(path, "w") as f:
            f.write(yaml.dump(
                traces_for_dump, 
                sort_keys=False, 
                allow_unicode=True, 
                indent=4,
                default_flow_style=False,
            ))

    @classmethod
    def load_from_yaml_file(cls, path: str):
        with open(path, "r") as file:
            data = yaml.safe_load(file)
        dataset = cls()
        dataset.traces = [Trace.from_dict(d) for d in data]
        return dataset
    
    def count(self):
        return len(self.traces)
    
    def avg_score(self, *, responder_name: str, judge_name: str, criterion: str):
        scores = []
        for trace in self.traces:
            for response in trace.responses:
                if response.responder_name == responder_name:
                    for grading in response.gradings:
                        if grading.judge_name == judge_name:
                            for c in grading.criteria:
                                if c.name == criterion:
                                    scores.append(c.rating)
        return sum(scores) / len(scores)
    
    def select(self, *, 
               responder_name: Optional[str] = None,
               judge_name: Optional[str] = None,
               criterion: Optional[str] = None,
               rating: Optional[int] = None,
               preferred_candidate: Optional[str] = None):
        selected_traces = []
        if responder_name and judge_name and criterion and rating is not None:
            # Filter based on responder_name, judge_name, criterion, and rating
            for trace in self.traces:
                for response in trace.responses:
                    if (response.responder_name == responder_name and
                        any(grading.judge_name == judge_name and
                            any(c.name == criterion and c.rating == rating for c in grading.criteria)
                            for grading in response.gradings)):
                        selected_traces.append(trace)
        elif judge_name and preferred_candidate:
            # Filter based on judge_name and preferred_candidate
            for trace in self.traces:
                for preference in trace.preferences:
                    if preference.judge_name == judge_name and preference.preferred_candidate == preferred_candidate:
                        selected_traces.append(trace)
        else:
            raise ValueError("Invalid combination of arguments")

        return Traces(traces=selected_traces)


class BrickyEvaluationDataset(Traces):
    """
    # Usage in notebook
    # importlib.reload(trace_utils)
    # from trace_utils import Trace, BrickyEvaluationDataset
    # csv_path = "../Bricky/gold_docs_qna_conversation_turns_2023_11_13.csv"
    # dataset = BrickyEvaluationDataset()
    # dataset.add_traces_from_usage_log_csv(csv_path)
    # dataset.write_to_yaml_file()
    # loaded_dataset = BrickyEvaluationDataset.load_from_yaml_file()
    # loaded_dataset.traces[21]
    """
    
    def add_traces_from_usage_log_csv(self, path):
        df = pd.read_csv(path)
        df["conversation_service_branch_names"] = df["conversation_service_branch_names"].apply(ast.literal_eval)
        for i, row in df.iterrows():
            t = Trace.from_usage_log(
                trace_id=len(self.traces),
                user_input=row["user_message"],
                responder_name="bricky@"+row["conversation_service_branch_names"][0],
                response_text=row["assistant_message"],
                source=[row["source_shown_to_user"]],
            )
            self.traces.append(t)
    
    def write_to_yaml_file(self):
        super(self).write_to_yaml_file("../data/bricky_from_users.yaml")
    
    @classmethod
    def load_from_yaml_file(cls):
        super(cls).load_from_yaml_file("../data/bricky_from_users.yaml")


class DatabricksSyntheticDataset(Traces):
    """
    # Usage in notebook
    # importlib.reload(trace_utils)
    # from trace_utils import Trace, DatabricksSyntheticDataset
    # csv_path = "../DatabricksSynthetic/question_answer_chunk_direct_context.csv"
    # dsd = DatabricksSyntheticDataset()
    # dsd.add_traces_from_csv(csv_path)
    # dsd.write_to_yaml_file()
    """
    
    def add_traces_from_csv(self, path):
        df = pd.read_csv(path, index_col=0)
        for i, row in df.iterrows():
            generated_ground_truth_answer = Response(
                responder_name="generated_ground_truth_answer",
                response_text=LongStr(text=row["answer"]),
                source=[row["chunk"]],
            )
            directly_answered_by_gpt_35 = Response(
                responder_name="directly_answered_by_gpt_35",
                response_text=LongStr(text=row["directly_answered_by_gpt35"]),
            )
            answered_by_gpt_35_with_ground_truth_context = Response(
                responder_name="answered_by_gpt_35_with_ground_truth_context",
                response_text=LongStr(text=row["answered_by_gpt35_with_context"]),
            )
            t = Trace(
                trace_id=i,
                user_input=row["question"],
                responses=[
                    generated_ground_truth_answer,
                    directly_answered_by_gpt_35,
                    answered_by_gpt_35_with_ground_truth_context,
                ],
            )
            self.traces.append(t)
    
    def write_to_yaml_file(self):
        super(self).write_to_yaml_file("../data/databricks_docs_synthetic_domain_knowledge.yaml")
    
    @classmethod
    def load_from_yaml_file(cls):
        super(cls).load_from_yaml_file("../data/databricks_docs_synthetic_domain_knowledge.yaml")
    