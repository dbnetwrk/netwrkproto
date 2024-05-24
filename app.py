from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import os
from sqlalchemy import func
from openai import OpenAI
from werkzeug.utils import secure_filename
from datetime import datetime
from random import choice
from sqlalchemy.sql import exists
import random
from sqlalchemy import and_
from sqlalchemy import or_
import re
import shutil
from flask import Flask
from flask_socketio import SocketIO, emit
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from dotenv import load_dotenv
import random
from flask import request
import boto3
import pytz
import uuid
import requests
import praw

load_dotenv()



UPLOAD_FOLDER = 'C:\\flasker\\static\\uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}



app = Flask(__name__)
socketio = SocketIO(app)


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://ubjg47i7g7isg8:p7b28d89d1d5c485255cd8f3ec14ffd4eedc961ef6e2d551b4c1be75734150385@cb889jp6h2eccm.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d7t68f59g1ep1t'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = '1'

api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['DEBUG'] = True


jobstores = {
    'default': SQLAlchemyJobStore(url=app.config['SQLALCHEMY_DATABASE_URI'])
}
scheduler = BackgroundScheduler(jobstores=jobstores)


scheduler.start()


db = SQLAlchemy(app)
migrate = Migrate(app, db)

def test_job():
    print(f"Test job executed at {datetime.datetime.now()}")



import logging

logging.basicConfig(level=logging.DEBUG)

@app.route('/jobs')
def list_jobs():
    logging.debug(f"Scheduler state: {'running' if scheduler.running else 'not running'}")
    if scheduler.running:
        jobs = [{
            'id': job.id,
            'name': job.name,
            'next_run_time': str(job.next_run_time),
            'trigger': str(job.trigger)
        } for job in scheduler.get_jobs()]
    else:
        jobs = ["Scheduler not running"]
    return jsonify(jobs)



#scheduler.add_job(test_job, 'interval', seconds=60, id='test_job')



user_community_association = db.Table('user_community',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('community_id', db.Integer, db.ForeignKey('community.id'), primary_key=True)
)

user_interest_association = db.Table('user_interest',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('interest_id', db.Integer, db.ForeignKey('interest.id'), primary_key=True)
)

community_interest_association = db.Table('community_interest',
    db.Column('community_id', db.Integer, db.ForeignKey('community.id'), primary_key=True),
    db.Column('interest_id', db.Integer, db.ForeignKey('interest.id'), primary_key=True)
)

followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)



community_subreddit_association = db.Table('community_subreddit',
    db.Column('community_id', db.Integer, db.ForeignKey('community.id'), primary_key=True),
    db.Column('subreddit_id', db.Integer, db.ForeignKey('subreddits.id'), primary_key=True)
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(50), nullable=False)
    profile_pic_url = db.Column(db.String(255), default='/static/images/default_profile.png')
    burner_username = db.Column(db.String(50), nullable=True)
    communities = db.relationship('Community', secondary=user_community_association, backref=db.backref('members', lazy='dynamic'))
    interests = db.relationship('Interest', secondary=user_interest_association, backref=db.backref('users', lazy='dynamic'))
    industry_id = db.Column(db.Integer, db.ForeignKey('industry.id'), nullable=True)
    industry = db.relationship('Industry', backref=db.backref('users', lazy=True))
    about_me = db.Column(db.Text, nullable=True)  # Add this line for the "About Me" section
    karma = db.Column(db.Integer, default = 0)
    background_color = db.Column(db.String(7))
    profile_color = db.Column(db.String(7), nullable=True)
    header_pic_url = db.Column(db.String(255), nullable=True)
    seeder = db.Column(db.Boolean, default=False, nullable=False)

    # Add a method to determine the display name
    def display_name(self, is_anonymous):
        if is_anonymous:
            return self.burner_username  # Return the burner username if the conversation is anonymous
        else:
            return f"{self.first_name} {self.last_name}"

    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0

from sqlalchemy.orm import backref


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    posted_time = db.Column(db.DateTime, default=datetime.utcnow)
    upvotes = db.Column(db.Integer, default=0)
    downvotes = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    community_id = db.Column(db.Integer, db.ForeignKey('community.id'), nullable=False)
    image_filename = db.Column(db.String(255))

    user = db.relationship('User', backref='posts')
    community = db.relationship('Community', backref='posts')
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")

    reddit_post_id = db.Column(db.String(255), nullable=True)




class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    posted_time = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    is_burner = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='comments')
    replies = db.relationship('Comment', backref=backref('parent', remote_side=[id]), lazy='dynamic')



class UserAction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    invite_scale = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('actions', lazy=True))

class Community(db.Model):
    __tablename__ = 'community'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    profile_pic_url = db.Column(db.String(255), nullable=True, default='/static/images/default_community.png')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_anonymous = db.Column(db.Boolean, default=False, nullable=False)
    color = db.Column(db.String(7), nullable=True)
    header_pic_url = db.Column(db.String(255), nullable=True)
    
    creator = db.relationship('User', backref=db.backref('created_communities', lazy=True))
    interests = db.relationship('Interest', secondary=community_interest_association, backref=db.backref('communities', lazy='dynamic'))
    subreddits = db.relationship('Subreddits', secondary=community_subreddit_association, backref=db.backref('communities', lazy='dynamic'))



class Interest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    interest_category_id = db.Column(db.Integer, db.ForeignKey('interest_category.id'))
    color = db.Column(db.String(7), nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    community_id = db.Column(db.Integer, db.ForeignKey('community.id'), nullable=True)  # New field for direct community link

    community = db.relationship('Community', backref=db.backref('direct_interests', lazy=True))
      # New foreign key column



class Industry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    industry_category_id = db.Column(db.Integer, db.ForeignKey('industry_category.id'), nullable=False)  # Reference to IndustryCategory model


class IndustryCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    industries = db.relationship('Industry', backref='industry_category', lazy=True)

class InterestCategory(db.Model):
    __tablename__ = 'interest_category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    interests = db.relationship('Interest', backref='interest_category', lazy='dynamic')

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=True)  # Optional name for group conversations
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_anonymous = db.Column(db.Boolean, default=False, nullable=False)

class UserConversation(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), primary_key=True)
    user = db.relationship('User', backref='user_conversations')
    conversation = db.relationship('Conversation', backref='user_conversations')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'))
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    user = db.relationship('User', backref='messages')
    conversation = db.relationship('Conversation', backref='messages')


class RecycledPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)  # For posts with images
    community_id = db.Column(db.Integer, db.ForeignKey('community.id'), nullable=False)

    community = db.relationship('Community', backref=db.backref('recycled_posts', lazy=True))


class AIPrompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.Text, nullable=False)
    community_id = db.Column(db.Integer, db.ForeignKey('community.id'), nullable=False)
    community = db.relationship('Community', backref='ai_prompts')
    interval_minutes = db.Column(db.Integer, nullable=False, default=1440)  # default to daily

    def __repr__(self):
        return f'<AIPrompt {self.prompt} every {self.interval_minutes} min>'

class Subreddits(db.Model):
    __tablename__ = 'subreddits'
    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.Text, nullable=False)
    
    



class AICommentPrompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.Text, nullable=False)



class ScheduledPost(db.Model):
    __tablename__ = 'scheduled_posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    reddit_post_id = db.Column(db.String(255), nullable=True)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    job_id = db.Column(db.String(255), nullable=True)  # Add this line

    def __repr__(self):
        return '<ScheduledPost {}>'.format(self.title)


class RedditPost(db.Model):
    __tablename__ = 'redditpost'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    image_url = db.Column(db.String(255))
    content = db.Column(db.Text)
    reddit_post_id = db.Column(db.String(50), unique=True)  # Ensure uniqueness to avoid duplicates
    subreddit_id = db.Column(db.Integer, db.ForeignKey('subreddits.id'))  # Assuming a FK relationship
    subreddit_name = db.Column(db.Text)




industry_images = {
    1: '/images/education.png',
    2: '/images/construction.png',
    3: '/images/design.png',
    4: '/images/corporate_services.png',
    5: '/images/retail.png',
    6: '/images/energy_mining.png',
    7: '/images/manufacturing.png',
    8: '/images/finance.png',
    9: '/images/recreation_travel.png',
    10: '/images/arts.png',
    11: '/images/health_care.png',
    12: '/images/hardware_networking.png',
    13: '/images/real_estate.png',
    14: '/images/legal.png',
    15: '/images/consumer_goods.png',
    16: '/images/agriculture.png',
    17: '/images/media_communications.png',
    18: '/images/nonprofit.png',
    19: '/images/software_it_services.png',
    20: '/images/transportation_logistics.png',
    21: '/images/entertainment.png',
    22: '/images/wellness_fitness.png',
    23: '/images/public_safety.png',
    24: '/images/public_administration.png',
}




from mimetypes import guess_type

def upload_file_to_s3(file, bucket_name, filename, content_type=None):
    # Assuming you use boto3 for S3 interaction
    import boto3
    s3 = boto3.client('s3')

    if not content_type:
        # Guess content type if not provided
        content_type, _ = guess_type(filename)
        if content_type is None:
            content_type = 'application/octet-stream'  # Default content type

    s3.upload_fileobj(
        file,
        bucket_name,
        filename,
        ExtraArgs={
            "ContentType": content_type
        }
    )

    return f"https://{bucket_name}.s3.amazonaws.com/{filename}"







@app.context_processor
def inject_location():
    location = request.args.get('location', 'Miami')  # Default location is 'Miami'
    return dict(location=location)

@app.route('/', methods=['GET', 'POST'])
def index():
    # Fetch top non-anonymous communities
    non_anon_communities = db.session.query(
        Community.id,
        Community.name,
        Community.profile_pic_url,
        Community.description,
        func.coalesce(func.count(user_community_association.c.user_id), 0).label("members_count")
    ).outerjoin(
        user_community_association, user_community_association.c.community_id == Community.id
    ).filter(
        Community.is_anonymous == False
    ).group_by(
        Community.id,
        Community.name,
        Community.profile_pic_url,
        Community.description
    ).order_by(
        func.coalesce(func.count(user_community_association.c.user_id), 0).desc()
    ).limit(20).all()  # Adjust number as needed

    # Fetch top anonymous communities
    anon_communities = db.session.query(
        Community.id,
        Community.name,
        Community.profile_pic_url,
        Community.description,
        func.coalesce(func.count(user_community_association.c.user_id), 0).label("members_count")
    ).outerjoin(
        user_community_association, user_community_association.c.community_id == Community.id
    ).filter(
        Community.is_anonymous == True
    ).group_by(
        Community.id,
        Community.name,
        Community.profile_pic_url,
        Community.description
    ).order_by(
        func.coalesce(func.count(user_community_association.c.user_id), 0).desc()
    ).limit(20).all()  # Adjust number as needed

    return render_template("index.html", non_anon_communities=non_anon_communities, anon_communities=anon_communities)






def generate_burner_username():
    professions = ['Strategist', 'Vanguard', 'Innovator', 'Architect', 'Visionary', 'Pioneer',
                   'Sculptor', 'Guru', 'Evangelist', 'Ace', 'Master', 'Sage', 'Prophet', 'Navigator',
                   'Crusader', 'Savant', 'Oracle', 'Geek', 'Pilot', 'Director', 'Captain', 'Queen',
                   'Unicorn', 'Commander', 'Sheriff', 'Innovator']
    adjectives = ['Tech', 'Data', 'Lead', 'System', 'Market', 'Edu', 'Digital', 'Research',
                  'Learning', 'Analytics', 'Build', 'Engineering', 'Project', 'Finance', 'Creative',
                  'Strategy', 'Operations', 'Growth', 'Product', 'Design', 'Content', 'Quality',
                  'UX', 'Cloud', 'Security', 'Infosec']

    # Randomly select one term from each list and combine
    username = random.choice(adjectives) + random.choice(professions)
    return username


@app.route('/signup_step1', methods=['POST'])
def signup_step1():
    # Existing user creation code
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    password = request.form.get('password')
    burner_username = request.form.get('burner_username')
    location = request.form.get('location', 'Miami')

    # Create the user
    user = User(first_name=first_name, last_name=last_name, password=password, burner_username=burner_username)
    db.session.add(user)
    db.session.commit()
  
    session['user_id'] = user.id

    # Now handle the topics
    #industry_topics = request.form.getlist('industry_topics[]')
    #general_topics = request.form.getlist('general_topics[]')
    #all_selected_topics = industry_topics + general_topics

    # Query all communities from the database, ordered by user count
    all_communities_query = db.session.query(
        Community.id,
        Community.name,
        Community.profile_pic_url,
        Community.description,
        func.count(user_community_association.c.user_id).label("members_count")
    ).outerjoin(
        user_community_association, user_community_association.c.community_id == Community.id
    ).group_by(
        Community.id,
        Community.name,
        Community.profile_pic_url,
        Community.description
    ).order_by(
        func.count(user_community_association.c.user_id).desc()
    ).all()  # Removed limit, but kept order by descending user count

    # Packaging community info
    all_communities_info = [
        {
            'id': id_,
            'name': name,
            'profile_pic_url': profile_pic_url,
            'description': description,
            'members_count': members_count
        }
        for id_, name, profile_pic_url, description, members_count in all_communities_query
    ]

    return render_template('select_communities.html', communities=all_communities_info, location=location)




@app.route('/vote/<int:post_id>', methods=['POST'])
def vote(post_id):
    post = Post.query.get_or_404(post_id)
    data = request.get_json()

    if data['upvote']:
        post.upvotes += 1
    else:
        post.downvotes += 1

    db.session.commit()

    new_vote_count = post.upvotes - post.downvotes

    return jsonify(new_vote_count=new_vote_count)



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


@app.route('/set_profile_pic', methods=['POST'])
def set_profile_pic():

    user_id = session.get('user_id')
    if not user_id:
        # User is not logged in, redirect to login page
        return redirect(url_for('login'))
    user = User.query.get(user_id)

    # Assuming there's a specific image everyone uses as a profile pic
    new_pic_url = '/static/images/special_profile_pic.png'
    user.profile_pic_url = new_pic_url
    db.session.commit()
    flash('Your profile picture has been updated!', 'success')
    return redirect(url_for('profile', user_id=user.id))


@app.context_processor
def inject_topics():
    topics = Interest.query.all()  # Adjust the query as per your model structure
    return dict(topics=topics)





@app.route('/update_background', methods=['GET', 'POST'])
def update_background():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if request.method == 'POST':
        user.background_color = request.form['background_color']
        db.session.commit()
        flash('Background color updated successfully.', 'success')
        return redirect(url_for('show_feed', user_id=user_id))
    
    # For a GET request, render the form with the current background color
    return render_template('update_background.html', current_color=user.background_color)



def get_top_20_community_ids():



    # Query to get the top 20 community IDs ordered by membership count
    top_20_ids_query = db.session.query(
        Community.id,
        func.count(user_community_association.c.user_id).label("members_count")
    ).join(
        user_community_association, user_community_association.c.community_id == Community.id
    ).group_by(
        Community.id
    ).order_by(
        func.count(user_community_association.c.user_id).desc()
    ).limit(20).all()

    # Extract just the IDs from the query results
    top_20_ids = [result[0] for result in top_20_ids_query]
    return top_20_ids



@app.route('/community/<int:community_id>')
def view_community(community_id):
    community = Community.query.get_or_404(community_id)
    posts = Post.query.filter_by(community_id=community_id).order_by(Post.posted_time.desc()).all()

    posts_with_comments = []
    for post in posts:
        comment_count = Comment.query.filter_by(post_id=post.id).count()
        posts_with_comments.append({'post': post, 'comment_count': comment_count})

    return render_template('view_community.html', community=community, posts=posts_with_comments)


@app.route('/post/<int:post_id>')
def show_post(post_id):
    user_id = session.get('user_id')
    if not user_id:
        # User is not logged in, redirect to login page
        return redirect(url_for('login'))
    user = User.query.get(user_id)

    post = Post.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.posted_time.desc()).all()
    return render_template('post_detail.html', post=post, comments=comments, user=user)





from flask import request
from datetime import datetime
from sqlalchemy.orm import aliased
from sqlalchemy import text, func


from sqlalchemy import func

@app.route('/feed')
def show_feed():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    filter_type = request.args.get('filter', 'new')  # Default to 'new' if not specified
    current_time = func.now()

    # Build the base query with comment counts
    comment_count_subquery = db.session.query(
        Comment.post_id,
        func.count('*').label('comment_count')
    ).group_by(Comment.post_id).subquery()

    # Create alias for easier reference
    comments = aliased(comment_count_subquery, name='comments')

    # Adjusted query using func.now() for PostgreSQL date arithmetic
    joined_posts_query = db.session.query(
        Post, 
        comments.c.comment_count
    ).outerjoin(
        comments, Post.id == comments.c.post_id
    ).join(
        Community, Post.community_id == Community.id
    ).join(
        user_community_association, user_community_association.c.community_id == Community.id
    ).filter(
        user_community_association.c.user_id == user_id
    )

    # Calculate the 'hot' formula
    if filter_type == 'hot':
        score = (Post.upvotes - Post.downvotes + 2 * func.coalesce(comments.c.comment_count, 0)) / func.pow(((func.extract('epoch', func.now() - Post.posted_time) / 3600) + 2), 1.5)
        joined_posts = joined_posts_query.order_by(score.desc()).all()
    else:  # 'new'
        joined_posts = joined_posts_query.order_by(Post.posted_time.desc()).all()

    all_posts = [{'post': post, 'comment_count': comment_count} for post, comment_count in joined_posts]

    return render_template("feed.html", posts=all_posts, active_page='feed', current_filter=filter_type)









@app.route('/search')
def search():
    query = request.args.get('q', '')
    if query:
        # Searching in User model
        users = User.query.filter(
            or_(
                User.first_name.ilike(f'%{query}%'),
                User.last_name.ilike(f'%{query}%'),
                User.burner_username.ilike(f'%{query}%')
            )
        ).all()
        
        # Searching in Post model
        posts = Post.query.filter(
            or_(
                Post.title.ilike(f'%{query}%'),
                Post.content.ilike(f'%{query}%')
            )
        ).all()
        
        # Searching in Community model
        communities = Community.query.filter(
            Community.name.ilike(f'%{query}%')
        ).all()
    else:
        users = []
        posts = []
        communities = []

    return render_template('search_results.html', query=query, users=users, posts=posts, communities=communities)


@app.route('/profile/<int:user_id>')
@app.route('/profile', defaults={'user_id': None})
def profile(user_id):
    if 'user_id' not in session:
        # User is not logged in, redirect to login page
        return redirect(url_for('login'))

    # If no specific user_id is provided, use the session's user_id
    if user_id is None:
        user_id = session['user_id']

    user = User.query.get(user_id)

    if not user:
        # User not found, redirecting to a suitable page
        flash('User not found.')
        return redirect(url_for('index'))  # Assuming 'index' is a valid route

    return render_template('profile.html', user=user, active_page='profile')


@app.route('/post/<int:post_id>/comment', methods=['POST'])
def submit_comment(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    comment_content = request.form.get('comment_content')
    parent_id = request.form.get('parent_id', None)  # Get the parent_id if provided
    post_as_burner = 'post_as_burner' in request.form  # Check if checkbox is checked
    
    # Validation checks
    if not comment_content:
        flash('Comment cannot be empty.', 'error')
        return redirect(url_for('show_post', post_id=post_id))
    
    if post_as_burner and not user.burner_username:
        flash('Burner username is required to post as burner.', 'error')
        return redirect(url_for('show_post', post_id=post_id))
    
    # Create the new comment, considering parent_id for replies
    new_comment = Comment(content=comment_content, user_id=user_id, post_id=post_id, parent_id=parent_id if parent_id else None, is_burner=post_as_burner)
    
    db.session.add(new_comment)
    db.session.commit()
    
    flash('Comment posted successfully.', 'success')
    return redirect(url_for('show_post', post_id=post_id))


from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import os

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get_or_404(user_id)  # Assuming you want to show a 404 if the user isn't found

    STATIC_FOLDER = app.static_folder

    if request.method == 'POST':
        user.about_me = request.form.get('aboutme')
        user.profile_color = request.form.get('color')

        # Handle file upload for profile picture
        profile_pic = request.files.get('profile_pic')
        if profile_pic and allowed_file(profile_pic.filename):
            filename = secure_filename(profile_pic.filename)
            save_path = os.path.join(STATIC_FOLDER, 'images', filename)
            rel_path = os.path.join('/static','images', filename).replace('\\', '/')  # Replace backslashes
            profile_pic.save(save_path)
            user.profile_pic_url = rel_path  # Store relative path

        # Handle file upload for header picture
        header_pic = request.files.get('header_pic')
        if header_pic and allowed_file(header_pic.filename):
            filename = secure_filename(header_pic.filename)
            save_path = os.path.join(STATIC_FOLDER, 'images', 'header_pics', filename)
            rel_path = os.path.join('images', 'header_pics', filename).replace('\\', '/')  # Replace backslashes
            header_pic.save(save_path)
            user.header_pic_url = rel_path  # Store relative path

        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('profile', user_id=user_id))

    return render_template('edit_profile.html', user=user)



@app.route('/edit_community/<int:community_id>', methods=['GET', 'POST'])
def edit_community(community_id):
    user_id = session.get('user_id')
    if not user_id:
        # User is not logged in, redirect to login page
        return redirect(url_for('login'))
    user = User.query.get(user_id)

    community = Community.query.get_or_404(community_id)
    if community.created_by != user.id:
        flash('You do not have permission to edit this community.', 'danger')
        return redirect(url_for('index'))

    STATIC_FOLDER = app.static_folder

    if request.method == 'POST':
        # Directly access form data using request.form
        description = request.form.get('description')
        color = request.form.get('color')

        # Add any necessary validation for form fields here

        # Update community details
        community.description = description if description else community.description
        community.color = color if color else community.color



        # Handle file upload for profile picture
        profile_pic = request.files.get('profile_pic')
        if profile_pic and allowed_file(profile_pic.filename):
            filename = secure_filename(profile_pic.filename)
            save_path = os.path.join(STATIC_FOLDER, 'images', filename)
            rel_path = os.path.join('images', filename).replace('\\', '/')  # Replace backslashes
            profile_pic.save(save_path)
            community.profile_pic_url = rel_path  # Store relative path

        # Handle file upload for header picture
        header_pic = request.files.get('header_pic')
        if header_pic and allowed_file(header_pic.filename):
            filename = secure_filename(header_pic.filename)
            save_path = os.path.join(STATIC_FOLDER, 'images', 'header_pics', filename)
            rel_path = os.path.join('images', 'header_pics', filename).replace('\\', '/')  # Replace backslashes
            header_pic.save(save_path)
            community.header_pic_url = rel_path  # Store relative path





        
        db.session.commit()
        flash('Your community has been updated.', 'success')
        return redirect(url_for('view_community', community_id=community.id))
    
    # If request.method is 'GET', display the form with existing community details
    return render_template('edit_community.html', community=community)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

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
        user_id = session.get('user_id')
        
        if not user_id:
            flash('You need to be logged in to perform this action.')
            return redirect(url_for('login'))
        
        # We assume the 'submit_scale' action value is set for submitting the scale
        action = request.form['action']
        if action == 'submit_scale':
            invite_scale = request.form.get('invite_scale', type=int)  # Ensure we are getting an integer
            user_action = UserAction(user_id=user_id, invite_scale=invite_scale, timestamp=datetime.utcnow())
            db.session.add(user_action)
            db.session.commit()
            flash('Thank you for your feedback!')
        
        return redirect(url_for('index'))  # or any other page you'd like to redirect to
    
    # If it's a GET request, just render the invite_decision page
    return render_template('invite_decision.html')



from flask import request, session, flash, redirect, url_for, render_template
from datetime import datetime
# Assuming the import of your db and models is done correctly

@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    if 'user_id' not in session:
        flash("Please log in to create a post.")
        return redirect(url_for('login'))

    community_id = request.args.get('community_id') if request.method == 'GET' else request.form.get('community')
    communities = Community.query.all()  # Assuming you have a Community model
    user_id = session['user_id']

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        image = request.files.get('image')
        image_url = None  # Default to None if no image is uploaded

        if image and allowed_file(image.filename):
            print("okay so we know there's an image")
            image_filename = secure_filename(image.filename)
            s3_folder = 'posts/'  # Define the folder path in S3
            bucket_name = 'netwrkproto'  # Your S3 bucket name

            # Upload image directly to S3 and retrieve the URL
            image_url = upload_file_to_s3(image, bucket_name, s3_folder + image_filename)

        # Create a new post with the S3 image URL
        new_post = Post(
            title=title,
            content=content,
            community_id=community_id,
            user_id=user_id,
            posted_time=datetime.utcnow(),
            upvotes=0,
            downvotes=0,
            image_filename=image_url  # Store the URL of the image
        )
        db.session.add(new_post)
        db.session.commit()

        flash("Post created successfully.")
        return redirect(url_for('view_community', community_id=community_id))

    return render_template('create_post.html', communities=communities, selected_community_id=community_id)





@app.route('/create_community', methods=['GET', 'POST'])
def create_community():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('logout'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        is_anonymous = request.form.get('is_anonymous') == 'on'  # Check if checkbox is checked

        # Prepend "[anon]" to the community name if it's marked as anonymous
        if is_anonymous:
            name = f"[anon] {name}"

        # Assuming `industry_images.get(industry_category_id)` is defined somewhere
        # and `industry_category_id` is fetched as before
        industry_category_id = user.industry.industry_category_id if user.industry else None
        profile_pic_url = industry_images.get(industry_category_id, '/static/images/default_community.png')

        new_community = Community(name=name, description=description, profile_pic_url=profile_pic_url, created_by=user_id, is_anonymous=is_anonymous)
        db.session.add(new_community)
        db.session.commit()

        flash("Community created successfully.")
        return redirect(url_for('view_community', community_id=new_community.id))

    return render_template('create_community.html')






@app.route('/follow/<int:user_id>', methods=['POST'])
def follow(user_id):
    session_user_id = session.get('user_id')
    if not session_user_id:
        # Redirect to login if the user is not logged in
        return redirect(url_for('login'))

    if session_user_id == user_id:
        # Prevent users from following themselves
        flash('You cannot follow yourself!', 'error')
        return redirect(url_for('profile', user_id=user_id))

    user_to_follow = User.query.get(user_id)
    if user_to_follow is None:
        flash('User not found.', 'error')
        return redirect(url_for('index'))

    current_user = User.query.get(session_user_id)
    current_user.follow(user_to_follow)
    db.session.commit()
    flash(f'You are now following {user_to_follow.first_name}.', 'success')
    return redirect(url_for('profile', user_id=user_id))




@app.route('/unfollow/<int:user_id>', methods=['POST'])
def unfollow(user_id):
    session_user_id = session.get('user_id')
    if not session_user_id:
        # Redirect to login if the user is not logged in
        return redirect(url_for('login'))

    if session_user_id == user_id:
        # Prevent users from unfollowing themselves
        flash('You cannot unfollow yourself!', 'error')
        return redirect(url_for('profile', user_id=user_id))

    user_to_unfollow = User.query.get(user_id)
    if user_to_unfollow is None:
        flash('User not found.', 'error')
        return redirect(url_for('index'))

    current_user = User.query.get(session_user_id)
    current_user.unfollow(user_to_unfollow)
    db.session.commit()
    flash(f'You are no longer following {user_to_unfollow.first_name}.', 'success')
    return redirect(url_for('profile', user_id=user_id))


def is_following(self, user):
    return self.followed.filter(followers.c.followed_id == user.id).count() > 0


@app.route('/more_communities/<type>/')
def more_communities(type):
    is_anonymous = type == 'anonymous'
    # Fetch communities and their member counts, including those with 0 members
    top_communities_query = db.session.query(
        Community.id,
        Community.name,
        Community.profile_pic_url,
        Community.description,
        func.coalesce(func.count(user_community_association.c.user_id), 0).label("members_count")
    ).outerjoin(
        user_community_association, user_community_association.c.community_id == Community.id
    ).filter(
        Community.is_anonymous == is_anonymous
    ).group_by(
        Community.id,
        Community.name,
        Community.profile_pic_url,
        Community.description
    ).order_by(
        func.coalesce(func.count(user_community_association.c.user_id), 0).desc()
    ).limit(50).all()

    # Convert query results to dictionaries for easier access in the template
    communities_info = [
        {'id': id_, 'name': name, 'profile_pic_url': profile_pic_url, 'description': description, 'members_count': members_count}
        for id_, name, profile_pic_url, description, members_count in top_communities_query
    ]

    return render_template('more_communities.html', communities=communities_info, is_anonymous=is_anonymous)


# Flask route example
@app.route('/get_display_name/<community_id>')
def get_display_name(community_id):
    community = Community.query.get(community_id)  # Assuming you have a model called Community
    is_anonymous = community.is_anonymous
    if is_anonymous:
        display_name = current_user.display_name(True)
    else:
        display_name = current_user.display_name(False)
    return jsonify(display_name=display_name)



@app.route('/user_leaderboard')
def user_leaderboard():
    top_users_query = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        User.profile_pic_url,
        User.karma
    ).order_by(User.karma.desc()).limit(10).all()  # Fetch the top 10 users by karma

    # Convert query results to dictionaries
    top_users_info = [
        {'id': id_, 'first_name': first_name, 'last_name': last_name, 'profile_pic_url': profile_pic_url, 'karma': karma}
        for id_, first_name, last_name, profile_pic_url, karma in top_users_query
    ]

    return render_template('user_leaderboard.html', top_users=top_users_info)



@app.route('/communities')
def communities():
    # Fetch top 10 non-anonymous community IDs and member counts
    non_anon_community_info = db.session.query(
        Community.id,
        func.count(user_community_association.c.user_id).label("members_count")
    ).join(
        user_community_association, user_community_association.c.community_id == Community.id
    ).filter(
        Community.is_anonymous == False
    ).group_by(
        Community.id
    ).order_by(
        func.count(user_community_association.c.user_id).desc()
    ).limit(10).all()

    # Fetch top 10 anonymous community IDs and member counts
    anon_community_info = db.session.query(
        Community.id,
        func.count(user_community_association.c.user_id).label("members_count")
    ).join(
        user_community_association, user_community_association.c.community_id == Community.id
    ).filter(
        Community.is_anonymous == True
    ).group_by(
        Community.id
    ).order_by(
        func.count(user_community_association.c.user_id).desc()
    ).limit(10).all()


    top_users_by_karma = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        User.profile_pic_url,
        User.karma
    ).order_by(
        User.karma.desc()
    ).limit(10).all()


    # Extract community IDs
    non_anon_community_ids = [info[0] for info in non_anon_community_info]
    anon_community_ids = [info[0] for info in anon_community_info]

    # Fetch full Community objects based on IDs
    non_anon_communities = Community.query.filter(Community.id.in_(non_anon_community_ids)).all()
    anon_communities = Community.query.filter(Community.id.in_(anon_community_ids)).all()

    # Sort communities based on the order of IDs in community_ids
    non_anon_communities_sorted = sorted(non_anon_communities, key=lambda x: non_anon_community_ids.index(x.id))
    anon_communities_sorted = sorted(anon_communities, key=lambda x: anon_community_ids.index(x.id))
    topics = Interest.query.all()

    return render_template('communities.html', non_anon_communities=non_anon_communities_sorted, anon_communities=anon_communities_sorted, top_users_by_karma=top_users_by_karma, topics=topics)



@app.route('/leaderboard/<interest_id>')
def leaderboard(interest_id):
    # Fetch the interest based on interest_id
    interest = Interest.query.get_or_404(interest_id)
    
    top_communities_query = db.session.query(
        Community.id,
        Community.name,
        Community.profile_pic_url,
        Community.description,
        func.count(user_community_association.c.user_id).label("members_count")
    ).outerjoin(
        user_community_association, user_community_association.c.community_id == Community.id
    ).join(
        Community.interests
    ).filter(
        Interest.id == interest_id
    ).group_by(
        Community.id,
        Community.name,
        Community.profile_pic_url,
        Community.description
    ).order_by(
        func.count(user_community_association.c.user_id).desc()
    ).limit(10).all()

    # Convert query results to dictionaries
    top_communities_info = [
        {'id': id_, 'name': name, 'profile_pic_url': profile_pic_url, 'description': description, 'members_count': members_count}
        for id_, name, profile_pic_url, description, members_count in top_communities_query
    ]

    return render_template('leaderboard.html', interest=interest, top_communities=top_communities_info)



@app.route('/join_communities', methods=['POST'])
def join_communities():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))  # Redirect to login if no user is logged in

    selected_community_ids = request.form.getlist('selected_communities[]')
    user = User.query.get_or_404(user_id)

    for community_id in selected_community_ids:
        community = Community.query.get(community_id)
        if community not in user.communities:
            user.communities.append(community)
            db.session.commit()
            flash(f"You have successfully joined {community.name}.", "success")
        else:
            flash(f"You are already a member of {community.name}.", "info")

    return redirect(url_for('show_feed'))  # Redirect to a main feed or dashboard



@app.route('/join_community/<int:community_id>', methods=['POST'])
def join_community(community_id):
    if 'user_id' not in session:
        flash("You must be logged in to join a community.", "danger")
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)
    community = Community.query.get(community_id)

    # Check if we are in the signup process
    if 'signup_process' in session:
        # Temporary storage for joined communities during signup
        joined_communities = session.get('joined_communities', set())

        if community_id not in joined_communities:
            # Add community to temporary storage instead of directly associating it with the user
            joined_communities.add(community_id)
            session['joined_communities'] = joined_communities  # Update session

            flash(f"You have successfully joined {community.name}.", "success")
        else:
            flash(f"You are already a member of {community.name}.", "info")

        return redirect(url_for('view_community', community_id=community.id))
    else:
        if community not in user.communities:
            user.communities.append(community)
            db.session.commit()
            flash(f"You have successfully joined {community.name}.", "success")
        else:
            flash(f"You are already a member of {community.name}.", "info")

        return redirect(url_for('view_community', community_id=community.id))





#for interests
@app.route('/api/interests/<int:category_id>')
def get_interests_by_category(category_id):
    interests = Interest.query.filter_by(interest_category_id=category_id).all()
    interest_list = [{'id': interest.id, 'name': interest.name} for interest in interests]
    return jsonify(interest_list)

@app.route('/api/search_interests')
def search_interests():
    search_term = request.args.get('term', '').lower()
    interests = Interest.query.filter(Interest.name.ilike(f'%{search_term}%')).all()
    interest_list = [{'id': interest.id, 'name': interest.name} for interest in interests]
    return jsonify(interest_list)

@app.route('/api/interest_categories')
def get_interest_categories():
    categories = InterestCategory.query.all()
    category_list = [{'id': category.id, 'name': category.name} for category in categories]
    return jsonify(category_list)


#for industries
@app.route('/api/industries/<int:category_id>')
def get_industries_by_category(category_id):
    industries = Industry.query.filter_by(industry_category_id=category_id).all()
    industry_list = [{'id': industry.id, 'name': industry.name} for industry in industries]
    return jsonify(industry_list)

@app.route('/api/search_industries')
def search_industries():
    search_term = request.args.get('term', '').lower()
    industries = Industry.query.filter(Industry.name.ilike(f'%{search_term}%')).all()
    industry_list = [{'id': industry.id, 'name': industry.name} for industry in industries]
    return jsonify(industry_list)

@app.route('/api/categories')
def get_categories():
    categories = IndustryCategory.query.all()
    category_list = [{'id': category.id, 'name': category.name} for category in categories]
    return jsonify(category_list)



@app.route('/start_direct_conversation/<int:recipient_id>', methods=['POST'])
def start_direct_conversation(recipient_id):
    user_id = session.get('user_id')  # Assuming you have authentication in place
    # Check if a direct conversation already exists
    existing_conversation = Conversation.query.join(UserConversation).filter(
        (UserConversation.user_id == user_id) | (UserConversation.user_id == recipient_id),
        Conversation.id == UserConversation.conversation_id
    ).group_by(Conversation.id).having(db.func.count() == 2).first()

    if not existing_conversation:
        # Create new conversation
        conversation = Conversation()
        db.session.add(conversation)
        db.session.flush()  # To get the conversation.id
        # Link both users to the conversation
        db.session.add_all([
            UserConversation(user_id=user_id, conversation_id=conversation.id),
            UserConversation(user_id=recipient_id, conversation_id=conversation.id)
        ])
        db.session.commit()
        return jsonify({'message': 'Conversation started', 'conversation_id': conversation.id}), 200
    else:
        return jsonify({'message': 'Conversation already exists', 'conversation_id': existing_conversation.id}), 200


@app.route('/start_anonymous_conversation/<int:recipient_id>', methods=['GET', 'POST'])
def start_anonymous_conversation(recipient_id):
    user_id = session.get('user_id')
    if not user_id:
        # User is not logged in, redirect to login page
        return redirect(url_for('login'))
    
    # Check if an anonymous direct conversation already exists
    existing_conversation = Conversation.query.join(UserConversation).filter(
        (UserConversation.user_id == user_id) | (UserConversation.user_id == recipient_id),
        Conversation.is_anonymous == True,
        Conversation.id == UserConversation.conversation_id
    ).group_by(Conversation.id).having(db.func.count() == 2).first()

    if not existing_conversation:
        # Create a new anonymous conversation
        conversation = Conversation(is_anonymous=True)
        db.session.add(conversation)
        db.session.flush()  # To get the conversation.id immediately for use

        # Link both users to the anonymous conversation
        db.session.add_all([
            UserConversation(user_id=user_id, conversation_id=conversation.id),
            UserConversation(user_id=recipient_id, conversation_id=conversation.id)
        ])
        db.session.commit()

        # Return a success message with the conversation ID
        return jsonify({'message': 'Anonymous conversation started', 'conversation_id': conversation.id}), 200
    else:
        # If there is an existing conversation, return its ID
        return jsonify({'message': 'Existing anonymous conversation found', 'conversation_id': existing_conversation.id}), 200




@app.route('/send_message', methods=['POST'])
def send_message():
    user_id = session.get('user_id')  # Ensure the user is authenticated
    if not user_id:
        # Redirect to login page if not authenticated
        return redirect(url_for('login'))

    conversation_id = request.form.get('conversation_id')
    message_body = request.form.get('message')

    if message_body:  # Check if the message is not empty
        message = Message(user_id=user_id, conversation_id=conversation_id, body=message_body)
        db.session.add(message)
        db.session.commit()
        flash('Message sent successfully!')
    else:
        flash('Message cannot be empty.')

    # Redirect back to the conversation view
    return redirect(url_for('get_messages', conversation_id=conversation_id))



@app.route('/messages/<int:conversation_id>')
def get_messages(conversation_id):
    user_id = session.get('user_id')
    messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.sent_at.asc()).all()
    conversation = Conversation.query.get_or_404(conversation_id)

    # Fetch all users in the conversation excluding the current user (optional)
    users_in_conversation = User.query.join(UserConversation).filter(
        UserConversation.conversation_id == conversation_id,
        User.id != user_id  # Remove this condition if you want to include the current user as well
    ).all()

    return render_template('messages.html', 
                           messages=messages, 
                           conversation_id=conversation_id, 
                           users_in_conversation=users_in_conversation, conversation=conversation)




@app.route('/my_messages')
def my_messages():
    user_id = session.get('user_id')
    
    if not user_id:
        return redirect(url_for('login'))

    # This part stays the same - getting the subquery for user conversations with anonymity status
    user_conversations = db.session.query(
        UserConversation.conversation_id,
        Conversation.is_anonymous
    ).join(
        Conversation, UserConversation.conversation_id == Conversation.id
    ).filter(
        UserConversation.user_id == user_id
    ).subquery('user_conversations')

    # Adjusted part: correctly utilizing the subquery for filtering
    # Get the latest message for each conversation the user is part of
    latest_messages = db.session.query(
        Message.conversation_id,
        func.max(Message.sent_at).label('latest_sent_at')
    ).filter(
        Message.conversation_id.in_(db.session.query(user_conversations.c.conversation_id))
    ).group_by(Message.conversation_id).subquery('latest_messages')

    # Get the message details for the latest message of each conversation
    conversations = db.session.query(
        Conversation.id,
        Message.body.label('latest_message'),
        latest_messages.c.latest_sent_at,
        user_conversations.c.is_anonymous
    ).join(
        latest_messages, Conversation.id == latest_messages.c.conversation_id
    ).join(
        Message, and_(
            Message.conversation_id == Conversation.id,
            Message.sent_at == latest_messages.c.latest_sent_at)
    ).join(
        user_conversations, Conversation.id == user_conversations.c.conversation_id
    ).order_by(
        latest_messages.c.latest_sent_at.desc()
    ).all()

    # Now, enhance this data with participants' names
    conversations_with_participants = []
    for conversation in conversations:
        participants = db.session.query(
            User.id, User.first_name, User.last_name, User.burner_username
        ).join(UserConversation, UserConversation.user_id == User.id
        ).filter(UserConversation.conversation_id == conversation.id,
                 User.id != user_id  # Exclude the logged-in user
        ).all()
        
        # Construct a list of participant details
        participant_details = [{
            'id': participant.id,
            'display_name': participant.burner_username if conversation.is_anonymous else f"{participant.first_name} {participant.last_name}",
            'is_anonymous': conversation.is_anonymous
        } for participant in participants]

        # Add participants and anonymity status to the conversation data
        conversations_with_participants.append({
            'id': conversation.id,
            'latest_message': conversation.latest_message,
            'sent_at': conversation.latest_sent_at,
            'participants': participant_details,
            'is_anonymous': conversation.is_anonymous
        })

    return render_template('my_messages.html', conversations=conversations_with_participants)




@app.route('/user/<int:user_id>/posts')
def user_posts(user_id):
    posts = Post.query.filter_by(user_id=user_id).all()
    posts_data = [{'id': post.id, 'title': post.title, 'content': post.content, 'posted_time': post.posted_time} for post in posts]
    return jsonify(posts_data)

@app.route('/user/<int:user_id>/comments')
def user_comments(user_id):
    comments = Comment.query.filter_by(user_id=user_id).all()
    comments_data = [{'id': comment.post_id, 'content': comment.content, 'posted_time': comment.posted_time} for comment in comments]
    return jsonify(comments_data)



@app.route('/burner_edit')
def burner_edit():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = User.query.get(user_id)
    return render_template('edit_burner.html', current_burner_username=user.burner_username)

@app.route('/edit_burner_username', methods=['POST'])
def edit_burner_username():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    new_burner_username = request.form['burner_username']

    # Validation logic here...
    user.burner_username = new_burner_username
    db.session.commit()

    flash('Burner username updated successfully.')
    return redirect(url_for('profile', user_id=user_id))


@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    # Check if the current user is the comment's owner or has the right to delete it
    if comment.user_id == current_user.id:
        comment.is_deleted = True
        db.session.commit()
        flash('Your comment has been deleted.', 'success')
    else:
        flash('You do not have permission to delete this comment.', 'error')
    
    return redirect(url_for('profile'))



def strip_html(value):
    """Remove HTML tags from a string."""
    clean_text = re.sub('<.*?>', '', value)
    return clean_text

app.add_template_filter(strip_html, 'strip_html')


#admin panel and seeder stuff


@app.route('/admin')
def admin_panel():
    return render_template('admin_panel.html')


@app.route('/get_seeders_community/<int:community_id>')
def get_seeders_community(community_id):
    community = Community.query.get(community_id)
    if not community:
        return jsonify({'error': 'Community not found'}), 404

    seeders = [{
        'id': user.id,
        'name': f"{user.first_name} {user.last_name}",
        'profile_picture': user.profile_pic_url
    } for user in community.members if user.seeder]

    return jsonify(seeders)





@app.route('/seeders', methods=['GET'])
def get_seeders():
    # Fetching all seeders and ordering them by id in ascending order
    seeders = User.query.filter_by(seeder=True).order_by(User.id.asc()).all()
    return render_template('seeder_list.html', seeders=seeders)

@app.route('/add_seeder', methods=['GET', 'POST'])
def add_seeder():
    communities = Community.query.all()  # Fetch all communities for selection in the form
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        burner_username = request.form.get('burner_username', None)
        community_ids = request.form.getlist('community_ids')  # Get all selected community IDs

        # Handle file upload for profile picture
        profile_pic = request.files.get('profile_pic')
        if profile_pic and allowed_file(profile_pic.filename):
            filename = secure_filename(profile_pic.filename)
            save_path = os.path.join(app.static_folder, 'images', filename)
            rel_path = os.path.join('/static', 'images', filename).replace('\\', '/')  # Normalize path for URL use
            profile_pic.save(save_path)
            profile_pic_url = rel_path
        else:
            profile_pic_url = '/static/images/default_profile.png'  # Default image if no file is uploaded

        new_seeder = User(first_name=first_name, last_name=last_name, burner_username=burner_username,
                          profile_pic_url=profile_pic_url, seeder=True)
        db.session.add(new_seeder)
        db.session.flush()  # Flush to get the ID if needed before committing

        # Assign communities to the new seeder
        for community_id in community_ids:
            community = Community.query.get(community_id)
            if community:
                new_seeder.communities.append(community)

        db.session.commit()
        return redirect(url_for('admin_panel'))

    return render_template('add_seeder.html', communities=communities)



@app.route('/edit_seeder/<int:id>', methods=['GET', 'POST'])
def edit_seeder(id):
    seeder = User.query.get_or_404(id)
    communities = Community.query.all()  # Fetch all communities
    STATIC_FOLDER = app.static_folder

    if request.method == 'POST':
        seeder.first_name = request.form['first_name']
        seeder.last_name = request.form['last_name']
        seeder.burner_username = request.form.get('burner_username', seeder.burner_username)
        seeder.about_me = request.form.get('about_me', seeder.about_me)
        seeder.karma = int(request.form.get('karma', seeder.karma))

        # Handle file upload for profile picture
        profile_pic = request.files.get('profile_pic')
        if profile_pic and allowed_file(profile_pic.filename):
            filename = secure_filename(profile_pic.filename)
            save_path = os.path.join(STATIC_FOLDER, 'images', filename)
            rel_path = os.path.join('/static', 'images', filename).replace('\\', '/')
            profile_pic.save(save_path)
            seeder.profile_pic_url = rel_path

        # Update community associations
        selected_community_ids = request.form.getlist('community_ids')
        selected_communities = Community.query.filter(Community.id.in_(selected_community_ids)).all()
        seeder.communities = selected_communities

        db.session.commit()
        return redirect(url_for('get_seeders'))

    return render_template('edit_seeder.html', seeder=seeder, communities=communities)




from sqlalchemy import func
from sqlalchemy.sql import distinct
from sqlalchemy import case

@app.route('/seeder_messages')
def seeder_messages():
    

    # Subquery for the latest message per conversation involving a seeder
    latest_message_time = db.session.query(
        Message.conversation_id.label('conversation_id'),
        func.max(Message.sent_at).label('max_sent_at')
    ).join(
        UserConversation, UserConversation.conversation_id == Message.conversation_id
    ).join(
        User, User.id == UserConversation.user_id
    ).filter(
        User.seeder == True
    ).group_by(
        Message.conversation_id
    ).subquery()

    # Fetch all users in each conversation and identify the seeder, showing burner_username if anonymous
    participants_query = db.session.query(
        UserConversation.conversation_id,
        func.array_agg(
            case(
    (Conversation.is_anonymous == True, User.burner_username),
    else_=func.concat(User.first_name, ' ', User.last_name)
)

        ).label('all_participants'),
        func.array_agg(User.seeder).label('seeder_flags'),
        func.array_agg(User.id).label('user_ids'),
        func.array_agg(User.profile_pic_url).label('profile_pics'),
        func.array_agg(Conversation.is_anonymous).label('is_anonymous')  # Fetch anonymity status
    ).join(
        User, User.id == UserConversation.user_id
    ).join(
        Conversation, Conversation.id == UserConversation.conversation_id  # Join with Conversation to access is_anonymous
    ).group_by(
        UserConversation.conversation_id
    ).subquery()


    # Join to get the actual message details along with participant info
    conversations = db.session.query(
        Conversation.id.label('conversation_id'),
        Message.body.label('latest_message'),
        Message.read.label('message_read'),  # Include read status of the message
        latest_message_time.c.max_sent_at.label('max_sent_at'),
        participants_query.c.all_participants,
        participants_query.c.seeder_flags,
        participants_query.c.user_ids,
        participants_query.c.profile_pics
    ).join(
        latest_message_time, Conversation.id == latest_message_time.c.conversation_id
    ).join(
        Message, and_(
            Message.conversation_id == latest_message_time.c.conversation_id,
            Message.sent_at == latest_message_time.c.max_sent_at
        )
    ).join(
        participants_query, participants_query.c.conversation_id == Conversation.id
    ).order_by(
        latest_message_time.c.max_sent_at.desc()
    ).all()


    # Adjust the final query to pass anonymity status
    conversations = db.session.query(
        Conversation.id.label('conversation_id'),
        Message.body.label('latest_message'),
        Message.read.label('message_read'),  # Include read status of the message
        latest_message_time.c.max_sent_at.label('max_sent_at'),
        participants_query.c.all_participants,
        participants_query.c.seeder_flags,
        participants_query.c.user_ids,
        participants_query.c.profile_pics,
        participants_query.c.is_anonymous  # Include anonymity flag
    ).join(
        latest_message_time, Conversation.id == latest_message_time.c.conversation_id
    ).join(
        Message, and_(
            Message.conversation_id == latest_message_time.c.conversation_id,
            Message.sent_at == latest_message_time.c.max_sent_at
        )
    ).join(
        participants_query, participants_query.c.conversation_id == Conversation.id
    ).order_by(
        latest_message_time.c.max_sent_at.desc()
    ).all()

    # Modify the structure data loop to account for anonymity
    conversations_with_details = []
    for conv in conversations:
        participants = []
        seeder_name = None
        seeder_id = None
        seeder_pic = None
        other_participants = []
        other_pics = []
        is_anonymous = conv.is_anonymous[0]  # Assume all flags are the same per conversation

        for name, seeder, user_id, pic in zip(conv.all_participants, conv.seeder_flags, conv.user_ids, conv.profile_pics):
            if seeder:
                seeder_name = name
                seeder_id = user_id
                seeder_pic = pic
            else:
                other_participants.append(name)
                other_pics.append(pic)

        conversations_with_details.append({
            'id': conv.conversation_id,
            'latest_message': conv.latest_message,
            'latest_sent_at': conv.max_sent_at,
            'message_read': conv.message_read,
            'seeder': {'name': seeder_name, 'id': seeder_id, 'pic': seeder_pic},
            'other_participants': other_participants,
            'other_pics': other_pics,
            'is_anonymous': is_anonymous  # Include this to handle display logic in template
        })

    return render_template('seeder_messages.html', conversations=conversations_with_details)



@app.route('/messages_admin/<int:conversation_id>')
def get_messages_admin(conversation_id):
    messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.sent_at.asc()).all()
    conversation = Conversation.query.get_or_404(conversation_id)

    # Fetch all users in the conversation
    users_in_conversation = User.query.join(UserConversation).filter(
        UserConversation.conversation_id == conversation_id
    ).all()

    # Attempt to find a seeder in the conversation
    seeder = next((user for user in users_in_conversation if user.seeder), None)

    # Check if a seeder was found and pass the seeder's user_id, otherwise pass None
    seeder_id = seeder.id if seeder else None

    return render_template('messages_admin.html', 
                           messages=messages, 
                           conversation_id=conversation_id, 
                           users_in_conversation=users_in_conversation, 
                           conversation=conversation,
                           seeder_id=seeder_id)



@app.route('/compose_message', methods=['GET', 'POST'])
def compose_message():
    if request.method == 'POST':
        seeder_id = request.form['seeder_id']
        user_identifier = request.form['user_identifier']
        message = request.form['message']
        
        # Check if the identifier includes a space, suggesting it's a full name
        if " " in user_identifier:
            # Split the identifier into first and last name
            first_name, last_name = user_identifier.split(maxsplit=1)
            user = User.query.filter_by(first_name=first_name, last_name=last_name, seeder=False).first()
            is_anonymous = False
        else:
            user = User.query.filter_by(burner_username=user_identifier, seeder=False).first()
            is_anonymous = True
        
        if user:
            # Create the conversation
            conversation = Conversation(is_anonymous=is_anonymous)
            db.session.add(conversation)
            db.session.commit()
            
            # Link the user and the seeder to the conversation
            db.session.add_all([
                UserConversation(user_id=user.id, conversation_id=conversation.id),
                UserConversation(user_id=seeder_id, conversation_id=conversation.id)
            ])
            
            # Add the initial message
            new_message = Message(body=message, user_id=seeder_id, conversation_id=conversation.id)
            db.session.add(new_message)
            db.session.commit()
        
        return redirect(url_for('seeder_messages'))
    else:
        seeders = User.query.filter_by(seeder=True).order_by(User.first_name, User.last_name).all()
        users = User.query.filter_by(seeder=False).order_by(User.first_name, User.last_name).all()
        return render_template('compose_message.html', seeders=seeders, users=users)





@app.route('/send_message_admin', methods=['POST'])
def send_message_admin():
    conversation_id = request.form.get('conversation_id')
    user_id = request.form.get('user_id')  # Get user_id from form
    message_body = request.form.get('message')

    # Validate user_id
    if not user_id.isdigit():
        flash('Invalid user ID provided.')
        return redirect(url_for('get_messages_admin', conversation_id=conversation_id))

    # Fetch all unread messages from this conversation and mark them as read
    unread_messages = Message.query.filter_by(conversation_id=conversation_id, read=False).all()
    for message in unread_messages:
        message.read = True

    # Check if the message is not empty
    if message_body:
        message = Message(user_id=int(user_id), conversation_id=conversation_id, body=message_body, read=True)
        db.session.add(message)
        db.session.commit()  # Commit changes including the new message and updated read statuses
        flash('Message sent successfully!')
    else:
        flash('Message cannot be empty.')

    return redirect(url_for('get_messages_admin', conversation_id=conversation_id))



@app.route('/seeder_review', defaults={'index': 0})
@app.route('/seeder_review/<int:index>')
def seeder_review(index):
    seeders = User.query.filter_by(seeder=True).all()
    if not seeders:
        return "No seeders found", 404

    # Handling boundary conditions
    if index < 0:
        index = 0
    elif index >= len(seeders):
        index = len(seeders) - 1

    seeder = seeders[index]
    next_index = index + 1 if index < len(seeders) - 1 else 0
    prev_index = index - 1 if index > 0 else len(seeders) - 1

    return render_template('seeder_review.html', seeder=seeder, next_index=next_index, prev_index=prev_index)


@app.route('/community_overview')
def community_overview():
    communities = Community.query.all()
    return render_template('community_overview.html', communities=communities)

@app.route('/ai_generator_community')
def ai_generator_community():
    communities = Community.query.all()
    return render_template('ai_generator_community.html', communities=communities)


from sqlalchemy.orm import joinedload

from flask import request

@app.route('/ai_generator_prompts')
def ai_generator_prompts():
    community_id = request.args.get('community_id', type=int)
    if community_id:
        prompts = AIPrompt.query.options(joinedload(AIPrompt.community)).filter_by(community_id=community_id).order_by(AIPrompt.community_id).all()
    else:
        prompts = AIPrompt.query.options(joinedload(AIPrompt.community)).order_by(AIPrompt.community_id).all()

    for prompt in prompts:
        job = scheduler.get_job(str(prompt.id))
        if job:
            prompt.next_run_time = job.next_run_time
        else:
            prompt.next_run_time = None

    communities = Community.query.order_by(Community.name).all()  # Load communities for dropdown
    return render_template('ai_generator_prompts.html', prompts=prompts, communities=communities)




@app.route('/ai_generator_prompts_community')
def ai_generator_prompts_community():
    
    # Fetch communities with prompt counts and sort by the number of prompts
    communities = db.session.query(
        Community.id, 
        Community.name, 
        Community.profile_pic_url, 
        Community.description, 
        db.func.count(AIPrompt.id).label('prompt_count')
    ).outerjoin(AIPrompt, Community.id == AIPrompt.community_id
    ).group_by(Community.id
    ).order_by(db.desc('prompt_count')
    ).all()

    # Prepare job information
    community_jobs = []
    for community in communities:
        job_id = f"community_{community.id}"
        job = scheduler.get_job(job_id)
        if job:
            next_run_time = job.next_run_time
        else:
            next_run_time = "No Job Scheduled"
        community_jobs.append({
            'id': community.id,
            'name': community.name,
            'profile_pic_url': community.profile_pic_url,
            'description': community.description,
            'prompt_count': community.prompt_count,
            'next_run_time': next_run_time
        })

    return render_template('ai_generator_prompts_community.html', communities=community_jobs)




@app.route('/queue_posts/<int:community_id>')
def queue_posts(community_id):
    community = Community.query.get_or_404(community_id)
    posts = RecycledPost.query.filter_by(community_id=community_id).all()
    job_id = f'schedule_posting_{community_id}'
    job = scheduler.get_job(job_id)
    next_run_time = job.next_run_time if job else None
    
    return render_template('queue_posts.html', community=community, posts=posts, next_run_time=next_run_time)


@app.route('/post_recycled/<int:recycled_post_id>', methods=['GET', 'POST'])
def post_recycled(recycled_post_id):
    recycled_post = RecycledPost.query.get_or_404(recycled_post_id)
    seeders = User.query.join(user_community_association).filter(
        user_community_association.c.community_id == recycled_post.community_id,
        User.seeder == True
    ).all()

    if not seeders:
        return jsonify({"message": "No seeders available."}), 400

    seeder = random.choice(seeders)
    new_post = Post(
        title=recycled_post.title,
        content=recycled_post.content,
        user_id=seeder.id,
        community_id=recycled_post.community_id,
        posted_time=datetime.utcnow(),
        image_filename=recycled_post.image_filename
    )
    db.session.add(new_post)
    db.session.commit()
    return jsonify({"message": "Recycled post published successfully."}), 200





@app.route('/add_recycled_post', methods=['GET', 'POST'])
def add_recycled_post():
    communities = Community.query.all()
    title = request.args.get('title', '')
    content = request.args.get('content', '')
    image_url = request.args.get('image_url', '')  # Handles an image URL if passed via GET

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        community_id = request.form.get('community_id')
        image_filename = request.form.get('image_filename')  # Get the filename from the hidden input if passed

        # If there's no filename via hidden input, check for uploaded image
        if not image_filename:
            image = request.files.get('image')
            if image and allowed_file(image.filename):
                image_filename = secure_filename(image.filename)
                image_path = os.path.join('static/images/posts', image_filename)
                image.save(image_path)
            else:
                # Handle case where no image is provided at all
                image_filename = None

        new_post = RecycledPost(
            title=title,
            content=content,
            community_id=community_id,
            image_filename=image_filename  # Use the existing or newly uploaded image filename
        )
        db.session.add(new_post)
        db.session.commit()
        flash("Post added to the queue.")
        return redirect(url_for('queue_posts', community_id=community_id))

    # Render form with possible pre-filled data if accessed via GET with parameters
    return render_template('add_recycled_post.html', communities=communities, title=title, content=content, image_url=image_url)


@app.route('/add_recycled_post_modal', methods=['POST'])
def add_recycled_post_modal():
    try:
        title = request.form.get('title')
        content = request.form.get('content')
        community_id = request.form.get('community_id')
        image_filename = request.form.get('image_filename').strip()  # Ensure there's no leading/trailing whitespace

        # Make sure filename does not contain any directory path
        image_filename = os.path.basename(image_filename)

        # Calculate the source and target paths using os.path.join consistently
        source_path = os.path.join(app.root_path, 'static', 'images', 'content', image_filename)
        target_path = os.path.join(app.root_path, 'static', 'images', 'posts', image_filename)

        # Debugging output
        print(f"Attempting to move from {source_path} to {target_path}")

        # Move the file from the temporary to the permanent directory
        if os.path.exists(source_path):
            os.rename(source_path, target_path)
        else:
            return jsonify({'error': 'Source file does not exist', 'source_path': source_path}), 400

        # Create and save the new recycled post
        new_post = RecycledPost(
            title=title,
            content=content,
            community_id=community_id,
            image_filename=image_filename  # Save only the filename
        )
        db.session.add(new_post)
        db.session.commit()

        # Redirect to the post recycler page
        return redirect(url_for('reddit_scraper'))

    except Exception as e:
        return jsonify({'error': str(e)}), 500








@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    post = RecycledPost.query.get_or_404(post_id)
    communities = Community.query.all()

    if request.method == 'POST':
        post.title = request.form.get('title')
        post.content = request.form.get('content')
        post.community_id = request.form.get('community_id')  # Assuming you want to allow changing the community

        image = request.files.get('image')
        if image and allowed_file(image.filename):
            image_filename = secure_filename(image.filename)
            image_path = os.path.join('static/images/posts', image_filename)
            image.save(image_path)
            post.image_filename = image_filename  # Update the image file name in the database

        db.session.commit()
        flash("Post updated successfully.")
        return redirect(url_for('queue_posts', community_id=post.community_id))

    return render_template('edit_post.html', post=post, communities=communities)


from datetime import datetime, timezone


def time_until(dt):
    utc_now = datetime.now(timezone.utc)
    if dt:
        return int((dt - utc_now).total_seconds() / 60)
    return "N/A"


app.jinja_env.filters['time_until'] = time_until

@app.route('/queue_prompts/<int:community_id>')
def queue_prompts(community_id):
    community = Community.query.get_or_404(community_id)
    prompts = AIPrompt.query.filter_by(community_id=community_id).all()
    
    for prompt in prompts:
        job = scheduler.get_job(str(prompt.id))
        if job:
            prompt.next_run_time = job.next_run_time
        else:
            prompt.next_run_time = None
    
    return render_template('queue_prompts.html', community=community, prompts=prompts, datetime=datetime)





from apscheduler.jobstores.base import JobLookupError

@app.route('/delete_prompt/<int:prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    # Retrieve the prompt
    prompt = AIPrompt.query.get_or_404(prompt_id)

    # Attempt to remove the associated job from the scheduler
    try:
        scheduler.remove_job(str(prompt_id))  # Assuming the job ID is the string version of prompt_id
        db.session.delete(prompt)  # Delete the prompt from the database
        db.session.commit()
        message = 'Prompt and associated job deleted successfully.'
        status_code = 200
    except JobLookupError:
        # This error occurs if the job doesn't exist in the scheduler
        db.session.delete(prompt)
        db.session.commit()
        message = 'Prompt deleted successfully, but no associated job was found.'
        status_code = 200
    except Exception as e:
        # Handle unexpected errors
        message = str(e)
        status_code = 500

    return jsonify({'message': message}), status_code



from datetime import datetime, timedelta

@app.route('/add_prompt', methods=['GET', 'POST'])
@app.route('/add_prompt/<int:community_id>', methods=['GET', 'POST'])
def add_prompt(community_id=None):
    community = Community.query.get(community_id) if community_id else None
    communities = Community.query.all()  # Fetch all communities for the dropdown

    if request.method == 'POST':
        community_id = request.form.get('community_id') or community_id
        if not community_id:
            flash("Please select a community.")
            return render_template('add_prompt.html', communities=communities, community=community)

        prompt_text = request.form.get('prompt')
        interval = request.form.get('interval')

        # Create and configure the new prompt object
        if interval.isdigit():
            interval = int(interval)
            new_prompt = AIPrompt(prompt=prompt_text, community_id=community_id, interval_minutes=interval)
            db.session.add(new_prompt)
            db.session.commit()

            # Schedule the job if interval is valid
            if interval > 0:
                scheduler.add_job(
                    func=execute_post_prompt,
                    trigger='interval',
                    minutes=interval,
                    args=[new_prompt.id],
                    next_run_time=datetime.now() + timedelta(minutes=interval),
                    id=str(new_prompt.id)
                )
                flash("Prompt added and scheduled successfully.")
            else:
                flash("Prompt added, but not scheduled due to non-positive interval.")
            return redirect(url_for('ai_generator_prompts'))
        else:
            flash("Invalid interval. Please enter a numeric value.")
    
    return render_template('add_prompt.html', communities=communities, community=community)


@app.route('/add_prompt_community', methods=['GET', 'POST'])
@app.route('/add_prompt_community/<int:community_id>', methods=['GET', 'POST'])
def add_prompt_community(community_id=None):
    community = Community.query.get(community_id) if community_id else None
    communities = Community.query.all()  # Fetch all communities for the dropdown

    if request.method == 'POST':
        community_id = request.form.get('community_id') or community_id
        if not community_id:
            flash("Please select a community.")
            return render_template('add_prompt_community.html', communities=communities, community=community)

        prompt_text = request.form.get('prompt')
        
        if not prompt_text:
            flash("Please enter a prompt text.")
            return render_template('add_prompt_community.html', communities=communities, community=community)

        # Create the new prompt object
        new_prompt = AIPrompt(prompt=prompt_text, community_id=community_id)
        db.session.add(new_prompt)
        db.session.commit()

        flash("Prompt added successfully.")
        return redirect(url_for('manage_community_job', community_id=community_id))
    
    return render_template('add_prompt_community.html', communities=communities, community=community)


from flask import request, render_template, redirect, url_for, flash

@app.route('/manage_community_job/<int:community_id>', methods=['GET', 'POST'])
def manage_community_job(community_id):
    job_id = f"community_{community_id}"
    job = scheduler.get_job(job_id)
    prompts = AIPrompt.query.filter_by(community_id=community_id).all()  # Fetch prompts for the community

    if request.method == 'POST':
        if 'pause' in request.form:
            job.pause()
            flash('Job has been paused.')
        elif 'resume' in request.form:
            job.resume()
            flash('Job has been resumed.')
        elif 'cancel' in request.form:
            job.remove()
            flash('Job has been cancelled.')
        elif 'update_interval' in request.form:
            interval = int(request.form.get('interval', 0))
            if interval > 0:
                job.reschedule(trigger='interval', minutes=interval)
                flash(f'Job interval has been updated to run every {interval} minutes.')
            else:
                flash('Invalid interval. Please enter a positive number of minutes.')
        elif 'start_job' in request.form:
            interval = int(request.form.get('start_interval', 0))
            if interval > 0:
                scheduler.add_job(
                    func=execute_post_prompt_community,  # Ensure this function is properly defined elsewhere in your code
                    trigger='interval',
                    minutes=interval,
                    args=[community_id],
                    next_run_time=datetime.now() + timedelta(minutes=1),  # Ensure this time is suitable for your needs
                    id=job_id
                )
                flash(f'Job for community {community_id} started, running every {interval} minutes.')
            else:
                flash('Invalid interval. Please enter a positive number of minutes.')

        return redirect(url_for('manage_community_job', community_id=community_id))

    return render_template('manage_community_job.html', job=job, community_id=community_id, prompts=prompts)



from apscheduler.triggers.interval import IntervalTrigger

@app.route('/edit_prompt/<int:prompt_id>', methods=['GET', 'POST'])
def edit_prompt(prompt_id):
    prompt = AIPrompt.query.get_or_404(prompt_id)
    if request.method == 'POST':
        prompt.prompt = request.form.get('prompt')
        new_interval = int(request.form.get('interval'))

        # Check if interval has changed
        if prompt.interval_minutes != new_interval:
            prompt.interval_minutes = new_interval
            # Reschedule the job
            job_id = str(prompt_id)
            scheduler.reschedule_job(job_id, trigger=IntervalTrigger(minutes=new_interval))

        db.session.commit()
        flash("Prompt and schedule updated successfully.")
        return redirect(url_for('queue_prompts', community_id=prompt.community_id))

    return render_template('edit_prompt.html', prompt=prompt)



from apscheduler.jobstores.base import JobLookupError

@app.route('/pause_prompt/<int:prompt_id>', methods=['POST'])
def pause_prompt(prompt_id):
    try:
        scheduler.pause_job(str(prompt_id))
        flash('Prompt paused successfully', 'success')
    except JobLookupError:
        prompt = AIPrompt.query.get_or_404(prompt_id)
        next_run_time = datetime.now() + timedelta(minutes=prompt.interval_minutes)
        scheduler.add_job(
            func=execute_post_prompt,  # Update this to the correct function path
            trigger='interval',
            minutes=prompt.interval_minutes,
            next_run_time=next_run_time,
            id=str(prompt.id)
        )
        flash('No active job found. Job restarted and paused.', 'info')
    return redirect(url_for('queue_prompts', community_id=request.args.get('community_id')))


@app.route('/resume_prompt/<int:prompt_id>', methods=['POST'])
def resume_prompt(prompt_id):
    prompt = AIPrompt.query.get_or_404(prompt_id)
    next_run_time = datetime.now() + timedelta(minutes=prompt.interval_minutes)
    try:
        scheduler.resume_job(str(prompt_id))
        flash('Prompt resumed successfully', 'success')
    except JobLookupError:
        # If the job does not exist, re-add it to the scheduler
        scheduler.add_job(
            func=execute_post_prompt,  # Direct reference to the function
            trigger='interval',
            minutes=prompt.interval_minutes,
            args=[prompt_id],  # Ensure args is a list containing prompt_id
            next_run_time=next_run_time,
            id=str(prompt_id)
        )
        flash('No active job found. Job restarted successfully.', 'success')
    return redirect(url_for('queue_prompts', community_id=request.args.get('community_id')))






@app.route('/post_prompt/<int:prompt_id>', methods=['POST'])
def post_prompt(prompt_id):
    prompt = AIPrompt.query.get_or_404(prompt_id)
    community = Community.query.get_or_404(prompt.community_id)
    seeders = User.query.join(user_community_association).filter(
        user_community_association.c.community_id == community.id,
        User.seeder == True
    ).all()

    if not seeders:
        return jsonify({"message": "No seeders available."}), 400

    seeder = random.choice(seeders)
    custom_prompt = f"{prompt.prompt} About the seeder: {seeder.about_me}."


    # Here, include the actual call to the AI model, which now uses the enriched prompt
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": custom_prompt}]
        )
        generated_text = response.choices[0].message.content
        parts = generated_text.split('\n\n', 1)
        title = parts[0].strip() if parts else ""
        content = parts[1].strip() if len(parts) > 1 else ""

        new_post = Post(
            title=title,
            content=content,
            user_id=seeder.id,
            community_id=community.id,
            posted_time=datetime.utcnow(),
            image_filename=None  # Update if using images
        )
        db.session.add(new_post)
        db.session.commit()
        return jsonify({"message": "AI-generated post published successfully."}), 200
    except Exception as e:
        print(f'Failed to generate post: {str(e)}')
        return jsonify({"message": f"Failed to generate post: {str(e)}"}), 500



def execute_post_prompt(prompt_id):
    with app.app_context():  # Ensure you have access to Flask context
        print(f"Starting to execute the prompt with ID: {prompt_id}")
        prompt = AIPrompt.query.get_or_404(prompt_id)
        community = Community.query.get_or_404(prompt.community_id)
        seeders = User.query.join(user_community_association).filter(
            user_community_association.c.community_id == community.id,
            User.seeder == True
        ).all()

        if not seeders:
            print("No seeders available")
            return

        seeder = random.choice(seeders)
        custom_prompt = f"{prompt.prompt} About the seeder: {seeder.about_me}. " \
                        f"Community title: {community.name}. Community description: {community.description}."

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": custom_prompt}]
            )
            generated_text = response.choices[0].message.content
            parts = generated_text.split('\n\n', 1)
            title = parts[0].strip() if parts else ""
            content = parts[1].strip() if len(parts) > 1 else ""

            new_post = Post(
                title=title,
                content=content,
                user_id=seeder.id,
                community_id=community.id,
                posted_time=datetime.utcnow(),
                image_filename=None  # Update if using images
            )
            db.session.add(new_post)
            db.session.commit()
            print("AI-generated post published successfully")
        except Exception as e:
            print(f'Failed to generate post: {str(e)}')



def execute_post_prompt_community(community_id):
    with app.app_context():  # Ensure you have access to Flask context
        print(f"Starting to execute a prompt for community ID: {community_id}")
        
        # Retrieve all prompts for the community
        prompts = AIPrompt.query.filter_by(community_id=community_id).all()
        if not prompts:
            print("No prompts available for this community.")
            return

        # Randomly select a prompt
        prompt = random.choice(prompts)
        
        community = Community.query.get_or_404(community_id)
        seeders = User.query.join(user_community_association).filter(
            user_community_association.c.community_id == community.id,
            User.seeder == True
        ).all()

        if not seeders:
            print("No seeders available")
            return

        seeder = random.choice(seeders)
        custom_prompt = f"{prompt.prompt} About the seeder: {seeder.about_me}. " \
                        f"Community title: {community.name}. Community description: {community.description}."

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": custom_prompt}]
            )
            generated_text = response.choices[0].message.content
            parts = generated_text.split('\n\n', 1)
            title = parts[0].strip() if parts else ""
            content = parts[1].strip() if len(parts) > 1 else ""

            new_post = Post(
                title=title,
                content=content,
                user_id=seeder.id,
                community_id=community.id,
                posted_time=datetime.utcnow(),
                image_filename=None  # Update if using images
            )
            db.session.add(new_post)
            db.session.commit()
            print("AI-generated post published successfully")
        except Exception as e:
            print(f'Failed to generate post: {str(e)}')




@app.template_filter('truncate_lines')
def truncate_lines(text, max_lines=7):
    lines = text.split('<br>')  # Adjust this if your line breaks are different
    if len(lines) > max_lines:
        return '<br>'.join(lines[:max_lines]) + '...'
    return text


@app.route('/make_concise', methods=['POST'])
def make_concise():
    
    data = request.get_json()
    content = data['content']
    prompt_text = data['prompt_text'] 

    combined_prompt = f"I want you to take this piece of text: {content} and {prompt_text}"

    try:
        # Assuming you have the OpenAI client setup with the key as shown previously
        response = client.chat.completions.create(
            model="gpt-4o",  # Adjust model as necessary
            messages=[
                {"role": "system", "content": combined_prompt}
            ]
        )
        concise_text = response.choices[0].message.content.strip()
        
        return jsonify({'concise_text': concise_text})
    except Exception as e:
        print(str(e))
        return jsonify({'error': str(e)}), 500


def scrape_subreddits():
    with app.app_context():
        subreddits = Subreddits.query.filter_by(content_type='images').all()
        for subreddit in subreddits:
            results = scrape_reddit_posts_2(subreddit.prompt, 'images', 100, 'new')

#start the thread up

from threading import Thread



@app.route('/start_scraping')
def start_scraping():
    thread = Thread(target=scrape_subreddits)
    thread.start()
    return jsonify({'status': 'Scraping started'}), 200



@app.route('/redfeed')
def redfeed():
    # Assuming you want to see only the newest 100 images from all subreddits
    posts = RedditPost.query.order_by(RedditPost.id.desc()).limit(100).all()
    return render_template('redfeed.html', posts=posts)




@app.route('/reddit_scraper/', methods=['GET', 'POST'])
def reddit_scraper():
    communities = Community.query.options(joinedload(Community.subreddits)).all()  # Preload subreddits with communities
    if request.method == 'POST':
        clear_image_directory()
        selected_community_id = request.form.get('community_id')
        subreddit_name = request.form.get('subreddit')  # Direct input of subreddit name
        number_of_posts = int(request.form.get('number_of_posts', 100))
        sort_option = request.form.get('sort_option', 'hot')

        session_data = {
            'subreddit_name': subreddit_name,
            'number_of_posts': number_of_posts,
            'sort_option': sort_option,
            'selected_community_id': selected_community_id
        }
        session.update(session_data)

        results = []
        if subreddit_name:
            results = scrape_reddit_posts(subreddit_name, number_of_posts, sort_option)
        elif selected_community_id:
            community = Community.query.get(selected_community_id)
            for subreddit in community.subreddits:
                results.extend(scrape_reddit_posts(subreddit.prompt, number_of_posts, sort_option))
        
        if results:
            flash(f"Scraped {len(results)} posts")

        return render_template('reddit_scraper.html', results=results, communities=communities, session=session)

    return render_template('reddit_scraper.html', communities=communities, session=session)


def post_exists(title, reddit_post_id=None):
    query = db.session.query(Post)
    if reddit_post_id:
        query = query.filter(Post.reddit_post_id == reddit_post_id)
    else:
        query = query.filter(Post.title == title)
    
    exists_in_posts = query.first() is not None

    # Check in scheduled posts
    sched_query = db.session.query(ScheduledPost)
    if reddit_post_id:
        sched_query = sched_query.filter(ScheduledPost.reddit_post_id == reddit_post_id)
    else:
        sched_query = sched_query.filter(ScheduledPost.title == title)

    exists_in_scheduled = sched_query.first() is not None

    return exists_in_posts or exists_in_scheduled


def scrape_reddit_posts(subreddit_name, limit, sort_option):
    reddit = praw.Reddit(
        client_id='i-SqiFyPh8Jgk34GFXwLCw',
        client_secret='mbAJH8RDW3G3S7L-gLb9HIUwj_on-g',
        user_agent='script:subreddit image and text downloader:v1.0 (by /u/DoodleChoco6642)'
    )

    subreddit = reddit.subreddit(subreddit_name)
    fetch_method = {
        'hot': subreddit.hot,
        'top': subreddit.top,
        'new': subreddit.new
    }.get(sort_option, subreddit.hot)

    results = []
    for submission in fetch_method(limit=limit):
        if not post_exists(submission.title, submission.id):  # Ensure you have a function to check for duplicate posts
            if submission.url.endswith(('jpg', 'jpeg', 'png')) and not submission.is_self:
                file_name = f"{submission.id}.jpg"
                local_filename = os.path.join('static', 'images', 'content', file_name)
                download_image(submission.url, local_filename)  # Make sure download_image handles errors properly

                web_path = os.path.join('images/content', file_name)
                web_path = web_path.replace(os.sep, '/')
                result = {
                    'subreddit': subreddit_name,
                    'image': web_path,
                    'title': submission.title,
                    'content': submission.selftext,
                    'reddit_post_id': submission.id
                }
                results.append(result)
            elif submission.is_self:
                # For text posts, just check it's not one of the image extensions
                if not submission.url.endswith(('jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff')):
                    results.append({
                        'subreddit': subreddit_name,
                        'title': submission.title,
                        'content': submission.selftext,
                        'image': None,  # No image associated with text posts
                        'reddit_post_id': submission.id
                    })

    return results



def scrape_reddit_posts_2(subreddit_name, content_type, limit, sort_option):
    reddit = praw.Reddit(
        client_id='i-SqiFyPh8Jgk34GFXwLCw',
        client_secret='mbAJH8RDW3G3S7L-gLb9HIUwj_on-g',
        user_agent='script:subreddit image downloader:v1.0 (by /u/DoodleChoco6642)'
    )
    subreddit = reddit.subreddit(subreddit_name)
    fetch_method = {
        'hot': subreddit.hot,
        'top': subreddit.top,
        'new': subreddit.new
    }.get(sort_option, subreddit.hot)

    results = []
    for submission in fetch_method(limit=limit):
        if not RedditPost.query.filter_by(reddit_post_id=submission.id).first():
            if content_type == 'images' and submission.url.endswith(('jpg', 'jpeg', 'png')):
                file_name = f"{submission.id}.jpg"
                local_filename = os.path.join('static', 'images', 'content', file_name)
                download_image(submission.url, local_filename)

                web_path = os.path.join('images/content', file_name)
                web_path = web_path.replace(os.sep, '/')
                reddit_post = RedditPost(
                    title=submission.title,
                    content=submission.selftext,
                    image_url=web_path,
                    reddit_post_id=submission.id,
                    subreddit_name=subreddit_name
                )
                db.session.add(reddit_post)

                results.append(reddit_post)
                db.session.commit()
            elif content_type == 'text' and submission.is_self:
                if not submission.url.endswith(('jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff')):
                    reddit_post = RedditPost(
                        title=submission.title,
                        content=submission.selftext,
                        reddit_post_id=submission.id,
                        subreddit_name=subreddit_name
                    )
                    db.session.add(reddit_post)
                    
                    results.append(reddit_post)
                    db.session.commit()

    
    return results







def download_image(image_url, local_filename):
    """Utility function to download and save an image."""
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(local_filename, 'wb') as f:
            f.write(response.content)
    return local_filename


def clear_image_directory(directory='static/images/content'):
    """Clears all files in the specified directory."""
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))



def schedule_random_post(community_id):
    with app.app_context():  # This ensures that the function has access to Flask's context-dependent features
        recycled_posts = RecycledPost.query.filter_by(community_id=community_id).all()
        if not recycled_posts:
            print("No recycled posts available.")
            return

        recycled_post = random.choice(recycled_posts)
        seeders = User.query.join(user_community_association).filter(
            user_community_association.c.community_id == community_id,
            User.seeder == True
        ).all()

        if not seeders:
            print("No seeders available.")
            return

        seeder = random.choice(seeders)
        new_post = Post(
            title=recycled_post.title,
            content=recycled_post.content,
            user_id=seeder.id,
            community_id=community_id,
            posted_time=datetime.utcnow(),
            image_filename=recycled_post.image_filename
        )
        db.session.add(new_post)
        db.session.commit()
        print("Recycled post published successfully.")



from apscheduler.jobstores.base import JobLookupError

@app.route('/set_schedule/<int:community_id>', methods=['POST'])
def set_schedule(community_id):
    interval = int(request.form.get('interval'))
    job_id = f'schedule_posting_{community_id}'

    # Attempt to remove the old job if it exists
    try:
        scheduler.remove_job(job_id)
    except JobLookupError:
        # If the job is not found, no action is needed
        pass

    # Schedule a new job
    scheduler.add_job(
        schedule_random_post, 
        'interval', 
        minutes=interval, 
        args=[community_id], 
        id=job_id
    )

    flash(f"Scheduled random posts every {interval} minutes.")
    return redirect(url_for('queue_posts', community_id=community_id))


@app.route('/stop_schedule/<int:community_id>', methods=['POST'])
def stop_schedule(community_id):
    job_id = f'schedule_posting_{community_id}'
    try:
        scheduler.remove_job(job_id)
        flash("Scheduling stopped successfully.")
    except JobLookupError:
        flash("No active scheduling found.")
    except Exception as e:
        flash(f"Failed to stop scheduling: {str(e)}")
    
    return redirect(url_for('queue_posts', community_id=community_id))



@app.route('/schedule_post', methods=['GET', 'POST'])
def schedule_post():
    communities = Community.query.all()  # Get all communities
    users = User.query.filter(User.seeder == True).all()

    if request.method == 'POST':
        action = request.form.get('action', 'schedule')
        title = request.form['title']
        content = request.form['content']
        user_id = int(request.form['user_id'])
        community_id = int(request.form['community_id'])
        posted_time_str = request.form.get('posted_time')
        image = request.files.get('image')
        existing_image = request.form.get('existing_image')
        reddit_post_id = request.form.get('reddit_post_id')

        image_url = None
        if image and image.filename != '':
            image_filename = secure_filename(image.filename)
            s3_folder = 'posts/'
            bucket_name = 'netwrkproto'
            image_url = upload_file_to_s3(image, bucket_name, s3_folder + image_filename)
        elif existing_image:
            image_filename = os.path.basename(existing_image)
            s3_folder = 'posts/'
            bucket_name = 'netwrkproto'
            content_type, _ = guess_type(image_filename)
            full_path = os.path.join(app.root_path, 'static', 'images', 'content', image_filename)
            with open(full_path, 'rb') as file:
                image_url = upload_file_to_s3(file, bucket_name, s3_folder + image_filename, content_type)

        new_post = Post(title=title, content=content, user_id=user_id, community_id=community_id, image_filename=image_url, reddit_post_id=reddit_post_id)

        if action == 'post_now':
            new_post.posted_time = datetime.utcnow()
            db.session.add(new_post)
            db.session.commit()
            flash('Post made successfully!')
        elif posted_time_str:
            posted_time = datetime.strptime(posted_time_str, '%Y-%m-%dT%H:%M')
            est = pytz.timezone('America/New_York')
            utc = pytz.utc
            posted_time = est.localize(posted_time).astimezone(utc)
            new_post.posted_time = posted_time
            job_id = "post_" + str(uuid.uuid4())
            scheduler.add_job(post_to_community, 'date', run_date=posted_time, args=[new_post], id=job_id)

            new_scheduled_post = ScheduledPost(title=title, reddit_post_id=reddit_post_id, scheduled_time=posted_time, job_id=job_id)
            db.session.add(new_scheduled_post)
            db.session.commit()


            
            flash('Post scheduled successfully!')
        else:
            flash('No post time provided, posting now.')
            new_post.posted_time = datetime.utcnow()
            db.session.add(new_post)
            db.session.commit()

        return redirect(url_for('schedule_post'))

    scheduled_posts = []
    jobs = scheduler.get_jobs()
    for job in jobs:
        if job.id.startswith("post_"):
            post_info = job.args[0]
            scheduled_posts.append({
                'job_id': job.id,
                'run_time': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'title': post_info.title,
                'content': post_info.content
            })

    return render_template('schedule_post.html', communities=communities, users=users, scheduled_posts=scheduled_posts)




def post_to_community(post):

    with app.app_context():
        ScheduledPost.query.filter_by(id=post.id).delete()
        db.session.commit()
        db.session.add(post)
        db.session.commit()


@app.route('/cancel_job/<job_id>', methods=['POST'])
def cancel_job(job_id):
    try:
        scheduler.remove_job(job_id)
        flash('Scheduled post has been successfully canceled.', 'success')
    except JobLookupError:
        flash('Failed to cancel the scheduled post. Job not found.', 'error')
    return redirect(url_for('schedule_post'))


@app.route('/manage_posts')
def manage_posts():
    # Retrieve filter options from query parameters
    show_seeders_only = request.args.get('seeders_only', 'false').lower() == 'true'
    community_id = request.args.get('community_id')

    query = Post.query

    # Filter by seeder posts only
    if show_seeders_only:
        query = query.join(User).filter(User.seeder == True)
    
    # Filter by community if a specific community ID is provided
    if community_id:
        query = query.filter(Post.community_id == community_id)

    # Fetch posts in descending order of the time they were posted
    posts = query.order_by(Post.posted_time.desc()).all()
    communities = Community.query.all()  # Fetch all communities for dropdown

    return render_template('manage_posts.html', posts=posts, communities=communities)


@app.route('/edit_regular_post/<int:post_id>', methods=['GET', 'POST'])
def edit_regular_post(post_id):
    post = Post.query.get_or_404(post_id)
    if request.method == 'POST':
        # Update post details based on form inputs
        post.title = request.form['title']
        post.content = request.form['content']
        db.session.commit()
        flash('Post updated successfully.', 'success')
        return redirect(url_for('manage_posts'))
    
    # Render edit post form template
    return render_template('edit_regular_post.html', post=post)



@app.route('/delete_post/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Post has been successfully deleted.', 'success')
    return redirect(url_for('manage_posts'))


@app.route('/admin/post_comments/<int:post_id>')
def admin_post_comments(post_id):
    post = Post.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.posted_time.desc()).all()
    seeders = User.query.filter_by(seeder=True).all()  # Fetching all seeders for reply options
    return render_template('admin_post_comments.html', post=post, comments=comments, seeders=seeders)



@app.route('/admin/submit_comment/<int:post_id>', methods=['POST'])
def admin_submit_comment(post_id):
    content = request.form.get('comment_content')
    user_id = request.form.get('user_id')  # Seeder's user ID chosen by admin
    parent_id = request.form.get('parent_id', type=int)  # Optional, for replies

    if not content or not user_id:
        flash('Comment content and seeder selection are required.', 'error')
        return redirect(url_for('admin_post_comments', post_id=post_id))

    comment = Comment(content=content, post_id=post_id, user_id=user_id, parent_id=parent_id)
    db.session.add(comment)
    db.session.commit()
    flash('Comment posted successfully.', 'success')
    return redirect(url_for('admin_post_comments', post_id=post_id))



@app.route('/upvote_booster_form')
def upvote_booster_form():
    return render_template('upvote_booster.html')


@app.route('/upvote_booster', methods=['POST'])
def upvote_booster():
    type = request.form.get('type')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    min_upvotes = int(request.form.get('min_upvotes'))
    max_upvotes = int(request.form.get('max_upvotes'))

    query = Post.query if type == 'posts' else Comment.query
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(Post.posted_time >= start_date if type == 'posts' else Comment.posted_time >= start_date)
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        query = query.filter(Post.posted_time <= end_date if type == 'posts' else Comment.posted_time <= end_date)

    items = query.all()
    
    for item in items:
        boost = random.randint(min_upvotes, max_upvotes)
        item.upvotes += boost  # Make sure your model has an 'upvotes' attribute

    db.session.commit()
    flash('Upvotes successfully boosted!', 'success')
    return redirect(url_for('upvote_booster_form'))

@app.route('/manage_communities')
def manage_communities():
    communities = Community.query.all()  # Fetch all community records
    return render_template('manage_communities.html', communities=communities)


@app.route('/add_community', methods=['GET', 'POST'])
def add_community():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        profile_pic = request.files['profile_pic']
        filename = secure_filename(profile_pic.filename)
        profile_pic.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        community = Community(name=name, description=description, profile_pic_url=filename)
        db.session.add(community)
        db.session.commit()
        flash('Community added successfully!')
        return redirect(url_for('manage_communities'))

    return render_template('add_edit_community.html', community=None)


@app.route('/edit_community_admin/<int:community_id>', methods=['GET', 'POST'])
def edit_community_admin(community_id):
    community = Community.query.get_or_404(community_id)
    if request.method == 'POST':
        community.name = request.form['name']
        community.description = request.form['description']
        if 'profile_pic' in request.files:
            profile_pic = request.files['profile_pic']
            if profile_pic.filename:  # Ensure there is a filename
                filename = secure_filename(profile_pic.filename)
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)  # Ensure directory exists
                profile_pic.save(save_path)
                community.profile_pic_url = os.path.join('uploads', filename)  # Adjust according to your needs

        db.session.commit()
        flash('Community updated successfully!')
        return redirect(url_for('manage_communities'))

    return render_template('add_edit_community.html', community=community)


@app.route('/job_manager')
def job_manager():
    jobs = scheduler.get_jobs()
    job_list = [{
        'id': job.id,
        'name': job.name,
        'next_run_time': job.next_run_time,
        'trigger': str(job.trigger)
    } for job in jobs]
    return render_template('job_manager.html', jobs=job_list)

@app.route('/delete_job/<string:job_id>', methods=['POST'])
def delete_job(job_id):
    try:
        # Remove the job from the scheduler
        scheduler.remove_job(job_id)
        # Also, remove the corresponding scheduled post from the database
        ScheduledPost.query.filter_by(job_id=job_id).delete()
        db.session.commit()
        flash('Job and associated post deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()  # Ensure to rollback in case of an exception
        flash(str(e), 'danger')
    return redirect(url_for('job_manager'))



#Building the prototype tool reddit scraper:

@app.route('/reddit_scraper_proto', methods=['GET', 'POST'])
def reddit_scraper_proto():
    communities = Community.query.all()  # Retrieve communities for every request

    if request.method == 'POST':
        if 'scrape' in request.form:  # Check if the request is for scraping
            clear_image_directory()
            subreddit_name = request.form.get('subreddit')
            content_type = request.form.get('content_type', 'images')
            number_of_posts = request.form.get('number_of_posts', 100, type=int)
            sort_option = request.form.get('sort_option', 'hot')

            # Store form data for reuse and scraping results
            session['subreddit_name'] = subreddit_name
            session['content_type'] = content_type
            session['number_of_posts'] = number_of_posts
            session['sort_option'] = sort_option

            results = scrape_reddit_posts(subreddit_name, content_type, number_of_posts, sort_option)
            session['results'] = results  # Assuming results are serializable or storing references

            if results:
                flash(f"Scraped {len(results)} posts from /r/{subreddit_name}")
            return render_template('reddit_scraper_proto.html', results=results, communities=communities)

        elif 'publish' in request.form:  # Handle submission of selected posts
            selected_posts = request.form.getlist('selected_posts')
            community_id = request.form.get('community_id')
            results = session.get('results', [])

            if not selected_posts:
                flash("No posts selected for publishing.")
            else:
                publish_posts(selected_posts, community_id)
                flash(f"Published {len(selected_posts)} posts to the community.")
            
            return redirect(url_for('reddit_scraper_proto'))

    # Initialize form with session data if available
    return render_template('reddit_scraper_proto.html', communities=communities,
                           subreddit_name=session.get('subreddit_name'),
                           content_type=session.get('content_type'),
                           number_of_posts=session.get('number_of_posts'),
                           sort_option=session.get('sort_option'))

def publish_posts(selected_posts, community_id):
    """Publish selected image posts to a specific community and move images."""
    base_directory = 'static/images/posts/'  # Adjusted base directory for posts
    for image_path in selected_posts:
        # Extract the filename from the original image path
        filename = os.path.basename(image_path)
        
        # Define the new full path for the image
        new_image_full_path = os.path.join(base_directory, filename)
        
        # Ensure the base directory exists
        os.makedirs(os.path.dirname(new_image_full_path), exist_ok=True)
        
        # Move the file to the new directory
        try:
            shutil.move(os.path.join('static', image_path), new_image_full_path)  # Ensure the source path is correctly specified
        except FileNotFoundError as e:
            print(f"Error moving file: {e}")
            continue  # Skip this file and continue with the next
        
        # Create a new post with the filename only (assuming the base path is known)
        new_post = Post(
            title="",
            content="",
            image_filename=filename,  # Store only the filename
            community_id=community_id,
            user_id=random_seeder_id(community_id),
            posted_time=datetime.utcnow(),
            upvotes=0,
            downvotes=0
        )
        db.session.add(new_post)
    db.session.commit()



def random_seeder_id(community_id):
    """Select a random seeder member from the community."""
    # Query users who are seeders and are part of the specified community
    seeders = User.query.join(user_community_association, (user_community_association.c.user_id == User.id)).\
        filter(user_community_association.c.community_id == community_id, User.seeder == True).all()

    if seeders:
        return random.choice(seeders).id
    return None


#upvote randomizer

@app.route('/upvote_randomizer', methods=['GET'])
def show_upvote_randomizer():
    return render_template('upvote_randomizer.html')



@app.route('/upvote_randomizer', methods=['POST'])
def upvote_randomizer():
    min_upvotes = int(request.form.get('min_upvotes', 0))
    max_upvotes = int(request.form.get('max_upvotes', 0))

    if min_upvotes > max_upvotes:
        flash("Minimum upvotes cannot be greater than maximum upvotes.")
        return redirect(url_for('show_upvote_randomizer'))  # Redirect to the form page

    # Fetch all posts
    posts = Post.query.all()
    for post in posts:
        post.upvotes = random.randint(min_upvotes, max_upvotes)
    db.session.commit()

    flash("Upvotes randomized successfully.")
    return redirect(url_for('show_upvote_randomizer'))  # Redirect back to the form or any other appropriate page


#post randomizer for prototype:




@app.route('/randomize_post_dates', methods=['POST'])
def randomize_post_dates():
    end_date_str = request.form.get('end_date')
    try:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        flash("Invalid date format. Please use YYYY-MM-DD format.")
        return redirect(url_for('show_post_randomizer'))

    # Check that the end date is before today's date
    if end_date >= datetime.utcnow():
        flash("End date must be before today's date.")
        return redirect(url_for('show_post_randomizer'))

    # Fetch all posts
    posts = Post.query.all()
    for post in posts:
        # Calculate the total number of seconds between the end date and now
        total_seconds = int((datetime.utcnow() - end_date).total_seconds())
        random_seconds = random.randint(0, total_seconds)
        
        # Create a new random date within the specified interval
        random_date = datetime.utcnow() - timedelta(seconds=random_seconds)
        
        # Update the post's posted_time
        post.posted_time = random_date

    # Commit changes to the database
    db.session.commit()

    flash("Post dates randomized successfully.")
    return redirect(url_for('show_post_randomizer'))

@app.route('/show_post_randomizer')
def show_post_randomizer():
    return render_template('post_randomizer.html')


#delete all posts in community


@app.route('/delete_community_posts', methods=['POST'])
def delete_community_posts():
    community_id = request.form.get('community_id')
    if not community_id:
        flash("No community selected.")
        return redirect(url_for('show_delete_page'))

    # Delete comments associated with posts in the selected community
    Comment.query.filter(Comment.post.has(community_id=community_id)).delete(synchronize_session=False)
    
    # Delete posts in the community
    Post.query.filter_by(community_id=community_id).delete(synchronize_session=False)
    
    db.session.commit()
    flash(f"All posts and comments deleted for the community with ID {community_id}.")
    return redirect(url_for('show_delete_page'))


@app.route('/show_delete_page')
def show_delete_page():
    communities = Community.query.all()
    return render_template('delete_community.html', communities=communities)


#ai comment prompt management


@app.route('/ai_comment_prompts')
def ai_comment_prompts():
    prompts = AICommentPrompt.query.all()
    communities = Community.query.all()  # Assuming you have a model called Community
    return render_template('ai_comment_prompts.html', prompts=prompts, communities=communities)




@app.route('/add_ai_comment_prompt', methods=['POST'])
def add_ai_comment_prompt():
    prompt_text = request.form.get('prompt')
    if prompt_text:
        new_prompt = AICommentPrompt(prompt=prompt_text)
        db.session.add(new_prompt)
        db.session.commit()
        flash('New prompt added successfully.')
    else:
        flash('Prompt text is required.')
    return redirect(url_for('ai_comment_prompts'))


@app.route('/edit_ai_comment_prompt/<int:id>', methods=['GET'])
def edit_ai_comment_prompt(id):
    prompt = AICommentPrompt.query.get_or_404(id)
    return render_template('edit_ai_comment_prompt.html', prompt=prompt)



@app.route('/update_ai_comment_prompt/<int:id>', methods=['POST'])
def update_ai_comment_prompt(id):
    prompt = AICommentPrompt.query.get_or_404(id)
    prompt_text = request.form.get('prompt_text')
    if prompt_text:
        prompt.prompt = prompt_text
        db.session.commit()
        flash('Prompt updated successfully.')
    else:
        flash('Prompt text is required.')
    return redirect(url_for('ai_comment_prompts'))



@app.route('/delete_ai_comment_prompt/<int:id>', methods=['POST'])
def delete_ai_comment_prompt(id):
    prompt = AICommentPrompt.query.get_or_404(id)
    db.session.delete(prompt)
    db.session.commit()
    flash('Prompt deleted successfully.')
    return redirect(url_for('ai_comment_prompts'))



from threading import Thread

@app.route('/start_seed_job', methods=['POST'])
def start_seed_job():
    num_comments_per_post = request.form.get('num_comments_per_post', type=int)
    community_id = request.form.get('community_id')

    if num_comments_per_post is None or num_comments_per_post <= 0:
        flash('Please enter a valid number of comments per post.')
        return redirect(url_for('ai_comment_prompts'))

    # Start the job in a background thread
    thread = Thread(target=generate_comments_for_all_posts, args=(num_comments_per_post, community_id))
    thread.start()

    flash('Comment generation started!')
    return redirect(url_for('ai_comment_prompts'))

def generate_comments_for_all_posts(num_comments_per_post, community_id=None):
    with app.app_context():
        prompts = AICommentPrompt.query.all()
        if community_id:
            posts = Post.query.filter(Post.community_id == community_id).all()
        else:
            posts = Post.query.all()

        if not posts:
            return "No posts available."
        if not prompts:
            return "No prompts available."

        results = []

        for post in posts:
            # Include post title and content in the AI prompt
            post_context = f"You're in a conversation with your friend. Your friend just said this: {post.title}\nContent: {post.content}\n\n"

            for _ in range(num_comments_per_post):
                user = User.query.filter_by(seeder=True).order_by(func.random()).first()
                if not user:
                    results.append("No users available for commenting.")
                    continue

                # Choose a random prompt and append post details
                prompt_text = choice(prompts).prompt
                combined_prompt = f"{post_context} {prompt_text}"

                try:
                    # Call OpenAI's API to generate the comment
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "system", "content": combined_prompt}]
                    )
                    generated_comment = response.choices[0].message.content.strip()

                    # Create a new comment object and save it to the database
                    new_comment = Comment(
                        content=generated_comment,
                        user_id=user.id,
                        post_id=post.id,
                        posted_time=datetime.utcnow(),
                        is_burner=False
                    )
                    db.session.add(new_comment)
                    db.session.commit()

                    results.append(f"Generated and posted comment successfully for post {post.id} in community {post.community.name}")
                except Exception as e:
                    results.append(f"Failed to generate comment for post {post.id} in community {post.community.name}: {str(e)}")

        return results


#subreddit/content manager

@app.route('/subreddits')
def subreddits():
    communities = Community.query.all()
    subreddits = Subreddits.query.all()
    return render_template('subreddits.html', communities=communities, subreddits=subreddits)

@app.route('/add-subreddit', methods=['POST'])
def add_subreddit():
    prompt = request.form['prompt']
    #content_type = request.form['content_type']
    if prompt:
        new_subreddit = Subreddits(prompt=prompt)
        db.session.add(new_subreddit)
        db.session.commit()
        flash('Subreddit added successfully!')
    else:
        flash('Prompt is required to add a new subreddit.')
    return redirect(url_for('subreddits'))

@app.route('/add-subreddit-to-community/<int:community_id>', methods=['POST'])
def add_subreddit_to_community(community_id):
    prompt = request.form.get('prompt')
    #content_type = request.form.get('content_type')
    # Create the subreddit if it does not exist
    subreddit = Subreddits.query.filter_by(prompt=prompt).first()
    if not subreddit:
        subreddit = Subreddits(prompt=prompt)
        db.session.add(subreddit)
        db.session.commit()

    # Add to community
    community = Community.query.get(community_id)
    if community:
        community.subreddits.append(subreddit)
        db.session.commit()
        flash('Subreddit added to community successfully!', 'success')
    else:
        flash('Community not found!', 'error')

    return redirect(url_for('subreddits'))


@app.route('/delete-subreddit/<int:id>', methods=['POST'])
def delete_subreddit(id):
    subreddit = Subreddits.query.get_or_404(id)
    db.session.delete(subreddit)
    db.session.commit()
    flash('Subreddit deleted successfully!')
    return redirect(url_for('subreddits'))


@app.route('/remove-subreddit-from-community/<int:community_id>/<int:subreddit_id>', methods=['GET'])
def remove_subreddit_from_community(community_id, subreddit_id):
    try:
        # Build a delete statement for the association table
        delete_statement = community_subreddit_association.delete().where(
            and_(
                community_subreddit_association.c.community_id == community_id,
                community_subreddit_association.c.subreddit_id == subreddit_id
            )
        )
        # Execute the delete statement through the session
        db.session.execute(delete_statement)
        db.session.commit()
        flash('Subreddit removed successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
        app.logger.error('Error removing subreddit from community', exc_info=True)

    return redirect(url_for('subreddits'))





@app.route('/get_seeder_info/<user_id>', methods=['GET'])
def get_seeder_info(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Seeder not found'}), 404

    return jsonify({
        'about_me': user.about_me,
        'profile_picture': user.profile_pic_url  # Assuming the profile pictures are stored in the static folder
    })



## IDEA FACTORY ##


@app.route('/idea_factory/', methods=['GET', 'POST'])
def idea_factory():
    communities = Community.query.options(joinedload(Community.subreddits)).all()
    if request.method == 'POST':
        clear_image_directory()
        selected_community_id = request.form.get('community_id')
        subreddit_name = request.form.get('subreddit')
        number_of_posts = int(request.form.get('number_of_posts', 100))
        sort_option = request.form.get('sort_option', 'hot')
        professional_context = 'professional_context' in request.form  # Check if checkbox is checked

        session_data = {
            'subreddit_name': subreddit_name,
            'number_of_posts': number_of_posts,
            'sort_option': sort_option,
            'selected_community_id': selected_community_id,
            'professional_context': professional_context
        }
        session.update(session_data)

        results = []
        if subreddit_name:
            results = scrape_reddit_posts(subreddit_name, number_of_posts, sort_option)
        elif selected_community_id:
            community = Community.query.get(selected_community_id)
            for subreddit in community.subreddits:
                results.extend(scrape_reddit_posts(subreddit.prompt, number_of_posts, sort_option))

        # Modify text content using OpenAI
        for post in results:
            if post['image'] is None:  # Process only text posts
                full_text = f"Title: {post.get('title', '')}\n\n{post['content']}"
                modified_content = modify_text_with_openai(full_text, professional_context)
                post['ai_content'] = modified_content

        text_results = [post for post in results if post['image'] is None]

        if text_results:
            flash(f"Scraped and processed {len(text_results)} text posts")

        return render_template('idea_factory.html', results=text_results, communities=communities, session=session)

    return render_template('idea_factory.html', communities=communities, session=session)


def modify_text_with_openai(text, professional_context):
    context_suffix = "in a professional context." if professional_context else "make it completely different from the original post"
    print(context_suffix)
    prompt = (
    f"Take this Reddit post and extract the general, underlying theme from it: \n\n"
    f"{text}\n\n"
    f"and then below that, generate an example post that follows the theme, but {context_suffix}. "
    "Pretend you are a young adult. The example post needs to follow these guidelines for making it more personable and viral:\n\n"
    f"Authenticity: The content feels genuine and honest, reflecting the individual's true thoughts or feelings. "
    "It doesn’t feel scripted or generic.\n"
    f"Detail-Oriented: Instead of general statements, a personal post includes specific details that reveal more "
    "about the person's situation or viewpoint.\n"
    f"Emotional Engagement: The post connects on an emotional level, whether it's sharing joy, struggles, doubts, "
    "or achievements. This helps create a bond with readers.\n"
    f"Storytelling: Personal posts often incorporate elements of storytelling, which is also a key aspect of virality. "
    "A clear narrative, a personal journey, or anecdotes make them more engaging and relatable.\n"
    f"Relevance: These posts are relevant to the interests and needs of the community. In a professional or young "
    "adult setting, topics might include career challenges, educational experiences, personal development, or "
    "balancing life and work.\n"
    f"Interactive: Personal posts invite interaction by asking questions or seeking advice, thereby fostering a "
    "community dialogue.\n"
    f"Reflective: They often reflect on personal experiences or lessons learned, which can provide valuable insights "
    "to others in similar situations.\n\n"
    f"Virality Principles:\n"
    f"1. Social Currency: Create content that makes people feel informed or 'in the know,' enhancing their social image.\n"
    f"2. Triggers: Include references to well-known brands, products, or dates to create associative triggers.\n"
    f"3. Emotion: Aim to elicit strong emotions like awe, excitement, amusement, anger, or anxiety which are linked to higher sharing rates.\n"
    f"4. Public: Encourage behaviors that people can see others doing, fostering a trend or common action.\n"
    f"5. Practical Value: Offer practical, useful information or tips that people will want to share because it provides value to others.\n"
    f"6. Stories: Utilize the power of narrative to make your content more memorable and shareable.\n\n"
    f"Format your response clearly with the extracted main theme and then the example post which is at most two paragraphs."
)
    print(prompt)
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Use the appropriate model
            messages=[
                {"role": "system", "content": prompt}
            ]
        )
        modified_text = response.choices[0].message.content.strip()  # Capitalize all letters
        final_output = f"{modified_text}"
        return final_output
    except Exception as e:
        print(f"Failed to modify text: {str(e)}")
        return text  # Return the original text if modification fails






if __name__ == '__main__':
    
    app.run(debug=True)
