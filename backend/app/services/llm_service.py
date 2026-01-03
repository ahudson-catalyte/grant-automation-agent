from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.models.schemas import Timeline, Budget, WorkPlan, GrantData
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv
import re
import json

load_dotenv()


class LLMService:
    """Service for interacting with OpenAI via LangChain"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    def _safe_parse_amount(self, amount_str: str) -> Optional[float]:
        """Safely parse amount strings to float"""
        if not amount_str:
            return None
        
        # Remove common formatting
        cleaned = str(amount_str).replace('$', '').replace(',', '').strip()
        
        # Handle placeholder values like "X,000.00" or "TBD"
        if not cleaned or cleaned.lower() in ['x', 'tbd', 'n/a', 'na', 'unknown']:
            return None
        
        # Extract numbers
        numbers = re.findall(r'\d+\.?\d*', cleaned)
        if numbers:
            try:
                return float(numbers[0])
            except (ValueError, IndexError):
                return None
        
        return None
    
    def extract_timeline(self, text: str) -> Optional[Timeline]:
        """Extract timeline items from grant acceptance letter"""
        parser = PydanticOutputParser(pydantic_object=Timeline)
        
        prompt = ChatPromptTemplate.from_template("""
Extract a comprehensive timeline of all deadlines, milestones, and payments from this grant acceptance letter.

Include:
- Due dates for reports, deliverables, and milestones
- Payment amounts and disbursement dates
- Penalties, late fees, or compliance deadlines
- Grant start and end dates
- Any other time-sensitive requirements

For amounts, use actual dollar values if available. If not specified, use empty string.
Categorize each item as: milestone, payment, deliverable, compliance, or other.

{format_instructions}

Document:
{text}
""")
        
        try:
            chain = prompt | self.llm | parser
            result = chain.invoke({
                "text": text,
                "format_instructions": parser.get_format_instructions()
            })
            return result
        except Exception as e:
            print(f"⚠️  Timeline extraction failed: {str(e)}")
            return None
    
    def extract_budget(self, text: str) -> Optional[Budget]:
        """Extract budget information from grant letter"""
        
        # First, try to extract with structured output
        prompt = ChatPromptTemplate.from_template("""
Extract detailed budget information from this grant acceptance letter.

CRITICAL INSTRUCTIONS:
- For total_grant_amount: Use ONLY the actual numeric dollar amount if explicitly stated. If the amount is a placeholder like "X,000.00" or not specified, use 0.
- For each budget item amount: Use ONLY actual numeric values. If not specified or is a placeholder, use 0.
- Do NOT include dollar signs, commas, or any text in numeric fields.
- Extract only information that is explicitly stated in the document.

Return your response as a valid JSON object with this exact structure:
{{
  "total_grant_amount": <number>,
  "items": [
    {{
      "category": "string",
      "amount": <number>,
      "description": "string or null",
      "timeline": "string or null"
    }}
  ]
}}

Document:
{text}

Respond with ONLY the JSON object, no additional text.
""")
        
        try:
            chain = prompt | self.llm
            result = chain.invoke({"text": text})
            
            # Parse the JSON response
            content = result.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```'):
                content = re.sub(r'```json\s*|\s*```', '', content).strip()
            
            data = json.loads(content)
            
            # Validate and clean the data
            total_amount = self._safe_parse_amount(data.get('total_grant_amount', 0)) or 0.0
            
            items = []
            for item in data.get('items', []):
                amount = self._safe_parse_amount(item.get('amount', 0)) or 0.0
                items.append({
                    'category': item.get('category', 'Unknown'),
                    'amount': amount,
                    'description': item.get('description'),
                    'timeline': item.get('timeline')
                })
            
            # Create Budget object
            from app.models.schemas import BudgetItem
            budget_items = [BudgetItem(**item) for item in items]
            
            return Budget(
                total_grant_amount=total_amount,
                items=budget_items
            )
            
        except Exception as e:
            print(f"⚠️  Budget extraction failed: {str(e)}")
            # Return a minimal budget structure
            from app.models.schemas import BudgetItem
            return Budget(
                total_grant_amount=0.0,
                items=[BudgetItem(
                    category="Information not available",
                    amount=0.0,
                    description="Budget details could not be extracted from the document"
                )]
            )
    
    def extract_workplan(self, text: str) -> Optional[WorkPlan]:
        """Extract work plan elements from grant letter"""
        
        prompt = ChatPromptTemplate.from_template("""
Extract work plan information from this grant acceptance letter.

Identify:
- Project title and goals
- Grant period (start and end dates)
- Key tasks, activities, and milestones
- Deliverables for each task
- Responsible parties (if mentioned)
- Timeline for each activity

Return your response as a valid JSON object with this exact structure:
{{
  "project_title": "string",
  "grant_period": "string",
  "tasks": [
    {{
      "task_name": "string",
      "description": "string",
      "start_date": "string or null",
      "end_date": "string or null",
      "responsible_party": "string or null",
      "deliverables": "string or null"
    }}
  ]
}}

If you cannot find specific information, use descriptive placeholders or null.

Document:
{text}

Respond with ONLY the JSON object, no additional text.
""")
        
        try:
            chain = prompt | self.llm
            result = chain.invoke({"text": text})
            
            # Parse the JSON response
            content = result.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```'):
                content = re.sub(r'```json\s*|\s*```', '', content).strip()
            
            data = json.loads(content)
            
            # Create WorkPlan object
            from app.models.schemas import WorkPlanTask
            tasks = [WorkPlanTask(**task) for task in data.get('tasks', [])]
            
            return WorkPlan(
                project_title=data.get('project_title', 'Unknown Project'),
                grant_period=data.get('grant_period', 'Not specified'),
                tasks=tasks
            )
            
        except Exception as e:
            print(f"⚠️  WorkPlan extraction failed: {str(e)}")
            return None
    
    def extract_all_data(self, text: str) -> GrantData:
        """Extract all relevant information from grant letter"""
        
        print("🔍 Extracting basic information...")
        
        # Extract basic info using simple prompting
        basic_prompt = ChatPromptTemplate.from_template("""
From this grant acceptance letter, extract the following information.

If a field is not found or is a placeholder (like "X" or "TBD"), respond with "Not specified".

For the grant amount:
- If you see an actual dollar amount (like $50,000 or $10,000.00), extract just the number
- If you see a placeholder (like "X,000.00" or "$X"), respond with "0"
- If not mentioned, respond with "0"

Respond in this exact format:
Organization: [name or "Not specified"]
Grant Title: [title or "Not specified"]
Amount: [number only, no $ or commas, or "0"]
Period: [dates or "Not specified"]
Funder: [name or "Not specified"]

Document:
{text}
""")
        
        try:
            basic_chain = basic_prompt | self.llm
            basic_response = basic_chain.invoke({"text": text})
            basic_data = self._parse_basic_info(basic_response.content)
            print(f"✓ Basic info extracted: {basic_data}")
        except Exception as e:
            print(f"⚠️  Basic info extraction failed: {str(e)}")
            basic_data = {}
        
        # Extract structured data with error handling
        print("📊 Extracting timeline...")
        timeline = self.extract_timeline(text)
        
        print("💰 Extracting budget...")
        budget = self.extract_budget(text)
        
        print("📋 Extracting workplan...")
        workplan = self.extract_workplan(text)
        
        print("✅ All extractions complete")
        
        return GrantData(
            organization_name=basic_data.get("organization"),
            grant_title=basic_data.get("grant_title"),
            grant_amount=basic_data.get("amount"),
            grant_period=basic_data.get("period"),
            funder_name=basic_data.get("funder"),
            timeline=timeline,
            budget=budget,
            workplan=workplan,
            raw_text=text
        )
    
    def _parse_basic_info(self, response: str) -> Dict[str, Any]:
        """Parse basic info from LLM response"""
        data = {}
        lines = response.strip().split('\n')
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                # Skip "Not specified" values
                if value.lower() in ['not specified', 'n/a', 'na', 'unknown']:
                    continue
                
                if key == 'amount':
                    # Extract numeric value
                    amount = self._safe_parse_amount(value)
                    if amount is not None and amount > 0:
                        data['amount'] = amount
                else:
                    data[key] = value
        
        return data