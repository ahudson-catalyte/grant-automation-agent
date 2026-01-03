from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.models.schemas import Timeline, Budget, WorkPlan, GrantData
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv
import time
import json

load_dotenv()

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"


class LLMService:
    """Service for interacting with OpenAI via LangChain"""
    
    def __init__(self):
        if not DEMO_MODE:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0,
                api_key=os.getenv("OPENAI_API_KEY"),
                request_timeout=60,
                max_tokens=3000
            )
        else:
            print("⚠️  DEMO MODE ENABLED - Using mock data instead of OpenAI")
    
    def extract_all_data_single_call(self, text: str) -> GrantData:
        """
        Extract ALL grant data in a SINGLE LLM call with deep analysis.
        This extracts not just data, but the REQUIREMENTS and SPECIFICATIONS.
        """
        
        # Truncate text if too long
        max_input_length = 12000
        if len(text) > max_input_length:
            print(f"⚠ Text too long ({len(text)} chars), truncating to {max_input_length}")
            text = text[:max_input_length] + "\n...[truncated]"
        
        prompt = ChatPromptTemplate.from_template("""
You are a grant management expert AI. Analyze this grant acceptance letter and extract ALL requirements, specifications, and details.

CRITICAL: Extract ACTUAL requirements from the letter, not generic assumptions.

Extract the following:

1. BASIC INFORMATION:
   - organization_name: Recipient organization
   - grant_title: Official grant program name
   - grant_amount: Total award (number only, e.g., 50000)
   - grant_period: Exact dates/duration from letter
   - funder_name: Funding organization name

2. TIMELINE (extract ALL dates, deadlines, and milestones mentioned):
   For each timeline item, identify:
   - date: The actual date (convert relative dates like "within 30 days" to approximate dates)
   - amount: Payment amount if applicable (as string like "$25,000")
   - description: What is due/happening
   - category: Type (payment, report, deliverable, milestone, meeting, compliance, deadline, submission)
   
   MUST INCLUDE:
   - Grant start and end dates
   - All payment/disbursement dates
   - All report submission deadlines (interim, final, quarterly, etc.)
   - All deliverable due dates
   - Any compliance or documentation deadlines
   - Any required meetings or check-ins
   - Project milestone dates mentioned

3. BUDGET (extract budget requirements and restrictions):
   - total_grant_amount: Total award amount
   - items: Budget line items with:
     * category: Specific category name from letter (e.g., "Personnel - Program Coordinator", "Educational Materials")
     * amount: Dollar amount (number)
     * description: Specific allowed uses from letter
     * timeline: When funds should be used (if specified)
   
   EXTRACT:
   - Specific budget categories mentioned in letter
   - Any percentage restrictions (e.g., "no more than 15% for admin")
   - Allowable and non-allowable expenses
   - Match requirements
   - Indirect cost limits

4. WORK PLAN (extract required activities and deliverables):
   - project_title: Project name from letter
   - grant_period: Duration
   - tasks: For each required activity:
     * task_name: Specific activity name from letter
     * description: Detailed requirements from letter
     * start_date: When to start (from letter or inferred)
     * end_date: When to complete
     * responsible_party: Who is responsible (if specified)
     * deliverables: EXACT deliverables required by letter (e.g., "50 participants enrolled", "100 hours of instruction")
   
   EXTRACT:
   - Specific activities/programs required by funder
   - Measurable outcomes expected
   - Target populations to serve
   - Required partnerships or collaborations
   - Evaluation/assessment requirements

5. REPORTING REQUIREMENTS (extract what reports are needed):
   Add as timeline items AND describe in tasks:
   - Frequency (monthly, quarterly, annual, final)
   - Format requirements
   - What must be included
   - Supporting documentation needed
   - Financial vs. narrative reports

6. COMPLIANCE & RESTRICTIONS:
   Include in timeline and work plan:
   - Required approvals for changes
   - Spending restrictions
   - Documentation requirements
   - Site visit expectations
   - Audit requirements

RULES:
- Use ACTUAL information from the letter, not assumptions
- If amount shows as "X,000", try to determine from context or use 0
- Convert all monetary values to numbers
- Use null for truly missing fields
- Be specific: "Educational supplies" not "Supplies"
- Include ALL deadlines and requirements
- Return ONLY valid JSON

Document:
{text}

Return JSON in this structure:
{{
  "organization_name": "...",
  "grant_title": "...",
  "grant_amount": 50000,
  "grant_period": "...",
  "funder_name": "...",
  "timeline": [
    {{
      "date": "2025-02-01",
      "amount": null,
      "description": "Grant period begins",
      "category": "milestone"
    }},
    {{
      "date": "2025-02-15",
      "amount": "$25,000",
      "description": "First disbursement - Initial payment",
      "category": "payment"
    }},
    {{
      "date": "2025-07-31",
      "amount": null,
      "description": "Interim progress report due",
      "category": "report"
    }}
  ],
  "budget": {{
    "total_grant_amount": 50000,
    "items": [
      {{
        "category": "Personnel - Program Coordinator",
        "amount": 25000,
        "description": "Salary and benefits for full-time program coordinator",
        "timeline": "Throughout grant period"
      }},
      {{
        "category": "Educational Materials",
        "amount": 10000,
        "description": "Curriculum materials, workbooks, and supplies for 50 participants",
        "timeline": "Months 1-3"
      }}
    ]
  }},
  "workplan": {{
    "project_title": "...",
    "grant_period": "...",
    "tasks": [
      {{
        "task_name": "Program Setup and Staffing",
        "description": "Hire program coordinator, establish program framework, secure classroom space",
        "start_date": "2025-02-01",
        "end_date": "2025-03-15",
        "responsible_party": "Executive Director",
        "deliverables": "Program coordinator hired, program framework document completed, signed facility agreement"
      }},
      {{
        "task_name": "Participant Recruitment",
        "description": "Recruit and enroll 50 participants from target community as specified in proposal",
        "start_date": "2025-03-01",
        "end_date": "2025-04-30",
        "responsible_party": "Program Coordinator",
        "deliverables": "50 participants enrolled with completed applications and eligibility verification"
      }}
    ]
  }}
}}
""")
        
        def make_call():
            chain = prompt | self.llm
            response = chain.invoke({"text": text})
            return response.content
        
        # Make the call
        response_text = make_call()
        
        # Parse JSON response
        try:
            # Clean response
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            data = json.loads(response_text)
            
            # Build Timeline
            timeline = None
            if data.get('timeline'):
                from app.models.schemas import TimelineItem
                timeline_items = [TimelineItem(**item) for item in data['timeline']]
                # Sort by date
                timeline_items.sort(key=lambda x: x.date)
                timeline = Timeline(items=timeline_items)
            
            # Build Budget  
            budget = None
            if data.get('budget') and data['budget'].get('items'):
                from app.models.schemas import BudgetItem
                budget_items = [BudgetItem(**item) for item in data['budget']['items']]
                budget = Budget(
                    total_grant_amount=data['budget'].get('total_grant_amount', 0),
                    items=budget_items
                )
            
            # Build WorkPlan
            workplan = None
            if data.get('workplan') and data['workplan'].get('tasks'):
                from app.models.schemas import WorkPlanTask
                workplan_tasks = [WorkPlanTask(**task) for task in data['workplan']['tasks']]
                workplan = WorkPlan(
                    project_title=data['workplan'].get('project_title', ''),
                    grant_period=data['workplan'].get('grant_period', ''),
                    tasks=workplan_tasks
                )
            
            return GrantData(
                organization_name=data.get('organization_name'),
                grant_title=data.get('grant_title'),
                grant_amount=data.get('grant_amount'),
                grant_period=data.get('grant_period'),
                funder_name=data.get('funder_name'),
                timeline=timeline,
                budget=budget,
                workplan=workplan,
                raw_text=text
            )
            
        except Exception as e:
            print(f"❌ LLM extraction error: {e}")
            print(f"Response was: {response_text[:500]}")
            raise
    
    def extract_all_data(self, text: str) -> GrantData:
        """Main entry point - extracts grant data with fallback"""
        
        if DEMO_MODE:
            return self._get_demo_data(text)
        
        try:
            return self.extract_all_data_single_call(text)
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            
            # Return minimal data with raw text
            return GrantData(
                organization_name=None,
                grant_title="Processing Failed",
                grant_amount=None,
                grant_period=None,
                funder_name=None,
                timeline=None,
                budget=None,
                workplan=None,
                raw_text=text
            )
    
    def _get_demo_data(self, text: str) -> GrantData:
        """Return demo/mock data for testing"""
        from app.models.schemas import (
            Timeline, TimelineItem, 
            Budget, BudgetItem,
            WorkPlan, WorkPlanTask
        )
        
        timeline = Timeline(items=[
            TimelineItem(
                date="2025-02-01",
                amount=None,
                description="Grant period begins - Project kickoff",
                category="milestone"
            ),
            TimelineItem(
                date="2025-02-15",
                amount="$25,000",
                description="First payment disbursement (50% of total award)",
                category="payment"
            ),
            TimelineItem(
                date="2025-03-15",
                amount=None,
                description="Program coordinator hiring completed",
                category="deliverable"
            ),
            TimelineItem(
                date="2025-04-30",
                amount=None,
                description="Participant enrollment deadline - 50 participants required",
                category="deliverable"
            ),
            TimelineItem(
                date="2025-07-31",
                amount=None,
                description="Interim progress report and financial statement due",
                category="report"
            ),
            TimelineItem(
                date="2025-08-15",
                amount="$25,000",
                description="Second payment disbursement (remaining 50%)",
                category="payment"
            ),
            TimelineItem(
                date="2025-12-31",
                amount=None,
                description="Program completion - All 100 instruction hours delivered",
                category="deliverable"
            ),
            TimelineItem(
                date="2026-01-31",
                amount=None,
                description="Grant period ends",
                category="milestone"
            ),
            TimelineItem(
                date="2026-02-28",
                amount=None,
                description="Final report, financial statement, and outcomes assessment due",
                category="report"
            )
        ])
        
        budget = Budget(
            total_grant_amount=50000.00,
            items=[
                BudgetItem(
                    category="Personnel - Program Coordinator", 
                    amount=25000, 
                    description="Full-time program coordinator salary and benefits for 12-month grant period",
                    timeline="February 2025 - January 2026"
                ),
                BudgetItem(
                    category="Educational Materials and Curriculum", 
                    amount=10000, 
                    description="Workbooks, textbooks, online learning subscriptions, and supplies for 50 participants",
                    timeline="Months 1-3 (February-April 2025)"
                ),
                BudgetItem(
                    category="Technology and Equipment", 
                    amount=8000, 
                    description="10 tablets for participants, software licenses, and educational technology",
                    timeline="Month 1 (February 2025)"
                ),
                BudgetItem(
                    category="Program Supplies and Materials", 
                    amount=4000, 
                    description="General classroom supplies, printing, and participant materials",
                    timeline="Throughout grant period"
                ),
                BudgetItem(
                    category="Administrative and Indirect Costs", 
                    amount=3000, 
                    description="Administrative overhead, facilities, utilities (not to exceed 6% of total)",
                    timeline="Throughout grant period"
                ),
            ]
        )
        
        workplan = WorkPlan(
            project_title="Youth Education and Empowerment Initiative",
            grant_period="February 1, 2025 - January 31, 2026",
            tasks=[
                WorkPlanTask(
                    task_name="Program Setup and Infrastructure",
                    description="Hire program coordinator, establish program framework, secure classroom space, and set up technology infrastructure",
                    start_date="2025-02-01",
                    end_date="2025-03-15",
                    responsible_party="Executive Director and HR Manager",
                    deliverables="Program coordinator hired and onboarded, program operations manual completed, signed facility use agreement, technology setup complete"
                ),
                WorkPlanTask(
                    task_name="Participant Recruitment and Enrollment",
                    description="Recruit 50 eligible youth participants from target communities through community outreach, school partnerships, and information sessions",
                    start_date="2025-03-01",
                    end_date="2025-04-30",
                    responsible_party="Program Coordinator and Outreach Team",
                    deliverables="50 participants enrolled with completed applications, eligibility verification, parental consents, and needs assessments"
                ),
                WorkPlanTask(
                    task_name="Curriculum Development and Preparation",
                    description="Develop 100-hour comprehensive education curriculum aligned with grant objectives and participant needs",
                    start_date="2025-03-01",
                    end_date="2025-04-15",
                    responsible_party="Program Coordinator and Education Consultant",
                    deliverables="Complete curriculum guide, lesson plans for 100 hours of instruction, assessment tools, and participant progress tracking system"
                ),
                WorkPlanTask(
                    task_name="Program Implementation - Educational Services",
                    description="Deliver 100 hours of educational instruction to enrolled participants through workshops, tutoring, and mentoring",
                    start_date="2025-05-01",
                    end_date="2025-12-31",
                    responsible_party="Program Coordinator and Teaching Staff",
                    deliverables="100 hours of instruction completed, attendance records, weekly progress reports, participant feedback surveys"
                ),
                WorkPlanTask(
                    task_name="Participant Assessment and Outcomes Measurement",
                    description="Conduct pre and post-program assessments to measure participant progress and program effectiveness",
                    start_date="2025-05-01",
                    end_date="2026-01-15",
                    responsible_party="Program Coordinator and Evaluation Consultant",
                    deliverables="Pre-assessment data for all participants, mid-program progress checks, final post-assessments, outcomes analysis report"
                ),
                WorkPlanTask(
                    task_name="Interim Reporting and Compliance",
                    description="Prepare and submit interim progress report and financial statement as required by funder",
                    start_date="2025-07-01",
                    end_date="2025-07-31",
                    responsible_party="Program Coordinator and Finance Manager",
                    deliverables="Interim progress report submitted, financial statement with supporting documentation, attendance and outcomes data"
                ),
                WorkPlanTask(
                    task_name="Final Reporting and Grant Closeout",
                    description="Complete final program evaluation, compile all required documentation, and submit comprehensive final report",
                    start_date="2026-01-15",
                    end_date="2026-02-28",
                    responsible_party="Program Coordinator and Executive Director",
                    deliverables="Final narrative report, complete financial statement, outcomes assessment, participant testimonials, sustainability plan"
                ),
            ]
        )
        
        return GrantData(
            organization_name="Community Empowerment Foundation",
            grant_title="Mesa Pathways Innovation Grant 2025",
            grant_amount=50000.00,
            grant_period="February 1, 2025 - January 31, 2026",
            funder_name="Mesa Pathways Committee",
            timeline=timeline,
            budget=budget,
            workplan=workplan,
            raw_text=text
        )