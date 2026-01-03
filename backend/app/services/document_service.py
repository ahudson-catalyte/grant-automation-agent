from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from icalendar import Calendar, Event
from datetime import datetime
from app.models.schemas import GrantData, Timeline, Budget, WorkPlan
from typing import Dict
import os


class DocumentService:
    """Service for generating various document types"""
    
    def __init__(self, temp_dir: str = "temp_files"):
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)
    
    def generate_workplan_pdf(self, grant_data: GrantData, file_id: str) -> str:
        """Generate work plan PDF"""
        filename = f"{file_id}_workplan.pdf"
        filepath = os.path.join(self.temp_dir, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=30,
            alignment=1  # Center
        )
        
        title = Paragraph(f"Work Plan<br/>{grant_data.grant_title or 'Grant Project'}", title_style)
        story.append(title)
        story.append(Spacer(1, 0.3 * inch))
        
        # Grant Information
        info_data = [
            ['Organization:', grant_data.organization_name or 'N/A'],
            ['Funder:', grant_data.funder_name or 'N/A'],
            ['Grant Period:', grant_data.grant_period or 'N/A'],
            ['Total Amount:', f"${grant_data.grant_amount:,.2f}" if grant_data.grant_amount else 'N/A'],
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECF0F1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 0.4 * inch))
        
        # Work Plan Tasks
        if grant_data.workplan and grant_data.workplan.tasks:
            story.append(Paragraph("Project Tasks & Deliverables", styles['Heading2']))
            story.append(Spacer(1, 0.2 * inch))
            
            for idx, task in enumerate(grant_data.workplan.tasks, 1):
                task_data = [
                    [f"Task {idx}: {task.task_name}"],
                    ['Description:', task.description],
                    ['Timeline:', f"{task.start_date or 'TBD'} to {task.end_date or 'TBD'}"],
                    ['Responsible Party:', task.responsible_party or 'To be assigned'],
                    ['Deliverables:', task.deliverables or 'See description'],
                ]
                
                task_table = Table(task_data, colWidths=[1.5*inch, 4.5*inch])
                task_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('SPAN', (0, 0), (-1, 0)),
                ]))
                
                story.append(task_table)
                story.append(Spacer(1, 0.2 * inch))
        
        doc.build(story)
        return filepath
    
    def generate_budget_excel(self, grant_data: GrantData, file_id: str) -> str:
        """Generate budget and disbursement Excel spreadsheet"""
        filename = f"{file_id}_budget.xlsx"
        filepath = os.path.join(self.temp_dir, filename)
        
        wb = Workbook()
        
        # Budget Sheet
        ws_budget = wb.active
        ws_budget.title = "Budget"
        
        # Styles
        header_fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True, size=12)
        total_fill = PatternFill(start_color="3498DB", end_color="3498DB", fill_type="solid")
        total_font = Font(bold=True, size=11, color="FFFFFF")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Budget Headers
        ws_budget['A1'] = 'Grant Budget'
        ws_budget['A1'].font = Font(bold=True, size=14)
        
        ws_budget['A2'] = f"Organization: {grant_data.organization_name or 'N/A'}"
        ws_budget['A3'] = f"Grant: {grant_data.grant_title or 'N/A'}"
        ws_budget['A4'] = f"Total Amount: ${grant_data.grant_amount:,.2f}" if grant_data.grant_amount else "Total Amount: N/A"
        
        # Budget Table Headers
        headers = ['Category', 'Description', 'Amount', 'Timeline/Notes']
        for col_num, header in enumerate(headers, 1):
            cell = ws_budget.cell(row=6, column=col_num)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = border
        
        # Budget Data
        row = 7
        total_amount = 0
        
        if grant_data.budget and grant_data.budget.items:
            for item in grant_data.budget.items:
                ws_budget.cell(row=row, column=1, value=item.category).border = border
                ws_budget.cell(row=row, column=2, value=item.description or '').border = border
                
                amount_cell = ws_budget.cell(row=row, column=3, value=item.amount)
                amount_cell.number_format = '"$"#,##0.00'
                amount_cell.border = border
                
                ws_budget.cell(row=row, column=4, value=item.timeline or '').border = border
                
                total_amount += item.amount
                row += 1
        
        # Total Row
        ws_budget.cell(row=row, column=1, value='TOTAL').font = total_font
        ws_budget.cell(row=row, column=1).fill = total_fill
        ws_budget.cell(row=row, column=1).border = border
        
        total_cell = ws_budget.cell(row=row, column=3, value=total_amount)
        total_cell.number_format = '"$"#,##0.00'
        total_cell.font = total_font
        total_cell.fill = total_fill
        total_cell.border = border
        
        # Adjust column widths
        ws_budget.column_dimensions['A'].width = 20
        ws_budget.column_dimensions['B'].width = 35
        ws_budget.column_dimensions['C'].width = 15
        ws_budget.column_dimensions['D'].width = 25
        
        # Disbursement Schedule Sheet
        ws_disbursement = wb.create_sheet("Disbursement Schedule")
        
        ws_disbursement['A1'] = 'Disbursement Schedule'
        ws_disbursement['A1'].font = Font(bold=True, size=14)
        
        disburse_headers = ['Date', 'Amount', 'Purpose', 'Status']
        for col_num, header in enumerate(disburse_headers, 1):
            cell = ws_disbursement.cell(row=3, column=col_num)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
            cell.border = border
        
        # Add timeline payment items
        row = 4
        if grant_data.timeline and grant_data.timeline.items:
            for item in grant_data.timeline.items:
                if item.amount:  # Only include items with payment amounts
                    ws_disbursement.cell(row=row, column=1, value=item.date).border = border
                    ws_disbursement.cell(row=row, column=2, value=item.amount).border = border
                    ws_disbursement.cell(row=row, column=3, value=item.description).border = border
                    ws_disbursement.cell(row=row, column=4, value='Pending').border = border
                    row += 1
        
        ws_disbursement.column_dimensions['A'].width = 15
        ws_disbursement.column_dimensions['B'].width = 15
        ws_disbursement.column_dimensions['C'].width = 40
        ws_disbursement.column_dimensions['D'].width = 15
        
        wb.save(filepath)
        return filepath
    
    def generate_report_template_docx(self, grant_data: GrantData, file_id: str) -> str:
        """Generate progress report template in Word"""
        filename = f"{file_id}_report_template.docx"
        filepath = os.path.join(self.temp_dir, filename)
        
        doc = Document()
        
        # Title
        title = doc.add_heading('Grant Progress Report', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Grant Information
        doc.add_heading('Grant Information', 1)
        
        info_table = doc.add_table(rows=5, cols=2)
        info_table.style = 'Light Grid Accent 1'
        
        info_data = [
            ('Organization:', grant_data.organization_name or '[Organization Name]'),
            ('Grant Title:', grant_data.grant_title or '[Grant Title]'),
            ('Funder:', grant_data.funder_name or '[Funder Name]'),
            ('Reporting Period:', '[Start Date] to [End Date]'),
            ('Report Date:', '[Current Date]'),
        ]
        
        for idx, (label, value) in enumerate(info_data):
            info_table.rows[idx].cells[0].text = label
            info_table.rows[idx].cells[1].text = value
            info_table.rows[idx].cells[0].paragraphs[0].runs[0].font.bold = True
        
        doc.add_paragraph()
        
        # Executive Summary
        doc.add_heading('Executive Summary', 1)
        doc.add_paragraph('[Provide a brief overview of progress during this reporting period, key achievements, and any challenges encountered.]')
        doc.add_paragraph()
        
        # Activities and Accomplishments
        doc.add_heading('Activities and Accomplishments', 1)
        
        if grant_data.workplan and grant_data.workplan.tasks:
            for idx, task in enumerate(grant_data.workplan.tasks, 1):
                doc.add_heading(f'Task {idx}: {task.task_name}', 2)
                doc.add_paragraph(f'Planned Activity: {task.description}')
                doc.add_paragraph('Progress:')
                doc.add_paragraph('[Describe progress made on this task during the reporting period]', style='List Bullet')
                doc.add_paragraph('[Include specific accomplishments, metrics, or outcomes]', style='List Bullet')
                doc.add_paragraph('[Note any challenges or deviations from the plan]', style='List Bullet')
                doc.add_paragraph()
        else:
            doc.add_paragraph('[Describe activities completed during this reporting period]', style='List Bullet')
            doc.add_paragraph('[Include measurable outcomes and achievements]', style='List Bullet')
            doc.add_paragraph('[Note any milestones reached]', style='List Bullet')
            doc.add_paragraph()
        
        # Financial Report
        doc.add_heading('Financial Report', 1)
        
        financial_table = doc.add_table(rows=1, cols=4)
        financial_table.style = 'Light Grid Accent 1'
        
        header_cells = financial_table.rows[0].cells
        headers = ['Budget Category', 'Budgeted Amount', 'Spent to Date', 'Remaining']
        for idx, header in enumerate(headers):
            header_cells[idx].text = header
            header_cells[idx].paragraphs[0].runs[0].font.bold = True
        
        if grant_data.budget and grant_data.budget.items:
            for item in grant_data.budget.items:
                row_cells = financial_table.add_row().cells
                row_cells[0].text = item.category
                row_cells[1].text = f"${item.amount:,.2f}"
                row_cells[2].text = '$[Amount]'
                row_cells[3].text = '$[Amount]'
        
        doc.add_paragraph()
        doc.add_paragraph('Financial Summary Notes:')
        doc.add_paragraph('[Explain any significant variances from the budget]', style='List Bullet')
        doc.add_paragraph('[Describe any budget reallocations or modifications]', style='List Bullet')
        doc.add_paragraph()
        
        # Challenges and Solutions
        doc.add_heading('Challenges and Solutions', 1)
        doc.add_paragraph('[Describe any challenges encountered during this period]')
        doc.add_paragraph('[Explain solutions implemented or planned]')
        doc.add_paragraph()
        
        # Upcoming Activities
        doc.add_heading('Upcoming Activities', 1)
        doc.add_paragraph('[Outline planned activities for the next reporting period]')
        doc.add_paragraph('[Include expected outcomes and milestones]')
        doc.add_paragraph()
        
        # Attachments
        doc.add_heading('Attachments', 1)
        doc.add_paragraph('[List any supporting documents, photos, testimonials, or other evidence of progress]', style='List Bullet')
        
        doc.save(filepath)
        return filepath
    
    def generate_calendar_ics(self, grant_data: GrantData, file_id: str) -> str:
        """Generate ICS calendar file with deadlines and meetings"""
        filename = f"{file_id}_calendar.ics"
        filepath = os.path.join(self.temp_dir, filename)
        
        cal = Calendar()
        cal.add('prodid', '-//Grant Management Calendar//EN')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('x-wr-calname', f"{grant_data.grant_title or 'Grant'} - Timeline")
        
        if grant_data.timeline and grant_data.timeline.items:
            for item in grant_data.timeline.items:
                event = Event()
                event.add('summary', f"{item.description}")
                
                # Parse date (basic parsing, assumes various formats)
                try:
                    event_date = self._parse_date(item.date)
                    event.add('dtstart', event_date.date())
                    event.add('dtend', event_date.date())
                except:
                    # If parsing fails, skip this event
                    continue
                
                description = f"{item.description}"
                if item.amount:
                    description += f"\nAmount: {item.amount}"
                if item.category:
                    description += f"\nCategory: {item.category}"
                
                event.add('description', description)
                event.add('location', grant_data.organization_name or '')
                
                # Add alarm (1 week before)
                from icalendar import Alarm
                alarm = Alarm()
                alarm.add('action', 'DISPLAY')
                alarm.add('description', f"Reminder: {item.description}")
                alarm.add('trigger', '-P7D')  # 7 days before
                event.add_component(alarm)
                
                cal.add_component(event)
        
        with open(filepath, 'wb') as f:
            f.write(cal.to_ical())
        
        return filepath
    
    def _parse_date(self, date_str: str) -> datetime:
        """Attempt to parse various date formats"""
        from dateutil import parser
        return parser.parse(date_str)
    
    def generate_all_documents(self, grant_data: GrantData, file_id: str, options: Dict[str, bool]) -> Dict[str, str]:
        """Generate all requested documents"""
        generated_files = {}
        
        if options.get('generate_workplan', True):
            try:
                generated_files['workplan'] = self.generate_workplan_pdf(grant_data, file_id)
            except Exception as e:
                generated_files['workplan_error'] = str(e)
        
        if options.get('generate_budget', True):
            try:
                generated_files['budget'] = self.generate_budget_excel(grant_data, file_id)
            except Exception as e:
                generated_files['budget_error'] = str(e)
        
        if options.get('generate_report_template', True):
            try:
                generated_files['report'] = self.generate_report_template_docx(grant_data, file_id)
            except Exception as e:
                generated_files['report_error'] = str(e)
        
        if options.get('generate_calendar', True):
            try:
                generated_files['calendar'] = self.generate_calendar_ics(grant_data, file_id)
            except Exception as e:
                generated_files['calendar_error'] = str(e)
        
        return generated_files