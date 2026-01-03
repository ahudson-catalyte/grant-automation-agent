export interface TimelineItem {
  date: string;
  amount?: string;
  description: string;
  category?: string;
}

export interface Timeline {
  items: TimelineItem[];
}

export interface BudgetItem {
  category: string;
  amount: number;
  description?: string;
  timeline?: string;
}

export interface Budget {
  total_grant_amount: number;
  items: BudgetItem[];
}

export interface WorkPlanTask {
  task_name: string;
  description: string;
  start_date?: string;
  end_date?: string;
  responsible_party?: string;
  deliverables?: string;
}

export interface WorkPlan {
  project_title: string;
  grant_period: string;
  tasks: WorkPlanTask[];
}

export interface GrantData {
  organization_name?: string;
  grant_title?: string;
  grant_amount?: number;
  grant_period?: string;
  funder_name?: string;
  timeline?: Timeline;
  budget?: Budget;
  workplan?: WorkPlan;
  raw_text: string;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  file_id: string;
  filename: string;
}

export interface GenerateDocumentsRequest {
  file_id: string;
  generate_workplan?: boolean;
  generate_budget?: boolean;
  generate_report_template?: boolean;
  generate_calendar?: boolean;
}

export interface GeneratedDocument {
  filename: string;
  download_url: string;
}

export interface GenerateDocumentsResponse {
  success: boolean;
  files: {
    workplan?: GeneratedDocument;
    budget?: GeneratedDocument;
    report?: GeneratedDocument;
    calendar?: GeneratedDocument;
  };
}

export interface GrantListItem {
  file_id: string;
  filename: string;
  organization?: string;
  grant_title?: string;
  grant_amount?: number;
  created_at?: string;
  processed: boolean;
}