import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, Send, X, Bot, User, Minimize2, Maximize2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

const suggestedQuestions = [
  "How to save more money?",
  "Give me student budget tips!",
  "How to track my expenses?",
  "How to set saving goals?"
];

const ChatBot: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isFullSize, setIsFullSize] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: '✨ Hey there! I\'m your AI budget buddy! Ask me anything about your expenses, savings goals, or get personalized budget tips! 💰',
      sender: 'bot',
      timestamp: new Date(),
    },
  ]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessageToGemini = async (userMessage: string) => {
    try {
      const response = await fetch(
        'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=AIzaSyB7DYDi2yVZ8NZDDvnQDlhnoDsvwBrRI10',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            contents: [{ parts: [{ text: `You are BudgetIt AI, a friendly budget assistant. ${userMessage}` }] }]
          })
        }
      );

      const data = await response.json();
      const botReply = data.candidates?.[0]?.content?.parts?.[0]?.text || '😅 Sorry, I couldn’t understand that.';

      return botReply;
    } catch (error) {
      console.error('Error contacting Gemini:', error);
      return '😅 Oops! Something went wrong. Please try again!';
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    const botReply = await sendMessageToGemini(userMessage.text);

    const botMessage: Message = {
      id: (Date.now() + 1).toString(),
      text: botReply,
      sender: 'bot',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, botMessage]);
    setIsLoading(false);
  };

  const handleSuggestedClick = (question: string) => {
    setInputText(question);
    setTimeout(() => {
      const fakeEvent = { preventDefault: () => { } } as React.FormEvent;
      handleSendMessage(fakeEvent);
    }, 100);
  };

  const toggleFullSize = () => {
    setIsFullSize(!isFullSize);
  };

  return (
    <>
      {/* Floating Chat Button */}
      <div className="fixed bottom-6 right-6 z-50">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="group relative p-4 bg-gradient-to-r from-pink-400 to-pink-500 text-white rounded-full shadow-2xl hover:shadow-pink-200 hover:scale-110 transition-all duration-300 border-4 border-white"
        >
          <MessageCircle className="h-8 w-8" />
          <div className="absolute -top-2 -right-2 w-6 h-6 bg-green-400 rounded-full flex items-center justify-center">
            <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
          </div>
          <div className="absolute -top-12 right-0 bg-gray-800 text-white px-3 py-1 rounded-lg text-sm opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">
            Chat with AI Buddy! 💬
          </div>
        </button>
      </div>

      {/* Chat Window */}
      {isOpen && (
        <div className={`fixed z-50 transition-all duration-300 ${isFullSize ? 'inset-4 md:inset-8' : 'bottom-24 right-6 w-96 h-[500px]'}`}>
          <div className="w-full h-full bg-white rounded-2xl shadow-2xl border border-pink-100 flex flex-col overflow-hidden backdrop-blur-sm bg-white/95">

            {/* Header */}
            <div className="flex items-center justify-between p-4 bg-gradient-to-r from-pink-400 to-green-400 text-white">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                  <Bot className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="font-bold text-lg">AI Budget Buddy</h3>
                  <p className="text-xs opacity-90">Always here to help! ✨</p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={toggleFullSize}
                  className="p-2 hover:bg-white/20 rounded-full transition-colors"
                >
                  {isFullSize ? <Minimize2 className="h-5 w-5" /> : <Maximize2 className="h-5 w-5" />}
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-2 hover:bg-white/20 rounded-full transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gradient-to-b from-pink-50/30 to-green-50/30">
              {messages.map(message => (
                <div
                  key={message.id}
                  className={`flex items-start space-x-3 ${message.sender === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}
                >
                  <div
                    className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center shadow-lg ${message.sender === 'user'
                      ? 'bg-gradient-to-r from-pink-400 to-pink-500 text-white'
                      : 'bg-gradient-to-r from-green-400 to-green-500 text-white'
                      }`}
                  >
                    {message.sender === 'user' ? (
                      <User className="h-5 w-5" />
                    ) : (
                      <Bot className="h-5 w-5" />
                    )}
                  </div>
                  <div
                    className={`flex-1 px-4 py-3 rounded-2xl shadow-sm ${message.sender === 'user'
                      ? 'bg-gradient-to-r from-pink-400 to-pink-500 text-white ml-12'
                      : 'bg-white text-gray-800 mr-12 border border-green-100'
                      }`}
                  >
                    <div className="text-sm leading-relaxed">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.text}</ReactMarkdown>
                    </div>
                    <p className={`text-xs mt-2 ${message.sender === 'user' ? 'text-pink-100' : 'text-gray-500'}`}>
                      {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-r from-green-400 to-green-500 text-white flex items-center justify-center shadow-lg">
                    <Bot className="h-5 w-5" />
                  </div>
                  <div className="flex-1 px-4 py-3 rounded-2xl bg-white mr-12 border border-green-100">
                    <div className="flex space-x-2">
                      <div className="w-3 h-3 bg-green-400 rounded-full animate-bounce"></div>
                      <div className="w-3 h-3 bg-pink-400 rounded-full animate-bounce delay-100"></div>
                      <div className="w-3 h-3 bg-green-400 rounded-full animate-bounce delay-200"></div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Suggested Questions */}
            {messages.length <= 3 && (
              <div className="px-4 py-2 bg-white border-t border-pink-100">
                <p className="text-xs mb-2 text-gray-500">Suggested questions:</p>
                <div className="flex flex-wrap gap-2">
                  {suggestedQuestions.map((question, index) => (
                    <button
                      key={index}
                      onClick={() => handleSuggestedClick(question)}
                      className="text-xs bg-gradient-to-r from-pink-400 to-green-400 px-2 py-1 rounded-full text-white hover:opacity-80 transition-opacity"
                    >
                      {question}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Input */}
            <form onSubmit={handleSendMessage} className="p-4 bg-white border-t border-pink-100">
              <div className="flex space-x-3">
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="Ask me anything about your budget... 💭"
                  className="flex-1 px-4 py-3 border-2 border-pink-200 rounded-full focus:outline-none focus:border-pink-400 focus:ring-4 focus:ring-pink-100 text-sm transition-all duration-200"
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  disabled={isLoading || !inputText.trim()}
                  className="px-6 py-3 bg-gradient-to-r from-pink-400 to-green-400 text-white rounded-full hover:shadow-lg hover:scale-105 focus:outline-none focus:ring-4 focus:ring-pink-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 transition-all duration-200"
                >
                  <Send className="h-5 w-5" />
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};

export default ChatBot;
