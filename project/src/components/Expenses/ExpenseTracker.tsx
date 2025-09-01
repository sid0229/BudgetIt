import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { expensesAPI } from '../../utils/api';
import { Plus, Calendar, DollarSign, Tag, Sparkles, TrendingDown } from 'lucide-react';

interface Expense {
  id: number;
  amount: number;
  category: string;
  description: string;
  date: string;
}

const ExpenseTracker: React.FC = () => {
  const { t } = useTranslation();
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newExpense, setNewExpense] = useState({
    amount: '',
    category: 'food',
    description: '',
    date: new Date().toISOString().split('T')[0],
  });

  const categories = ['food', 'transport', 'rent', 'entertainment', 'utilities', 'other'];
  const categoryEmojis: Record<string, string> = {
    food: '🍕',
    transport: '🚗',
    rent: '🏠',
    entertainment: '🎬',
    utilities: '💡',
    other: '📦'
  };

  useEffect(() => {
    fetchExpenses();
  }, []);

  const fetchExpenses = async () => {
    try {
      const response = await expensesAPI.getExpenses();
      setExpenses(response.data);
    } catch (error) {
      console.error('Error fetching expenses:', error);
    } finally {
      setIsLoading(false);
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
      setShowAddForm(false);
      fetchExpenses();
    } catch (error) {
      console.error('Error adding expense:', error);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setNewExpense({
      ...newExpense,
      [e.target.name]: e.target.value,
    });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-pink-50 to-green-50 flex items-center justify-center">
        <div className="text-lg text-gray-600 flex items-center space-x-2">
          <Sparkles className="h-6 w-6 animate-spin text-pink-400" />
          <span>{t('common.loading')}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 to-green-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-pink-500 to-green-500 bg-clip-text text-transparent">
              💸 {t('expenses.title')}
            </h1>
            <p className="text-gray-600 mt-1">Track your spending and stay on budget</p>
          </div>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="inline-flex items-center px-6 py-3 border border-transparent text-sm font-medium rounded-full shadow-lg text-white bg-gradient-to-r from-pink-400 to-green-400 hover:shadow-xl hover:scale-105 transition-all duration-200"
          >
            <Plus className="h-5 w-5 mr-2" />
            {t('expenses.add')}
          </button>
        </div>

        {showAddForm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
              <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                <Sparkles className="h-6 w-6 text-pink-400 mr-2" />
                Add New Expense
              </h3>
              <form onSubmit={handleAddExpense} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    💰 Amount
                  </label>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                    <input
                      type="number"
                      name="amount"
                      step="0.01"
                      required
                      className="pl-10 block w-full px-4 py-3 border-2 border-pink-200 rounded-xl focus:border-pink-400 focus:ring-4 focus:ring-pink-100 transition-all"
                      placeholder="0.00"
                      value={newExpense.amount}
                      onChange={handleInputChange}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    🏷️ Category
                  </label>
                  <div className="relative">
                    <Tag className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                    <select
                      name="category"
                      className="pl-10 block w-full px-4 py-3 border-2 border-pink-200 rounded-xl focus:border-pink-400 focus:ring-4 focus:ring-pink-100 transition-all"
                      value={newExpense.category}
                      onChange={handleInputChange}
                    >
                      {categories.map(category => (
                        <option key={category} value={category}>
                          {categoryEmojis[category]} {t(`expenses.categories.${category}`)}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    📅 Date
                  </label>
                  <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                    <input
                      type="date"
                      name="date"
                      required
                      className="pl-10 block w-full px-4 py-3 border-2 border-pink-200 rounded-xl focus:border-pink-400 focus:ring-4 focus:ring-pink-100 transition-all"
                      value={newExpense.date}
                      onChange={handleInputChange}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    📝 Description
                  </label>
                  <input
                    type="text"
                    name="description"
                    className="block w-full px-4 py-3 border-2 border-pink-200 rounded-xl focus:border-pink-400 focus:ring-4 focus:ring-pink-100 transition-all"
                    placeholder="What did you spend on?"
                    value={newExpense.description}
                    onChange={handleInputChange}
                  />
                </div>

                <div className="flex space-x-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowAddForm(false)}
                    className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-xl text-gray-700 hover:bg-gray-50 transition-all"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 px-4 py-3 bg-gradient-to-r from-pink-400 to-green-400 text-white rounded-xl hover:shadow-lg transition-all"
                  >
                    Add Expense
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Expenses List */}
        <div className="bg-white/80 backdrop-blur-sm shadow-lg rounded-2xl border border-pink-100">
          <div className="px-6 py-4 border-b border-pink-100">
            <h3 className="text-lg font-medium text-gray-900 flex items-center">
              <TrendingDown className="h-5 w-5 text-pink-400 mr-2" />
              Recent Expenses
            </h3>
          </div>
          <div className="divide-y divide-pink-50">
            {expenses.length === 0 ? (
              <div className="px-6 py-12 text-center text-gray-500">
                <div className="w-16 h-16 bg-gradient-to-r from-pink-100 to-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <DollarSign className="h-8 w-8 text-pink-400" />
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">No expenses yet!</h3>
                <p>Add your first expense to start tracking your spending 🚀</p>
              </div>
            ) : (
              expenses.map(expense => (
                <div key={expense.id} className="px-6 py-4 hover:bg-pink-50/50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center">
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gradient-to-r from-pink-100 to-green-100 text-gray-800">
                          {categoryEmojis[expense.category]} {t(`expenses.categories.${expense.category}`)}
                        </span>
                        <span className="ml-3 text-sm font-medium text-gray-900">
                          {expense.description || 'No description'}
                        </span>
                      </div>
                      <div className="mt-1 text-sm text-gray-500">
                        📅 {expense.date}
                      </div>
                    </div>
                    <div className="text-xl font-bold bg-gradient-to-r from-pink-500 to-green-500 bg-clip-text text-transparent">
                      ₹{expense.amount.toFixed(0)}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExpenseTracker;