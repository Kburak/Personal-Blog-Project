from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from wtforms.validators import InputRequired, Length, EqualTo, Email
from wtforms import StringField, PasswordField, BooleanField, TextAreaField
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "you_know_nothing"
Bootstrap(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@app.before_first_request
def create_tables():
    db.create_all()


class Blogpost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50))
    subtitle = db.Column(db.String(50))
    author = db.Column(db.String(20))
    content = db.Column(db.String(250))
    date_posted = db.Column(db.DateTime)


class Users(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String, unique=True)
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(80))


    @login_manager.user_loader
    def load_user(user_id):
        return Users.query.get(int(user_id))


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=80)])
    remember = BooleanField('Remember me')


class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=80)])
    confirm = PasswordField('Confirm Password', validators=[InputRequired(), EqualTo('password')])


class BlogForm(FlaskForm):
    title = StringField('Title', validators=[InputRequired(), Length(max=50)])
    subtitle = StringField('Subtitle', validators=[InputRequired(), Length(max=80)])
    content = TextAreaField('Blog Content', validators=[InputRequired(), Length(min=10, message='Your message is too short.')])


@app.route('/')
def index():
    posts = Blogpost.query.order_by(Blogpost.date_posted.desc()).all()

    return render_template('index.html', posts=posts)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            hashed_password = generate_password_hash(form.password.data, method='sha256')
            new_user = Users(username=form.username.data, email=form.email.data, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()

            return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST':
        user = Users.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=form.remember.data)

            return redirect(url_for('index'))
        else:
            return redirect(url_for('register'))

    return render_template('login.html', form=form)


@app.route('/userposts/<string:user_id>')
@login_required
def userposts(user_id):
    if user_id != current_user.get_id():
        abort(403)

    user = Users.query.filter(Users.id == user_id).first()
    posts = Blogpost.query.order_by(Blogpost.date_posted.desc()).filter(Blogpost.author == current_user.username)

    return render_template('userposts.html', posts=posts, user=user)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/post/<int:post_id>')
def post(post_id):
    post = Blogpost.query.filter_by(id=post_id).one()
    date_posted = post.date_posted.strftime('%B %d, %Y')


    return render_template('post.html', post=post, date_posted=date_posted)


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/add')
@login_required
def add():
    form = BlogForm(request.form)

    return render_template('add.html', form=form)


@app.route('/addpost', methods=['GET','POST'])
@login_required
def addpost():

    form = BlogForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            post = Blogpost(title=form.title.data, subtitle=form.subtitle.data, content=form.content.data,
                            author=current_user.username,
                            date_posted=datetime.now())
            db.session.add(post)
            db.session.commit()

        return redirect(url_for('index'))

    return render_template('add.html', form=form)

@app.route('/post/<int:post_id>/edit', methods = ['GET', 'POST'])
@login_required
def edit(post_id):
    post = Blogpost.query.filter_by(id=post_id).one()
    form = BlogForm(request.form)

    if post.author != current_user.username:
        return redirect(url_for('index'))

    if request.method == 'POST':
        if form.validate_on_submit():
            post.title = form.subtitle.data
            post.subtitle = form.subtitle.data
            post.content = form.content.data
            db.session.commit()
            flash('Your post has been updated!', 'success')
            return redirect(url_for('post', post_id=post_id))

    form.title.data = post.title
    form.subtitle.data = post.subtitle
    form.content.data = post.content

    return render_template('edit.html', post=post, form=form)


@app.route('/post/<int:post_id>/delete', methods=['GET'])
@login_required
def delete(post_id):
    delete_post = Blogpost.query.filter_by(id=post_id).first()
    if delete_post.author != current_user.username:
        return redirect(url_for('index'))
    db.session.delete(delete_post)
    db.session.commit()
    flash('Your record has been deleted!', 'success')
    return redirect(url_for('index', post_id=post_id))


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    if request.method == 'POST':
        logout_user()
        flash('Goodbye!', 'info')
        return redirect(url_for('index'))

    return render_template('logout.html')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run(debug=True)
