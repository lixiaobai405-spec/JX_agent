// API 类型定义

export type UserRole = 'employee' | 'manager' | 'hr_admin' | 'system_admin'
export type UserStatus = 'active' | 'inactive'

export interface User {
  id: string
  username: string
  email: string
  full_name: string
  role: UserRole
  status: UserStatus
  department_id: string | null
  department_name: string | null
  position_id: string | null
  position_name: string | null
  manager_id: string | null
  manager_name: string | null
  hire_date: string | null
  phone: string | null
  created_at: string
  updated_at: string | null
  last_login_at: string | null
}

export interface Department {
  id: string
  name: string
  code: string
  parent_id: string | null
  level: number
  manager_id: string | null
  manager_name: string | null
  description: string | null
  member_count: number
  created_at: string
}

export interface Position {
  id: string
  name: string
  code: string
  level: string | null
  department_id: string | null
  department_name: string | null
  description: string | null
  member_count: number
  created_at: string
}

export type PeriodStatus = 'draft' | 'open' | 'closed' | 'archived'

export interface Period {
  id: string
  user_id: string
  name: string
  start_date: string
  end_date: string
  status: PeriodStatus
  d_phase_completed: boolean
  description: string | null
  created_at: string
  updated_at: string | null
}

export interface Goal {
  id: string
  owner_user_id: string
  period_id: string
  title: string
  description: string | null
  created_at: string
}

export interface Indicator {
  id: string
  goal_id: string
  name: string
  definition: string | null
  direction: 'positive' | 'negative'
  weight: number
  target_value: number | null
  score_method: 'ratio' | 'mapping' | 'binary' | 'manual'
  redline: boolean
  created_at: string
}

export type TrafficLight = 'green' | 'yellow' | 'red'

export interface DiagnosticReport {
  id: string
  goal_id: string
  user_id: string
  report_date: string
  overall_progress: number | null
  weighted_achievement_rate: number | null
  time_progress: number | null
  progress_deviation: number | null
  indicators_analysis: Record<string, unknown> | null
  root_cause_analysis: Record<string, unknown> | null
  improvement_suggestions: Record<string, unknown> | null
  traffic_light_status: TrafficLight | null
  generated_by_ai: boolean
  created_at: string
}

export interface DataCheckin {
  id: string
  indicator_id: string
  user_id: string
  actual_value: Record<string, unknown>
  progress_description: string | null
  issues: string | null
  submitted_at: string
  created_at: string
}

export interface CoachingRequest {
  id: string
  diagnostic_report_id: string
  goal_id: string | null
  requester_id: string
  manager_id: string
  request_reason: string | null
  urgency_level: 'low' | 'normal' | 'high'
  status: 'pending' | 'accepted' | 'rejected' | 'completed'
  scheduled_time: string | null
  actual_time: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface SelfAssessment {
  id: string
  goal_id: string
  user_id: string
  items: Record<string, { score: number; comment: string }>
  status: 'draft' | 'submitted' | 'withdrawn'
  submitted_at: string | null
  created_at: string
  updated_at: string
}

export interface EvaluationTask {
  id: string
  goal_id: string
  indicator_id: string
  evaluator_user_id: string
  assigned_by: string
  status: 'pending' | 'completed' | 'expired'
  assigned_at: string
  due_at: string | null
}

export interface Evaluation {
  id: string
  task_id: string
  goal_id: string
  indicator_id: string
  evaluator_id: string
  score: number
  comment: string | null
  created_at: string
}

export interface FinalResult {
  id: string
  goal_id: string
  suggested_grade: string | null
  final_grade: string
  confirmed_by: string
  confirmed_at: string
  adjustment_reason: string | null
  status: 'pending' | 'confirmed' | 'adjusted' | 'archived'
  created_at: string
}

export interface ReviewReport {
  id: string
  final_result_id: string
  user_id: string
  report_type: string
  strengths_analysis: Record<string, unknown> | null
  improvement_areas: Record<string, unknown> | null
  development_suggestions: Record<string, unknown> | null
  ai_generated: boolean
  generated_at: string
  reviewed_by_user: boolean
  user_feedback: string | null
  next_cycle_focus_areas: Record<string, unknown> | null
  created_at: string
}

export type DevelopmentPlanStatus = 'draft' | 'reviewed' | 'approved' | 'active' | 'completed'

export interface DevelopmentPlan {
  id: string
  review_report_id: string
  user_id: string
  plan_version: number
  goals: Record<string, unknown>
  actions: Record<string, unknown>
  required_resources: Record<string, unknown> | null
  timeline: Record<string, unknown> | null
  smart_evaluation: Record<string, unknown> | null
  ai_reviewed: boolean
  ai_suggestions: Record<string, unknown> | null
  status: DevelopmentPlanStatus
  approved_by: string | null
  approved_at: string | null
  completion_status: 'not_started' | 'in_progress' | 'completed' | 'carried_forward'
  completion_rate: number | null
  carry_forward_reason: string | null
  linked_to_next_cycle: boolean
  created_at: string
}

export interface InheritanceSuggestion {
  id: string
  user_id: string
  previous_development_plan_id: string
  previous_final_result_id: string
  new_period_id: string
  suggestion_type: 'new_goal' | 'new_indicator' | 'adjust_weight' | 'raise_target'
  suggestions: Record<string, unknown>
  adopted_goal_id: string | null
  adopted_indicator_id: string | null
  adoption_modifications: Record<string, unknown> | null
  status: 'pending' | 'accepted' | 'rejected' | 'partially_adopted'
  rejected_reason: string | null
  accepted_at: string | null
  created_at: string
}

export interface SubordinateItem {
  id: string
  username: string
  full_name: string
  role: UserRole
  department_name: string | null
  position_name: string | null
  is_direct: boolean
  level: number
}

export interface SessionInfo {
  id: string
  device_info: {
    browser: string | null
    os: string | null
    device_type: string | null
  }
  ip_address: string | null
  created_at: string
  expires_at: string
  is_current: boolean
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: {
    id: string
    username: string
    email: string
    role: UserRole
    department_id: string | null
  }
}

export interface JobAnalysis {
  id: string
  user_id: string
  jd_text: string
  job_prototype_code: string | null
  quantifiability_score: number | null
  output_cycle_score: number | null
  work_nature_score: number | null
  features: Record<string, unknown> | null
  confidence: number | null
  analysis_result: Record<string, unknown> | null
  created_at: string
}

export interface PerformanceContract {
  id: string
  goal_id: string | null
  job_prototype_code: string
  strategy_config: Record<string, unknown>
  contract_data: Record<string, unknown>
  ai_generated: boolean
  confirmed_at: string | null
  confirmed_by: string | null
  created_at: string
  updated_at: string
}
