import praw
import requests
import os
from sqlalchemy import func
# Import the Flask application instance
from app import app, db, User, Post, Community, client, Comment
from app import community_interest_association  # Assuming this is defined in app.py
from sqlalchemy.sql.expression import func
from random import choice
from datetime import datetime
from random import choice as random_choice
from datetime import datetime
import random
import markdown2

# Authentication with Reddit
reddit = praw.Reddit(
    client_id='i-SqiFyPh8Jgk34GFXwLCw',
    client_secret='mbAJH8RDW3G3S7L-gLb9HIUwj_on-g',
    user_agent='script:subreddit image downloader:v1.0 (by /u/DoodleChoco6642)'
)


def download_image(image_url, local_filename):
    """Utility function to download and save an image."""
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(local_filename, 'wb') as f:
            f.write(response.content)
    return local_filename




def generate_reddit_post():
    with app.app_context():
        # Assuming reddit and other necessary imports (like Post, User, db) are already defined
        subreddit = reddit.subreddit('gaming')

        for submission in subreddit.top('all', limit=100):


            #if not submission.link_flair_text or 'Meme' not in submission.link_flair_text:
             #   continue

            # Skip everything except posts with image URLs ending in jpg, jpeg, png
            if not (submission.url.endswith('jpg') or submission.url.endswith('jpeg') or submission.url.endswith('png')):
                continue  # This skips non-image posts and other content
            
            # Image handling
            file_name = f"{submission.id}.jpg"  # Use jpg for uniformity or adapt based on actual URL
            local_filename = os.path.join('static/images/posts', file_name)
            download_image(submission.url, local_filename)  # Assume function to download image exists
            image_filename = file_name  # Store only the file name in the database
            
            # Select a random user
            random_user = User.query.order_by(db.func.random()).first()
            
            # Create a new post object with an empty content field since we're only handling images
            new_post = Post(
                title=submission.title,
                content="",  # No content since these are only image posts
                posted_time=datetime.utcnow(),
                user_id=random_user.id,  # Assuming this is a bot or specific user ID for posting
                community_id=437,  # Adjust as needed
                image_filename=image_filename,
                upvotes=submission.score,
                downvotes=0
            )
            
            # Try to add the post to the session and commit
            try:
                db.session.add(new_post)
                db.session.commit()
            except Exception as e:
                print(f"Failed to add or commit a post: {e}")
                db.session.rollback()  # Roll back the session in case of an error



if __name__ == "__main__":

    generate_reddit_post()