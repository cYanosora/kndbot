from pydantic import BaseModel, Field


class PlayResult(BaseModel):
    score: int
    last_time: int = Field(alias="last-time")
    nickname: str = ''
    message: str = ''


class SumbitResult(BaseModel):
    message: str = ''
    status: int = 200


class Query(BaseModel):
    id: str = Field(alias="q")


class Token(BaseModel):
    token: str
