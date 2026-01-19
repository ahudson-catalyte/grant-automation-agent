from pydantic import BaseModel, Field
from typing import List, Optional


class TimelineItem(BaseModel):
    """Individual timeline event"""
    date: str = Field(..., description="Due date or deadline")
    amount: Optional[str] = Field(None, description="Money involved, if any")
    description: str = Field(..., description="Brief description of the event")
    category: Optional[str] = Field(None, description="Event category")


class Timeline(BaseModel):
    """Complete timeline extraction"""
    items: List[TimelineItem] = Field(default_factory=list)


class BudgetItem(BaseModel):
    """Individual budget line item"""
    category: str = Field(..., description="Budget category")
    amount: float = Field(..., description="Dollar amount")
    description: Optional[str] = Field(None, description="Additional details")
    timeline: Optional[str] = Field(None, description="When to spend")


class Budget(BaseModel):
    """Complete budget breakdown"""
    total_grant_amount: float = Field(default=0.0)
    items: List[BudgetItem] = Field(default_factory=list)


class WorkPlanTask(BaseModel):
    """Individual task in work plan"""
    task_name: str = Field(..., description="Name of the task")
    description: str = Field(..., description="Task description")
    start_date: Optional[str] = Field(None, description="Start date")
    end_date: Optional[str] = Field(None, description="End date")
    responsible_party: Optional[str] = Field(None, description="Who is responsible")
    deliverables: Optional[str] = Field(None, description="Expected deliverables")


class WorkPlan(BaseModel):
    """Complete work plan"""
    project_title: str = Field(default="Project Plan")
    grant_period: str = Field(default="To Be Determined")  # THIS IS THE FIX - default value instead of requiring it
    tasks: List[WorkPlanTask] = Field(default_factory=list)


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
    raw_text: str = Field(..., description="Original text")


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