import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { CreditCard, TrendingUp, Target, MessageCircle, Sparkles, PiggyBank } from 'lucide-react';

const HomePage: React.FC = () => {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 via-white to-green-50">
      {/* Hero Section */}
      <div className="relative bg-gradient-to-br from-pink-100 to-green-100 overflow-hidden">
        <div className="max-w-7xl mx-auto">
          <div className="relative z-10 pb-8 sm:pb-16 md:pb-20 lg:max-w-2xl lg:w-full lg:pb-28 xl:pb-32">
            <main className="mt-10 mx-auto max-w-7xl px-4 sm:mt-12 sm:px-6 md:mt-16 lg:mt-20 lg:px-8 xl:mt-28">
              <div className="sm:text-center lg:text-left">
                <h1 className="text-4xl tracking-tight font-extrabold text-gray-900 sm:text-5xl md:text-6xl">
                  <span className="block xl:inline bg-gradient-to-r from-pink-500 to-green-500 bg-clip-text text-transparent">
                    ✨ {t('home.title')}
                  </span>
                </h1>
                <p className="mt-3 text-base text-gray-600 sm:mt-5 sm:text-lg sm:max-w-xl sm:mx-auto md:mt-5 md:text-xl lg:mx-0">
                  {t('home.subtitle')} 💰 Track, save, and grow with AI-powered insights! 🚀
                </p>
                <div className="mt-5 sm:mt-8 sm:flex sm:justify-center lg:justify-start">
                  <div className="rounded-full shadow-lg">
                    <Link
                      to="/signup"
                      className="w-full flex items-center justify-center px-8 py-4 border border-transparent text-base font-medium rounded-full text-white bg-gradient-to-r from-pink-400 to-green-400 hover:shadow-xl hover:scale-105 transition-all duration-300 md:py-4 md:text-lg md:px-10"
                    >
                      <Sparkles className="h-5 w-5 mr-2" />
                      {t('home.getStarted')}
                    </Link>
                  </div>
                  <div className="mt-3 sm:mt-0 sm:ml-3">
                    <Link
                      to="/signin"
                      className="w-full flex items-center justify-center px-8 py-4 border-2 border-pink-300 text-base font-medium rounded-full text-pink-600 bg-white hover:bg-pink-50 hover:scale-105 transition-all duration-300 md:py-4 md:text-lg md:px-10"
                    >
                      {t('auth.signin')}
                    </Link>
                  </div>
                </div>
              </div>
            </main>
          </div>
        </div>
        <div className="lg:absolute lg:inset-y-0 lg:right-0 lg:w-1/2">
          <div className="h-56 w-full bg-gradient-to-br from-pink-400 via-purple-400 to-green-400 sm:h-72 md:h-96 lg:w-full lg:h-full flex items-center justify-center relative overflow-hidden">
            <div className="absolute inset-0 bg-white/10 backdrop-blur-sm"></div>
            <div className="relative z-10 transform hover:scale-105 transition-transform duration-700 ease-out">
              <img 
                src="/ggcash.png" 
                alt="Cash Management" 
                className="w-80 h-80 object-contain drop-shadow-2xl hover:drop-shadow-3xl transition-all duration-500"
              />
            </div>
            <div className="absolute top-10 left-10 w-20 h-20 bg-white/20 rounded-full animate-bounce"></div>
            <div className="absolute bottom-10 right-10 w-16 h-16 bg-white/20 rounded-full animate-bounce delay-300"></div>
            <div className="absolute top-1/2 left-5 w-12 h-12 bg-pink-300/30 rounded-full animate-pulse"></div>
            <div className="absolute bottom-1/4 left-1/4 w-8 h-8 bg-green-300/30 rounded-full animate-pulse delay-500"></div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-16 bg-white/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="lg:text-center">
            <h2 className="text-base text-pink-600 font-semibold tracking-wide uppercase flex items-center justify-center">
              <Sparkles className="h-5 w-5 mr-2" />
              Features
            </h2>
            <p className="mt-2 text-3xl leading-8 font-extrabold tracking-tight bg-gradient-to-r from-pink-500 to-green-500 bg-clip-text text-transparent sm:text-4xl">
              Smart budgeting made simple ✨
            </p>
          </div>

          <div className="mt-12">
            <div className="space-y-10 md:space-y-0 md:grid md:grid-cols-2 md:gap-x-8 md:gap-y-10">
              <div className="relative group">
                <div className="absolute flex items-center justify-center h-16 w-16 rounded-2xl bg-gradient-to-r from-pink-400 to-pink-500 text-white shadow-lg group-hover:scale-110 transition-transform duration-300">
                  <TrendingUp className="h-8 w-8" />
                </div>
                <div className="ml-20">
                  <p className="text-xl leading-6 font-bold text-gray-900">🤖 AI-Powered Insights</p>
                  <p className="mt-2 text-base text-gray-600">
                    Get personalized budget recommendations and expense insights powered by cutting-edge AI technology.
                  </p>
                </div>
              </div>

              <div className="relative group">
                <div className="absolute flex items-center justify-center h-16 w-16 rounded-2xl bg-gradient-to-r from-green-400 to-green-500 text-white shadow-lg group-hover:scale-110 transition-transform duration-300">
                  <Target className="h-8 w-8" />
                </div>
                <div className="ml-20">
                  <p className="text-xl leading-6 font-bold text-gray-900">🎯 Goal Tracking</p>
                  <p className="mt-2 text-base text-gray-600">
                    Set and track your financial goals with beautiful visual progress indicators and smart milestones.
                  </p>
                </div>
              </div>

              <div className="relative group">
                <div className="absolute flex items-center justify-center h-16 w-16 rounded-2xl bg-gradient-to-r from-purple-400 to-purple-500 text-white shadow-lg group-hover:scale-110 transition-transform duration-300">
                  <MessageCircle className="h-8 w-8" />
                </div>
                <div className="ml-20">
                  <p className="text-xl leading-6 font-bold text-gray-900">💬 Budget Assistant</p>
                  <p className="mt-2 text-base text-gray-600">
                    Chat with our friendly AI assistant for instant budget advice, expense queries, and financial tips.
                  </p>
                </div>
              </div>

              <div className="relative group">
                <div className="absolute flex items-center justify-center h-16 w-16 rounded-2xl bg-gradient-to-r from-yellow-400 to-orange-400 text-white shadow-lg group-hover:scale-110 transition-transform duration-300">
                  <CreditCard className="h-8 w-8" />
                </div>
                <div className="ml-20">
                  <p className="text-xl leading-6 font-bold text-gray-900">💳 Smart Tracking</p>
                  <p className="mt-2 text-base text-gray-600">
                    Effortlessly track and categorize your daily expenses with our intuitive and beautiful interface.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-gradient-to-r from-pink-400 to-green-400 py-16">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-extrabold text-white sm:text-4xl">
            Ready to transform your finances? ✨
          </h2>
          <p className="mt-4 text-xl text-pink-100">
            Join thousands of students and professionals who are already saving smarter! 🚀
          </p>
          <div className="mt-8">
            <Link
              to="/signup"
              className="inline-flex items-center px-8 py-4 border-2 border-white text-lg font-medium rounded-full text-pink-600 bg-white hover:bg-pink-50 hover:scale-105 transition-all duration-300 shadow-lg"
            >
              <PiggyBank className="h-6 w-6 mr-2" />
              Start Your Journey Today!
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;