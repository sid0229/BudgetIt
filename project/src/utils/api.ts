import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ---------------------------------------------------------------------------
// Shared types
// ---------------------------------------------------------------------------

export type ExpenseCategory = 'food' | 'transport' | 'rent' | 'entertainment' | 'utilities' | 'other';

export interface AuthUser {
  id: number;
  name: string;
  email: string;
  userType: 'student' | 'professional';
}

export interface AuthResponse {
  message?: string;
  user: AuthUser;
}

export interface ExpenseRecord {
  id: number;
  amount: number;
  category: string;
  description: string;
  date: string;
}

export interface GoalRecord {
  id: number;
  title: string;
  target_amount: number;
  saved_amount: number;
  target_date: string;
}

export interface WeeklyAnalytics {
  expenses: Record<string, number>;
  budgets: Record<string, number>;
}

// Chat
export interface ChatSource {
  title: string;
  source: string;
}

export interface ChatResponse {
  response: string;
  sources: ChatSource[];
  tools_used: string[];
  generated_by: 'llm' | 'fallback';
  timestamp: string;
}

export interface ChatHistoryMessage {
  role: 'user' | 'bot';
  text: string;
  timestamp: string;
}

export interface ChatHistoryResponse {
  messages: ChatHistoryMessage[];
}

// Insights
export type InsightType = 'warning' | 'success' | 'info' | 'celebration';

export interface ServerInsight {
  id: string;
  type: InsightType;
  title: string;
  message: string;
  action: string | null;
  tip_id: string | null;
}

export interface Persona {
  key: string;
  label: string;
  description: string;
  method: 'kmeans' | 'prototype' | 'cold_start';
}

export interface CategoryForecast {
  spent: number;
  projected: number;
  budget: number | null;
}

export interface MonthForecast {
  month: string;
  spent_so_far: number;
  projected_total: number;
  monthly_budget: number | null;
  projected_overrun: number;
  overrun_date: string | null;
  by_category: Record<string, CategoryForecast>;
}

export interface SpendingAnomaly {
  category: string;
  this_week: number;
  baseline: number;
  ratio: number;
  z: number;
}

export interface InsightsResponse {
  insights: ServerInsight[];
  persona: Persona | null;
  forecast: MonthForecast | null;
  anomalies: SpendingAnomaly[];
  generated_by: 'llm' | 'rules';
}

export interface CategorizeResponse {
  category: ExpenseCategory;
  confidence: number;
  method: 'keyword' | 'llm' | 'default';
}

export interface AIStatusResponse {
  llm: boolean;
  dense_retrieval: boolean;
  model: string;
}

export interface MessageResponse {
  message: string;
}

// ---------------------------------------------------------------------------
// Authentication API
// ---------------------------------------------------------------------------
export const authAPI = {
  signup: (userData: {
    name: string;
    email: string;
    password: string;
    userType: 'student' | 'professional';
  }) => api.post<AuthResponse>('/auth/signup', userData),

  signin: (credentials: { email: string; password: string }) =>
    api.post<AuthResponse>('/auth/signin', credentials),

  logout: () => api.post<MessageResponse>('/auth/logout'),

  getCurrentUser: () => api.get<AuthResponse>('/auth/me'),
};

// Expenses API
export const expensesAPI = {
  getExpenses: () => api.get<ExpenseRecord[]>('/expenses'),

  addExpense: (expense: {
    amount: number;
    category: string;
    description?: string;
    date?: string;
  }) => api.post('/expenses', expense),

  categorize: (description: string) =>
    api.post<CategorizeResponse>('/expenses/categorize', { description }),
};

// Budgets API
export const budgetsAPI = {
  getBudgets: () => api.get('/budgets'),

  setBudget: (budget: {
    category: string;
    amount: number;
    period: 'weekly' | 'monthly';
  }) => api.post('/budgets', budget),
};

// Goals API
export const goalsAPI = {
  getGoals: () => api.get<GoalRecord[]>('/goals'),

  addGoal: (goal: {
    title: string;
    targetAmount: number;
    targetDate: string;
  }) => api.post('/goals', goal),
};

// Chat API
export const chatAPI = {
  sendMessage: (message: string) => api.post<ChatResponse>('/chat', { message }),

  getHistory: () => api.get<ChatHistoryResponse>('/chat/history'),

  clearHistory: () => api.delete<MessageResponse>('/chat/history'),
};

// Insights API
export const insightsAPI = {
  getInsights: () => api.get<InsightsResponse>('/insights'),

  sendFeedback: (tipId: string, reward: 0 | 1) =>
    api.post<MessageResponse>('/insights/feedback', { tip_id: tipId, reward }),
};

// AI status API (no auth required)
export const aiAPI = {
  getStatus: () => api.get<AIStatusResponse>('/ai/status'),
};

// Analytics API
export const analyticsAPI = {
  getWeeklyAnalytics: () => api.get<WeeklyAnalytics>('/analytics/weekly'),
};

export const isUnauthorized = (error: unknown): boolean => {
  if (typeof error !== 'object' || error === null) return false;
  const response = (error as { response?: { status?: number } }).response;
  return response?.status === 401;
};

export default api;
