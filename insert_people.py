# Import the Flask application instance
from app import app, db, User, Post, Community, Comment
from app import community_interest_association  # Assuming this is defined in app.py
from app import user_community_association
from sqlalchemy.sql.expression import func
from random import choice
from datetime import datetime
import os
import random
import string
from flask_sqlalchemy import SQLAlchemy



words_list = [
    'wanderlust', 'sunrise', 'twilight', 'meadow', 'groove', 'harmony', 'jubilee',
    'serendipity', 'quintessence', 'mystique', 'oasis', 'pinnacle', 'quartz',
    'riviera', 'saffron', 'talisman', 'unicorn', 'vintage', 'whimsy', 'xenon',
    'yacht', 'zealot', 'alchemy', 'breeze', 'citadel', 'dewdrop', 'effervescent',
    'fable', 'glimmer', 'havoc', 'illusion', 'jazz', 'kaleidoscope', 'labyrinth',
    'memento', 'nomad', 'opulence', 'palette', 'quest', 'rhapsody', 'sapphire',
    'tango', 'utopia', 'verve', 'willow', 'exotic', 'yarn', 'zephyr', 'azure',
    'beguile', 'carnival', 'dragonfly', 'ember', 'flourish', 'gossamer', 'horizon',
    'infinity', 'jubilation', 'knoll', 'luminous', 'mirage', 'nectar', 'oracle',
    'pilgrim', 'quiver', 'renaissance', 'solstice', 'tide', 'umbra', 'velvet',
    'whirl', 'pixie', 'yodel', 'zenith', 'arcadia', 'bliss', 'cascade'
]




def generate_random_password(length=10):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))


def generate_random_username(exclude_names):
    username = ''
    while not username or any(name in username for name in exclude_names):
        username = random.choice(words_list) + str(random.randint(10, 99))
    return username

def format_name(name):
    if len(name) > 1:
        # Convert the entire name to lowercase and then capitalize the first and last letter
        return name[0].upper() + name[1:].lower()
    else:
        # If the name is a single character, just capitalize it
        return name.upper()

def insert_users_from_images(folder_path):
    image_files = os.listdir(folder_path)
    for image_file in image_files:
        if image_file.endswith('.png'):
            first_name, last_name = image_file.replace('.png', '').split('_')
            password = generate_random_password()
            burner_username = generate_random_username([first_name, last_name])
            profile_pic_url = f'/static/images/profile_pics/{image_file}'
            karma = random.randint(20, 1000) 

            user = User(first_name=format_name(first_name), last_name=format_name(last_name), password=password, burner_username=burner_username, profile_pic_url=profile_pic_url, karma=karma)
            db.session.add(user)
    db.session.commit()


def populate_user_community_targeted():
    with app.app_context():
        # Directly specify user IDs from 1 to 141
        user_ids = list(range(1, 142))  # Python range is exclusive at the end, hence 142

        # Specific community IDs you're interested in
        target_community_ids = [283, 285, 286, 287, 288, 289]

        for community_id in target_community_ids:
            # Process each specified community
            for user_id in user_ids:
                # Check if the user is already a member of the community
                if not db.session.query(db.exists().where(db.and_(
                    user_community_association.c.user_id == user_id,
                    user_community_association.c.community_id == community_id
                ))).scalar():
                    # Insert new association if not exists
                    insert_stmt = user_community_association.insert().values(
                        user_id=user_id, community_id=community_id)
                    db.session.execute(insert_stmt)

            db.session.commit()  # Commit after processing each community



def populate_user_community():
    with app.app_context():
        user_ids = [user.id for user in User.query.all()]
        community_ids = [community.id for community in Community.query.all()]

        for community_id in community_ids:
            num_users = random.randint(141, 141)
            selected_user_ids = random.sample(user_ids, num_users)

            for user_id in selected_user_ids:
                if not db.session.query(db.exists().where(db.and_(
                    user_community_association.c.user_id == user_id,
                    user_community_association.c.community_id == community_id
                ))).scalar():
                    insert_stmt = user_community_association.insert().values(user_id=user_id, community_id=community_id)
                    db.session.execute(insert_stmt)

            db.session.commit()


@app.cli.command('update_upvotes')
def update_upvotes():
    posts = Post.query.all()  # Fetch all posts
    for post in posts:
        post.upvotes = random.randint(5, 1500)  # Assign a random number of upvotes
        db.session.add(post)
    db.session.commit()  # Commit all changes
    print("Upvotes updated successfully.")




if __name__ == '__main__':

	update_upvotes()