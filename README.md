# 💰 BudgetIt – GenAI-Powered Budgeting Assistant  

## 🌟 Overview  
**BudgetIt** is a **minimal yet powerful GenAI-powered budgeting assistant** developed during the **Summer Internship Program 2025**.  
The project is designed to help **students** track and manage their finances effectively through:  
- ✅ Personalized **expense recommendations**  
- ✅ Smart **savings goals**  
- ✅ Interactive **visual analytics**  

Unlike traditional budgeting apps, **BudgetIt is conversational and intuitive**. It integrates **Google’s Gemini 2.0 LLM** to power an **AI chatbot assistant** that delivers:  
- Real-time **budgeting tips**  
- Spending pattern **analysis**  
- AI-generated **financial insights**  

> 🎯 Our focus: **Affordability, Accessibility, and Interactivity** for student-centric financial management.  

---

## ⚡ Key Features  
- 🤖 **AI-powered chatbot** with Gemini 2.0 LLM  
- 📊 **Visual analytics** for clear expense tracking  
- 🎯 **Personalized savings recommendations**  
- 💡 **Real-time tips** for smarter budgeting  
- 🎓 Designed **for students**: minimal, intuitive, and affordable  

---

## 🚀 Tech Stack  
- **Frontend:** React + Tailwind CSS  
- **Backend:** Flask (Python)  
- **AI/LLM:** Google Gemini 2.0 API  
- **Database:** (if you used any, add here)  
- **Other Tools:** NPM, pip  

---

## 🛠️ Installation & Running Locally  

Clone the repo:  
```bash
git clone https://github.com/your-username/BudgetIt.git
cd BudgetIt

cd backend
pip install -r requirements.txt
python app.py

open a new terminal:
cd BudgetIt
npm install
npm run dev

API Key Setup

To enable the chatbot assistant, add your own Google Gemini API Key:

Open:

src/components/chatbot.tsx


Replace the placeholder with your API key:

const API_KEY = "YOUR_API_KEY";

