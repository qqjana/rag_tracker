import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        # Get project root directory
        self.project_root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Set up directories
        self.output_dir = self.project_root / "output"
        self.daily_dir = self.output_dir / "daily"
        self.data_dir = self.project_root / "data"
        
        # Create directories if they don't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Email settings
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = os.getenv("SMTP_PORT")
        self.sender_email = os.getenv("EMAIL_SENDER")
        self.sender_password = os.getenv("EMAIL_PASSWORD", "")  # Get from environment variable
        self.recipient_emails = os.getenv("EMAIL_RECIPIENTS", "").split(",")
        
        # Keywords for paper search
        self.search_keywords = [
            "retrieval augmented generation",
            "RAG",
            "retrieval-based language model",
            "knowledge retrieval"
        ]
        
        # Survey paper keywords
        self.survey_keywords = [
            "survey",
            "review",
        ] 


        # ArXiv search parameters
        self.search_query = " OR ".join(f'"{keyword}"' for keyword in self.search_keywords)
        self.max_results = 100
        self.sort_by = "submittedDate"
        self.sort_order = "descending"

        # Major organizations to track
        self.major_orgs = [
            "Google", "DeepMind", "Anthropic", "OpenAI", "Microsoft", 
            "Meta", "Facebook", "Amazon", "Apple", "IBM", "NVIDIA", "Intel",
            "Baidu", "Tencent", "Alibaba", "Huawei",
            "Peking University", "Tsinghua University"
        ]

    