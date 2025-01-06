import logging
import time
from pathlib import Path
import sys
from datetime import datetime
import pytz

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.config import Config
from src.arxiv_fetcher import ArxivFetcher
from src.paper_processor import PaperProcessor
from src.output_writer import OutputWriter
from src.email_sender import EmailSender

class RelativePathFilter(logging.Filter):
    """Filter to convert absolute paths to relative paths in log messages"""
    def __init__(self, base_path):
        super().__init__()
        self.base_path = str(base_path)
        
    def filter(self, record):
        if hasattr(record, 'pathname'):
            record.pathname = record.pathname.replace(self.base_path + '/', '')
        return True

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - [%(pathname)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',  # Remove microseconds
    level=logging.INFO,
    handlers=[
        logging.FileHandler(project_root / "rag_tracker.log"),
        logging.StreamHandler()
    ]
)

# Add relative path filter to root logger
logger = logging.getLogger()
logger.addFilter(RelativePathFilter(project_root))

def run_daily_update():
    """Run daily update process"""
    try:
        # Load config
        config = Config()
        
        # Initialize components
        fetcher = ArxivFetcher(config)
        processor = PaperProcessor(config)
        writer = OutputWriter(config)
        emailer = EmailSender(config)
        
        # Fetch papers
        papers = fetcher.fetch_papers()
        if not papers:
            logger.info("No new papers to process")
            return
            
        # Process papers
        processed_papers, org_count, survey_count = processor.process_papers(papers)
        
        # Write outputs
        md_paths = writer.write_outputs(processed_papers, org_count, survey_count)  # Now only returns md_paths
        
        # Send email
        try:
            emailer.send_daily_update(md_paths)
            logger.info("Daily update completed successfully")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            
    except Exception as e:
        logger.error(f"Error in daily update: {e}")
        raise

def main():
    """Main function with scheduling"""
    while True:
        try:
            # Run daily update
            run_daily_update()
            
            # Wait for next update time (24 hours)
            logger.info("Waiting 24 hours until next update...")
            time.sleep(24 * 60 * 60)  # 24 hours in seconds
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            # Wait 1 hour before retrying on error
            time.sleep(60 * 60)

if __name__ == "__main__":
    main() 