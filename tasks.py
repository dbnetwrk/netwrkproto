# Import the Flask application instance
from app import app, db, User, Post, Community, client, Comment
from app import community_interest_association  # Assuming this is defined in app.py
from sqlalchemy.sql.expression import func
from random import choice as random_choice
from datetime import datetime

def generate_post_core():
    # Create and use the application context
    with app.app_context():
        user = User.query.order_by(func.random()).first()

        if not user:
            print('User does not exist')
            return 'User does not exist', None

        
        communities = Community.query.filter_by(is_anonymous=False).all()

        community = random_choice(communities)
 
        prompt_opinion = f"Craft a post for the '{community.name}' forum, where people gather around '{community.description}'. Begin your response with a single sentence title with no quotation marks, followed by a blank line, then a single sentence or two that gives a controversial opinion you have. Make sure to keep it only one to two sentences. Use verbiage that is on an 8th grade reading level, and keep in mind that this is who you are: '{user.about_me}'. Do not begin your content with a greeting to the audience."
        #prompt_question = f"Craft a post for the '{community.name}' forum, where people gather around '{community.description}'. Begin your response with a single sentence title with no quotation marks, followed by a blank line, then a single sentence or two that asks a controversial question. Make sure to keep it only one to two sentences. Use verbiage that is on an 8th grade reading level, and keep in mind that this is who you are: '{user.about_me}'. Do not begin your content with a greeting to the audience."
        prompt_question = f"Craft a post for the '{community.name}' forum, where people gather around '{community.description}'. Your response needs to be a single sentence that asks a controversial question. Make sure to keep it only one sentence. Use verbiage that is on an 8th grade reading level, and keep in mind that this is who you are: '{user.about_me}'. Do not begin your content with a greeting to the audience."


        prompt = random_choice([prompt_question, prompt_question])


        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": prompt}]
            )
            generated_text = response.choices[0].message.content
            parts = generated_text.split('\n\n', 1)
            title = parts[0].strip() if parts else "Untitled"
            content = parts[1].strip() if len(parts) > 1 else ""
            
            new_post = Post(title=title, content=content, user_id=user.id, community_id=community.id, posted_time=datetime.utcnow())
            db.session.add(new_post)
            db.session.commit()

            print('Generated and posted successfully!')
            return 'Generated and posted successfully!', None
        except Exception as e:
            print(f'Failed to generate post: {str(e)}')
            return f'Failed to generate post: {str(e)}', None



def generate_post_core_anon():
    # Create and use the application context
    with app.app_context():
        user = User.query.order_by(func.random()).first()

        if not user:
            print('User does not exist')
            return 'User does not exist', None

        # Filter communities to only include non-anonymous ones
        communities = Community.query.filter_by(is_anonymous=True).all()

        if not communities:
            print('No non-anonymous communities available')
            return 'No non-anonymous communities available', None

        community = choice(communities)
        prompt_opinion = f"Craft a post for the '{community.name}' forum, where people gather around '{community.description}' Begin your response with a single sentence title with no quotation marks, followed by a blank line, then a one to two sentence controversial opinion you have. Make sure to keep it only one to two sentences. You are on an anonymous forum, so keep your identity hidden. Make sure to include only one of these 5 cuss words and their variations in your post: fuck, shit, hell, damnit, pissed. Use verbiage of an 8th grade reading level."
        #prompt_question = f"Craft a post for the '{community.name}' forum, where people gather around '{community.description}' Begin your response with a single sentence title with no quotation marks, followed by a blank line, then a one to two sentence controversial question you have. Make sure to keep it only one to two sentences. You are on an anonymous forum, so keep your identity hidden. Make sure to include only one of these 5 cuss words and their variations in your post: fuck, shit, hell, damnit, pissed. Use verbiage of an 8th grade reading level."
        prompt_question = f"Craft a post for the '{community.name}' forum, where people gather around '{community.description}' Your response needs to be a single sentence that asks a controversial question related to the forum topic. Make sure to keep it only one sentence, and make it concise. You are on an anonymous forum, so keep your identity hidden. Make sure to include only one of these 5 cuss words and their variations in your post: fuck, shit, hell, damnit, pissed. Use verbiage of an 8th grade reading level."

        prompt = random_choice([prompt_question, prompt_question])


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



from sqlalchemy import func



def generate_post_core_flood():
    with app.app_context():
        

        communities = Community.query.filter_by(is_anonymous=False).all()

        if not communities:
            print('No non-anonymous communities available')
            return 'No non-anonymous communities available', None

        results = []
        for community in communities:


            user = User.query.order_by(func.random()).first()

            if not user:
                print('User does not exist')
                return 'User does not exist', None

            prompt_opinion = f"Craft a post for the '{community.name}' forum, where people gather around '{community.description}'. Begin your response with a single sentence title with no quotation marks, followed by a blank line, then a single sentence or two that gives a controversial opinion you have. Make sure to keep it only one to two sentences. Use verbiage that is on an 8th grade reading level, and keep in mind that this is who you are: '{user.about_me}'. Do not begin your content with a greeting to the audience."
            #prompt_question = f"Craft a post for the '{community.name}' forum, where people gather around '{community.description}'. Begin your response with a single sentence title with no quotation marks, followed by a blank line, then a single sentence or two that asks a controversial question. Make sure to keep it only one to two sentences. Use verbiage that is on an 8th grade reading level, and keep in mind that this is who you are: '{user.about_me}'. Do not begin your content with a greeting to the audience."
            #prompt_question = f"Craft a post for the '{community.name}' forum, where this is the description '{community.description}'. Your response needs to be a single sentence that asks a controversial question that blends the forum topic with your background. Make sure to keep it only one sentence, and do not reference yourself. Use verbiage that is on an 8th grade reading level, and keep in mind that this is your about me: '{user.about_me}'. Do not put quotation marks around your response."
            prompt_question = f"Craft a post for the '{community.name}' forum, where this is the description '{community.description}'. Your response needs to be a single sentence where you are asking for help that blends the forum topic with your background. Make sure to keep it only one sentence, and make it extremely concise. Use verbiage that is on an 8th grade reading level, and keep in mind that this is your about me: '{user.about_me}'. Do not begin your question with a greeting to the audience. End your sentence with a question mark, and do not say you're looking for advice, and do not reference yourself."


            prompt = random_choice([prompt_question, prompt_question])

            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": prompt}]
                )
                generated_text = response.choices[0].message.content
                parts = generated_text.split('\n\n', 1)
                title = parts[0].strip() if parts else "Untitled"
                content = parts[1].strip() if len(parts) > 1 else ""

                new_post = Post(title=title, content=content, user_id=user.id, community_id=community.id, posted_time=datetime.utcnow())
                db.session.add(new_post)
                db.session.commit()

                results.append('Generated and posted successfully in ' + community.name)
            except Exception as e:
                print(f'Failed to generate post for {community.name}: {str(e)}')
                results.append(f'Failed to generate post for {community.name}: {str(e)}')

        return results


def generate_post_core_anon_flood():
    with app.app_context():
        

        communities = Community.query.filter_by(is_anonymous=True).all()

        if not communities:
            print('No anonymous communities available')
            return 'No anonymous communities available', None

        results = []
        for community in communities:


            user = User.query.order_by(func.random()).first()

            if not user:
                print('User does not exist')
                return 'User does not exist', None
            
            prompt_opinion = f"Craft a post for the '{community.name}' forum, where people gather around '{community.description}' Begin your response with a single sentence title with no quotation marks, followed by a blank line, then a one to two sentence controversial opinion you have. Make sure to keep it only one to two sentences. You are on an anonymous forum, so keep your identity hidden. Make sure to include only one of these 3 cuss words and their variations in your post: fuck, shit, piss. Use verbiage of an 8th grade reading level."
            #prompt_question = f"Craft a post for the '{community.name}' forum, where people gather around '{community.description}' Begin your response with a single sentence title with no quotation marks, followed by a blank line, then a one to two sentence controversial question you have. Make sure to keep it only one to two sentences. You are on an anonymous forum, so keep your identity hidden. Make sure to include only one of these 3 cuss words and their variations in your post: fuck, shit, piss. Use verbiage of an 8th grade reading level."
            #prompt_question = f"Craft a post for the '{community.name}' forum, where people gather around '{community.description}' Your response needs to be a single sentence that asks a controversial question related to the forum topic, but not about it being anonymous. Make sure to keep it only one sentence, and make it concise. You are on an anonymous forum, so keep your identity hidden. Make sure to include only one of these 5 cuss words and their variations in your post: fuck, shit, hell, damnit, pissed. Use verbiage of an 8th grade reading level, and do not put quotation marks around your response."
            prompt_question = f"Craft a post for the '{community.name}' forum, where people gather around '{community.description}' Your response needs to be a single sentence that where you are asking a controversial question related to the forum topic, but not about it being anonymous. Make sure to keep it only one sentence, and make it concise. You are on an anonymous forum, so keep your identity hidden. This is your about me: '{user.about_me}' Surprise me and decide whether or not to include one of the following cuss words: 'fuck', 'shit', 'piss'. Use verbiage of an 8th grade reading level, and do not put quotation marks around your response. Do not greet the audience, do not say looking for advice, and do not reference yourself."


            prompt = random_choice([prompt_question, prompt_question])

            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": prompt}]
                )
                generated_text = response.choices[0].message.content
                parts = generated_text.split('\n\n', 1)
                title = parts[0].strip() if parts else ""
                content = parts[1].strip() if len(parts) > 1 else ""

                new_post = Post(title=title, content=content, user_id=user.id, community_id=community.id, posted_time=datetime.utcnow())
                db.session.add(new_post)
                db.session.commit()

                results.append('Generated and posted successfully in ' + community.name)
            except Exception as e:
                print(f'Failed to generate post for {community.name}: {str(e)}')
                results.append(f'Failed to generate post for {community.name}: {str(e)}')

        return results


def generate_custom_posts(community_id, custom_prompt, num_posts):
    with app.app_context():
        community = Community.query.filter_by(id=community_id, is_anonymous=True).first()

        if not community:
            print('Community not found or not anonymous')
            return 'Community not found or not anonymous', None

        results = []
        for _ in range(num_posts):
            user = User.query.order_by(func.random()).first()

            if not user:
                print('User does not exist')
                return 'User does not exist', None

            try:
                # Note: Ensure that the custom prompt includes all necessary placeholders and is formatted correctly for use.
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": custom_prompt.format(user=user, community=community)}]
                )
                generated_text = response.choices[0].message.content
                parts = generated_text.split('\n\n', 1)
                title = parts[0].strip() if parts else ""
                content = parts[1].strip() if len(parts) > 1 else ""

                new_post = Post(title=title, content=content, user_id=user.id, community_id=community.id, posted_time=datetime.utcnow())
                db.session.add(new_post)
                db.session.commit()

                results.append(f'Generated and posted successfully in {community.name}')
            except Exception as e:
                print(f'Failed to generate post for {community.name}: {str(e)}')
                results.append(f'Failed to generate post for {community.name}: {str(e)}')

        return results




if __name__ == "__main__":


    #custom_prompt = "I need you to generate one controversial opinion about politics based on your background: {user.about_me}. Make it one sentence, and use verbiage suitable for a 8th grader. It is imporant you make it one sentence, and make it concise. Remember, you are on an anonymous forum, so don't reveal your identity. Do not wrap quotation marks around your sentence."
    custom_prompt = "I need you to generate one controversial question asking for advice, that is related to your background: {user.about_me}. Make it one sentence, and use verbiage suitable for a 8th grader. It is imporant you make it one sentence, and make it concise. Remember, you are on an anonymous forum, so don't reveal your identity. Do not wrap quotation marks around your sentence."

    generate_custom_posts(43, custom_prompt, 30)




