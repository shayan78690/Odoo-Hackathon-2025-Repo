from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Database setup
db = SQLAlchemy(app)

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    reputation = db.Column(db.Integer, default=0)
    bio = db.Column(db.Text)
    profile_picture = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    questions = db.relationship('Question', backref='author', lazy=True)
    answers = db.relationship('Answer', backref='author', lazy=True)
    votes = db.relationship('Vote', backref='user', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    
    questions = db.relationship('Question', backref='category', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    is_approved = db.Column(db.Boolean, default=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    
    answers = db.relationship('Answer', backref='question', lazy=True, cascade='all, delete-orphan')
    votes = db.relationship('Vote', backref='question', lazy=True, cascade='all, delete-orphan')
    
    def get_vote_score(self):
        upvotes = Vote.query.filter_by(question_id=self.id, vote_type='up').count()
        downvotes = Vote.query.filter_by(question_id=self.id, vote_type='down').count()
        return upvotes - downvotes

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_approved = db.Column(db.Boolean, default=True)
    is_accepted = db.Column(db.Boolean, default=False)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    
    votes = db.relationship('Vote', backref='answer', lazy=True, cascade='all, delete-orphan')
    
    def get_vote_score(self):
        upvotes = Vote.query.filter_by(answer_id=self.id, vote_type='up').count()
        downvotes = Vote.query.filter_by(answer_id=self.id, vote_type='down').count()
        return upvotes - downvotes

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vote_type = db.Column(db.String(10), nullable=False)  # 'up' or 'down'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=True)
    answer_id = db.Column(db.Integer, db.ForeignKey('answer.id'), nullable=True)

# Routes
@app.route('/')
def index():
    search_query = request.args.get('search', '')
    category_filter = request.args.get('category', '')
    
    query = Question.query.filter_by(is_approved=True)
    
    if search_query:
        query = query.filter(Question.title.contains(search_query) | Question.content.contains(search_query))
    
    if category_filter:
        query = query.filter_by(category_id=category_filter)
    
    questions = query.order_by(Question.created_at.desc()).limit(20).all()
    categories = Category.query.all()
    
    return render_template('index.html', questions=questions, categories=categories, 
                         search_query=search_query, category_filter=category_filter)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/ask', methods=['GET', 'POST'])
@login_required
def ask_question():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category_id = request.form.get('category_id')
        
        question = Question(
            title=title,
            content=content,
            user_id=current_user.id,
            category_id=category_id if category_id else None
        )
        
        db.session.add(question)
        db.session.commit()
        
        flash('Question posted successfully')
        return redirect(url_for('view_question', id=question.id))
    
    categories = Category.query.all()
    return render_template('ask.html', categories=categories)

@app.route('/question/<int:id>')
def view_question(id):
    question = Question.query.get_or_404(id)
    question.views += 1
    db.session.commit()
    
    answers = Answer.query.filter_by(question_id=id, is_approved=True).order_by(Answer.created_at.desc()).all()
    
    return render_template('question.html', question=question, answers=answers)

@app.route('/answer/<int:question_id>', methods=['POST'])
@login_required
def post_answer(question_id):
    content = request.form['content']
    
    answer = Answer(
        content=content,
        user_id=current_user.id,
        question_id=question_id
    )
    
    db.session.add(answer)
    db.session.commit()
    
    flash('Answer posted successfully')
    return redirect(url_for('view_question', id=question_id))

@app.route('/vote', methods=['POST'])
@login_required
def vote():
    data = request.get_json()
    vote_type = data.get('type')
    question_id = data.get('question_id')
    answer_id = data.get('answer_id')
    
    # Check if user already voted
    existing_vote = Vote.query.filter_by(
        user_id=current_user.id,
        question_id=question_id,
        answer_id=answer_id
    ).first()
    
    if existing_vote:
        if existing_vote.vote_type == vote_type:
            # Remove vote if clicking same vote type
            db.session.delete(existing_vote)
        else:
            # Change vote type
            existing_vote.vote_type = vote_type
    else:
        # Create new vote
        vote = Vote(
            vote_type=vote_type,
            user_id=current_user.id,
            question_id=question_id,
            answer_id=answer_id
        )
        db.session.add(vote)
    
    db.session.commit()
    
    # Calculate new score
    if question_id:
        question = Question.query.get(question_id)
        score = question.get_vote_score()
    else:
        answer = Answer.query.get(answer_id)
        score = answer.get_vote_score()
    
    return jsonify({'score': score})

@app.route('/profile/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    questions = Question.query.filter_by(user_id=user.id, is_approved=True).order_by(Question.created_at.desc()).limit(10).all()
    answers = Answer.query.filter_by(user_id=user.id, is_approved=True).order_by(Answer.created_at.desc()).limit(10).all()
    
    return render_template('profile.html', user=user, questions=questions, answers=answers)

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    
    # Get statistics
    stats = {
        'total_users': User.query.count(),
        'total_questions': Question.query.count(),
        'total_answers': Answer.query.count(),
        'pending_questions': Question.query.filter_by(is_approved=False).count(),
        'pending_answers': Answer.query.filter_by(is_approved=False).count()
    }
    
    # Get recent activity
    recent_questions = Question.query.order_by(Question.created_at.desc()).limit(5).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    return render_template('admin.html', stats=stats, recent_questions=recent_questions, recent_users=recent_users)

@app.route('/admin/approve/<type>/<int:id>')
@login_required
def approve_content(type, id):
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    
    if type == 'question':
        item = Question.query.get_or_404(id)
    elif type == 'answer':
        item = Answer.query.get_or_404(id)
    
    item.is_approved = True
    db.session.commit()
    
    flash(f'{type.capitalize()} approved successfully')
    return redirect(url_for('admin_dashboard'))

def create_default_data():
    """Create default categories and admin user"""
    
    # Create default categories
    if not Category.query.first():
        categories = [
            Category(name='General', description='General programming questions'),
            Category(name='Python', description='Python programming questions'),
            Category(name='JavaScript', description='JavaScript programming questions'),
            Category(name='Web Development', description='HTML, CSS, and web development'),
            Category(name='Database', description='Database related questions'),
            Category(name='Mobile Development', description='Mobile app development'),
        ]
        
        for category in categories:
            db.session.add(category)
    
    # Create default admin user
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@stackit.com',
            password_hash=generate_password_hash('admin123'),
            is_admin=True,
            bio='System Administrator'
        )
        db.session.add(admin)
    
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_default_data()
    
    app.run(debug=True)