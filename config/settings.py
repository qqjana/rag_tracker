import os
from dotenv import load_dotenv

load_dotenv()

# Email Configuration
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "").split(",")

# Target Organizations to highlight
TARGET_ORGANIZATIONS = [
    "Stanford", 
    "Allen AI", 
    "Meta AI", 
    "Google Research",
    "DeepMind",
    "University of Washington"
]

# Search keywords
SEARCH_KEYWORDS = [
    "retrieval augmented generation",
    "RAG",
    "retrieval-based language model",
    "knowledge retrieval"
]

# Update frequency (in hours)
UPDATE_FREQUENCY = 24 