# Import the Flask application instance
from app import app, db, User, Post, Community, client, Comment
from app import community_interest_association  # Assuming this is defined in app.py
from sqlalchemy.sql.expression import func
from random import choice
from datetime import datetime

def generate_post_core():
    # Create and use the application context
    with app.app_context():
        user = User.query.order_by(func.random()).first()

        if not user:
            print('User does not exist')
            return 'User does not exist', None

        user_interest_ids = {interest.id for interest in user.interests}
        # Find communities where the creator is in the same industry as the user
        communities = Community.query.join(User, Community.created_by == User.id) \
            .filter(User.industry_id == user.industry_id).distinct()

        if communities.count() == 0:
            print('No communities found with matching industry')
            return 'No communities found with matching industry', None

        community = choice(communities.all())
        prompt = f"Craft a post for the '{community.name}' forum, where people gather around '{community.description}'. Begin your response with a single sentence title with no quotation marks, followed by a blank line, then a 5 sentence paragraph that either celebrates a triumph, delves into a challenge, or seeks guidance and support from the community. Whether you're recounting a personal achievement, sharing a valuable lesson from a hardship, or asking for advice on a dilemma, your narrative should aim to connect, uplift, or rally the community for support. Use verbiage that is on a 8th grade reading level, and keep in mind you are 22 years old. Do not begin your content with a greeting to the audience."

        try:
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

            print('Generated and posted successfully!')
            return 'Generated and posted successfully!', None
        except Exception as e:
            print(f'Failed to generate post: {str(e)}')
            return f'Failed to generate post: {str(e)}', None


def generate_comment_core():
    with app.app_context():
        # Select a random user
        user = User.query.order_by(func.random()).first()
        
        if not user:
            print("No users available.")
            return "No users available.", None

        # Fetch user's interest IDs
        user_interest_ids = {interest.id for interest in user.interests}

        # Find posts within communities where the user shares at least one interest
        # First, get communities matching user's interests
        matching_communities = Community.query.join(User, Community.created_by == User.id) \
            .filter(User.industry_id == user.industry_id).distinct()

        # Then, find posts from these communities that the user hasn't commented on yet
        commented_post_ids = db.session.query(Comment.post_id).filter_by(user_id=user.id).subquery()
        posts = Post.query \
            .filter(Post.community_id.in_([community.id for community in matching_communities])) \
            .filter(Post.user_id != user.id, ~Post.id.in_(commented_post_ids)) \
            .order_by(func.random())

        # Select a random post from the filtered posts
        post = posts.first()

        if not post:
            print("No posts available for this user to comment on. Please try again.")
            return "No posts available for this user to comment on. Please try again.", None

        prompt = f"Read the following post titled '{post.title}' and its content: '{post.content}'. Now, craft a concise, thoughtful one or two sentence comment that either provides support, asks a clarifying question, or shares a related personal experience. Ensure your comment is concise. Use verbiage of an 8th-grade reading level in your comment, and remember that you are 22 years old."

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "system", "content": prompt}]
            )
            generated_comment = response.choices[0].message.content.strip()

            new_comment = Comment(
                content=generated_comment,
                user_id=user.id,
                post_id=post.id,
                posted_time=datetime.utcnow(),
                is_burner=False
            )
            db.session.add(new_comment)
            db.session.commit()

            print("Generated and posted comment successfully!")
            return "Generated and posted comment successfully!", None
        except Exception as e:
            print(f"Failed to generate comment: {str(e)}")
            return f"Failed to generate comment: {str(e)}", None

if __name__ == "__main__":
    message, error = generate_post_core()
    if error:
        print(error)
    else:
        print(message)

    message, error = generate_comment_core()
    if error:
        print(error)
    else:
        print(message)