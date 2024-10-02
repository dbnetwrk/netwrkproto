from app import app, db, Venue
from openai import OpenAI
import os
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure you have set your OpenAI API key in your environment variables
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

MAIN_CATEGORIES = [
    "Arts & Culture", "Bar", "Restaurant", "Cafe", "Coworking Space",
    "Beauty", "Wellness", "Fitness", "Club", "Park",
    "Corporate office", "Career", "Misc"
]

def get_ai_category(venue):
    logger.debug(f"Getting AI category for venue ID: {venue.id}")
    custom_prompt = f"""
    Based on the following venue information, categorize it into one of these main categories:
    {', '.join(MAIN_CATEGORIES)}
    Venue Information:
    Title: {venue.title}
    Description: {venue.description}
    Sub_category Name: {venue.category_name}
    Please respond only with the category name that best fits this venue.
    """
    logger.debug(f"Custom prompt for venue ID {venue.id}: {custom_prompt}")

    try:
        logger.debug(f"Sending request to OpenAI API for venue ID: {venue.id}")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": custom_prompt}]
        )
        generated_category = response.choices[0].message.content.strip()
        logger.debug(f"Generated category for venue ID {venue.id}: {generated_category}")
        
        # Ensure the generated category is in our list of main categories
        if generated_category not in MAIN_CATEGORIES:
            logger.debug(f"Generated category not in MAIN_CATEGORIES. Defaulting to 'Misc' for venue ID: {venue.id}")
            return "Misc"
        return generated_category
    except Exception as e:
        logger.error(f"Error in AI categorization for venue {venue.id}: {str(e)}")
        return None

def categorize_venues():
    logger.info("Starting venue categorization process")
    with app.app_context():
        venues = Venue.query.all()
        logger.debug(f"Total venues to process: {len(venues)}")
        for venue in venues:
            logger.debug(f"Processing venue ID: {venue.id}, Current main_category: {venue.main_category}")
            if venue.main_category not in MAIN_CATEGORIES:
                logger.debug(f"Venue ID {venue.id} needs categorization")
                new_category = get_ai_category(venue)
                if new_category:
                    venue.main_category = new_category
                    db.session.add(venue)
                    logger.info(f"Updated venue {venue.id} category to: {new_category}")
            else:
                logger.debug(f"Skipping venue ID {venue.id}, already has a valid main_category: {venue.main_category}")
        
        logger.debug("Committing changes to database")
        db.session.commit()
        logger.info("Categorization complete")

if __name__ == "__main__":
    logger.info("Script started")
    categorize_venues()
    logger.info("Script finished")