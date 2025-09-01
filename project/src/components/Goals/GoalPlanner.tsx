import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { goalsAPI } from '../../utils/api';
import { Plus, Target, Calendar, DollarSign, Sparkles, Trophy } from 'lucide-react';

interface Goal {
  id: number;
  title: string;
  target_amount: number;
  saved_amount: number;
  target_date: string;
}

const GoalPlanner: React.FC = () => {
  const { t } = useTranslation();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newGoal, setNewGoal] = useState({
    title: '',
    targetAmount: '',
    targetDate: '',
  });

  useEffect(() => {
    fetchGoals();
  }, []);

  const fetchGoals = async () => {
    try {
      const response = await goalsAPI.getGoals();
      setGoals(response.data);
    } catch (error) {
      console.error('Error fetching goals:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await goalsAPI.addGoal({
        title: newGoal.title,
        targetAmount: parseFloat(newGoal.targetAmount),
        targetDate: newGoal.targetDate,
      });
      
      setNewGoal({
        title: '',
        targetAmount: '',
        targetDate: '',
      });
      setShowAddForm(false);
      fetchGoals();
    } catch (error) {
      console.error('Error adding goal:', error);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setNewGoal({
      ...newGoal,
      [e.target.name]: e.target.value,
    });
  };

  const getProgressPercentage = (goal: Goal) => {
    return Math.min((goal.saved_amount / goal.target_amount) * 100, 100);
  };

  const getDaysRemaining = (targetDate: string) => {
    const target = new Date(targetDate);
    const today = new Date();
    const diffTime = target.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
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
              🎯 {t('goals.title')}
            </h1>
            <p className="text-gray-600 mt-1">Set goals, track progress, achieve dreams</p>
          </div>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="inline-flex items-center px-6 py-3 border border-transparent text-sm font-medium rounded-full shadow-lg text-white bg-gradient-to-r from-pink-400 to-green-400 hover:shadow-xl hover:scale-105 transition-all duration-200"
          >
            <Plus className="h-5 w-5 mr-2" />
            {t('goals.add')}
          </button>
        </div>

        {showAddForm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
              <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                <Target className="h-6 w-6 text-green-400 mr-2" />
                Create New Goal
              </h3>
              <form onSubmit={handleAddGoal} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    🎯 Goal Title
                  </label>
                  <input
                    type="text"
                    name="title"
                    required
                    className="block w-full px-4 py-3 border-2 border-green-200 rounded-xl focus:border-green-400 focus:ring-4 focus:ring-green-100 transition-all"
                    value={newGoal.title}
                    onChange={handleInputChange}
                    placeholder="e.g., New Laptop, Dream Vacation"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    💰 Target Amount
                  </label>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                    <input
                      type="number"
                      name="targetAmount"
                      step="0.01"
                      required
                      className="pl-10 block w-full px-4 py-3 border-2 border-green-200 rounded-xl focus:border-green-400 focus:ring-4 focus:ring-green-100 transition-all"
                      value={newGoal.targetAmount}
                      onChange={handleInputChange}
                      placeholder="0.00"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    📅 Target Date
                  </label>
                  <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                    <input
                      type="date"
                      name="targetDate"
                      required
                      className="pl-10 block w-full px-4 py-3 border-2 border-green-200 rounded-xl focus:border-green-400 focus:ring-4 focus:ring-green-100 transition-all"
                      value={newGoal.targetDate}
                      onChange={handleInputChange}
                    />
                  </div>
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
                    className="flex-1 px-4 py-3 bg-gradient-to-r from-green-400 to-green-500 text-white rounded-xl hover:shadow-lg transition-all"
                  >
                    Create Goal
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Goals List */}
        <div className="space-y-6">
          {goals.length === 0 ? (
            <div className="bg-white/80 backdrop-blur-sm p-12 rounded-2xl shadow-lg border border-green-100 text-center">
              <div className="w-20 h-20 bg-gradient-to-r from-green-100 to-pink-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <Target className="h-10 w-10 text-green-400" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">No Goals Yet! 🎯</h3>
              <p className="text-gray-600 mb-6">Start setting your financial goals to track your progress and achieve your dreams!</p>
              <button
                onClick={() => setShowAddForm(true)}
                className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-green-400 to-green-500 text-white rounded-full hover:shadow-lg hover:scale-105 transition-all duration-200"
              >
                <Plus className="h-5 w-5 mr-2" />
                Create Your First Goal
              </button>
            </div>
          ) : (
            goals.map(goal => {
              const progress = getProgressPercentage(goal);
              const daysRemaining = getDaysRemaining(goal.target_date);
              
              return (
                <div key={goal.id} className="bg-white/80 backdrop-blur-sm p-6 rounded-2xl shadow-lg border border-green-100 hover:shadow-xl transition-all duration-300">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center space-x-3">
                      <div className="w-12 h-12 bg-gradient-to-r from-green-400 to-pink-400 rounded-xl flex items-center justify-center">
                        <Trophy className="h-6 w-6 text-white" />
                      </div>
                      <div>
                        <h3 className="text-xl font-bold text-gray-900">{goal.title}</h3>
                        <p className="text-sm text-gray-600">
                          💰 Target: ₹{goal.target_amount.toFixed(0)} | 
                          {daysRemaining > 0 ? ` ⏰ ${daysRemaining} days remaining` : ' 🎉 Target date reached!'}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-3xl font-bold bg-gradient-to-r from-green-500 to-pink-500 bg-clip-text text-transparent">
                        {progress.toFixed(1)}%
                      </p>
                      <p className="text-sm text-gray-500">Complete</p>
                    </div>
                  </div>
                  
                  <div className="mb-4">
                    <div className="flex justify-between text-sm text-gray-600 mb-2">
                      <span className="font-medium">Progress</span>
                      <span className="font-medium">₹{goal.saved_amount.toFixed(0)} / ₹{goal.target_amount.toFixed(0)}</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                      <div 
                        className="bg-gradient-to-r from-green-400 to-pink-400 h-3 rounded-full transition-all duration-500 ease-out"
                        style={{ width: `${progress}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <div className="text-sm text-gray-600">
                      <span className="font-medium">💸 Still needed:</span> ₹{(goal.target_amount - goal.saved_amount).toFixed(0)}
                    </div>
                    <div className="text-sm text-gray-600">
                      <span className="font-medium">📅 Target:</span> {goal.target_date}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};

export default GoalPlanner;