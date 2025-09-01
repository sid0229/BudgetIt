import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { analyticsAPI, budgetsAPI, expensesAPI } from '../../utils/api';
import { 
  DollarSign, TrendingUp, Target, Plus, Settings, Sparkles, PiggyBank, 
  AlertTriangle, CheckCircle, TrendingDown, Calendar, Bell, 
  Activity, Zap, Award, Filter, Download, RefreshCw, Edit, Trash2, X
} from 'lucide-react';

interface AnalyticsData {
  expenses: Record<string, number>;
  budgets: Record<string, number>;
}

interface AIInsight {
  type: 'warning' | 'success' | 'info' | 'celebration';
  title: string;
  message: string;
  icon: React.ReactNode;
  color: string;
  tip?: string;
  quote?: string;
}

interface Expense {
  id: number;
  amount: number;
  category: string;
  description: string;
  date: string;
}

interface AINotification {
  id: string;
  type: 'warning' | 'success' | 'info' | 'celebration';
  title: string;
  message: string;
  show: boolean;
}

const Dashboard: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { isDarkMode } = useTheme();
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showBudgetForm, setShowBudgetForm] = useState(false);
  const [showExpenseForm, setShowExpenseForm] = useState(false);
  const [showEditExpense, setShowEditExpense] = useState(false);
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);
  const [showInsights, setShowInsights] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [aiNotification, setAiNotification] = useState<AINotification | null>(null);
  const [newBudget, setNewBudget] = useState({
    category: 'food',
    amount: '',
    period: 'weekly' as 'weekly' | 'monthly',
  });
  const [newExpense, setNewExpense] = useState({
    amount: '',
    category: 'food',
    description: '',
    date: new Date().toISOString().split('T')[0],
  });
  const [editExpense, setEditExpense] = useState({
    amount: '',
    category: 'food',
    description: '',
    date: '',
  });

  const categories = ['food', 'transport', 'rent', 'entertainment', 'utilities', 'other'];

  useEffect(() => {
    fetchAnalytics();
    fetchExpenses();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const response = await analyticsAPI.getWeeklyAnalytics();
      setAnalytics(response.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchExpenses = async () => {
    try {
      const response = await expensesAPI.getExpenses();
      setExpenses(response.data);
    } catch (error) {
      console.error('Error fetching expenses:', error);
    }
  };

  const handleSetBudget = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await budgetsAPI.setBudget({
        category: newBudget.category,
        amount: parseFloat(newBudget.amount),
        period: newBudget.period,
      });
      setNewBudget({ category: 'food', amount: '', period: 'weekly' });
      setShowBudgetForm(false);
      fetchAnalytics();
      showAINotification();
    } catch (error) {
      console.error('Error setting budget:', error);
    }
  };

  const handleAddExpense = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await expensesAPI.addExpense({
        amount: parseFloat(newExpense.amount),
        category: newExpense.category,
        description: newExpense.description,
        date: newExpense.date,
      });
      setNewExpense({
        amount: '',
        category: 'food',
        description: '',
        date: new Date().toISOString().split('T')[0],
      });
      setShowExpenseForm(false);
      fetchAnalytics();
      fetchExpenses();
      showAINotification();
    } catch (error) {
      console.error('Error adding expense:', error);
    }
  };

  const handleEditExpense = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingExpense) return;
    
    try {
      // Note: You'll need to implement updateExpense in your API
      // await expensesAPI.updateExpense(editingExpense.id, {
      //   amount: parseFloat(editExpense.amount),
      //   category: editExpense.category,
      //   description: editExpense.description,
      //   date: editExpense.date,
      // });
      
      setEditExpense({
        amount: '',
        category: 'food',
        description: '',
        date: '',
      });
      setShowEditExpense(false);
      setEditingExpense(null);
      fetchAnalytics();
      fetchExpenses();
      showAINotification();
    } catch (error) {
      console.error('Error updating expense:', error);
    }
  };

  const handleDeleteExpense = async (expenseId: number) => {
    if (!confirm('Are you sure you want to delete this expense?')) return;
    
    try {
      // Note: You'll need to implement deleteExpense in your API
      // await expensesAPI.deleteExpense(expenseId);
      fetchAnalytics();
      fetchExpenses();
      showAINotification();
    } catch (error) {
      console.error('Error deleting expense:', error);
    }
  };

  const openEditExpense = (expense: Expense) => {
    setEditingExpense(expense);
    setEditExpense({
      amount: expense.amount.toString(),
      category: expense.category,
      description: expense.description,
      date: expense.date,
    });
    setShowEditExpense(true);
  };

  const showAINotification = () => {
    const insights = generateAIInsights();
    if (insights.length > 0) {
      const randomInsight = insights[Math.floor(Math.random() * insights.length)];
      setAiNotification({
        id: Date.now().toString(),
        type: randomInsight.type,
        title: randomInsight.title,
        message: randomInsight.message,
        show: true,
      });
      
      // Auto hide after 5 seconds
      setTimeout(() => {
        setAiNotification(null);
      }, 5000);
    }
  };

  const getCategoryData = () => {
    if (!analytics) return [];
    
    const categories = Object.keys(analytics.expenses);
    return categories.map(category => ({
      name: category,
      spent: analytics.expenses[category] || 0,
      budget: analytics.budgets[category] || 0,
    }));
  };

  const getPieData = () => {
    if (!analytics) return [];
    
    return Object.entries(analytics.expenses).map(([category, amount]) => ({
      name: category,
      value: amount,
    }));
  };

  const totalSpent = analytics ? Object.values(analytics.expenses).reduce((sum, amount) => sum + amount, 0) : 0;
  const totalBudget = analytics ? Object.values(analytics.budgets).reduce((sum, amount) => sum + amount, 0) : 0;
  const remaining = totalBudget - totalSpent;
  const spendingPercentage = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0;

  // AI Insights Generation
  const generateAIInsights = (): AIInsight[] => {
    const insights: AIInsight[] = [];

    if (spendingPercentage > 90) {
      insights.push({
        type: 'warning',
        title: '🚨 Overspending Alert!',
        message: `You've spent ₹${totalSpent.toFixed(0)} (${spendingPercentage.toFixed(1)}% of budget)`,
        icon: <AlertTriangle className="h-6 w-6" />,
        color: 'from-red-400 to-pink-500',
        tip: '💡 Quick Fixes: Cook at home (save ₹200/day), use public transport, cancel unused subscriptions, set daily spending limits of ₹500.',
        quote: '"A budget is telling your money where to go instead of wondering where it went." - Dave Ramsey'
      });
    } else if (spendingPercentage > 75) {
      insights.push({
        type: 'info',
        title: '⚠️ Approaching Budget Limit',
        message: `You're at ₹${totalSpent.toFixed(0)} (${spendingPercentage.toFixed(1)}% of budget)`,
        icon: <Bell className="h-6 w-6" />,
        color: 'from-yellow-400 to-orange-500',
        tip: '🎯 Stay on track: Review daily expenses, avoid impulse purchases, stick to your meal plan, use discount apps.',
        quote: '"It\'s not how much money you make, but how much money you keep." - Robert Kiyosaki'
      });
    } else if (spendingPercentage < 50) {
      insights.push({
        type: 'celebration',
        title: '🎉 Fantastic Savings!',
        message: `Outstanding! Only ₹${totalSpent.toFixed(0)} spent (${spendingPercentage.toFixed(1)}% of budget)`,
        icon: <Award className="h-6 w-6" />,
        color: 'from-green-400 to-emerald-500',
        tip: '💰 Investment Ideas: Start SIP with ₹1000/month, open PPF account, invest in index funds, build emergency fund worth 6 months expenses.',
        quote: '"The best time to plant a tree was 20 years ago. The second best time is now." - Chinese Proverb'
      });
    } else {
      insights.push({
        type: 'success',
        title: '✅ Perfect Balance!',
        message: `Excellent! ₹${totalSpent.toFixed(0)} spent (${spendingPercentage.toFixed(1)}% of budget)`,
        icon: <CheckCircle className="h-6 w-6" />,
        color: 'from-green-400 to-green-500',
        tip: '🌟 Keep the momentum: Continue tracking daily, reward yourself occasionally, maintain this discipline for long-term wealth.',
        quote: '"A penny saved is a penny earned." - Benjamin Franklin'
      });
    }

    // Category-specific insights
    if (analytics) {
      Object.entries(analytics.expenses).forEach(([category, spent]) => {
        const budget = analytics.budgets[category] || 0;
        if (budget > 0 && spent > budget * 0.9) {
          insights.push({
            type: 'warning',
            title: `${category.charAt(0).toUpperCase() + category.slice(1)} Alert`,
            message: `You're overspending on ${category}. Consider alternatives!`,
            icon: <TrendingDown className="h-5 w-5" />,
            color: 'from-orange-400 to-red-500'
          });
        }
      });
    }

    return insights;
  };

  const aiInsights = generateAIInsights();

  const COLORS = ['#F472B6', '#34D399', '#A78BFA', '#FBBF24', '#FB7185'];

  if (isLoading) {
    return (
      <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gradient-to-br from-pink-50 to-green-50'} flex items-center justify-center`}>
        <div className="text-lg text-gray-600 dark:text-gray-400 flex items-center space-x-2">
          <Sparkles className="h-6 w-6 animate-spin text-pink-400" />
          <span>{t('common.loading')}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gradient-to-br from-pink-50 via-white to-green-50'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-pink-500 to-green-500 bg-clip-text text-transparent">
                ✨ {t('dashboard.title')}
              </h1>
              <p className={`${isDarkMode ? 'text-gray-400' : 'text-gray-600'} mt-1`}>
                {user?.userType === 'student' ? '🎓 Student Dashboard' : '💼 Professional Dashboard'}
              </p>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={() => fetchAnalytics()}
                className="px-4 py-2 bg-gradient-to-r from-purple-400 to-purple-500 text-white rounded-full hover:shadow-lg hover:scale-105 transition-all duration-200 flex items-center space-x-2"
              >
                <RefreshCw className="h-4 w-4" />
                <span>Refresh</span>
              </button>
              <button
                onClick={() => setShowBudgetForm(true)}
                className="px-6 py-3 bg-gradient-to-r from-pink-400 to-pink-500 text-white rounded-full hover:shadow-lg hover:scale-105 transition-all duration-200 flex items-center space-x-2"
              >
                <Settings className="h-5 w-5" />
                <span>Set Budget</span>
              </button>
              <button
                onClick={() => setShowExpenseForm(true)}
                className="px-6 py-3 bg-gradient-to-r from-green-400 to-green-500 text-white rounded-full hover:shadow-lg hover:scale-105 transition-all duration-200 flex items-center space-x-2"
              >
                <Plus className="h-5 w-5" />
                <span>Add Expense</span>
              </button>
            </div>
          </div>
        </div>

        {/* AI Insights Section */}
        {showInsights && aiInsights.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'} flex items-center`}>
                <Zap className="h-6 w-6 text-yellow-400 mr-2" />
                AI Insights
              </h2>
              <button
                onClick={() => setShowInsights(false)}
                className={`text-sm ${isDarkMode ? 'text-gray-400 hover:text-gray-300' : 'text-gray-600 hover:text-gray-700'} transition-colors`}
              >
                Dismiss
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {aiInsights.map((insight, index) => (
                <div
                  key={index}
                  className={`${isDarkMode ? 'bg-gray-800/80' : 'bg-white/80'} backdrop-blur-sm p-6 rounded-2xl shadow-lg border ${isDarkMode ? 'border-gray-700' : 'border-pink-100'} hover:shadow-xl transition-all duration-300`}
                >
                  <div className="flex items-start space-x-3">
                    <div className={`flex-shrink-0 p-3 bg-gradient-to-r ${insight.color} rounded-xl text-white`}>
                      {insight.icon}
                    </div>
                    <div className="flex-1">
                      <h3 className={`font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'} mb-2`}>
                        {insight.title}
                      </h3>
                      <p className={`text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                        {insight.message}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="mb-8">
          <div className={`${isDarkMode ? 'bg-gray-800/80' : 'bg-white/80'} backdrop-blur-sm rounded-2xl p-2 shadow-lg border ${isDarkMode ? 'border-gray-700' : 'border-pink-100'}`}>
            <div className="flex space-x-2">
              {[
                { id: 'overview', label: '📊 Overview', icon: Activity },
                { id: 'analytics', label: '📈 Analytics', icon: TrendingUp },
                { id: 'insights', label: '🧠 AI Insights', icon: Zap },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 flex items-center justify-center space-x-2 px-4 py-3 rounded-xl font-medium transition-all duration-200 ${
                    activeTab === tab.id
                      ? 'bg-gradient-to-r from-pink-400 to-green-400 text-white shadow-lg'
                      : `${isDarkMode ? 'text-gray-400 hover:text-white hover:bg-gray-700' : 'text-gray-600 hover:text-gray-900 hover:bg-pink-50'}`
                  }`}
                >
                  <tab.icon className="h-5 w-5" />
                  <span>{tab.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* AI Notification Popup */}
        {aiNotification && aiNotification.show && (
          <div className="fixed top-20 right-6 z-50 transform transition-all duration-500 ease-out animate-in slide-in-from-right">
            <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl shadow-2xl border-l-4 ${
              aiNotification.type === 'warning' ? 'border-red-400' :
              aiNotification.type === 'success' ? 'border-green-400' :
              aiNotification.type === 'celebration' ? 'border-purple-400' :
              'border-yellow-400'
            } p-6 max-w-sm`}>
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3">
                  <div className={`p-2 rounded-full ${
                    aiNotification.type === 'warning' ? 'bg-red-100 text-red-600' :
                    aiNotification.type === 'success' ? 'bg-green-100 text-green-600' :
                    aiNotification.type === 'celebration' ? 'bg-purple-100 text-purple-600' :
                    'bg-yellow-100 text-yellow-600'
                  }`}>
                    <Zap className="h-5 w-5" />
                  </div>
                  <div className="flex-1">
                    <h4 className={`font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'} mb-1`}>
                      {aiNotification.title}
                    </h4>
                    <p className={`text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                      {aiNotification.message}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setAiNotification(null)}
                  className={`${isDarkMode ? 'text-gray-400 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'} transition-colors`}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="mt-3 flex items-center space-x-2">
                <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-1">
                  <div className={`h-1 rounded-full ${
                    aiNotification.type === 'warning' ? 'bg-red-400' :
                    aiNotification.type === 'success' ? 'bg-green-400' :
                    aiNotification.type === 'celebration' ? 'bg-purple-400' :
                    'bg-yellow-400'
                  } transition-all duration-5000 ease-out`} style={{ width: '100%' }}></div>
                </div>
                <span className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>AI</span>
              </div>
            </div>
          </div>
        )}

        {/* Recent Expenses with Edit/Delete */}
        <div className="mb-8">
          <div className={`${isDarkMode ? 'bg-gray-800/80' : 'bg-white/80'} backdrop-blur-sm rounded-2xl shadow-lg border ${isDarkMode ? 'border-gray-700' : 'border-pink-100'} overflow-hidden`}>
            <div className="px-6 py-4 border-b border-pink-100 dark:border-gray-700">
              <h3 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'} flex items-center`}>
                <TrendingDown className="h-5 w-5 text-pink-400 mr-2" />
                Recent Expenses
              </h3>
            </div>
            <div className="max-h-64 overflow-y-auto">
              {expenses.slice(0, 5).map(expense => (
                <div key={expense.id} className={`px-6 py-4 border-b border-pink-50 dark:border-gray-700 hover:bg-pink-50/50 dark:hover:bg-gray-700/50 transition-colors flex items-center justify-between group`}>
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gradient-to-r from-pink-100 to-green-100 text-gray-800">
                        {expense.category}
                      </span>
                      <span className={`font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                        {expense.description || 'No description'}
                      </span>
                    </div>
                    <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'} mt-1`}>
                      {expense.date}
                    </p>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className="text-lg font-bold bg-gradient-to-r from-pink-500 to-green-500 bg-clip-text text-transparent">
                      ₹{expense.amount.toFixed(0)}
                    </span>
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity flex space-x-2">
                      <button
                        onClick={() => openEditExpense(expense)}
                        className="p-2 text-blue-600 hover:bg-blue-100 rounded-lg transition-colors"
                      >
                        <Edit className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteExpense(expense.id)}
                        className="p-2 text-red-600 hover:bg-red-100 rounded-lg transition-colors"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Budget Form Modal */}
        {showBudgetForm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl`}>
              <h3 className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'} mb-4`}>💰 Set Budget</h3>
              <form onSubmit={handleSetBudget} className="space-y-4">
                <div>
                  <label className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'} mb-2`}>Category</label>
                  <select
                    value={newBudget.category}
                    onChange={(e) => setNewBudget({...newBudget, category: e.target.value})}
                    className={`w-full px-4 py-3 border-2 ${isDarkMode ? 'border-gray-600 bg-gray-700 text-white' : 'border-pink-200'} rounded-xl focus:border-pink-400 focus:ring-4 focus:ring-pink-100 transition-all`}
                  >
                    {categories.map(category => (
                      <option key={category} value={category}>
                        {t(`expenses.categories.${category}`)}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'} mb-2`}>Amount</label>
                  <input
                    type="number"
                    step="0.01"
                    value={newBudget.amount}
                    onChange={(e) => setNewBudget({...newBudget, amount: e.target.value})}
                    className={`w-full px-4 py-3 border-2 ${isDarkMode ? 'border-gray-600 bg-gray-700 text-white' : 'border-pink-200'} rounded-xl focus:border-pink-400 focus:ring-4 focus:ring-pink-100 transition-all`}
                    placeholder="Enter budget amount in ₹"
                    required
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'} mb-2`}>Period</label>
                  <select
                    value={newBudget.period}
                    onChange={(e) => setNewBudget({...newBudget, period: e.target.value as 'weekly' | 'monthly'})}
                    className={`w-full px-4 py-3 border-2 ${isDarkMode ? 'border-gray-600 bg-gray-700 text-white' : 'border-pink-200'} rounded-xl focus:border-pink-400 focus:ring-4 focus:ring-pink-100 transition-all`}
                  >
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>
                <div className="flex space-x-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowBudgetForm(false)}
                    className={`flex-1 px-4 py-3 border-2 ${isDarkMode ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-300 text-gray-700 hover:bg-gray-50'} rounded-xl transition-all`}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 px-4 py-3 bg-gradient-to-r from-pink-400 to-pink-500 text-white rounded-xl hover:shadow-lg transition-all"
                  >
                    Set Budget
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Expense Form Modal */}
        {showExpenseForm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl`}>
              <h3 className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'} mb-4`}>💸 Add Expense</h3>
              <form onSubmit={handleAddExpense} className="space-y-4">
                <div>
                  <label className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'} mb-2`}>Amount</label>
                  <input
                    type="number"
                    step="0.01"
                    value={newExpense.amount}
                    onChange={(e) => setNewExpense({...newExpense, amount: e.target.value})}
                    className={`w-full px-4 py-3 border-2 ${isDarkMode ? 'border-gray-600 bg-gray-700 text-white' : 'border-green-200'} rounded-xl focus:border-green-400 focus:ring-4 focus:ring-green-100 transition-all`}
                    placeholder="Enter amount in ₹"
                    required
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'} mb-2`}>Category</label>
                  <select
                    value={newExpense.category}
                    onChange={(e) => setNewExpense({...newExpense, category: e.target.value})}
                    className={`w-full px-4 py-3 border-2 ${isDarkMode ? 'border-gray-600 bg-gray-700 text-white' : 'border-green-200'} rounded-xl focus:border-green-400 focus:ring-4 focus:ring-green-100 transition-all`}
                  >
                    {categories.map(category => (
                      <option key={category} value={category}>
                        {t(`expenses.categories.${category}`)}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'} mb-2`}>Description</label>
                  <input
                    type="text"
                    value={newExpense.description}
                    onChange={(e) => setNewExpense({...newExpense, description: e.target.value})}
                    className={`w-full px-4 py-3 border-2 ${isDarkMode ? 'border-gray-600 bg-gray-700 text-white' : 'border-green-200'} rounded-xl focus:border-green-400 focus:ring-4 focus:ring-green-100 transition-all`}
                    placeholder="What did you spend on?"
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'} mb-2`}>Date</label>
                  <input
                    type="date"
                    value={newExpense.date}
                    onChange={(e) => setNewExpense({...newExpense, date: e.target.value})}
                    className={`w-full px-4 py-3 border-2 ${isDarkMode ? 'border-gray-600 bg-gray-700 text-white' : 'border-green-200'} rounded-xl focus:border-green-400 focus:ring-4 focus:ring-green-100 transition-all`}
                    required
                  />
                </div>
                <div className="flex space-x-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowExpenseForm(false)}
                    className={`flex-1 px-4 py-3 border-2 ${isDarkMode ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-300 text-gray-700 hover:bg-gray-50'} rounded-xl transition-all`}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 px-4 py-3 bg-gradient-to-r from-green-400 to-green-500 text-white rounded-xl hover:shadow-lg transition-all"
                  >
                    Add Expense
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Edit Expense Modal */}
        {showEditExpense && editingExpense && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl`}>
              <h3 className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'} mb-4`}>✏️ Edit Expense</h3>
              <form onSubmit={handleEditExpense} className="space-y-4">
                <div>
                  <label className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'} mb-2`}>Amount</label>
                  <input
                    type="number"
                    step="0.01"
                    value={editExpense.amount}
                    onChange={(e) => setEditExpense({...editExpense, amount: e.target.value})}
                    className={`w-full px-4 py-3 border-2 ${isDarkMode ? 'border-gray-600 bg-gray-700 text-white' : 'border-blue-200'} rounded-xl focus:border-blue-400 focus:ring-4 focus:ring-blue-100 transition-all`}
                    placeholder="Enter amount in ₹"
                    required
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'} mb-2`}>Category</label>
                  <select
                    value={editExpense.category}
                    onChange={(e) => setEditExpense({...editExpense, category: e.target.value})}
                    className={`w-full px-4 py-3 border-2 ${isDarkMode ? 'border-gray-600 bg-gray-700 text-white' : 'border-blue-200'} rounded-xl focus:border-blue-400 focus:ring-4 focus:ring-blue-100 transition-all`}
                  >
                    {categories.map(category => (
                      <option key={category} value={category}>
                        {t(`expenses.categories.${category}`)}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'} mb-2`}>Description</label>
                  <input
                    type="text"
                    value={editExpense.description}
                    onChange={(e) => setEditExpense({...editExpense, description: e.target.value})}
                    className={`w-full px-4 py-3 border-2 ${isDarkMode ? 'border-gray-600 bg-gray-700 text-white' : 'border-blue-200'} rounded-xl focus:border-blue-400 focus:ring-4 focus:ring-blue-100 transition-all`}
                    placeholder="What did you spend on?"
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'} mb-2`}>Date</label>
                  <input
                    type="date"
                    value={editExpense.date}
                    onChange={(e) => setEditExpense({...editExpense, date: e.target.value})}
                    className={`w-full px-4 py-3 border-2 ${isDarkMode ? 'border-gray-600 bg-gray-700 text-white' : 'border-blue-200'} rounded-xl focus:border-blue-400 focus:ring-4 focus:ring-blue-100 transition-all`}
                    required
                  />
                </div>
                <div className="flex space-x-3 pt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setShowEditExpense(false);
                      setEditingExpense(null);
                    }}
                    className={`flex-1 px-4 py-3 border-2 ${isDarkMode ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-300 text-gray-700 hover:bg-gray-50'} rounded-xl transition-all`}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 px-4 py-3 bg-gradient-to-r from-blue-400 to-blue-500 text-white rounded-xl hover:shadow-lg transition-all"
                  >
                    Update Expense
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className={`${isDarkMode ? 'bg-gray-800/80' : 'bg-white/80'} backdrop-blur-sm p-6 rounded-2xl shadow-lg border ${isDarkMode ? 'border-gray-700' : 'border-pink-100'} hover:shadow-xl transition-all duration-300`}>
                <div className="flex items-center">
                  <div className="flex-shrink-0 p-3 bg-gradient-to-r from-pink-400 to-pink-500 rounded-xl">
                    <DollarSign className="h-8 w-8 text-white" />
                  </div>
                  <div className="ml-4">
                    <p className={`text-sm font-medium ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>{t('dashboard.totalSpent')}</p>
                    <p className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>₹{totalSpent.toFixed(0)}</p>
                  </div>
                </div>
              </div>

              <div className={`${isDarkMode ? 'bg-gray-800/80' : 'bg-white/80'} backdrop-blur-sm p-6 rounded-2xl shadow-lg border ${isDarkMode ? 'border-gray-700' : 'border-green-100'} hover:shadow-xl transition-all duration-300`}>
                <div className="flex items-center">
                  <div className="flex-shrink-0 p-3 bg-gradient-to-r from-green-400 to-green-500 rounded-xl">
                    <Target className="h-8 w-8 text-white" />
                  </div>
                  <div className="ml-4">
                    <p className={`text-sm font-medium ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>{t('dashboard.totalBudget')}</p>
                    <p className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>₹{totalBudget.toFixed(0)}</p>
                  </div>
                </div>
              </div>

              <div className={`${isDarkMode ? 'bg-gray-800/80' : 'bg-white/80'} backdrop-blur-sm p-6 rounded-2xl shadow-lg border ${isDarkMode ? 'border-gray-700' : 'border-purple-100'} hover:shadow-xl transition-all duration-300`}>
                <div className="flex items-center">
                  <div className={`flex-shrink-0 p-3 rounded-xl ${remaining >= 0 ? 'bg-gradient-to-r from-green-400 to-green-500' : 'bg-gradient-to-r from-pink-400 to-pink-500'}`}>
                    <PiggyBank className="h-8 w-8 text-white" />
                  </div>
                  <div className="ml-4">
                    <p className={`text-sm font-medium ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>{t('dashboard.remaining')}</p>
                    <p className={`text-2xl font-bold ${remaining >= 0 ? 'text-green-600' : 'text-pink-600'}`}>
                      ₹{remaining.toFixed(0)}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Spending by Category - Pie Chart */}
              <div className={`${isDarkMode ? 'bg-gray-800/80' : 'bg-white/80'} backdrop-blur-sm p-6 rounded-2xl shadow-lg border ${isDarkMode ? 'border-gray-700' : 'border-pink-100'}`}>
                <h3 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'} mb-4 flex items-center`}>
                  <Sparkles className="h-5 w-5 text-pink-400 mr-2" />
                  Spending by Category
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={getPieData()}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {getPieData().map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Budget vs Actual - Bar Chart */}
              <div className={`${isDarkMode ? 'bg-gray-800/80' : 'bg-white/80'} backdrop-blur-sm p-6 rounded-2xl shadow-lg border ${isDarkMode ? 'border-gray-700' : 'border-green-100'}`}>
                <h3 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'} mb-4 flex items-center`}>
                  <TrendingUp className="h-5 w-5 text-green-400 mr-2" />
                  Budget vs Actual
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={getCategoryData()}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="budget" fill="#34D399" name="Budget" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="spent" fill="#F472B6" name="Spent" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        )}

        {activeTab === 'analytics' && (
          <div className="space-y-6">
            <div className={`${isDarkMode ? 'bg-gray-800/80' : 'bg-white/80'} backdrop-blur-sm p-6 rounded-2xl shadow-lg border ${isDarkMode ? 'border-gray-700' : 'border-purple-100'}`}>
              <h3 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'} mb-4 flex items-center`}>
                <Activity className="h-5 w-5 text-purple-400 mr-2" />
                Spending Trends
              </h3>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={getCategoryData()}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="spent" stroke="#F472B6" strokeWidth={3} />
                  <Line type="monotone" dataKey="budget" stroke="#34D399" strokeWidth={3} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {activeTab === 'insights' && (
          <div className="space-y-6">
            <div className={`${isDarkMode ? 'bg-gray-800/80' : 'bg-white/80'} backdrop-blur-sm p-8 rounded-2xl shadow-lg border ${isDarkMode ? 'border-gray-700' : 'border-yellow-100'} text-center`}>
              <div className="relative">
                <Zap className="h-16 w-16 text-yellow-400 mx-auto mb-4 animate-pulse" />
                <div className="absolute -top-2 -right-2 w-6 h-6 bg-green-400 rounded-full flex items-center justify-center">
                  <div className="w-2 h-2 bg-white rounded-full animate-ping"></div>
                </div>
              </div>
              <h3 className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'} mb-4`}>
                🧠 AI-Powered Insights
              </h3>
              <p className={`${isDarkMode ? 'text-gray-300' : 'text-gray-600'} mb-6`}>
                Get personalized recommendations and insights about your spending patterns.
              </p>
              
              {/* AI Processing Status */}
              <div className="mb-6 space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className={isDarkMode ? 'text-gray-400' : 'text-gray-600'}>AI Analysis Progress</span>
                  <span className="text-green-500 font-medium">92% Complete</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div className="bg-gradient-to-r from-green-400 to-blue-500 h-2 rounded-full transition-all duration-1000 ease-out" style={{ width: '92%' }}></div>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {aiInsights.map((insight, index) => (
                  <div
                    key={index}
                    className={`p-6 rounded-xl border ${isDarkMode ? 'border-gray-600 bg-gray-700/50' : 'border-gray-200 bg-gray-50'} hover:shadow-lg transition-all duration-300 transform hover:scale-105`}
                  >
                    <div className="flex items-center space-x-3 mb-4">
                      <div className={`p-2 bg-gradient-to-r ${insight.color} rounded-lg text-white`}>
                        {insight.icon}
                      </div>
                      <h4 className={`font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                        {insight.title}
                      </h4>
                    </div>
                    <p className={`text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-600'} mb-3`}>
                      {insight.message}
                    </p>
                    {insight.tip && (
                      <div className={`mt-3 p-3 rounded-lg ${isDarkMode ? 'bg-gray-600/50' : 'bg-blue-50'} border-l-4 border-blue-400`}>
                        <p className={`text-xs ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                          {insight.tip}
                        </p>
                      </div>
                    )}
                    {insight.quote && (
                      <div className={`mt-3 p-3 rounded-lg ${isDarkMode ? 'bg-gray-600/30' : 'bg-purple-50'} border-l-4 border-purple-400`}>
                        <p className={`text-xs italic ${isDarkMode ? 'text-gray-400' : 'text-purple-700'}`}>
                          {insight.quote}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;