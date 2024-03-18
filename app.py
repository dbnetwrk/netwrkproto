from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import os
from openai import OpenAI
from werkzeug.utils import secure_filename
from datetime import datetime
from random import choice
from sqlalchemy.sql import exists













UPLOAD_FOLDER = 'C:\\flasker\\static\\uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}



app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://ubjg47i7g7isg8:p7b28d89d1d5c485255cd8f3ec14ffd4eedc961ef6e2d551b4c1be75734150385@cb889jp6h2eccm.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d7t68f59g1ep1t'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = '1'
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))




db = SQLAlchemy(app)
migrate = Migrate(app, db)


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


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    posted_time = db.Column(db.DateTime, default=datetime.utcnow)
    upvotes = db.Column(db.Integer, nullable=False, default=0)
    downvotes = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    community_id = db.Column(db.Integer, db.ForeignKey('community.id'), nullable=False)

    user = db.relationship('User', backref=db.backref('posts', lazy=True))
    community = db.relationship('Community', backref=db.backref('posts', lazy=True))


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

class Community(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    profile_pic_url = db.Column(db.String(255), nullable=True, default='/static/images/default_community.png')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    creator = db.relationship('User', backref=db.backref('created_communities', lazy=True))
    interests = db.relationship('Interest', secondary=community_interest_association, backref=db.backref('communities', lazy='dynamic'))

class Interest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)



class Industry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)





interest_image_map = {
    1: 'football.png',
    2: 'reading.png',
    3: 'startups.png',
    4: 'gym.png',
    5: 'music.png',
    6: 'walking.png',
    7: 'sports.png',
    8: 'movies.png',
    9: 'skincare.png',
    10: 'coffee.png',
}

def update_community_profile_pics():
    communities = Community.query.all()
    for community in communities:
        for interest in community.interests:
            if interest.id in interest_image_map:
                # Construct the path to the image file
                image_filename = interest_image_map[interest.id]
                community.profile_pic_url = f'/images/{image_filename}'
                break  # Remove this break if you want to iterate through all interests
        
        db.session.add(community)
    db.session.commit()











# Initialize the database
@app.before_first_request
def create_tables():
    db.create_all()



@app.route('/', methods=['GET', 'POST'])
def index():

	return render_template("index.html")



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    industries = Industry.query.all()  # Fetch industries here to be available for both GET and POST
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        password = request.form.get('password')
        industry_id = request.form.get('industry_id')  # Corrected to use 'industry_id' based on your form
        selected_interests_ids = request.form.getlist('interests')

        # Assuming the Industry relation is correctly set up in your User model
        user = User(first_name=first_name, last_name=last_name, password=password, industry_id=industry_id)

        # Add selected interests to the user
        for interest_id in selected_interests_ids:
            interest = Interest.query.get(interest_id)
            if interest:
                user.interests.append(interest)
        
        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id
        return redirect(url_for('show_feed'))

    interests = Interest.query.all()  # Fetch all available interests to display in the form
    return render_template("signup.html", interests=interests, industries=industries)





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
    user_id = session.get('user_id')
    if not user_id:
        # User is not logged in, redirect to login page
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if not user:
        # User not found, clear session and redirect to login
        return redirect(url_for('login'))

    user_industry_id = user.industry_id
    user_interest_ids = [interest.id for interest in user.interests]

    # Posts from communities in user's industry with shared interests
    posts_in_industry_with_shared_interests = Post.query \
        .join(Community, Post.community_id == Community.id) \
        .join(User, Community.created_by == User.id) \
        .join(community_interest_association, Community.id == community_interest_association.c.community_id) \
        .filter(User.industry_id == user_industry_id, community_interest_association.c.interest_id.in_(user_interest_ids)) \
        .order_by(Post.posted_time.desc()) \
        .distinct()

    # Posts from communities just within the same industry
    posts_in_industry = Post.query \
        .join(Community, Post.community_id == Community.id) \
        .join(User, Community.created_by == User.id) \
        .filter(User.industry_id == user_industry_id) \
        .filter(~Post.id.in_([post.id for post in posts_in_industry_with_shared_interests])) \
        .order_by(Post.posted_time.desc()) \
        .distinct()

    # Posts from communities based on shared interests
    posts_based_on_interests = Post.query \
        .join(Community, Post.community_id == Community.id) \
        .join(community_interest_association, Community.id == community_interest_association.c.community_id) \
        .filter(community_interest_association.c.interest_id.in_(user_interest_ids)) \
        .filter(~Post.id.in_([post.id for post in posts_in_industry_with_shared_interests])) \
        .filter(~Post.id.in_([post.id for post in posts_in_industry])) \
        .order_by(Post.posted_time.desc()) \
        .distinct()

    # Random community posts that don't relate necessarily
    rest_of_posts = Post.query \
        .join(Community, Post.community_id == Community.id) \
        .filter(~Post.id.in_([post.id for post in posts_in_industry_with_shared_interests])) \
        .filter(~Post.id.in_([post.id for post in posts_based_on_interests])) \
        .filter(~Post.id.in_([post.id for post in posts_in_industry])) \
        .order_by(Post.posted_time.desc()) \
        .all()

    # Concatenating the post lists into a single list for display
    all_posts = posts_in_industry_with_shared_interests.all() + posts_in_industry.all() + posts_based_on_interests.all() + rest_of_posts

    return render_template("feed.html", posts=all_posts, active_page='feed')




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
    
    return render_template('profile.html', user=user, active_page='profile')


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


@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    if 'user_id' not in session:
        flash("Please log in to create a post.")
        return redirect(url_for('login'))
    
    communities = Community.query.all()  # Assuming you have a Community model

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        community_id = request.form.get('community')  # Note the change here
        user_id = session['user_id']

        new_post = Post(title=title, content=content, community_id=community_id, user_id=user_id, posted_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), upvotes=0, downvotes=0)
        db.session.add(new_post)
        db.session.commit()
        
        flash("Post created successfully.")
        return redirect(url_for('show_feed'))

    return render_template('create_post.html', communities=communities)



@app.route('/create_community', methods=['GET', 'POST'])
def create_community():
    if 'user_id' not in session:
        flash("Please log in to create a community.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        # Assume a file input named 'profile_pic' for uploading community profile pictures
        file = request.files.get('profile_pic')
        profile_pic_url = '/static/images/default_community.png'  # Default picture
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            profile_pic_url = url_for('static', filename='uploads/' + filename)

        new_community = Community(name=name, description=description, profile_pic_url=profile_pic_url, created_by=session['user_id'])
        db.session.add(new_community)
        db.session.commit()

        flash("Community created successfully.")
        return redirect(url_for('show_feed'))

    return render_template('create_community.html')

@app.route('/communities')
def communities():
    user_id = session.get('user_id')
    if not user_id:
        # If the user is not logged in, redirect them to the login page
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('logout'))

    user_industry_id = user.industry_id
    user_interest_ids = [interest.id for interest in user.interests]

    # Communities in user's industry with shared interests
    communities_in_industry_with_shared_interests = Community.query \
        .join(User, Community.created_by == User.id) \
        .join(community_interest_association, Community.id == community_interest_association.c.community_id) \
        .filter(User.industry_id == user_industry_id, community_interest_association.c.interest_id.in_(user_interest_ids)) \
        .distinct()

    # Communities just within the same industry, excluding those already selected
    communities_in_industry = Community.query \
        .join(User, Community.created_by == User.id) \
        .filter(User.industry_id == user_industry_id) \
        .filter(~Community.id.in_([community.id for community in communities_in_industry_with_shared_interests])) \
        .distinct()

    # Fetching communities based on shared interests (excluding those already displayed)
    communities_based_on_interests = Community.query \
        .join(community_interest_association, Community.id == community_interest_association.c.community_id) \
        .filter(community_interest_association.c.interest_id.in_(user_interest_ids)) \
        .filter(~Community.id.in_([community.id for community in communities_in_industry_with_shared_interests])) \
        .filter(~Community.id.in_([community.id for community in communities_in_industry])) \
        .distinct()

    # Fetching the rest of the communities not based on shared interests or industry
    rest_of_communities = Community.query \
        .filter(~Community.id.in_([community.id for community in communities_in_industry_with_shared_interests])) \
        .filter(~Community.id.in_([community.id for community in communities_based_on_interests])) \
        .filter(~Community.id.in_([community.id for community in communities_in_industry])) \
        .all()

    user_communities = set(community.id for community in user.communities)

    return render_template('communities.html', 
                           communities_in_industry_with_shared_interests=communities_in_industry_with_shared_interests, 
                           communities_in_industry=communities_in_industry,
                           communities_based_on_interests=communities_based_on_interests, 
                           rest_of_communities=rest_of_communities, 
                           user_communities=user_communities)





@app.route('/generate_and_post', methods=['GET'])
def generate_and_post():
    # Select a random user
    user = User.query.order_by(db.func.random()).first()
    
    if not user:
        return render_template('generate_post_page.html', error='User does not exist')

    # Assuming each user has a many-to-many relationship with interests
    user_interest_ids = {interest.id for interest in user.interests}

    # Finding communities where the creator's interests overlap with the user's interests
    communities = Community.query.join(User, Community.created_by == User.id).join(User.interests).filter(Interest.id.in_(user_interest_ids)).distinct()

    if communities.count() == 0:
        return render_template('generate_post_page.html', error='No communities found with matching interests')

    community = choice(communities.all())

    prompt = f"Craft a post for the '{community.name}' forum, where people gather around '{community.description}'. Begin your response with a single sentence title with no quotation marks, followed by a blank line, then a 5 sentence paragraph that either celebrates a triumph, delves into a challenge, or seeks guidance and support from the community. Whether you're recounting a personal achievement, sharing a valuable lesson from a hardship, or asking for advice on a dilemma, your narrative should aim to connect, uplift, or rally the community for support. Use verbiage that is on a 8th grade reading level, and keep in mind you are 22 years old. Do not begin your content with a greeting to the audience."

    try:
        # Assuming the OpenAI API usage
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}]
        )
        generated_text = response.choices[0].message.content
        parts = generated_text.split('\n\n', 1)
        title = parts[0].strip() if parts else "Untitled"
        content = parts[1].strip() if len(parts) > 1 else "No content"
        
        new_post = Post(title=title, content=content, user_id=user.id, community_id=community.id, posted_time=datetime.utcnow())
        db.session.add(new_post)
        db.session.commit()

        return render_template('generate_post_page.html', title=title, content=content, success='Generated and posted successfully!')
    except Exception as e:
        return render_template('generate_post_page.html', error=f'Failed to generate post: {str(e)}')



@app.route('/generate_and_comment', methods=['GET'])
def generate_and_comment():
    # Select a random user
    user = User.query.order_by(db.func.random()).first()
    
    if not user:
        return render_template('generate_comment_page.html', error='No users available.')

    # Find posts that the user hasn't commented on yet
    commented_post_ids = db.session.query(Comment.post_id).filter_by(user_id=user.id).subquery()
    post = Post.query.filter(Post.user_id != user.id, ~Post.id.in_(commented_post_ids)).order_by(db.func.random()).first()

    if not post:
        # If no suitable post is found, display a message
        return render_template('generate_comment_page.html', error="No posts available for this user to comment on. Please try again.")

    prompt = f"Read the following post titled '{post.title}' and its content: '{post.content}'. Now, craft a concise, thoughtful one or two sentence comment that either provides support, asks a clarifying question, or shares a related personal experience. Ensure your comment is concise. Use verbiage of an 8th-grade reading level in your comment, and remember that you are 22 years old"

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt}
            ]
        )

        generated_comment = response.choices[0].message.content.strip()

        # Create and save the new comment
        new_comment = Comment(
            content=generated_comment, 
            user_id=user.id,
            post_id=post.id, 
            posted_time=datetime.utcnow(),
            is_burner=False
        )
        db.session.add(new_comment)
        db.session.commit()

        # Display the generated comment details
        return render_template(
            'generate_comment_page.html', 
            post_title=post.title, 
            post_content=post.content, 
            commenter_name=user.first_name + " " + user.last_name, 
            generated_comment=generated_comment
        )
    except Exception as e:
        return render_template('generate_comment_page.html', error=f'Failed to generate comment: {str(e)}')


@app.route('/join_community/<int:community_id>', methods=['POST'])
def join_community(community_id):
    if 'user_id' not in session:
        flash("You must be logged in to join a community.", "danger")
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)
    community = Community.query.get(community_id)
    
    if community not in user.communities:
        user.communities.append(community)
        db.session.commit()
        flash(f"You have successfully joined {community.name}.", "success")
    else:
        flash(f"You are already a member of {community.name}.", "info")

    return redirect(url_for('communities'))



if __name__ == '__main__':
    with app.app_context():
        update_community_profile_pics()
        print("Community profile pictures updated based on interests.")
	#app.run(debug=True)