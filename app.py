from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import markdown2
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    notes = db.relationship('Note', backref='author', lazy=True)
    todos = db.relationship('Todo', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    notes = db.relationship('Note', backref='category', lazy=True)
    todos = db.relationship('Todo', backref='category', lazy=True)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    is_public = db.Column(db.Boolean, default=False)
    tags = db.Column(db.String(200))

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    completed = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Integer, default=0)  # 0: Low, 1: Medium, 2: High
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    search_query = request.args.get('search', '')
    category_id = request.args.get('category', type=int)
    
    query = Note.query
    if search_query:
        query = query.filter(
            (Note.title.ilike(f'%{search_query}%')) |
            (Note.content.ilike(f'%{search_query}%')) |
            (Note.tags.ilike(f'%{search_query}%'))
        )
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if current_user.is_authenticated:
        notes = query.filter(
            (Note.user_id == current_user.id) |
            (Note.is_public == True)
        ).order_by(Note.updated_at.desc()).all()
    else:
        notes = query.filter_by(is_public=True).order_by(Note.updated_at.desc()).all()
    
    categories = Category.query.all()
    return render_template('index.html', notes=notes, categories=categories, 
                         search_query=search_query, selected_category=category_id)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category_id = request.form.get('category_id', type=int)
        tags = request.form.get('tags', '')
        is_public = 'is_public' in request.form
        
        if not title or not content:
            flash('Title and content are required!', 'error')
            return redirect(url_for('create'))
        
        note = Note(
            title=title,
            content=content,
            user_id=current_user.id,
            category_id=category_id,
            tags=tags,
            is_public=is_public
        )
        db.session.add(note)
        db.session.commit()
        flash('Note created successfully!', 'success')
        return redirect(url_for('index'))
    
    categories = Category.query.all()
    return render_template('create.html', categories=categories)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    note = Note.query.get_or_404(id)
    if note.user_id != current_user.id:
        flash('You do not have permission to edit this note', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category_id = request.form.get('category_id', type=int)
        tags = request.form.get('tags', '')
        is_public = 'is_public' in request.form
        
        if not title or not content:
            flash('Title and content are required!', 'error')
            return redirect(url_for('edit', id=id))
        
        note.title = title
        note.content = content
        note.category_id = category_id
        note.tags = tags
        note.is_public = is_public
        db.session.commit()
        flash('Note updated successfully!', 'success')
        return redirect(url_for('index'))
    
    categories = Category.query.all()
    return render_template('edit.html', note=note, categories=categories)

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    note = Note.query.get_or_404(id)
    if note.user_id != current_user.id:
        flash('You do not have permission to delete this note', 'error')
        return redirect(url_for('index'))
    
    db.session.delete(note)
    db.session.commit()
    flash('Note deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/preview/<int:id>')
def preview(id):
    note = Note.query.get_or_404(id)
    if not note.is_public and (not current_user.is_authenticated or note.user_id != current_user.id):
        flash('You do not have permission to view this note', 'error')
        return redirect(url_for('index'))
    
    html_content = markdown2.markdown(note.content)
    return render_template('preview.html', note=note, html_content=html_content)

@app.route('/categories')
@login_required
def manage_categories():
    categories = Category.query.all()
    return render_template('categories.html', categories=categories)

@app.route('/category/add', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name')
    if name:
        category = Category(name=name)
        db.session.add(category)
        db.session.commit()
        flash('Category added successfully!', 'success')
    return redirect(url_for('manage_categories'))

@app.route('/category/delete/<int:id>')
@login_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    if category.notes:
        flash('Cannot delete category with associated notes', 'error')
    else:
        db.session.delete(category)
        db.session.commit()
        flash('Category deleted successfully!', 'success')
    return redirect(url_for('manage_categories'))

@app.route('/todos')
@login_required
def todos():
    category_id = request.args.get('category', type=int)
    show_completed = request.args.get('show_completed', type=bool)
    
    query = Todo.query.filter_by(user_id=current_user.id)
    if category_id:
        query = query.filter_by(category_id=category_id)
    if not show_completed:
        query = query.filter_by(completed=False)
    
    todos = query.order_by(Todo.priority.desc(), Todo.due_date.asc()).all()
    categories = Category.query.all()
    return render_template('todos.html', todos=todos, categories=categories, 
                         selected_category=category_id, show_completed=show_completed)

@app.route('/todo/add', methods=['POST'])
@login_required
def add_todo():
    title = request.form.get('title')
    description = request.form.get('description')
    due_date_str = request.form.get('due_date')
    priority = request.form.get('priority', type=int)
    category_id = request.form.get('category_id', type=int)
    
    if not title:
        flash('Title is required!', 'error')
        return redirect(url_for('todos'))
    
    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format', 'error')
            return redirect(url_for('todos'))
    
    todo = Todo(
        title=title,
        description=description,
        due_date=due_date,
        priority=priority or 0,
        category_id=category_id,
        user_id=current_user.id
    )
    
    db.session.add(todo)
    db.session.commit()
    flash('Todo added successfully!', 'success')
    return redirect(url_for('todos'))

@app.route('/todo/<int:id>/toggle')
@login_required
def toggle_todo(id):
    todo = Todo.query.get_or_404(id)
    if todo.user_id != current_user.id:
        flash('You do not have permission to modify this todo', 'error')
        return redirect(url_for('todos'))
    
    todo.completed = not todo.completed
    db.session.commit()
    flash('Todo status updated!', 'success')
    return redirect(url_for('todos'))

@app.route('/todo/<int:id>/edit', methods=['POST'])
@login_required
def edit_todo(id):
    todo = Todo.query.get_or_404(id)
    if todo.user_id != current_user.id:
        flash('You do not have permission to edit this todo', 'error')
        return redirect(url_for('todos'))
    
    title = request.form.get('title')
    description = request.form.get('description')
    due_date_str = request.form.get('due_date')
    priority = request.form.get('priority', type=int)
    category_id = request.form.get('category_id', type=int)
    
    if not title:
        flash('Title is required!', 'error')
        return redirect(url_for('todos'))
    
    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format', 'error')
            return redirect(url_for('todos'))
    
    todo.title = title
    todo.description = description
    todo.due_date = due_date
    todo.priority = priority or 0
    todo.category_id = category_id
    
    db.session.commit()
    flash('Todo updated successfully!', 'success')
    return redirect(url_for('todos'))

@app.route('/todo/<int:id>/delete')
@login_required
def delete_todo(id):
    todo = Todo.query.get_or_404(id)
    if todo.user_id != current_user.id:
        flash('You do not have permission to delete this todo', 'error')
        return redirect(url_for('todos'))
    
    db.session.delete(todo)
    db.session.commit()
    flash('Todo deleted successfully!', 'success')
    return redirect(url_for('todos'))

# Initialize database with some default categories
def init_db():
    with app.app_context():
        db.create_all()
        if not Category.query.first():
            default_categories = ['Work', 'Personal', 'Ideas', 'To-Do']
            for category_name in default_categories:
                category = Category(name=category_name)
                db.session.add(category)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
