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
                model="gpt-4.1",
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

CRITICAL JSON RULES:
1. ALL string fields must be strings, never null - use empty string "" if unknown
2. Use 0 for missing numbers
3. Use empty array [] for missing lists
4. Return valid JSON with no markdown formatting

EXTRACT THESE CATEGORIES:

1. BASIC GRANT INFORMATION
- organization_name: Who is receiving? (string, use "" if unknown)
- grant_title: Grant program name (string, use "" if unknown)
- grant_amount: Total dollars (number, use 0 if unknown)
- grant_period: Duration (string, use "" if unknown)
- funder_name: Who is giving? (string, use "" if unknown)

2. TIMELINE - Extract ALL dates
For each:
- date: YYYY-MM-DD format (required string)
- amount: "$X,XXX" as string or null
- description: What happens (required string)
- category: "payment", "report", "deliverable", "milestone", "compliance", "meeting", "deadline", "submission"

3. BUDGET
- total_grant_amount: Number (use 0 if unknown)
- items: Array, each with:
  * category: Name (required string)
  * amount: Number (required)
  * description: Details (string or null)
  * timeline: When (string or null)

4. WORK PLAN
- project_title: Project name (string, use "" if unknown)
- grant_period: Duration (string, use "" if unknown - NEVER null)
- tasks: Array, each with:
  * task_name: Activity (required string)
  * description: Details (required string)
  * start_date: YYYY-MM-DD or null
  * end_date: YYYY-MM-DD or null
  * responsible_party: Who (string or null)
  * deliverables: Outputs (string or null)

Document:
{text}

Return ONLY JSON (no markdown):
{{
  "organization_name": "",
  "grant_title": "",
  "grant_amount": 0,
  "grant_period": "",
  "funder_name": "",
  "timeline": [],
  "budget": {{"total_grant_amount": 0, "items": []}},
  "workplan": {{"project_title": "", "grant_period": "", "tasks": []}}
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
        
        # Ensure basic fields exist with defaults
        data.setdefault('organization_name', "")
        data.setdefault('grant_title', "")
        data.setdefault('grant_amount', 0)
        data.setdefault('grant_period', "")
        data.setdefault('funder_name', "")
        data.setdefault('timeline', [])
        data.setdefault('budget', {'total_grant_amount': 0, 'items': []})
        data.setdefault('workplan', {'project_title': '', 'grant_period': '', 'tasks': []})
        
        # Convert None to empty string for strings
        if data['organization_name'] is None:
            data['organization_name'] = ""
        if data['grant_title'] is None:
            data['grant_title'] = ""
        if data['grant_period'] is None:
            data['grant_period'] = ""
        if data['funder_name'] is None:
            data['funder_name'] = ""
        
        # Clean grant_amount
        if isinstance(data['grant_amount'], str):
            amount_str = re.sub(r'[^\d.]', '', data['grant_amount'])
            data['grant_amount'] = float(amount_str) if amount_str else 0
        
        # Ensure budget amounts are numbers
        if data['budget'] and data['budget'].get('items'):
            for item in data['budget']['items']:
                if isinstance(item.get('amount'), str):
                    amount_str = re.sub(r'[^\d.]', '', item['amount'])
                    item['amount'] = float(amount_str) if amount_str else 0
        
        # Fix workplan null values BEFORE validation
        if data.get('workplan'):
            if data['workplan'].get('project_title') is None:
                data['workplan']['project_title'] = data.get('grant_title') or 'Project Plan'
            if data['workplan'].get('grant_period') is None:
                data['workplan']['grant_period'] = data.get('grant_period') or 'To Be Determined'
            if not data['workplan'].get('tasks'):
                data['workplan']['tasks'] = []
        else:
            data['workplan'] = {
                'project_title': data.get('grant_title') or 'Project Plan',
                'grant_period': data.get('grant_period') or 'To Be Determined',
                'tasks': []
            }
        
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
        
        # Build WorkPlan with better null handling
        workplan = None
        if data.get('workplan'):
            workplan_data = data['workplan']
            
            # Handle null/empty values
            project_title = workplan_data.get('project_title') or data.get('grant_title') or 'Project Plan'
            grant_period = workplan_data.get('grant_period') or data.get('grant_period') or 'To Be Determined'
            
            # Build tasks
            tasks = []
            if workplan_data.get('tasks'):
                tasks = [WorkPlanTask(**task) for task in workplan_data['tasks']]
            
            workplan = WorkPlan(
                project_title=project_title,
                grant_period=grant_period,
                tasks=tasks
            )
        
        return GrantData(
            organization_name=data.get('organization_name') or None,
            grant_title=data.get('grant_title') or None,
            grant_amount=float(data.get('grant_amount', 0)) if data.get('grant_amount') else None,
            grant_period=data.get('grant_period') or None,
            funder_name=data.get('funder_name') or None,
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
                workplan=WorkPlan(project_title="Project Plan", grant_period="To Be Determined", tasks=[]),
                raw_text=text
            )
    
    def _get_demo_data(self, text: str) -> GrantData:
        """Demo data - truncated for brevity"""
        from app.models.schemas import TimelineItem, BudgetItem, WorkPlanTask
        
        return GrantData(
            organization_name="Demo Organization",
            grant_title="Demo Grant Program",
            grant_amount=50000.00,
            grant_period="January 1, 2025 - December 31, 2025",
            funder_name="Demo Foundation",
            timeline=Timeline(items=[]),
            budget=Budget(total_grant_amount=50000, items=[]),
            workplan=WorkPlan(
                project_title="Demo Project",
                grant_period="January 1, 2025 - December 31, 2025",
                tasks=[]
            ),
            raw_text=text
        )