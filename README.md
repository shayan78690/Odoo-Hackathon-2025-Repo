# StackIt - Q&A Platform


A full-featured question and answer platform built with Python Flask, featuring user authentication, rich text editing, voting system, and admin dashboard.

## ✨ Features

- **User System**:
  - Secure registration/login
  - Profile pages with reputation
  - Admin privileges

- **Q&A Engine**:
  - Ask/edit/delete questions
  - Post/edit/delete answers
  - Accept best answers
  - Voting (upvote/downvote)

- **Content**:
  - Rich text editor (images, formatting)
  - Tagging system
  - Categories
  - Search functionality

- **Notifications**:
  - Real-time updates
  - Answer notifications
  - Vote alerts

## 🛠️ Technologies

| Area          | Technologies |
|---------------|--------------|
| **Backend**   | Python, Flask, SQLAlchemy |
| **Frontend**  | HTML5, CSS3, JavaScript, CKEditor |
| **Database**  | SQLite (dev), PostgreSQL (prod) |
| **Security**  | Flask-Login, Werkzeug |

## 🚀 Quick Start

1. **Clone & Setup**:
   ```bash
   git clone https://github.com/yourusername/stackit.git
   cd stackit
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
