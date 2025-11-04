
from vertexai.generative_models import GenerativeModel
from google.cloud import aiplatform
from google.oauth2 import service_account
import os  
  
def setup_vertex_ai():
    # Read environment variables
    project_id = os.environ.get("GEMINI_PROJECT_ID")
    location = os.environ.get("GEMINI_LOCATION", "us-central1")
    credentials_path = os.environ.get("GEMINI_CREDENTIALS_PATH")

    # Load credentials from the file path (either local .env or mounted secret in Cloud Run)
    credentials = service_account.Credentials.from_service_account_file(credentials_path)

    # Initialize Vertex AI / Gemini
    aiplatform.init(   
        project=project_id,
        location=location,
        credentials=credentials
    )

    # Return a Gemini model instance
    return GenerativeModel("gemini-2.5-flash")

def get_gemini_reply(prompt, personality):
    model = setup_vertex_ai()
    system_prompt = {
        'genz': "Reply like a Gen-Z coach — short, energetic, emojis ok. 2–3 lines max.",
        'calm': "Reply calmly, short and mindful, 2–3 lines max.",
        'friendly': "Be friendly and supportive, reply in 2–3 lines max."
    }.get(personality, 'friendly')

    full_prompt = f"{system_prompt}\n\nUser: {prompt}"
    response = model.generate_content(full_prompt)
    return response.text.strip()[:300]
                            