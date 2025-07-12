from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from flask_ckeditor import CKEditor, upload_fail, upload_success
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
ckeditor = CKEditor(app)

# ========== DATABASE MODELS ==========
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
    notifications = db.relationship('Notification', backref='user', lazy=True, 
                                  order_by='Notification.created_at.desc()')

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
    
    answers = db.relationship('Answer', backref='question', lazy=True, 
                            cascade='all, delete-orphan')
    votes = db.relationship('Vote', backref='question', lazy=True, 
                          cascade='all, delete-orphan')
    tags = db.relationship('QuestionTag', back_populates='question', 
                         cascade='all, delete-orphan')

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
    
    votes = db.relationship('Vote', backref='answer', lazy=True, 
                          cascade='all, delete-orphan')

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

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    questions = db.relationship('QuestionTag', back_populates='tag')

class QuestionTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'))
    question = db.relationship('Question', back_populates='tags')
    tag = db.relationship('Tag', back_populates='questions')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    link = db.Column(db.String(200))

# ========== LOGIN MANAGER ==========
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ========== HELPER FUNCTIONS ==========
def create_notification(user_id, content, link=None):
    try:
        notification = Notification(
            user_id=user_id,
            content=content,
            link=link
        )
        db.session.add(notification)
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Error creating notification: {str(e)}")
        db.session.rollback()

def validate_tags(tag_string, max_tags=5):
    tags = [t.strip() for t in tag_string.split(',') if t.strip()]
    return tags[:max_tags]

def create_default_data():
    """Create default categories and admin user"""
    with app.app_context():
        if not Category.query.first():
            categories = [
                Category(name='General', description='General programming questions'),
                Category(name='Python', description='Python programming questions'),
                Category(name='JavaScript', description='JavaScript programming questions'),
                Category(name='Web Development', description='HTML, CSS, and web development'),
                Category(name='Database', description='Database related questions'),
                Category(name='Mobile Development', description='Mobile app development'),
            ]
            db.session.add_all(categories)
        
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

# ========== ROUTES ==========
@app.route('/upload', methods=['POST'])
@login_required
def upload():
    f = request.files.get('upload')
    if not f:
        return upload_fail('No file uploaded!')
    
    filename = secure_filename(f.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    f.save(filepath)
    url = url_for('static', filename=f'uploads/{filename}')
    return upload_success(url, filename)

@app.route('/notifications')
@login_required
def get_notifications():
    notifications = Notification.query.filter_by(
        user_id=current_user.id, 
        is_read=False
    ).order_by(Notification.created_at.desc()).limit(10).all()
    
    return jsonify([{
        'id': n.id,
        'content': n.content,
        'link': n.link,
        'created_at': n.created_at.strftime('%b %d, %H:%M')
    } for n in notifications])

@app.route('/notifications/mark_read/<int:id>')
@login_required
def mark_notification_read(id):
    notification = Notification.query.get_or_404(id)
    if notification.user_id != current_user.id:
        return jsonify({'success': False})
    
    notification.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/')
def index():
    try:
        search_query = request.args.get('search', '')
        category_filter = request.args.get('category', '')
        
        query = Question.query.filter_by(is_approved=True)
        
        if search_query:
            query = query.filter(Question.title.contains(search_query) | 
                               Question.content.contains(search_query))
        
        if category_filter:
            query = query.filter_by(category_id=category_filter)
        
        questions = query.order_by(Question.created_at.desc()).limit(20).all()
        categories = Category.query.all()
        
        return render_template('index.html', 
                             questions=questions, 
                             categories=categories,
                             search_query=search_query, 
                             category_filter=category_filter)
    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}")
        flash('An error occurred while loading questions')
        return redirect(url_for('index'))

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
        try:
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            
            if not title or not content:
                flash('Title and content are required')
                return redirect(url_for('ask_question'))
            
            tag_names = validate_tags(request.form.get('tags', ''))
            category_id = request.form.get('category_id')
            
            question = Question(
                title=title,
                content=content,
                user_id=current_user.id,
                category_id=category_id if category_id else None
            )
            
            # Handle tags
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                question.tags.append(QuestionTag(tag=tag))
            
            db.session.add(question)
            db.session.commit()
            flash('Question posted successfully')
            return redirect(url_for('view_question', id=question.id))
        
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error posting question: {str(e)}")
            flash('An error occurred while posting your question')
            return redirect(url_for('ask_question'))
    
    categories = Category.query.all()
    return render_template('ask.html', categories=categories)

@app.route('/question/<int:id>')
def view_question(id):
    try:
        question = Question.query.get_or_404(id)
        question.views += 1
        db.session.commit()
        
        answers = Answer.query.filter_by(
            question_id=id, 
            is_approved=True
        ).order_by(Answer.created_at.desc()).all()
        
        return render_template('question.html', 
                             question=question, 
                             answers=answers)
    except Exception as e:
        app.logger.error(f"Error viewing question: {str(e)}")
        flash('An error occurred while loading the question')
        return redirect(url_for('index'))

@app.route('/question/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_question(id):
    question = Question.query.get_or_404(id)
    
    # Authorization check
    if current_user.id != question.user_id and not current_user.is_admin:
        flash('You are not authorized to edit this question')
        return redirect(url_for('view_question', id=id))
    
    if request.method == 'POST':
        try:
            question.title = request.form.get('title', '').strip()
            question.content = request.form.get('content', '').strip()
            
            if not question.title or not question.content:
                flash('Title and content are required')
                return redirect(url_for('edit_question', id=id))
            
            question.category_id = request.form.get('category_id')
            question.updated_at = datetime.utcnow()
            
            # Handle tags update
            current_tags = {qt.tag.name for qt in question.tags}
            new_tags = set(validate_tags(request.form.get('tags', '')))
            
            # Remove deleted tags
            for qt in question.tags[:]:
                if qt.tag.name not in new_tags:
                    db.session.delete(qt)
            
            # Add new tags
            for tag_name in new_tags - current_tags:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                question.tags.append(QuestionTag(tag=tag))
            
            db.session.commit()
            flash('Question updated successfully')
            return redirect(url_for('view_question', id=id))
        
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating question: {str(e)}")
            flash('An error occurred while updating the question')
            return redirect(url_for('edit_question', id=id))
    
    categories = Category.query.all()
    current_tags = ','.join([qt.tag.name for qt in question.tags])
    return render_template('edit_question.html', 
                         question=question, 
                         categories=categories,
                         current_tags=current_tags)

@app.route('/question/delete/<int:id>', methods=['POST'])
@login_required
def delete_question(id):
    question = Question.query.get_or_404(id)
    
    # Authorization check
    if current_user.id != question.user_id and not current_user.is_admin:
        flash('You are not authorized to delete this question')
        return redirect(url_for('view_question', id=id))
    
    try:
        db.session.delete(question)
        db.session.commit()
        flash('Question deleted successfully')
        return redirect(url_for('index'))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting question: {str(e)}")
        flash('An error occurred while deleting the question')
        return redirect(url_for('view_question', id=id))

@app.route('/answer/<int:question_id>', methods=['POST'])
@login_required
def post_answer(question_id):
    content = request.form['content']
    question = Question.query.get_or_404(question_id)
    
    answer = Answer(
        content=content,
        user_id=current_user.id,
        question_id=question_id
    )
    
    db.session.add(answer)
    db.session.commit()
    
    # Notify question author
    if question.author.id != current_user.id:
        create_notification(
            user_id=question.author.id,
            content=f"{current_user.username} answered your question: {question.title}",
            link=url_for('view_question', id=question_id)
        )
    
    flash('Answer posted successfully')
    return redirect(url_for('view_question', id=question_id))

@app.route('/answer/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_answer(id):
    answer = Answer.query.get_or_404(id)
    
    # Authorization check
    if current_user.id != answer.user_id and not current_user.is_admin:
        flash('You are not authorized to edit this answer')
        return redirect(url_for('view_question', id=answer.question_id))
    
    if request.method == 'POST':
        try:
            answer.content = request.form.get('content', '').strip()
            
            if not answer.content:
                flash('Content is required')
                return redirect(url_for('edit_answer', id=id))
            
            answer.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Answer updated successfully')
            return redirect(url_for('view_question', id=answer.question_id))
        
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating answer: {str(e)}")
            flash('An error occurred while updating the answer')
            return redirect(url_for('edit_answer', id=id))
    
    return render_template('edit_answer.html', answer=answer)

@app.route('/answer/delete/<int:id>', methods=['POST'])
@login_required
def delete_answer(id):
    answer = Answer.query.get_or_404(id)
    question_id = answer.question_id
    
    # Authorization check
    if current_user.id != answer.user_id and not current_user.is_admin:
        flash('You are not authorized to delete this answer')
        return redirect(url_for('view_question', id=question_id))
    
    try:
        db.session.delete(answer)
        db.session.commit()
        flash('Answer deleted successfully')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting answer: {str(e)}")
        flash('An error occurred while deleting the answer')
    
    return redirect(url_for('view_question', id=question_id))

@app.route('/vote', methods=['POST'])
@login_required
def vote():
    data = request.get_json()
    vote_type = data.get('type')
    question_id = data.get('question_id')
    answer_id = data.get('answer_id')
    
    existing_vote = Vote.query.filter_by(
        user_id=current_user.id,
        question_id=question_id,
        answer_id=answer_id
    ).first()
    
    if existing_vote:
        if existing_vote.vote_type == vote_type:
            db.session.delete(existing_vote)
        else:
            existing_vote.vote_type = vote_type
    else:
        vote = Vote(
            vote_type=vote_type,
            user_id=current_user.id,
            question_id=question_id,
            answer_id=answer_id
        )
        db.session.add(vote)
    
    db.session.commit()
    
    # Notify content author
    if question_id:
        content = Question.query.get(question_id)
        score = content.get_vote_score()
    else:
        content = Answer.query.get(answer_id)
        score = content.get_vote_score()
        
        # Notify answer author for answer votes
        if content.author.id != current_user.id:
            create_notification(
                user_id=content.author.id,
                content=f"{current_user.username} voted on your answer",
                link=url_for('view_question', id=content.question_id)
            )
    
    return jsonify({'score': score})

@app.route('/answer/accept/<int:id>', methods=['POST'])
@login_required
def accept_answer(id):
    answer = Answer.query.get_or_404(id)
    question = answer.question
    
    # Authorization check
    if current_user.id != question.user_id and not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        # Unaccept any previously accepted answer
        Answer.query.filter_by(question_id=question.id, is_accepted=True).update({'is_accepted': False})
        
        # Accept this answer
        answer.is_accepted = True
        db.session.commit()
        
        # Notify answer author
        if answer.author.id != current_user.id:
            create_notification(
                user_id=answer.author.id,
                content=f"Your answer was accepted for: {question.title}",
                link=url_for('view_question', id=question.id)
            )
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error accepting answer: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@app.route('/profile/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    questions = Question.query.filter_by(
        user_id=user.id, 
        is_approved=True
    ).order_by(Question.created_at.desc()).limit(10).all()
    
    answers = Answer.query.filter_by(
        user_id=user.id, 
        is_approved=True
    ).order_by(Answer.created_at.desc()).limit(10).all()
    
    return render_template('profile.html', 
                         user=user, 
                         questions=questions, 
                         answers=answers)

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('index'))
    
    stats = {
        'total_users': User.query.count(),
        'total_questions': Question.query.count(),
        'total_answers': Answer.query.count(),
        'pending_questions': Question.query.filter_by(is_approved=False).count(),
        'pending_answers': Answer.query.filter_by(is_approved=False).count()
    }
    
    recent_questions = Question.query.order_by(
        Question.created_at.desc()
    ).limit(5).all()
    
    recent_users = User.query.order_by(
        User.created_at.desc()
    ).limit(5).all()
    
    return render_template('admin.html', 
                         stats=stats, 
                         recent_questions=recent_questions, 
                         recent_users=recent_users)

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
    else:
        flash('Invalid content type')
        return redirect(url_for('admin_dashboard'))
    
    item.is_approved = True
    db.session.commit()
    
    flash(f'{type.capitalize()} approved successfully')
    return redirect(url_for('admin_dashboard'))

# ========== APPLICATION START ==========
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_default_data()
    app.run(debug=True)