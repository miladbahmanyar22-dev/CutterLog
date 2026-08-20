# database/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List
from database.models import StageEnum, PaymentTypeEnum


class DriveLocationBase(BaseModel):
    drive_label: str = Field(..., min_length=1, max_length=100)
    absolute_path: str = Field(..., min_length=1)
    is_primary: bool = True


class DriveLocationRead(DriveLocationBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class TransactionBase(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in Toman")
    payment_type: PaymentTypeEnum = PaymentTypeEnum.STAGE_PAYMENT
    tracking_code: Optional[str] = None
    notes: Optional[str] = None
    paid_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class TransactionRead(TransactionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    client_id: int


class ClientBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    company: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientRead(ClientBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    client_id: int
    total_fee: int = Field(default=0, ge=0)
    description: Optional[str] = None
    current_stage: StageEnum = StageEnum.ROUGH_CUT
    deadline: Optional[datetime] = None
    drive_locations: List[DriveLocationBase] = []


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    client_id: int
    total_fee: int
    description: Optional[str]
    current_stage: StageEnum
    deadline: Optional[datetime]
    created_at: datetime
    completed_at: Optional[datetime]
    client: Optional[ClientRead] = None
    drive_locations: List[DriveLocationRead] = []
    transactions: List[TransactionRead] = []