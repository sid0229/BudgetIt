import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { Link } from 'react-router-dom';
import { Mail, Lock, User, GraduationCap, Briefcase, Sparkles, Eye, EyeOff } from 'lucide-react';

const SignUp: React.FC = () => {
  const { t } = useTranslation();
  const { signup } = useAuth();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    userType: 'student' as 'student' | 'professional',
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await signup(formData);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Sign up failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-pink-50 via-white to-green-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-gradient-to-r from-pink-400 to-green-400 rounded-2xl flex items-center justify-center mb-4">
            <Sparkles className="h-8 w-8 text-white" />
          </div>
          <h2 className="text-3xl font-extrabold bg-gradient-to-r from-pink-500 to-green-500 bg-clip-text text-transparent">
            Join BudgetIt! ✨
          </h2>
          <p className="mt-2 text-gray-600">Create your account and start your smart budgeting journey</p>
        </div>
        
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl p-8 border border-pink-100">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="rounded-xl bg-pink-50 border border-pink-200 p-4">
                <div className="text-sm text-pink-700">{error}</div>
              </div>
            )}
            
            <div className="space-y-4">
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                  Full Name
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <input
                    id="name"
                    name="name"
                    type="text"
                    required
                    className="pl-10 block w-full px-4 py-3 border-2 border-pink-200 rounded-xl focus:outline-none focus:border-pink-400 focus:ring-4 focus:ring-pink-100 transition-all duration-200"
                    placeholder="Enter your full name"
                    value={formData.name}
                    onChange={handleChange}
                  />
                </div>
              </div>
              
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <input
                    id="email"
                    name="email"
                    type="email"
                    required
                    className="pl-10 block w-full px-4 py-3 border-2 border-pink-200 rounded-xl focus:outline-none focus:border-pink-400 focus:ring-4 focus:ring-pink-100 transition-all duration-200"
                    placeholder="Enter your email"
                    value={formData.email}
                    onChange={handleChange}
                  />
                </div>
              </div>
              
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    className="pl-10 pr-10 block w-full px-4 py-3 border-2 border-pink-200 rounded-xl focus:outline-none focus:border-pink-400 focus:ring-4 focus:ring-pink-100 transition-all duration-200"
                    placeholder="Create a strong password"
                    value={formData.password}
                    onChange={handleChange}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </div>
              
              <div>
                <label htmlFor="userType" className="block text-sm font-medium text-gray-700 mb-2">
                  I am a...
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setFormData({...formData, userType: 'student'})}
                    className={`p-4 rounded-xl border-2 transition-all duration-200 ${
                      formData.userType === 'student'
                        ? 'border-pink-400 bg-pink-50 text-pink-700'
                        : 'border-gray-200 hover:border-pink-200'
                    }`}
                  >
                    <GraduationCap className="h-6 w-6 mx-auto mb-2" />
                    <div className="text-sm font-medium">Student</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setFormData({...formData, userType: 'professional'})}
                    className={`p-4 rounded-xl border-2 transition-all duration-200 ${
                      formData.userType === 'professional'
                        ? 'border-green-400 bg-green-50 text-green-700'
                        : 'border-gray-200 hover:border-green-200'
                    }`}
                  >
                    <Briefcase className="h-6 w-6 mx-auto mb-2" />
                    <div className="text-sm font-medium">Professional</div>
                  </button>
                </div>
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-xl text-white bg-gradient-to-r from-pink-400 to-green-400 hover:shadow-lg hover:scale-105 focus:outline-none focus:ring-4 focus:ring-pink-200 disabled:opacity-50 disabled:hover:scale-100 transition-all duration-200"
              >
                {isLoading ? (
                  <div className="flex items-center">
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                    Creating account...
                  </div>
                ) : (
                  <span className="flex items-center">
                    <Sparkles className="h-5 w-5 mr-2" />
                    {t('auth.createAccount')}
                  </span>
                )}
              </button>
            </div>

            <div className="text-center">
              <Link
                to="/signin"
                className="font-medium text-pink-600 hover:text-pink-500 transition-colors"
              >
                {t('auth.haveAccount')} <span className="underline">{t('auth.signin')}</span>
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default SignUp;