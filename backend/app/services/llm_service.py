from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.models.schemas import Timeline, Budget, WorkPlan, GrantData
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv
import json
import re

load_dotenv()

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"


class LLMService:
    """Universal grant letter analysis service that adapts to any grant format"""
    
    def __init__(self):
        if not DEMO_MODE:
            self.llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0,
                api_key=os.getenv("OPENAI_API_KEY"),
                request_timeout=60,
                max_tokens=3500
            )
        else:
            print("⚠️  DEMO MODE ENABLED - Using mock data instead of OpenAI")
    
    def extract_all_data_single_call(self, text: str) -> GrantData:
        """
        Universal grant letter analyzer - works with ANY grant format.
        Intelligently extracts whatever information is available.
        """
        
        # Truncate if needed
        max_input_length = 12000
        if len(text) > max_input_length:
            print(f"⚠ Text truncated from {len(text)} to {max_input_length} characters")
            text = text[:max_input_length] + "\n...[Document continues]"
        
        prompt = ChatPromptTemplate.from_template("""
You are an expert grant analyst. Analyze this grant letter and extract ALL available information.

YOUR GOAL: Extract maximum useful information to help nonprofits manage this grant effectively.

INSTRUCTIONS:
1. Find and extract ANY information present - don't skip anything
2. Infer reasonable defaults when specific details aren't stated
3. Be comprehensive - look for hidden requirements and implicit obligations
4. Categorize timeline items by purpose (payment, report, deliverable, etc.)
5. Extract specific, actionable tasks - not generic statements

EXTRACT THESE CATEGORIES:

═══════════════════════════════════════════════════════════════
1. BASIC GRANT INFORMATION
═══════════════════════════════════════════════════════════════
- organization_name: Who is receiving the grant?
- grant_title: Official name/title of the grant program
- grant_amount: Total dollar amount (extract number, e.g., 50000 not "$50,000")
  * If shows as "X,000" or unclear, look for context clues or use 0
- grant_period: Duration (e.g., "January 1, 2025 - December 31, 2025")
- funder_name: Who is giving the grant?

═══════════════════════════════════════════════════════════════
2. COMPREHENSIVE TIMELINE
═══════════════════════════════════════════════════════════════
Extract EVERY date mentioned. For each:
- date: Actual or estimated date (YYYY-MM-DD format)
- amount: Dollar amount if it's a payment (as string "$X,XXX" or null)
- description: Clear description of what happens/is due
- category: Choose best fit:
  * "payment" - Money being disbursed to organization
  * "report" - Any report due (interim, final, quarterly, etc.)
  * "deliverable" - Specific outputs required (documents, programs, events)
  * "milestone" - Project phase or significant event
  * "compliance" - Legal, regulatory, or administrative requirement
  * "meeting" - Check-ins, site visits, or required meetings
  * "deadline" - General deadlines
  * "submission" - Application or documentation submissions

MUST EXTRACT:
✓ Grant start date (or infer from context)
✓ Grant end date (or infer from duration)
✓ ALL payment dates and amounts
✓ ALL report deadlines (look for "report", "statement", "update")
✓ Any deliverable due dates
✓ Any meetings, check-ins, or site visits
✓ Compliance deadlines (insurance, approvals, etc.)
✓ Budget modification deadlines
✓ Extension request deadlines

CONVERT RELATIVE DATES:
- "within 30 days of award" → Calculate from today/context
- "quarterly" → Create 4 dates
- "by end of grant period" → Use grant end date

═══════════════════════════════════════════════════════════════
3. DETAILED BUDGET ANALYSIS
═══════════════════════════════════════════════════════════════
- total_grant_amount: Total award (number)
- items: Budget categories with details

For each budget category:
- category: Specific name (e.g., "Personnel - Project Manager", "Educational Supplies")
  * Use ACTUAL categories from letter when provided
  * Create reasonable categories if letter is vague
- amount: Dollar amount (number, not string)
- description: Specific allowed uses, restrictions, or requirements
- timeline: When to spend these funds (if mentioned)

LOOK FOR:
✓ Explicit budget breakdowns in letter
✓ Percentage restrictions (e.g., "no more than 15% for admin")
✓ Allowable vs non-allowable expenses
✓ Required cost sharing or matching
✓ Pre-approved categories
✓ Indirect cost rates
✓ Purchase approval requirements

IF NO BUDGET PROVIDED:
Create reasonable standard categories:
- Personnel (40-50%)
- Program Supplies (20-30%)
- Equipment (10-15%)
- Administrative (5-10%)

═══════════════════════════════════════════════════════════════
4. COMPREHENSIVE WORK PLAN
═══════════════════════════════════════════════════════════════
- project_title: Official project name
- grant_period: Duration
- tasks: Specific activities required

For each task/activity:
- task_name: Short, clear activity name
- description: Detailed explanation of what must be done
- start_date: When to begin (YYYY-MM-DD or null)
- end_date: When to complete (YYYY-MM-DD or null)
- responsible_party: Who leads this (if mentioned, else null)
- deliverables: SPECIFIC measurable outputs
  * Use ACTUAL deliverables from letter (e.g., "Enroll 50 participants")
  * Include numbers, quantities, metrics when mentioned
  * Be specific: "Train 100 teachers" not "Provide training"

EXTRACT ACTIVITIES FROM:
✓ Explicit "Scope of Work" sections
✓ "Deliverables" lists
✓ "Activities" or "Tasks" sections
✓ Project description narratives
✓ Requirements scattered throughout letter

CREATE TASKS FOR:
✓ Program setup and planning
✓ Staffing and hiring (if personnel budget exists)
✓ Participant recruitment (if program serves people)
✓ Program implementation
✓ Evaluation and assessment
✓ Reporting activities
✓ Project closeout

INFER TASKS FROM:
✓ Budget categories (e.g., equipment budget → "Procure equipment")
✓ Timeline items (e.g., report due → "Prepare quarterly report")
✓ Grant purpose (e.g., education grant → "Develop curriculum")

═══════════════════════════════════════════════════════════════
CRITICAL REQUIREMENTS FOR JSON OUTPUT
═══════════════════════════════════════════════════════════════
1. All monetary amounts in budget MUST be numbers, not strings
2. All dates in YYYY-MM-DD format
3. Timeline items sorted chronologically
4. No null for arrays - use empty array [] if nothing found
5. Use null only for optional string/date fields
6. Be comprehensive - 15-30 timeline items is normal
7. Be specific - avoid generic descriptions

Document to analyze:
{text}

Return ONLY this JSON structure (no markdown, no explanations):
{{
  "organization_name": "string or null",
  "grant_title": "string or null",
  "grant_amount": 50000,
  "grant_period": "string or null",
  "funder_name": "string or null",
  "timeline": [
    {{
      "date": "2025-02-01",
      "amount": "$25,000",
      "description": "First disbursement payment",
      "category": "payment"
    }}
  ],
  "budget": {{
    "total_grant_amount": 50000,
    "items": [
      {{
        "category": "Personnel - Program Director",
        "amount": 30000,
        "description": "Salary and benefits for full-time program director",
        "timeline": "Throughout grant period"
      }}
    ]
  }},
  "workplan": {{
    "project_title": "string",
    "grant_period": "string",
    "tasks": [
      {{
        "task_name": "Program Planning and Setup",
        "description": "Establish program framework and hire key staff",
        "start_date": "2025-02-01",
        "end_date": "2025-03-15",
        "responsible_party": "Executive Director",
        "deliverables": "Program plan completed, program director hired"
      }}
    ]
  }}
}}
""")
        
        # Make API call
        chain = prompt | self.llm
        response = chain.invoke({"text": text})
        response_text = response.content
        
        # Parse and validate JSON
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
            
            # Parse JSON
            data = json.loads(response_text)
            
            # Validate and clean data
            data = self._validate_and_clean_data(data, text)
            
            # Build structured objects
            grant_data = self._build_grant_data(data, text)
            
            print(f"✓ Extracted: {len(grant_data.timeline.items) if grant_data.timeline else 0} timeline items, "
                  f"{len(grant_data.budget.items) if grant_data.budget else 0} budget items, "
                  f"{len(grant_data.workplan.tasks) if grant_data.workplan else 0} tasks")
            
            return grant_data
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"Response preview: {response_text[:300]}")
            raise Exception(f"Failed to parse AI response as JSON: {str(e)}")
        except Exception as e:
            print(f"❌ Data processing error: {e}")
            raise
    
    def _validate_and_clean_data(self, data: Dict, original_text: str) -> Dict:
        """Validate and clean extracted data"""
        
        # Ensure basic fields exist
        data.setdefault('organization_name', None)
        data.setdefault('grant_title', None)
        data.setdefault('grant_amount', 0)
        data.setdefault('grant_period', None)
        data.setdefault('funder_name', None)
        data.setdefault('timeline', [])
        data.setdefault('budget', {'total_grant_amount': 0, 'items': []})
        data.setdefault('workplan', {'project_title': '', 'grant_period': '', 'tasks': []})
        
        # Clean grant_amount
        if isinstance(data['grant_amount'], str):
            # Try to extract number from string
            amount_str = re.sub(r'[^\d.]', '', data['grant_amount'])
            data['grant_amount'] = float(amount_str) if amount_str else 0
        
        # Ensure budget amounts are numbers
        if data['budget'] and data['budget'].get('items'):
            for item in data['budget']['items']:
                if isinstance(item.get('amount'), str):
                    amount_str = re.sub(r'[^\d.]', '', item['amount'])
                    item['amount'] = float(amount_str) if amount_str else 0
        
        # Sort timeline by date
        if data.get('timeline'):
            try:
                data['timeline'].sort(key=lambda x: x.get('date', '9999-12-31'))
            except:
                pass
        
        # Ensure timeline items have required fields
        for item in data.get('timeline', []):
            item.setdefault('amount', None)
            item.setdefault('category', 'deadline')
        
        # Ensure work plan tasks have required fields
        for task in data.get('workplan', {}).get('tasks', []):
            task.setdefault('start_date', None)
            task.setdefault('end_date', None)
            task.setdefault('responsible_party', None)
            task.setdefault('deliverables', None)
        
        return data
    
    def _build_grant_data(self, data: Dict, original_text: str) -> GrantData:
        """Build GrantData object from parsed JSON"""
        from app.models.schemas import TimelineItem, BudgetItem, WorkPlanTask
        
        # Build Timeline
        timeline = None
        if data.get('timeline'):
            timeline_items = [TimelineItem(**item) for item in data['timeline']]
            timeline = Timeline(items=timeline_items)
        
        # Build Budget  
        budget = None
        if data.get('budget') and data['budget'].get('items'):
            budget_items = [BudgetItem(**item) for item in data['budget']['items']]
            budget = Budget(
                total_grant_amount=float(data['budget'].get('total_grant_amount', 0)),
                items=budget_items
            )
        
        # Build WorkPlan
        workplan = None
        if data.get('workplan') and data['workplan'].get('tasks'):
            workplan_tasks = [WorkPlanTask(**task) for task in data['workplan']['tasks']]
            workplan = WorkPlan(
                project_title=data['workplan'].get('project_title', ''),
                grant_period=data['workplan'].get('grant_period', ''),
                tasks=workplan_tasks
            )
        
        return GrantData(
            organization_name=data.get('organization_name'),
            grant_title=data.get('grant_title'),
            grant_amount=float(data.get('grant_amount', 0)) if data.get('grant_amount') else None,
            grant_period=data.get('grant_period'),
            funder_name=data.get('funder_name'),
            timeline=timeline,
            budget=budget,
            workplan=workplan,
            raw_text=original_text
        )
    
    def extract_all_data(self, text: str) -> GrantData:
        """Main entry point - universal grant extraction"""
        
        if DEMO_MODE:
            return self._get_demo_data(text)
        
        try:
            return self.extract_all_data_single_call(text)
        except Exception as e:
            print(f"❌ Full extraction failed: {e}")
            
            # Fallback: Return partial data
            return GrantData(
                organization_name=None,
                grant_title="Extraction Incomplete - Review Required",
                grant_amount=None,
                grant_period=None,
                funder_name=None,
                timeline=Timeline(items=[]),
                budget=Budget(total_grant_amount=0, items=[]),
                workplan=WorkPlan(project_title="", grant_period="", tasks=[]),
                raw_text=text
            )
    
    def _get_demo_data(self, text: str) -> GrantData:
        """Enhanced demo data showing comprehensive extraction"""
        from app.models.schemas import TimelineItem, BudgetItem, WorkPlanTask
        
        # Comprehensive timeline with all event types
        timeline = Timeline(items=[
            TimelineItem(
                date="2025-02-01",
                amount=None,
                description="Grant period begins - Project kickoff and planning phase starts",
                category="milestone"
            ),
            TimelineItem(
                date="2025-02-10",
                amount=None,
                description="Submit proof of insurance and signed grant agreement",
                category="compliance"
            ),
            TimelineItem(
                date="2025-02-15",
                amount="$25,000",
                description="First disbursement - Initial payment (50% of total award)",
                category="payment"
            ),
            TimelineItem(
                date="2025-03-01",
                amount=None,
                description="Kickoff meeting with funder program officer",
                category="meeting"
            ),
            TimelineItem(
                date="2025-03-15",
                amount=None,
                description="Program coordinator hiring deadline",
                category="deliverable"
            ),
            TimelineItem(
                date="2025-04-30",
                amount=None,
                description="Participant recruitment completed - 50 participants enrolled",
                category="deliverable"
            ),
            TimelineItem(
                date="2025-06-30",
                amount=None,
                description="Quarterly progress report due",
                category="report"
            ),
            TimelineItem(
                date="2025-07-31",
                amount=None,
                description="Mid-year financial statement and narrative report due",
                category="report"
            ),
            TimelineItem(
                date="2025-08-15",
                amount="$25,000",
                description="Second disbursement - Final payment (remaining 50%)",
                category="payment"
            ),
            TimelineItem(
                date="2025-09-30",
                amount=None,
                description="Quarterly progress report due",
                category="report"
            ),
            TimelineItem(
                date="2025-10-15",
                amount=None,
                description="Site visit scheduled - Funder will observe program activities",
                category="meeting"
            ),
            TimelineItem(
                date="2025-12-31",
                amount=None,
                description="Program implementation completed - All 100 instruction hours delivered",
                category="deliverable"
            ),
            TimelineItem(
                date="2026-01-15",
                amount=None,
                description="Participant post-assessments and surveys completed",
                category="deliverable"
            ),
            TimelineItem(
                date="2026-01-31",
                amount=None,
                description="Grant period officially ends",
                category="milestone"
            ),
            TimelineItem(
                date="2026-02-28",
                amount=None,
                description="Final comprehensive report, financial statement, and outcomes data due",
                category="report"
            ),
        ])
        
        # Detailed budget aligned with specific grant requirements
        budget = Budget(
            total_grant_amount=50000.00,
            items=[
                BudgetItem(
                    category="Personnel - Program Coordinator",
                    amount=25000,
                    description="Full-time program coordinator salary and benefits for 12-month grant period. Responsible for program implementation, participant management, and reporting.",
                    timeline="February 2025 - January 2026"
                ),
                BudgetItem(
                    category="Educational Materials and Curriculum",
                    amount=10000,
                    description="Comprehensive curriculum materials including workbooks ($3,000), digital learning subscriptions ($4,000), textbooks ($2,000), and supplementary materials ($1,000) for 50 participants",
                    timeline="Months 1-3 (February-April 2025)"
                ),
                BudgetItem(
                    category="Technology and Equipment",
                    amount=8000,
                    description="10 tablets for participant use ($6,000), educational software licenses ($1,500), and technology accessories ($500)",
                    timeline="Month 1 (February 2025)"
                ),
                BudgetItem(
                    category="Program Supplies and Materials",
                    amount=4000,
                    description="Classroom supplies, printing and copying, participant folders and materials, name badges, certificates",
                    timeline="Throughout grant period as needed"
                ),
                BudgetItem(
                    category="Administrative and Indirect Costs",
                    amount=3000,
                    description="Administrative overhead including facilities use, utilities, insurance, accounting (6% of total, within funder guidelines)",
                    timeline="Throughout grant period"
                ),
            ]
        )
        
        # Comprehensive work plan with specific, measurable deliverables
        workplan = WorkPlan(
            project_title="Youth Education and Empowerment Initiative",
            grant_period="February 1, 2025 - January 31, 2026 (12 months)",
            tasks=[
                WorkPlanTask(
                    task_name="Program Planning and Infrastructure Setup",
                    description="Establish comprehensive program framework including policies, procedures, participant tracking systems, and facility setup. Develop program operations manual and obtain all necessary permits and approvals.",
                    start_date="2025-02-01",
                    end_date="2025-02-28",
                    responsible_party="Executive Director and Operations Manager",
                    deliverables="Program operations manual completed, facility agreement signed, participant database system established, insurance and compliance documents submitted to funder"
                ),
                WorkPlanTask(
                    task_name="Staff Recruitment and Onboarding",
                    description="Recruit, interview, and hire qualified program coordinator. Provide comprehensive onboarding including grant requirements, program goals, curriculum overview, and systems training.",
                    start_date="2025-02-01",
                    end_date="2025-03-15",
                    responsible_party="HR Manager and Executive Director",
                    deliverables="Program coordinator hired with completed background check, onboarding training completed, coordinator ready to begin program implementation"
                ),
                WorkPlanTask(
                    task_name="Technology and Materials Procurement",
                    description="Purchase all required technology equipment, educational materials, and program supplies. Set up tablets with appropriate software and learning apps. Organize materials for distribution.",
                    start_date="2025-02-15",
                    end_date="2025-03-31",
                    responsible_party="Program Coordinator and Procurement Specialist",
                    deliverables="10 tablets purchased and configured, all educational materials received and inventoried, supply closet organized and stocked"
                ),
                WorkPlanTask(
                    task_name="Curriculum Development and Adaptation",
                    description="Develop comprehensive 100-hour education curriculum aligned with program goals and participant needs. Create lesson plans, activities, assessments, and supplementary materials. Pilot test curriculum components.",
                    start_date="2025-03-01",
                    end_date="2025-04-15",
                    responsible_party="Program Coordinator and Education Consultant",
                    deliverables="Complete curriculum guide with 100 hours of lesson plans, pre/post assessment tools, participant progress tracking forms, curriculum evaluation rubric"
                ),
                WorkPlanTask(
                    task_name="Participant Recruitment and Enrollment",
                    description="Conduct community outreach through schools, community centers, and partner organizations. Host information sessions for youth and families. Complete enrollment process including applications, eligibility verification, needs assessments, and parental consents.",
                    start_date="2025-03-01",
                    end_date="2025-04-30",
                    responsible_party="Program Coordinator and Outreach Team",
                    deliverables="50 eligible participants enrolled with completed applications, eligibility documentation verified, parental consent forms signed, needs assessments completed, participant cohort finalized"
                ),
                WorkPlanTask(
                    task_name="Program Implementation - Educational Instruction",
                    description="Deliver comprehensive 100-hour educational program to enrolled participants through interactive workshops, tutoring sessions, mentoring, and hands-on learning activities. Monitor attendance and engagement. Provide individualized support as needed.",
                    start_date="2025-05-01",
                    end_date="2025-12-31",
                    responsible_party="Program Coordinator and Teaching Staff",
                    deliverables="100 hours of instruction delivered, daily attendance records maintained, weekly progress reports for each participant, mid-program assessments completed, participant engagement data collected"
                ),
                WorkPlanTask(
                    task_name="Continuous Assessment and Participant Support",
                    description="Conduct ongoing assessment of participant progress through formative and summative evaluations. Provide additional tutoring and support for participants needing extra help. Track individual learning outcomes and skill development.",
                    start_date="2025-05-01",
                    end_date="2026-01-15",
                    responsible_party="Program Coordinator and Assessment Specialist",
                    deliverables="Pre-program assessments for all 50 participants, mid-program progress checks (Month 6), final post-program assessments, individual progress reports, skills development tracking data"
                ),
                WorkPlanTask(
                    task_name="Quarterly and Mid-Year Reporting",
                    description="Compile program data, financial information, and narrative updates for required quarterly and mid-year reports to funder. Include participant outcomes, budget status, challenges, and upcoming activities.",
                    start_date="2025-06-01",
                    end_date="2025-07-31",
                    responsible_party="Program Coordinator and Finance Manager",
                    deliverables="Q2 quarterly report submitted (June 30), Mid-year narrative and financial report submitted (July 31), supporting documentation organized"
                ),
                WorkPlanTask(
                    task_name="Program Evaluation and Outcomes Analysis",
                    description="Conduct comprehensive evaluation of program effectiveness. Analyze participant outcomes data, collect feedback through surveys and focus groups, assess achievement of grant objectives, identify lessons learned and best practices.",
                    start_date="2025-12-01",
                    end_date="2026-01-31",
                    responsible_party="Program Coordinator and External Evaluator",
                    deliverables="Comprehensive evaluation report with quantitative and qualitative data, participant satisfaction surveys (95% completion rate), focus group summaries, outcomes analysis comparing pre/post assessments, recommendations for program improvement"
                ),
                WorkPlanTask(
                    task_name="Final Reporting and Grant Closeout",
                    description="Prepare comprehensive final report documenting all program activities, achievements, challenges, and outcomes. Compile complete financial documentation. Prepare sustainability plan for program continuation. Submit all required closeout documentation to funder.",
                    start_date="2026-01-15",
                    end_date="2026-02-28",
                    responsible_party="Executive Director, Program Coordinator, and Finance Manager",
                    deliverables="Final narrative report (15-20 pages), complete financial statement with receipts, outcomes data summary, participant testimonials and success stories, photo documentation, sustainability plan, all closeout documents submitted"
                ),
            ]
        )
        
        return GrantData(
            organization_name="Community Empowerment Foundation",
            grant_title="Mesa Pathways Innovation Grant 2025 - Youth Education Initiative",
            grant_amount=50000.00,
            grant_period="February 1, 2025 - January 31, 2026 (12 months)",
            funder_name="Mesa Pathways Committee / Community Foundation",
            timeline=timeline,
            budget=budget,
            workplan=workplan,
            raw_text=text
        )