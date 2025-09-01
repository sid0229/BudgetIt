# BudgetIt - AI-Powered Budgeting App

A full-stack budgeting application designed for students and young professionals with AI-powered insights and recommendations.

## Features

- **AI-Powered Recommendations**: Get personalized budget suggestions and expense insights
- **Conversational Budget Assistant**: Chat with AI for instant budget advice
- **Weekly Progress Dashboard**: Visual analytics with charts and progress tracking
- **Goal-Based Savings Planner**: Set and track financial goals with visual progress
- **Expense Categorization**: Automatic categorization with detailed insights
- **Multi-language Support**: English and Hindi support with i18next
- **User-Specific Dashboards**: Different layouts for students and professionals

## Tech Stack

### Frontend
- React 18 with TypeScript
- Tailwind CSS for styling
- Recharts for data visualization
- React Router for navigation
- i18next for internationalization
- Axios for API calls

### Backend
- Python Flask with SQLite database
- RESTful API architecture
- Session-based authentication
- CORS enabled for frontend integration

## Project Structure

```
├── src/
│   ├── components/
│   │   ├── Auth/          # Authentication components
│   │   ├── Dashboard/     # Dashboard and analytics
│   │   ├── Expenses/      # Expense tracking
│   │   ├── Goals/         # Goal planning
│   │   ├── Chat/          # AI chatbot
│   │   ├── Layout/        # Navigation and layout
│   │   └── Home/          # Landing page
│   ├── contexts/          # React contexts
│   ├── utils/             # API utilities
│   └── i18n/              # Internationalization
├── backend/
│   ├── app.py            # Flask application
│   └── requirements.txt  # Python dependencies
└── README.md
```

## Setup Instructions

### Frontend Setup
1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

### Backend Setup
1. Navigate to backend directory:
   ```bash
   cd backend
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the Flask server:
   ```bash
   python app.py
   ```

The backend will run on `http://localhost:5000` and the frontend on `http://localhost:5173`.

## API Endpoints

### Authentication
- `POST /api/auth/signup` - Create new user account
- `POST /api/auth/signin` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/me` - Get current user

### Expenses
- `GET /api/expenses` - Get user expenses
- `POST /api/expenses` - Add new expense

### Budgets
- `GET /api/budgets` - Get user budgets
- `POST /api/budgets` - Set budget for category

### Goals
- `GET /api/goals` - Get user goals
- `POST /api/goals` - Create new goal

### Chat
- `POST /api/chat` - Send message to AI assistant

### Analytics
- `GET /api/analytics/weekly` - Get weekly spending analytics

## AI Integration

The app includes placeholders for OpenAI API integration:
- Budget recommendations based on spending patterns
- Conversational AI assistant for budget queries
- Personalized financial advice and tips

To integrate OpenAI:
1. Add your OpenAI API key to the backend
2. Replace mock responses in `/api/chat` endpoint
3. Implement actual AI logic for budget recommendations

## Database Schema

### Users
- id, name, email, password_hash, user_type, created_at

### Expenses
- id, user_id, amount, category, description, date, created_at

### Budgets
- id, user_id, category, amount, period, created_at

### Goals
- id, user_id, title, target_amount, saved_amount, target_date, created_at

## Features to Add

- Push notifications for budget alerts
- Receipt scanning with OCR
- Investment tracking
- Bill reminders
- Spending insights and trends
- Social sharing of achievements
- Export data to CSV/PDF

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.