from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def generate_itinerary(source, destination, start_date, end_date, no_of_day):
    prompt = f"""
    Create a {no_of_day}-day travel itinerary
    From {source} to {destination}
    Dates: {start_date} to {end_date}
    Budget-friendly, INR
    """

    try:
        response = client.models.generate_content(
            model="models/gemini-flash-latest",
            contents=prompt
        )
        return response.text

    except Exception as e:
        print("AI Error:", e)
        return "⚠️ AI service is temporarily unavailable. Please try again later."
