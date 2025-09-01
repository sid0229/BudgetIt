import React from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { LogOut, Globe, Sparkles, PiggyBank, Moon, Sun } from 'lucide-react';
import { Link } from 'react-router-dom';

const Navbar: React.FC = () => {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();
  const { isDarkMode, toggleDarkMode } = useTheme();

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'hi' : 'en';
    i18n.changeLanguage(newLang);
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  return (
    <nav className="bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm shadow-lg border-b border-pink-100 dark:border-gray-700 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link to={user ? "/dashboard" : "/"} className="flex items-center space-x-3">
            <div className="h-10 w-10 bg-gradient-to-r from-pink-400 to-green-400 rounded-xl flex items-center justify-center">
              <PiggyBank className="h-6 w-6 text-white" />
            </div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-pink-500 to-green-500 bg-clip-text text-transparent">
              BudgetIt
            </h1>
          </Link>
          
          {user && (
            <div className="hidden md:flex items-center space-x-6">
              <Link
                to="/dashboard"
                className="text-gray-700 dark:text-gray-300 hover:text-pink-600 dark:hover:text-pink-400 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                📊 Dashboard
              </Link>
              <Link
                to="/expenses"
                className="text-gray-700 dark:text-gray-300 hover:text-pink-600 dark:hover:text-pink-400 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                💸 Expenses
              </Link>
              <Link
                to="/goals"
                className="text-gray-700 dark:text-gray-300 hover:text-pink-600 dark:hover:text-pink-400 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                🎯 Goals
              </Link>
            </div>
          )}
          
          <div className="flex items-center space-x-4">
            <button
              onClick={toggleDarkMode}
              className="flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-pink-600 dark:hover:text-pink-400 hover:bg-pink-50 dark:hover:bg-gray-800 transition-all duration-200"
            >
              {isDarkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
            <button
              onClick={toggleLanguage}
              className="flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-pink-600 dark:hover:text-pink-400 hover:bg-pink-50 dark:hover:bg-gray-800 transition-all duration-200"
            >
              <Globe className="h-4 w-4" />
              <span>{i18n.language === 'en' ? 'हिं' : 'EN'}</span>
            </button>
            
            {user && (
              <>
                <div className="flex items-center space-x-2 px-3 py-2 bg-gradient-to-r from-pink-100 to-green-100 dark:from-pink-900/30 dark:to-green-900/30 rounded-lg">
                  <Sparkles className="h-4 w-4 text-pink-500" />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {user.name}
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium text-white bg-gradient-to-r from-pink-400 to-pink-500 hover:shadow-lg hover:scale-105 transition-all duration-200"
                >
                  <LogOut className="h-4 w-4" />
                  <span>{t('nav.logout')}</span>
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;