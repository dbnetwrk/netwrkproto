from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from openai import OpenAI
from flask_sqlalchemy import SQLAlchemy
from sentence_transformers import SentenceTransformer, util
import numpy as np
import torch
import os
from werkzeug.utils import secure_filename


UPLOAD_FOLDER = 'C:\\flasker\\static\\uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}






model = SentenceTransformer('all-MiniLM-L6-v2')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = '1'

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(50), nullable=False)
    tags = db.Column(db.JSON)
    profile_pic = db.Column(db.String(255))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Initialize the database
@app.before_first_request
def create_tables():
    db.create_all()

# Initialize the OpenAI client
client = OpenAI(api_key="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")


@app.route('/', methods=['GET', 'POST'])
def index():

	return render_template("index.html")

@app.route('/quiz', methods=['GET'])
def quiz():
    # Display the quiz form to the user
    return render_template('quiz.html')

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        if not user:
            return 'User not found', 404

        # Collect responses from the form
        form_data = {key: request.form.get(key) for key in request.form.keys()}
        user_content = "\n".join([f"{value}" for value in form_data.values() if value])

        messages = [
            {"role": "system", "content": "Generate comma-separated tags based on the quiz responses provided."},
            {"role": "user", "content": user_content}
        ]

        completion = client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )

        # Assume new tags are appended to existing ones, ensuring no duplication
        new_tags = str(completion.choices[0].message.content).split(', ')
        updated_tags = list(set(user.tags + new_tags))  # Combine and remove duplicates
        user.tags = updated_tags
        db.session.commit()

        return redirect(url_for('show_tags'))
    else:
        return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():

	if request.method == 'POST':

		name = request.form.get('name')
		password = request.form.get('password')
		selected_tags = request.form.getlist('tags')

		file = request.files.get('profile_pic')
		profile_pic_path = None

		if User.query.filter_by(name=name).first():
			return 'User already exists.'


		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			# Save the relative path
			user.profile_pic = os.path.join('uploads', filename)
			db.session.commit()

		user = User(name=name, password= password, tags=selected_tags, profile_pic=profile_pic_path)
		db.session.add(user)
		db.session.commit()

		return redirect(url_for('login'))


	return render_template("signup.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(name=request.form.get('name')).first()
        if user and user.password == request.form.get('password'):
            session['user_id'] = user.id  # Log in the user
            return redirect(url_for('show_tags'))
        else:
            return 'Invalid username or password'
    return render_template('login.html')


def aggregate_tag_vectors(tag_list):
    """
    Encode all tags and return the average vector.
    """
    if not tag_list:  # Check if the tag list is empty
        return None
    # Encode each tag to get a list of vectors
    tag_vectors = model.encode(tag_list, convert_to_tensor=True)
    # Calculate the mean of these vectors
    aggregated_vector = torch.mean(tag_vectors, dim=0)
    return aggregated_vector


def determine_badge(similarity_score):
    if similarity_score > 0.9:
        return 'Platinum Badge'
    elif similarity_score > 0.8:
        return 'Gold Badge'
    elif similarity_score > 0.75:
        return 'Silver Badge'
    elif similarity_score > 0.7:
        return 'Bronze Badge'
    else:
        return 'Copper Badge'


@app.route('/tags')
def show_tags():
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        if current_user:
            users_similarity = []
            # Aggregate the current user's tag vectors
            current_user_tags_vector = aggregate_tag_vectors(current_user.tags)
            
            if current_user_tags_vector is None:
                return 'Current user has no tags.'

            # Iterate over other users to calculate similarity
            other_users = User.query.filter(User.id != current_user.id).all()
            for user in other_users:
                user_tags_vector = aggregate_tag_vectors(user.tags)
                
                if user_tags_vector is None:
                    continue  # Skip users with no tags

                # Calculate cosine similarity between aggregated vectors
                similarity = util.pytorch_cos_sim(current_user_tags_vector.unsqueeze(0), user_tags_vector.unsqueeze(0))
                similarity_score = similarity[0][0].item()
                badge = determine_badge(similarity_score)
                users_similarity.append((user.name, similarity_score, badge, user.profile_pic))

            # Sort users by similarity score
            users_similarity.sort(key=lambda x: x[1], reverse=True)
            
            # For simplicity, just returning the list
            return render_template('tags.html', users_similarity=users_similarity)
        return 'User not found'
    return redirect(url_for('login'))


if __name__ == '__main__':
	app.run(debug=True)