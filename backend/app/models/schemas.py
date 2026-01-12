from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class TimelineItem(BaseModel):
    """Individual timeline event"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    date: Optional[str] = Field(None, description="Due date or deadline")
    amount: Optional[str] = Field(None, description="Money involved, if any")
    description: str = Field(..., description="Brief description of the event")
    category: Optional[str] = Field(None, description="Event category (milestone, payment, deliverable)")


class Timeline(BaseModel):
    """Complete timeline extraction"""
    items: List[TimelineItem]


class BudgetItem(BaseModel):
    """Individual budget line item"""
    category: str = Field(..., description="Budget category or line item name")
    amount: float = Field(..., description="Dollar amount")
    description: Optional[str] = Field(None, description="Additional details")
    timeline: Optional[str] = Field(None, description="When this should be spent")


class Budget(BaseModel):
    """Complete budget breakdown"""
    total_grant_amount: float
    items: List[BudgetItem]


class WorkPlanTask(BaseModel):
    """Individual task in work plan"""
    task_name: str
    description: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    responsible_party: Optional[str] = None
    deliverables: Optional[str] = None


class WorkPlan(BaseModel):
    """Complete work plan"""
    project_title: str
    grant_period: str
    tasks: List[WorkPlanTask]


class GrantData(BaseModel):
    """Complete extracted grant information"""
    organization_name: Optional[str] = None
    grant_title: Optional[str] = None
    grant_amount: Optional[float] = None
    grant_period: Optional[str] = None
    funder_name: Optional[str] = None
    timeline: Optional[Timeline] = None
    budget: Optional[Budget] = None
    workplan: Optional[WorkPlan] = None
    raw_text: str


class UploadResponse(BaseModel):
    """Response after file upload"""
    success: bool
    message: str
    file_id: str
    filename: str


class GenerateDocumentsRequest(BaseModel):
    """Request to generate documents"""
    file_id: str
    generate_workplan: bool = True
    generate_budget: bool = True
    generate_report_template: bool = True
    generate_calendar: bool = True