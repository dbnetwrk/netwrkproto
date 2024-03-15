from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from datetime import datetime


UPLOAD_FOLDER = 'C:\\flasker\\static\\uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}



model = SentenceTransformer('all-MiniLM-L6-v2')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://ubjg47i7g7isg8:p7b28d89d1d5c485255cd8f3ec14ffd4eedc961ef6e2d551b4c1be75734150385@cb889jp6h2eccm.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d7t68f59g1ep1t'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = '1'


db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(50), nullable=False)
    profile_pic_url = db.Column(db.String(255), default='/static/images/default_profile.png')
    burner_username = db.Column(db.String(50), nullable=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    community_name = db.Column(db.String(100), nullable=False)
    profile_pic_url = db.Column(db.String(255), nullable=True)  # Optional
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    posted_time = db.Column(db.String(50), nullable=False)
    upvotes = db.Column(db.Integer, nullable=False, default=0)
    downvotes = db.Column(db.Integer, nullable=False, default=0)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_post_user_id'), nullable=False)  # Add this line

    user = db.relationship('User', backref=db.backref('posts', lazy=True))  # Add this line

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    posted_time = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Optional, if you want to track which user made the comment

    post = db.relationship('Post', backref=db.backref('comments', lazy=True))
    user = db.relationship('User', backref=db.backref('comments', lazy=True))  # Optional, as above
    is_burner = db.Column(db.Boolean, default=False, nullable=False)

class UserAction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(20), nullable=False)  # 'invite' or 'no_thanks'
    friend_phone = db.Column(db.String(20), nullable=True)  # Optional phone number
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('actions', lazy=True))



# Initialize the database
@app.before_first_request
def create_tables():
    db.create_all()



@app.route('/', methods=['GET', 'POST'])
def index():

	return render_template("index.html")



@app.route('/signup', methods=['GET', 'POST'])
def signup():

	if request.method == 'POST':

		first_name = request.form.get('first_name')
		last_name = request.form.get('last_name')
		password = request.form.get('password')


		user = User(first_name=first_name, last_name = last_name, password= password)
		db.session.add(user)
		db.session.commit()

		session['user_id'] = user.id

		return redirect(url_for('show_feed'))


	return render_template("signup.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        password = request.form.get('password')

        # Adjust the query to filter by both first name and last name
        user = User.query.filter_by(first_name=first_name, last_name=last_name, password=password).first()

        if user:
            session['user_id'] = user.id  # Log in the user
            return redirect(url_for('show_feed'))
        else:
            # Provide feedback that login was unsuccessful
            flash('Invalid first name, last name, or password')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/post/<int:post_id>')
def show_post(post_id):
    post = Post.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.posted_time.desc()).all()
    return render_template('post_detail.html', post=post, comments=comments)



@app.route('/feed')
def show_feed():
    posts = Post.query.all()
    return render_template("feed.html", posts=posts)


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        # User is not logged in, redirect to login page
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if not user:
        # User not found, maybe redirect to logout to clear the session
        return redirect(url_for('login'))
    
    return render_template('profile.html', user=user)


@app.route('/post/<int:post_id>/comment', methods=['POST'])
def submit_comment(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    comment_content = request.form.get('comment_content')
    post_as_burner = 'post_as_burner' in request.form  # Check if checkbox is checked
    
    if not comment_content:
        flash('Comment cannot be empty.')
        return redirect(url_for('show_post', post_id=post_id))
    
    # If posting as burner, ensure the user has a burner username set
    if post_as_burner and not user.burner_username:
        flash('Burner username is required to post as burner.')
        return redirect(url_for('show_post', post_id=post_id))
    
    new_comment = Comment(content=comment_content, user_id=user_id, post_id=post_id, is_burner=post_as_burner)
    db.session.add(new_comment)
    db.session.commit()
    
    return redirect(url_for('show_post', post_id=post_id))



def time_ago(time):
    """
    Convert a datetime object to a human-readable time-difference string.
    """
    if type(time) is not datetime:
        return time

    now = datetime.utcnow()
    diff = now - time

    seconds = diff.total_seconds()
    minutes = seconds / 60
    hours = minutes / 60
    days = hours / 24

    if days >= 1:
        return f"{int(days)} day{'s' if days > 1 else ''} ago"
    elif hours >= 1:
        return f"{int(hours)} hour{'s' if hours > 1 else ''} ago"
    elif minutes >= 1:
        return f"{int(minutes)} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"

app.jinja_env.filters['time_ago'] = time_ago


@app.context_processor
def inject_user():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return {'current_user': user}
    return {'current_user': None}


@app.route('/create_burner_username', methods=['POST'])
def create_burner_username():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    if user:
        user.burner_username = request.form.get('burner_username')
        db.session.commit()
        flash('Burner username created successfully.')
    else:
        flash('User not found.')
    
    return redirect(url_for('profile'))


@app.route('/logout', methods=['POST'])
def logout():
    # Add any necessary cleanup before logging out
    # Redirect to the decision page
    return redirect(url_for('invite_decision'))

@app.route('/invite_decision', methods=['GET', 'POST'])
def invite_decision():
    if request.method == 'POST':
        action = request.form['action']  # 'invite' or 'no_thanks'
        user_id = session.get('user_id')
        
        if not user_id:
            flash('You need to be logged in to perform this action.')
            return redirect(url_for('login'))
        
        if action == 'invite':
            friend_phone = request.form.get('friend_phone')
            user_action = UserAction(user_id=user_id, action='invite', friend_phone=friend_phone, timestamp=datetime.utcnow())
            db.session.add(user_action)
            db.session.commit()
            # Optionally, add logic to send an invite via SMS to friend_phone
            flash('Invitation sent successfully.')
        elif action == 'no_thanks':
            user_action = UserAction(user_id=user_id, action='no_thanks', timestamp=datetime.utcnow())
            db.session.add(user_action)
            db.session.commit()
            flash('Your choice has been recorded.')
        
        return redirect(url_for('index'))  # or any other page you'd like to redirect to
    
    # If it's a GET request, just render the invite_decision page
    return render_template('invite_decision.html')


if __name__ == '__main__':
	app.run(debug=True)