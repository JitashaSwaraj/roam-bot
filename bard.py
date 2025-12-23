from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def generate_itinerary(source, destination, start_date, end_date, no_of_day):
    prompt = f"""
    Create a {no_of_day}-day travel itinerary.

    From: {source}
    To: {destination}
    Dates: {start_date} to {end_date}

    Requirements:
    - Day-wise breakdown
    - Morning / Afternoon / Evening
    - Food suggestions
    - Budget-friendly (INR)
    """

    response = client.models.generate_content(
        model="models/gemini-flash-latest",
        contents=prompt
    )

    return response.text
