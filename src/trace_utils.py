from pydantic import BaseModel, Field, validator
from typing import ClassVar, List
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
        description="Name of the judge (ai or human)",
        pattern="ai|human"
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
        pattern="ai|human"
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

class BrickyEvaluationDataset(BaseModel):
    traces: List[Trace] = Field(description="List of Traces", default=[])
    
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
        traces_for_dump = [t.dict_for_yaml_print() for t in self.traces]
        with open("bricky_human_feedback.yaml", "w") as f:
            f.write(yaml.dump(
                traces_for_dump, 
                sort_keys=False, 
                allow_unicode=True, 
                indent=4,
                default_flow_style=False,
            ))
    
    @classmethod
    def load_from_yaml_file(cls):
        with open("bricky_human_feedback.yaml", "r") as file:
            data = yaml.safe_load(file)
        dataset = cls()
        dataset.traces = [Trace.from_dict(d) for d in data]
        return dataset