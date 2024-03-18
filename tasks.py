# tasks.py
from app import db, User, Post, Community, client, create_app
# Import any other necessary items from your app
from sqlalchemy.sql.expression import func
from random import choice

def generate_post_core():
    app = create_app()
    with app.app_context():
        user = User.query.order_by(func.random()).first()
        
        if not user:
            print('User does not exist')
            return 'User does not exist', None

        user_interest_ids = {interest.id for interest in user.interests}
        communities = Community.query \
            .join(community_interest_association, Community.id == community_interest_association.c.community_id) \
            .filter(community_interest_association.c.interest_id.in_(user_interest_ids)).distinct()

        if communities.count() == 0:
            print('No communities found with matching interests')
            return 'No communities found with matching interests', None

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
