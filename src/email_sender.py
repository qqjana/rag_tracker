import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import ssl
from datetime import datetime
from typing import List, Optional
import markdown2
import time

logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self, config):
        self.config = config
        self.smtp_server = config.smtp_server
        self.smtp_port = config.smtp_port
        self.sender_email = config.sender_email
        self.sender_password = config.sender_password
        self.recipient_emails = config.recipient_emails
        
        self.css_style = """
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                line-height: 1.6;
                padding: 20px;
                max-width: 1000px;
                margin: 0 auto;
                color: #333;
            }
            h1 { color: #2c3e50; border-bottom: 2px solid #eee; }
            h2 { color: #34495e; margin-top: 30px; }
            h3 { color: #455a64; }
            a { color: #3498db; text-decoration: none; }
            a:hover { text-decoration: underline; }
            code { background: #f8f9fa; padding: 2px 4px; border-radius: 3px; }
            pre { background: #f8f9fa; padding: 15px; border-radius: 5px; }
            .summary { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }
            .authors { margin-left: 20px; }
            .keywords { color: #666; }
            .paper-link { background: #e8f4f8; padding: 5px 10px; border-radius: 3px; }
            .org-tag { background: #dff0d8; padding: 2px 6px; border-radius: 3px; }
            .survey-tag { background: #fcf8e3; padding: 2px 6px; border-radius: 3px; }
        </style>
        """

    def update_last_email_date(self):
        """Update last email date to today's date"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            last_email_file = self.config.data_dir / 'last_email.txt'
            with open(last_email_file, 'w') as f:
                f.write(today)
            logger.info(f"Updated last email date to {today}")
        except Exception as e:
            logger.error(f"Error updating last email date: {e}")
            raise

    def convert_to_html(self, md_path: Path) -> Optional[str]:
        """Convert markdown file to HTML string with styling"""
        try:
            # Read markdown content
            with open(md_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # Convert to HTML
            html_content = markdown2.markdown(
                md_content,
                extras=['fenced-code-blocks', 'tables', 'header-ids']
            )
            
            # Wrap with HTML structure and add CSS
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Daily RAG Papers</title>
                {self.css_style}
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            
            return full_html
            
        except Exception as e:
            logger.error(f"Error converting markdown to HTML: {e}")
            return None

    def send_daily_update(self, md_paths: List[Path]):
        """Send daily update email with paper summaries"""
        MAX_RETRIES = 5
        RETRY_DELAY = 5  # seconds between retries
        
        try:
            if not md_paths:
                logger.info("No markdown files to process")
                return
                
            # Ensure md_paths is a list
            if not isinstance(md_paths, list):
                md_paths = [md_paths]
            
            # Convert all paths to Path objects if they aren't already
            md_paths = [Path(p) if not isinstance(p, Path) else p for p in md_paths]
            
            # Sort by filename (which contains the date)
            for md_path in sorted(md_paths, key=lambda x: x.name):
                logger.info(f"Processing {md_path} for email")
                
                # Get markdown content
                md_content = md_path.read_text(encoding='utf-8')
                
                # Convert markdown to HTML for email
                full_html = self.convert_to_html(md_path)
                if not full_html:
                    logger.error(f"Failed to convert {md_path} to HTML")
                    continue
                
                # Get dates and setup email
                paper_date = md_path.stem.split('_')[0]
                today = datetime.now()
                today_str = today.strftime('%Y%m%d_%H%M%S')
                
                # Save email content to log file with markdown
                email_log_dir = Path('output/email_logs')
                email_log_dir.mkdir(parents=True, exist_ok=True)
                email_log_path = email_log_dir / f"email_{paper_date}_{today_str}.txt"
                
                with open(email_log_path, 'w', encoding='utf-8') as f:
                    f.write(f"Subject: Daily RAG Papers Update ({paper_date})\n")
                    f.write(f"From: {self.sender_email}\n")
                    f.write(f"To: {', '.join(self.recipient_emails)}\n")
                    f.write(f"Sent: {today.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("\nContent (Markdown):\n")
                    f.write(md_content)
                
                # Send email
                msg = MIMEMultipart('alternative')
                msg['Subject'] = f"Daily RAG Papers Update ({paper_date})"
                msg['From'] = self.sender_email
                msg['To'] = ', '.join(self.recipient_emails)
                
                # Attach HTML version
                msg.attach(MIMEText(full_html, 'html'))
                
                # Send the email with retry
                for attempt in range(MAX_RETRIES):
                    try:
                        with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                            server.login(self.sender_email, self.sender_password)
                            server.send_message(msg)
                        
                        logger.info(f"Sent email update for {paper_date}")
                        logger.info(f"Email content saved to {email_log_path}")
                        break  # Success - exit retry loop
                        
                    except Exception as e:
                        if attempt < MAX_RETRIES - 1:  # Don't sleep on last attempt
                            logger.warning(f"Email sending attempt {attempt + 1} failed: {str(e)}")
                            logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                            time.sleep(RETRY_DELAY)
                        else:
                            logger.error(f"Failed to send email after {MAX_RETRIES} attempts")
                            raise  # Re-raise the last exception
                
                # Update last email date only if sending succeeded
                self.update_last_email_date()
                
        except Exception as e:
            logger.error(f"Error in send_daily_update: {str(e)}")
            raise