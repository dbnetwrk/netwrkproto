from sqlalchemy import func
# Import the Flask application instance
from app import app, db, User, Post, Community, client, Comment
from app import community_interest_association  # Assuming this is defined in app.py
from sqlalchemy.sql.expression import func
from random import choice
from datetime import datetime
from random import choice as random_choice


def generate_comment_core():
    with app.app_context():
        # Select a random user
        user = User.query.order_by(func.random()).first()
        
        if not user:
            print("No users available.")
            return "No users available.", None

        # Find posts from these communities that the user hasn't commented on yet
        commented_post_ids = db.session.query(Comment.post_id).filter(Comment.user_id == user.id).subquery()
        
        # Select the most recent post from a non-anonymous community that the user hasn't commented on
        post = Post.query.join(Community, Post.community_id == Community.id) \
            .filter(Community.is_anonymous == False) \
            .filter(~Post.id.in_(commented_post_ids)) \
            .order_by(Post.id.desc()).first()  # Sorting by ID descending to get the most recent post

        if not post:
            print("No posts available for this user to comment on. Please try again.")
            return "No posts available for this user to comment on. Please try again.", None

        prompt = f"Read the following post titled '{post.title}' and its content: '{post.content}'. Now generate a two sentence comment to this post that agrees and shares a unique insight. Use verbiage of a 6th grade reading level, and use a casual tone. Do not use ANY exclamation points or the word reckon. I repeat, do not use the word reckon. You are also roleplaying as someone with this as their about me: '{user.about_me}' Do not use any proper nouns in your comment. I repeat, do not use any proper nouns in your comment."
        #prompt_question = f"Read the following post titled '{post.title}' and its content: '{post.content}'. Now generate a two sentence comment to this post that asks a question. Use verbiage of a 6th grade reading level, and use a casual tone. Do not use ANY exclamation points or the word reckon. I repeat, do not use the word reckon. You are also roleplaying as someone with this as their about me: '{user.about_me}' Do not use any proper nouns in your comment. I repeat, do not use any proper nouns in your comment."


        #prompt = random_choice([prompt_opinion, prompt_question])

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



def generate_comment_core_anon():
    with app.app_context():
        # Select a random user
        user = User.query.order_by(func.random()).first()
        
        if not user:
            print("No users available.")
            return "No users available.", None

        # Find posts from anonymous communities that the user hasn't commented on yet
        commented_post_ids = db.session.query(Comment.post_id).filter(Comment.user_id == user.id).subquery()
        
        # Select a random post from an anonymous community that the user hasn't commented on
        post = Post.query.join(Community, Post.community_id == Community.id) \
            .filter(Community.is_anonymous == True) \
            .filter(~Post.id.in_(commented_post_ids)) \
            .order_by(func.random()).first()

        if not post:
            print("No posts available for this user to comment on. Please try again.")
            return "No posts available for this user to comment on. Please try again.", None

        prompt_opinion = f"Read the following post titled '{post.title}' and its content: '{post.content}'. Now generate a two sentence comment to this post that shares a controversial opinion. Use verbiage of a 6th grade reading level, and use a casual tone. Do not use ANY exclamation points or the word reckon. I repeat, do not use the word reckon. Make sure to include only one of these 5 cuss words in your post: fuck, shit, hell, damnit, pissed. You are also roleplaying as someone with this as their about me: '{user.about_me}' Do not use any proper nouns in your comment. I repeat, do not use any proper nouns in your comment."
        prompt_question = f"Read the following post titled '{post.title}' and its content: '{post.content}'. Now generate a two sentence comment to this post that asks a controversial question. Use verbiage of a 6th grade reading level, and use a casual tone. Do not use ANY exclamation points or the word reckon. I repeat, do not use the word reckon. Make sure to include only one of these 5 cuss words in your post: fuck, shit, hell, damnit, pissed. You are also roleplaying as someone with this as their about me: '{user.about_me}' Do not use any proper nouns in your comment. I repeat, do not use any proper nouns in your comment."

        prompt = random_choice([prompt_opinion, prompt_question])

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


def generate_comments_for_all_posts():
    with app.app_context():
        # Fetch all posts, joining with communities to check if they are anonymous
        #posts = Post.query.join(Community).all()
        #posts = Post.query.join(Community).outerjoin(Comment, Post.id == Comment.post_id).filter(Comment.id == None).all()
        posts = Post.query.join(Community) \
            .outerjoin(Comment, Post.id == Comment.post_id) \
            .filter(Comment.id == None, Post.image_filename == None) \
            .all()


        if not posts:
            print("No posts available.")
            return "No posts available.", None

        results = []
        for post in posts:


            for _ in range(4):  # Generate four comments per post
                user = User.query.order_by(func.random()).first()
                if not user:
                    results.append("No users available.")
                    continue

                if post.community.is_anonymous:
                    # Use anonymous community prompts
                    #prompt_1 = f"Read the following post titled '{post.title}' and its content: '{post.content}'. Now generate a one sentence comment to this post that shares a unique insight. Use verbiage of a 6th grade reading level, and use a casual tone. Do not use ANY exclamation points or the word reckon. Make sure to include only one of these 5 cuss words in your post: fuck, shit, hell, damnit, pissed. You are also roleplaying as someone with this as their about me: '{user.about_me}' Do not use any proper nouns in your comment."
                    prompt = f"You're in a conversation with your friend. Your friend just said this: '{post.title}'. Directly respond to your friend with a 20 word personal story related to your background. Use a casual tone, with 10th grade level verbiage. Do not say you agree with your friend. Do not use ANY exclamation points or the word reckon. Make sure to include only one of these 3 cusswords in your post: fuck, shit, hell. You are also roleplaying as someone with this as their background: '{user.about_me}' Do not use any proper nouns, and do not use any introductory clauses. I repeat do not use any introductory clauses, just be direct and to the point."
                    #prompt_3 = f"Read the following post titled '{post.title}' and its content: '{post.content}'. Now generate a one sentence comment to this post that shares a respectful challenge. Use verbiage of a 6th grade reading level, and use a casual tone. Do not use ANY exclamation points or the word reckon. Make sure to include only one of these 5 cuss words in your post: fuck, shit, hell, damnit, pissed. You are also roleplaying as someone with this as their about me: '{user.about_me}' Do not use any proper nouns in your comment."
                else:
                    # Use non-anonymous community prompts
                    #prompt_1 = f"Read the following post titled '{post.title}' and its content: '{post.content}'. Now generate a one sentence comment to this post that asks a unique question. Use verbiage of a 6th grade reading level, and use a casual tone. Do not use ANY exclamation points or the word reckon or the word but. You are also roleplaying as someone with this as their about me: '{user.about_me}' Do not use any proper nouns, and do not use any introductory clauses. I repeat do not use any introductory clauses, just be direct and to the point."
                    prompt = f"You're in a conversation with your friend. Your friend just said this: '{post.title}'. Directly respond to your friend with a 20 word personal story related to your background. Use a casual tone, with 10th grade level verbiage. Do not say you agree with your friend. Do not use ANY exclamation points or the word reckon. You are also roleplaying as someone with this as their background: '{user.about_me}' Do not use any proper nouns, and do not use any introductory clauses. I repeat do not use any introductory clauses, just be direct and to the point."
                    #prompt_3 = f"Read the following post titled '{post.title}' and its content: '{post.content}'. Now generate a one sentence comment to this post that shares a unique opinion. Use verbiage of a 6th grade reading level, and use a casual tone. Do not use ANY exclamation points or the word reckon or the word but. You are also roleplaying as someone with this as their about me: '{user.about_me}' Do not use any proper nouns, and do not use any introductory clauses. I repeat do not use any introductory clauses, just be direct and to the point."

                #prompt = random_choice([prompt_2])

                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
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

                    results.append(f"Generated and posted comment successfully for post {post.id} in community {post.community.name}")
                except Exception as e:
                    results.append(f"Failed to generate comment for post {post.id} in community {post.community.name}: {str(e)}")

        return results


# To run the function and print results
if __name__ == "__main__":
    comment_results = generate_comments_for_all_posts()
    for result in comment_results:
        print(result)