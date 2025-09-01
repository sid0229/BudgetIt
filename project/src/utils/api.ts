import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Authentication API
export const authAPI = {
  signup: (userData: {
    name: string;
    email: string;
    password: string;
    userType: 'student' | 'professional';
  }) => api.post('/auth/signup', userData),
  
  signin: (credentials: { email: string; password: string }) =>
    api.post('/auth/signin', credentials),
  
  logout: () => api.post('/auth/logout'),
  
  getCurrentUser: () => api.get('/auth/me'),
};

// Expenses API
export const expensesAPI = {
  getExpenses: () => api.get('/expenses'),
  
  addExpense: (expense: {
    amount: number;
    category: string;
    description?: string;
    date?: string;
  }) => api.post('/expenses', expense),
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
  getGoals: () => api.get('/goals'),
  
  addGoal: (goal: {
    title: string;
    targetAmount: number;
    targetDate: string;
  }) => api.post('/goals', goal),
};

// Chat API
export const chatAPI = {
  sendMessage: (message: string) => api.post('/chat', { message }),
};

// Analytics API
export const analyticsAPI = {
  getWeeklyAnalytics: () => api.get('/analytics/weekly'),
};

export default api;