
from pydantic import BaseModel, ConfigDict, Field


class TicketCreate(BaseModel):
    order_id: int = Field(gt=0)
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10)


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    subject: str
    description: str
    status: str
