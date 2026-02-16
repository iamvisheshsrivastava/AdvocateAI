# AdvocateAI

An intelligent platform that connects users with legal professionals (lawyers, advocates, consultants) using AI-powered semantic matching. The system uses embeddings to understand user queries and recommend the most relevant legal professionals based on expertise, location, and ratings.

---

## 🎯 Features

### Core Functionality
- **AI-Powered Professional Search**: Uses semantic embeddings to match user queries with relevant legal professionals
- **User Authentication**: Secure login system with email and password
- **Chat Interface**: Conversational interface to search for and get recommendations on legal professionals
- **Watchlist Management**: Save and manage preferred legal professionals
- **Professional Database**: Comprehensive database of lawyers across major German cities
- **Ratings & Reviews**: View professional ratings and review counts
- **Notifications System**: In-app notifications for relevant updates

### Technical Highlights
- **Embedding-Based Search**: Uses sentence transformers for semantic search rather than keyword matching
- **Multi-Platform Support**: Flutter frontend supporting Web, Android, iOS, Windows, macOS, and Linux
- **RESTful API**: FastAPI backend with CORS support for seamless frontend integration
- **Database**: PostgreSQL for persistent storage of users and professionals

---

## 🏗️ Architecture Overview

```
AdvocateAI/
├── backend/              # FastAPI Python backend
├── test_app/            # Flutter mobile/web application
```

### Backend Architecture
The backend fetches lawyer data from Google Places API, generates semantic embeddings, and stores them in PostgreSQL. When a user sends a message, the system:
1. Generates an embedding for the user's query
2. Compares it against stored professional embeddings
3. Returns the top 3 matching professionals
4. Uses Google's Gemini API to generate contextual responses

### Frontend Architecture
The Flutter app provides a multi-page interface:
- **Login Page**: User authentication
- **Home Page**: Chat-based professional search
- **Watchlist Page**: Saved professionals management
- **Notifications Page**: User updates and alerts

---

## 💻 Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL
- **ML/Embeddings**: Sentence Transformers (all-MiniLM-L6-v2)
- **APIs**: 
  - Google Places API (lawyer discovery)
  - Google Gemini API (response generation)
- **Authentication**: Email/Password

### Frontend
- **Framework**: Flutter 3.11+
- **State Management**: StatefulWidget
- **HTTP Client**: http 1.2.0
- **Local Storage**: shared_preferences 2.2.2
- **Markdown Rendering**: flutter_markdown 0.6.18
- **Platforms**: Web, Android, iOS, Windows, macOS, Linux

---

## 📋 Prerequisites

### Backend Requirements
- Python 3.8+
- PostgreSQL 12+
- Google Places API Key
- Google Gemini API Key

### Frontend Requirements
- Flutter 3.11.0 or higher
- Dart 3.11.0 or higher
- Android SDK (for Android builds)
- Xcode (for iOS builds)
- Additional platform SDKs as needed

---

## 🚀 Getting Started

### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install fastapi uvicorn psycopg2-binary sentence-transformers pydantic python-dotenv requests
   ```

4. **Set up PostgreSQL database**:
   ```bash
   psql -U postgres -d postgres -f schema.sql
   ```

5. **Create `.env` file** in the backend directory:
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   GOOGLE_API_KEY=your_google_places_api_key
   ```

6. **Populate the database with lawyers**:
   ```bash
   python fetch_professionals.py
   ```

7. **Generate embeddings for professionals**:
   ```bash
   python generate_embeddings.py
   ```

8. **Start the FastAPI server**:
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Navigate to test_app directory**:
   ```bash
   cd test_app
   ```

2. **Get Flutter dependencies**:
   ```bash
   flutter pub get
   ```

3. **Run on development device/emulator**:
   ```bash
   flutter run
   ```

4. **Build for specific platform**:
   ```bash
   # Web
   flutter build web

   # Android
   flutter build apk

   # iOS
   flutter build ios

   # Windows
   flutter build windows

   # macOS
   flutter build macos

   # Linux
   flutter build linux
   ```

---

## 🔧 Configuration

### Backend Configuration
- **Database Connection**: Update credentials in `app.py`, `fetch_professionals.py`, and `generate_embeddings.py`
  - Host: localhost
  - Port: 5432
  - Database: postgres
  - User: postgres
  - Password: postgres

- **CORS Settings**: Currently allows all origins in `app.py`. Restrict as needed for production.

### Frontend Configuration
- **API Endpoint**: Defined in `lib/config.dart`
  - Local: `http://localhost:8000`
  - Production: Uses server host + `/api`

---

## 📁 Project Structure

### Backend (`backend/`)
```
backend/
├── app.py                      # FastAPI main application with endpoints
├── fetch_professionals.py       # Script to fetch lawyers from Google Places API
├── generate_embeddings.py       # Script to generate semantic embeddings
├── schema.sql                   # PostgreSQL database schema
└── __pycache__/               # Python cache
```

**Key Files**:
- `app.py`: Contains POST endpoints for `/login` and `/chat`
- `schema.sql`: Defines tables for users, professionals, agents, ratings, and watchlists

### Frontend (`test_app/`)
```
test_app/
├── lib/
│   ├── main.dart              # App entry point
│   ├── login_page.dart        # User authentication
│   ├── home_page.dart         # Main chat interface for searching professionals
│   ├── watchlist_page.dart    # Manage saved professionals
│   ├── notifications_page.dart # User notifications
│   └── config.dart            # API configuration
├── pubspec.yaml               # Flutter dependencies
├── android/                   # Android-specific configuration
├── ios/                       # iOS-specific configuration
├── web/                       # Web build configuration
├── windows/                   # Windows build configuration
├── macos/                     # macOS build configuration
└── linux/                     # Linux build configuration
```

**Key Screens**:
- **LoginPage**: Email/password authentication
- **HomePage**: Conversational search interface with chat history
- **WatchListPage**: Table view of saved professionals with options to add/remove
- **NotificationsPage**: User notification center

---

## 🔌 API Endpoints

### Authentication
- **POST** `/login`
  - Body: `{ "email": "user@example.com", "password": "password" }`
  - Returns: `{ "success": true, "user_id": 1, "email": "user@example.com" }`

### Chat & Search
- **POST** `/chat`
  - Body: `{ "message": "I need a lawyer for contract review in Berlin" }`
  - Returns: `{ "response": "Top matching professionals: ..." }`

### Watchlist
- **GET** `/watchlist/{user_id}` - Retrieve user's watchlist
- **GET** `/professionals/{user_id}` - Get available professionals
- **POST** `/watchlist/add` - Add professionals to watchlist
  - Body: `{ "user_id": 1, "professional_ids": [1, 2, 3] }`

---

## 📊 Database Schema

### Users Table
- `id`: Primary key
- `name`: User's name
- `email`: Unique email (login identifier)
- `created_at`: Timestamp

### Professionals Table
- `id`: Primary key
- `name`: Professional's name
- `address`: Physical address
- `city`: Location
- `rating`: Average rating (float)
- `review_count`: Number of reviews
- `category`: Type (e.g., "lawyer")
- `embedding`: Vector embedding for semantic search (TEXT - JSON)
- `created_at`: Timestamp

### Watchlist Table
- `id`: Primary key
- `user_id`: Foreign key to users
- `professional_id`: Foreign key to professionals

### Other Tables
- `agents`: AI agent configurations per user
- `ratings`: User ratings of professionals (1-5 scale)

---

## 🤖 How the Semantic Search Works

1. **Professional Discovery**: `fetch_professionals.py` uses Google Places API to find lawyers in major German cities
2. **Embedding Generation**: `generate_embeddings.py` creates vector embeddings using the `all-MiniLM-L6-v2` model
3. **Query Matching**: When a user sends a message:
   - The user's message is converted to an embedding
   - Similarity scores are calculated against all professional embeddings
   - Top 3 matches are selected
4. **Response Generation**: Context from top matches is sent to Gemini API for a natural language response

---

## 🔐 Security Notes

### Current Implementation
- Password stored in plain text (⚠️ **Development only**)
- No token-based authentication (⚠️ **Development only**)
- CORS allows all origins (⚠️ **Development only**)

### Production Recommendations
1. Hash passwords with bcrypt or similar
2. Implement JWT or OAuth2 authentication
3. Restrict CORS to specific domains
4. Use HTTPS for all communications
5. Implement rate limiting on API endpoints
6. Add input validation and sanitization
7. Use environment variables for all secrets

---

## 📝 Development Notes

### Adding New Features
1. **Backend Feature**: Add endpoint in `app.py`, update schema if needed
2. **Frontend Feature**: Create new page widget, import in relevant navigation
3. **Update Database**: Run migrations with `alter table` statements in `schema.sql`

### Testing
- Use Postman or curl to test API endpoints
- Flutter provides hot reload for rapid UI development

### Performance Considerations
- Embeddings are cached in the database
- Top 3 results limit reduces API calls
- Consider pagination for watchlist with many items

---

## 📞 Support & Contribution

This project is a development prototype for the AdvocateAI concept. For contributions or questions:
1. Review the code structure
2. Ensure backend database is running
3. Test both backend and frontend changes
4. Follow the existing code style

---

## 📄 License

This project is provided as-is for educational and development purposes.

---

## 🎓 Key Learning Points

- **Semantic Search with Embeddings**: How enterprise-grade matching systems work
- **Full-Stack Development**: Integration between Python backend and Flutter frontend
- **Database Design**: Relational schema with foreign key relationships
- **API Design**: RESTful patterns and CORS handling
- **Multi-Platform Development**: Flutter's cross-platform capabilities

---

**Last Updated**: February 2026  
**Status**: Development/Beta
