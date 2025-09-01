import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  en: {
    translation: {
      // Navigation
      'nav.dashboard': 'Dashboard',
      'nav.expenses': 'Expenses',
      'nav.goals': 'Goals',
      'nav.reports': 'Reports',
      'nav.logout': 'Logout',
      
      // Authentication
      'auth.signin': 'Sign In',
      'auth.signup': 'Sign Up',
      'auth.email': 'Email',
      'auth.password': 'Password',
      'auth.name': 'Full Name',
      'auth.userType': 'User Type',
      'auth.student': 'Student',
      'auth.professional': 'Professional',
      'auth.createAccount': 'Create Account',
      'auth.haveAccount': 'Already have an account?',
      'auth.noAccount': "Don't have an account?",
      
      // Dashboard
      'dashboard.title': 'Budget Dashboard',
      'dashboard.weeklyProgress': 'Weekly Progress',
      'dashboard.totalSpent': 'Total Spent',
      'dashboard.totalBudget': 'Total Budget',
      'dashboard.remaining': 'Remaining',
      'dashboard.quickAdd': 'Quick Add Expense',
      
      // Expenses
      'expenses.title': 'Expense Tracker',
      'expenses.add': 'Add Expense',
      'expenses.amount': 'Amount',
      'expenses.category': 'Category',
      'expenses.description': 'Description',
      'expenses.date': 'Date',
      'expenses.categories.food': 'Food',
      'expenses.categories.transport': 'Transport',
      'expenses.categories.rent': 'Rent',
      'expenses.categories.entertainment': 'Entertainment',
      'expenses.categories.utilities': 'Utilities',
      'expenses.categories.other': 'Other',
      
      // Goals
      'goals.title': 'Savings Goals',
      'goals.add': 'Add Goal',
      'goals.goalTitle': 'Goal Title',
      'goals.targetAmount': 'Target Amount',
      'goals.targetDate': 'Target Date',
      'goals.progress': 'Progress',
      
      // Chat
      'chat.placeholder': 'Ask me about your budget...',
      'chat.send': 'Send',
      'chat.title': 'Budget Assistant',
      
      // Common
      'common.save': 'Save',
      'common.cancel': 'Cancel',
      'common.close': 'Close',
      'common.loading': 'Loading...',
      'common.error': 'Error',
      'common.success': 'Success',
      
      // Home
      'home.title': 'Track Your Expenses Smartly',
      'home.subtitle': 'AI-powered budgeting for students and professionals',
      'home.getStarted': 'Get Started'
    }
  },
  hi: {
    translation: {
      // Navigation
      'nav.dashboard': 'डैशबोर्ड',
      'nav.expenses': 'खर्च',
      'nav.goals': 'लक्ष्य',
      'nav.reports': 'रिपोर्ट',
      'nav.logout': 'लॉगआउट',
      
      // Authentication
      'auth.signin': 'साइन इन',
      'auth.signup': 'साइन अप',
      'auth.email': 'ईमेल',
      'auth.password': 'पासवर्ड',
      'auth.name': 'पूरा नाम',
      'auth.userType': 'उपयोगकर्ता प्रकार',
      'auth.student': 'छात्र',
      'auth.professional': 'पेशेवर',
      'auth.createAccount': 'खाता बनाएं',
      'auth.haveAccount': 'पहले से खाता है?',
      'auth.noAccount': 'खाता नहीं है?',
      
      // Dashboard
      'dashboard.title': 'बजट डैशबोर्ड',
      'dashboard.weeklyProgress': 'साप्ताहिक प्रगति',
      'dashboard.totalSpent': 'कुल खर्च',
      'dashboard.totalBudget': 'कुल बजट',
      'dashboard.remaining': 'शेष',
      'dashboard.quickAdd': 'त्वरित खर्च जोड़ें',
      
      // Expenses
      'expenses.title': 'खर्च ट्रैकर',
      'expenses.add': 'खर्च जोड़ें',
      'expenses.amount': 'राशि',
      'expenses.category': 'श्रेणी',
      'expenses.description': 'विवरण',
      'expenses.date': 'तारीख',
      'expenses.categories.food': 'खाना',
      'expenses.categories.transport': 'यातायात',
      'expenses.categories.rent': 'किराया',
      'expenses.categories.entertainment': 'मनोरंजन',
      'expenses.categories.utilities': 'उपयोगिताएं',
      'expenses.categories.other': 'अन्य',
      
      // Goals
      'goals.title': 'बचत लक्ष्य',
      'goals.add': 'लक्ष्य जोड़ें',
      'goals.goalTitle': 'लक्ष्य शीर्षक',
      'goals.targetAmount': 'लक्ष्य राशि',
      'goals.targetDate': 'लक्ष्य तारीख',
      'goals.progress': 'प्रगति',
      
      // Chat
      'chat.placeholder': 'अपने बजट के बारे में पूछें...',
      'chat.send': 'भेजें',
      'chat.title': 'बजट सहायक',
      
      // Common
      'common.save': 'सेव',
      'common.cancel': 'रद्द करें',
      'common.close': 'बंद करें',
      'common.loading': 'लोड हो रहा है...',
      'common.error': 'त्रुटि',
      'common.success': 'सफलता',
      
      // Home
      'home.title': 'अपने खर्च को स्मार्ट तरीके से ट्रैक करें',
      'home.subtitle': 'छात्रों और पेशेवरों के लिए AI-संचालित बजटिंग',
      'home.getStarted': 'शुरू करें'
    }
  }
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: 'en',
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false
    }
  });

export default i18n;