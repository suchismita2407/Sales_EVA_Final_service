from pydantic import BaseModel, ConfigDict, Field


class OpportunityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    client: str = Field(min_length=1, max_length=200)
    industry: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=100)
    stage: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=10000)
    requirements: str = Field(min_length=1, max_length=10000)


class OfferingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    industry: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=10000)
