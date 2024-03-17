from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from openai import OpenAI
from flask_sqlalchemy import SQLAlchemy
from sentence_transformers import SentenceTransformer, util
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = '1'

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(50), nullable=False)
    tags = db.Column(db.JSON)

# Initialize the database
@app.before_first_request
def create_tables():
    db.create_all()

# Initialize the OpenAI client
client = OpenAI(api_key="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")


@app.route('/', methods=['GET', 'POST'])
def index():

	return render_template("index.html")


@app.route('/signup', methods=['GET', 'POST'])
def signup():

	if request.method == 'POST':

		name = request.form.get('name')
		password = request.form.get('password')

		if User.query.filter_by(name=name).first():
			return 'User already exists.'

		form_data = {key: request.form.get(key) for key in request.form.keys() if key not in ['name', 'password']}

		user_content = "\n".join([f"{key}: {value}" for key, value in form_data.items() if value])

		messages = [

			{"role": "system", "content": "Generate comma-separated tags based on the quiz responses provided."},

			{"role": "user", "content": user_content}

		]


		completion = client.chat.completions.create(
			model="gpt-4",
			messages=messages

		)

		tags = str(completion.choices[0].message.content).split(', ')
		user = User(name=name, password= password, tags=tags)
		db.session.add(user)
		db.session.commit()

		return tags


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

@app.route('/tags')
def show_tags():
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        if current_user:
            users_similarity = []
            # Convert current user's tags to a single vector
            current_user_tags_vector = model.encode(current_user.tags, convert_to_tensor=True)
            
            # Iterate over other users to calculate similarity
            other_users = User.query.filter(User.id != current_user.id).all()
            for user in other_users:
                user_tags_vector = model.encode(user.tags, convert_to_tensor=True)
                # Calculate cosine similarity
                similarity = util.pytorch_cos_sim(current_user_tags_vector, user_tags_vector)
                # Correctly extract the similarity score as a float
                similarity_score = similarity[0][0].item()  # .item() converts a one-element tensor to a scalar
                users_similarity.append((user.name, similarity_score))
            
            # Sort users by similarity score
            users_similarity.sort(key=lambda x: x[1], reverse=True)
            
            # For simplicity, just returning the list
            return jsonify(users_similarity)
        return 'User not found'
    return redirect(url_for('login'))


if __name__ == '__main__':
	app.run(debug=True)