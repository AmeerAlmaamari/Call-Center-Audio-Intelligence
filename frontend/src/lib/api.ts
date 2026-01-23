import axios from "axios"

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
})

export interface Agent {
  id: string
  name: string
  email: string
  department: string | null
  created_at: string
}

export interface CallAgent {
  id: string
  name: string
  email: string | null
  department: string | null
}

export interface Call {
  id: string
  filename: string
  file_path: string
  file_size: number | null
  duration_seconds: number | null
  status: string
  agent_id: string | null
  agent: CallAgent | null
  quality_flag: string
  quality_notes: string | null
  created_at: string
  updated_at: string
  transcript?: Transcript
  analysis?: CallAnalysis
}

export interface Transcript {
  id: string
  call_id: string
  raw_text: string
  segments: TranscriptSegment[]
  created_at: string
}

export interface TranscriptSegment {
  start: number
  end: number
  text: string
  speaker?: string
}

export interface CallAnalysis {
  id: string
  call_id: string
  performance_score: number | null
  communication_clarity: number | null
  responsiveness: number | null
  objection_handling_score: number | null
  listening_ratio: number | null
  performance_explanation: string | null
  interest_level: string | null
  buying_signals_detected: string[] | null
  sentiment_progression: SentimentPhase[] | null
  conversion_likelihood: number | null
  call_reason: string | null
  call_reason_confidence: number | null
  call_outcome: string | null
  call_outcome_confidence: number | null
  products_discussed: ProductMention[] | null
  recommended_products: ProductRecommendation[] | null
  objections_detected: Objection[] | null
  missed_opportunities: MissedOpportunity[] | null
  missed_opportunity_flag: boolean
  agent_speaking_time: number | null
  customer_speaking_time: number | null
  created_at: string
}

export interface SentimentPhase {
  phase: string
  sentiment: string
  notes: string
}

export interface ProductMention {
  name: string
  context: string
  confidence: number
}

export interface ProductRecommendation {
  name: string
  reason: string
  confidence: number
}

export interface Objection {
  type: string
  quote: string
  agent_response: string
  handling_score: number
}

export interface MissedOpportunity {
  description: string
  customer_signal?: string
}

export interface ActionItem {
  id: string
  call_id: string
  category: string
  priority: string
  description: string
  is_completed: boolean
  created_at: string
}

export interface RecentCall {
  id: string
  filename: string
  status: string
  agent_id: string | null
  agent_name: string | null
  created_at: string
  duration_seconds: number | null
}

export interface DashboardOverview {
  total_calls: number
  analyzed_calls: number
  calls_today: number
  conversion_rate: number
  avg_performance_score: number | null
  avg_conversion_likelihood: number | null
  avg_sentiment: number | null
  calls_by_status: Record<string, number>
  calls_by_outcome: Record<string, number>
  outcome_distribution: Record<string, number>
  recent_calls: RecentCall[]
}

export interface ActionCenterData {
  pending_followups: ActionItem[]
  missed_opportunities: { call_id: string; description?: string }[]
  coaching_recommendations: ActionItem[]
  training_needs: Record<string, number>
}

export interface AgentPerformance {
  agent_id: string
  agent_name: string
  total_calls: number
  avg_performance_score: number | null
  avg_objection_handling: number | null
  avg_conversion_likelihood: number | null
  conversion_rate: number
  successful_sales: number
}

export interface CallListResponse {
  items: Call[]
  total: number
  page: number
  page_size: number
}

export const callsApi = {
  list: async (params?: { status?: string; agent_id?: string; page?: number; page_size?: number }) => {
    const { data } = await api.get<CallListResponse>("/calls", { params })
    return data.items
  },
  get: async (id: string) => {
    const { data } = await api.get<Call>(`/calls/${id}`)
    return data
  },
  upload: async (file: File, agentId?: string) => {
    const formData = new FormData()
    formData.append("file", file)
    if (agentId) formData.append("agent_id", agentId)
    const { data } = await api.post<Call>("/calls/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    return data
  },
  transcribe: async (id: string) => {
    const { data } = await api.post<Call>(`/calls/${id}/transcribe`)
    return data
  },
  analyze: async (id: string) => {
    const { data } = await api.post<Call>(`/calls/${id}/analyze`)
    return data
  },
  getTranscript: async (id: string) => {
    const { data } = await api.get<Transcript>(`/calls/${id}/transcript`)
    return data
  },
  getAnalysis: async (id: string) => {
    const { data } = await api.get<CallAnalysis>(`/calls/${id}/analysis`)
    return data
  },
  getActionItems: async (id: string) => {
    const { data } = await api.get<ActionItem[]>(`/calls/${id}/actions`)
    return data
  },
  delete: async (id: string) => {
    const { data } = await api.delete<{ message: string }>(`/calls/${id}`)
    return data
  },
  process: async (id: string) => {
    const { data } = await api.post<{ message: string; call_id: string }>(`/calls/${id}/process`)
    return data
  },
  getStatus: async (id: string) => {
    const { data } = await api.get<CallProcessingStatus>(`/calls/${id}/status`)
    return data
  },
}

export interface CallProcessingStatus {
  call_id: string
  status: string
  has_transcript: boolean
  has_analysis: boolean
  action_items_count: number
  is_processing: boolean
  is_complete: boolean
  is_failed: boolean
}

export interface AgentCreate {
  name: string
  email?: string
  department?: string
}

export interface AgentUpdate {
  name?: string
  email?: string
  department?: string
}

export const agentsApi = {
  list: async () => {
    const { data } = await api.get<Agent[]>("/agents")
    return data
  },
  get: async (id: string) => {
    const { data } = await api.get<Agent>(`/agents/${id}`)
    return data
  },
  create: async (agentData: AgentCreate) => {
    const { data } = await api.post<Agent>("/agents", agentData)
    return data
  },
  update: async (id: string, agentData: AgentUpdate) => {
    const { data } = await api.patch<Agent>(`/agents/${id}`, agentData)
    return data
  },
  delete: async (id: string) => {
    const { data } = await api.delete<{ message: string }>(`/agents/${id}`)
    return data
  },
  getPerformance: async (id: string) => {
    const { data } = await api.get<AgentPerformance>(`/agents/${id}/performance`)
    return data
  },
}

export const dashboardApi = {
  getOverview: async () => {
    const { data } = await api.get<DashboardOverview>("/dashboard/overview")
    return data
  },
  getAgentPerformance: async () => {
    const { data } = await api.get<AgentPerformance[]>("/dashboard/agents")
    return data
  },
  getActionCenter: async () => {
    const { data } = await api.get<ActionCenterData>("/dashboard/actions")
    return data
  },
}

export default api
