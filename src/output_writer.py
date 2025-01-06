import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
import pytz
from typing import List, Dict, Optional
from collections import defaultdict
import markdown2

logger = logging.getLogger(__name__)

class OutputWriter:
    def __init__(self, config):
        self.config = config
        self.excel_path = self.config.output_dir / "papers.xlsx"
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
        
    def write_outputs(self, papers: List[Dict], org_count: int, survey_count: int) -> List[Path]:
        """Write papers to markdown and excel. Returns list of markdown paths."""
        try:
            # Group papers by date
            papers_by_date = defaultdict(list)
            for paper in papers:
                date = paper['date']
                papers_by_date[date].append(paper)
            
            # Write markdown files for each date
            md_paths = []
            for date, date_papers in papers_by_date.items():
                md_filename = f"{date}_{len(date_papers)}_{self._count_org(date_papers)}_{self._count_survey(date_papers)}.md"
                md_path = self.config.daily_dir / md_filename
                self._write_markdown(md_path, date_papers)
                md_paths.append(md_path)
            
            # Update excel
            self._update_excel(papers)
            
            logger.info(f"Saved papers to {len(md_paths)} markdown files and excel")
            return md_paths
            
        except Exception as e:
            logger.error(f"Error writing outputs: {e}")
            raise
            
    def _count_org(self, papers):
        return sum(1 for p in papers if p['is_org'])
        
    def _count_survey(self, papers):
        return sum(1 for p in papers if p['is_survey'])
        
    def _write_markdown(self, md_path: Path, papers: List[Dict]):
        """Write papers to markdown file"""
        with open(md_path, 'w', encoding='utf-8') as f:
            date = md_path.stem.split('_')[0]
            
            # Write header for Markdown
            f.write(f"# Daily RAG Papers ({date})\n\n")
            
            # Write summary
            f.write("## Summary\n")
            f.write(f"- Total papers: {len(papers)}\n")
            f.write(f"- Papers from major organizations: {self._count_org(papers)}\n")
            f.write(f"- Survey papers: {self._count_survey(papers)}\n\n")
            
            # Write paper list
            f.write("## Paper List\n\n")
            for i, paper in enumerate(papers, 1):
                # Get first author info
                first_author = "Unknown"
                if paper.get('authors_info') and paper['authors_info']:
                    first_author = paper['authors_info'][0]['name']
                    if paper['authors_info'][0]['affiliations']:
                        first_author += f" {paper['authors_info'][0]['affiliations'][0]}"
                
                # Create links with brackets
                pdf_link = f"[Pdf]({paper['pdf_url']})" if 'pdf_url' in paper else ''
                kimi_link = f"[Kimi](https://papers.cool/arxiv/{paper['paper_id']})"
                
                # Add tags
                tags = []
                if paper['is_org']:
                    tags.append('📢[Org]')
                if paper['is_survey']:
                    tags.append('📋[Survey]')
                tag_str = f" {' '.join(tags)}" if tags else ""
                
                # Write paper entry
                f.write(f"{i}.{tag_str} {paper['title']}")
                f.write(f", {first_author}, \[{pdf_link}\] \[{kimi_link}\]\n\n")
            
            # Write paper details
            f.write("## Papers\n\n")
            for i, paper in enumerate(papers, 1):
                # Add tags
                tags = []
                if paper['is_org']:
                    tags.append('📢[Org]')
                if paper['is_survey']:
                    tags.append('📋[Survey]')
                tag_str = f" {' '.join(tags)}" if tags else ""
                
                f.write(f"### {i}. {tag_str}{paper['title']}\n")
                f.write(f"- **Date**: {paper['date']}\n")
                f.write(f"- **Link**: {paper['arxiv_url']}\n")
                f.write(f"- **Kimi**: https://papers.cool/arxiv/{paper['paper_id']}\n")
                
                # Write authors and affiliations
                if paper.get('authors_info'):
                    f.write("- **Authors**: ")
                    authors = []
                    for author in paper['authors_info']:
                        if author['aff_numbers']:
                            authors.append(f"{author['name']}[{','.join(author['aff_numbers'])}]")
                        else:
                            authors.append(author['name'])
                    f.write(", ".join(authors))
                    f.write("\n")
                    
                    # Write affiliations
                    if any(author['affiliations'] for author in paper['authors_info']):
                        for author in paper['authors_info']:
                            for num, aff in zip(author['aff_numbers'], author['affiliations']):
                                f.write(f"  [{num}] {aff}\n")
                
                # Write keywords and summary
                if paper.get('keywords'):
                    f.write(f"- **Keywords**: {', '.join(paper['keywords'])}\n")
                if paper.get('summary'):
                    summary = ' '.join(paper['summary'].split())
                    f.write(f"- **Summary**: {summary}\n")
                
                f.write("\n")

    def _update_excel(self, papers: List[Dict]):
        """Update excel file with new papers"""
        # Read existing excel if it exists
        if self.excel_path.exists():
            df_existing = pd.read_excel(self.excel_path)
        else:
            df_existing = pd.DataFrame()
            
        # Convert papers to dataframe
        papers_data = []
        for paper in papers:
            paper_data = {
                'date': paper['date'],
                'title': paper['title'],
                'authors': ', '.join(paper['authors']),
                'arxiv_url': paper['arxiv_url'],
                'pdf_url': paper['pdf_url'],
                'paper_id': paper['paper_id'],
                'is_org': paper['is_org'],
                'is_survey': paper['is_survey'],
                'affiliations': ', '.join(paper['affiliations']),
                'keywords': ', '.join(paper.get('keywords', [])),
            }
            papers_data.append(paper_data)
            
        df_new = pd.DataFrame(papers_data)
        
        # Combine and remove duplicates
        if not df_existing.empty:
            df_combined = pd.concat([df_existing, df_new])
            df_combined = df_combined.drop_duplicates(subset=['paper_id'], keep='last')
        else:
            df_combined = df_new
            
        # Sort by date and save
        df_combined = df_combined.sort_values('date', ascending=False)
        df_combined.to_excel(self.excel_path, index=False)
        
   