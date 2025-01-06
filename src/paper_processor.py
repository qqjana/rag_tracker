import logging
import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import pytz
from datetime import datetime
import re
import traceback

logger = logging.getLogger(__name__)

class PaperProcessor:
    def __init__(self, config):
        self.config = config
        self.major_orgs = config.major_orgs
        
    def _get_last_email_date(self) -> datetime:
        """Get date of last processed papers"""
        try:
            last_email_file = self.config.data_dir / 'last_email.txt'
            if last_email_file.exists():
                with open(last_email_file, 'r') as f:
                    date_str = f.read().strip()
                    return pd.to_datetime(date_str).tz_localize(pytz.UTC)
        except Exception as e:
            logger.error(f"Error reading last email date: {e}")
            
        # Default to yesterday
        return (datetime.now(pytz.UTC) - pd.Timedelta(days=1))
        
    def process_papers(self, papers):
        """Process papers and extract metadata from HTML"""
        last_processed_date = self._get_last_email_date()
        logger.info(f"Processing papers since {last_processed_date.strftime('%Y-%m-%d')}")
        
        current_papers = []
        for paper in papers:
            paper_date = paper['date_dt']
            if paper_date > last_processed_date:
                current_papers.append(paper)
        
        logger.info(f"Found {len(current_papers)} recent papers")
        
        processed_papers = []
        org_count = 0
        survey_count = 0
        
        for paper in current_papers:
            try:
                # Initialize default metadata
                paper['authors_info'] = []  # Initialize as empty list
                paper['keywords'] = []
                paper['affiliations'] = []
                paper['is_org'] = False
                paper['is_survey'] = False
                
                paper_id = paper['paper_id']
                html_url = f"https://arxiv.org/html/{paper_id}"
                response = requests.get(html_url)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract metadata
                    authors_info, paper_details = self._extract_author_info(soup)  # Now returns list of dicts and paper details
                    keywords = self._extract_keywords(soup)
                    
                    # Update paper info if HTML parsing successful
                    if authors_info:
                        paper['authors_info'] = authors_info
                        # Extract all unique affiliations
                        all_affiliations = set()
                        for author in authors_info:
                            all_affiliations.update(author['affiliations'])
                        paper['affiliations'] = list(all_affiliations)
                    
                    if keywords:
                        paper['keywords'] = keywords
                    
                    # Check if from major org
                    paper['is_org'] = any(org.lower() in ' '.join(paper['affiliations']).lower() 
                                        for org in self.major_orgs)
                    if paper['is_org']:
                        org_count += 1
                        
                    # Check if survey paper
                    paper['is_survey'] = self._check_if_survey(paper['title'], keywords)
                    if paper['is_survey']:
                        survey_count += 1
                        
                    logger.debug(f"Processed paper {paper_id} authors_info: {paper['authors_info']}")
                else:
                    logger.warning(f"Could not fetch HTML for paper {paper_id}: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Error processing paper {paper['paper_id']}: {str(e)}")
                # Continue with basic paper info even if HTML processing fails
                
            processed_papers.append(paper)
        
        processed_papers.sort(key=lambda x: (-x['is_org'], -x['is_survey'], x['title']))
        
        return processed_papers, org_count, survey_count
        
    def _check_if_org(self, affiliations):
        """Check if paper is from major organization"""
        if not affiliations:
            return False
        return any(org.lower() in ' '.join(affiliations).lower() for org in self.major_orgs)
        
    def _check_if_survey(self, title, keywords):
        """Check if paper is a survey/review"""
        survey_terms = ['survey', 'review', 'overview', 'systematic']
        text = f"{title} {' '.join(keywords)}".lower()
        return any(term in text for term in survey_terms)
        
    def _get_all_affiliations(self, authors_info):
        """Get unique affiliations from all authors"""
        affiliations = set()
        for author in authors_info:
            affiliations.update(author.get('affiliations', []))
        return list(affiliations)
        
    def _extract_author_info(self, soup):
        """Extract author names and affiliations from the HTML soup."""
        try:
            authors = []
            affiliations_map = {}
            author_block = soup.find('div', class_='ltx_authors')
            
            if not author_block:
                logger.warning("No author block found")
                return [], {'authors': [], 'affiliations': []}
            
            # First find all affiliations (they come after the author names)
            for br in author_block.find_all('br', class_='ltx_break'):
                sup = br.find_next('sup', class_='ltx_sup')
                if sup:
                    aff_num = sup.get_text().strip()
                    # Get the text after the sup as a NavigableString
                    next_text = sup.next_sibling
                    if isinstance(next_text, str):
                        aff_text = next_text.strip()
                        if aff_text:
                            affiliations_map[aff_num] = aff_text
            
            logger.debug(f"Found affiliations: {affiliations_map}")
            
            # Find the personname span that contains all authors
            person_span = author_block.find('span', class_='ltx_personname')
            if person_span:
                current_author = None
                current_name = ""
                current_affs = []
                
                # Process each child element
                for element in person_span.children:
                    if isinstance(element, str):
                        text = element.strip().strip(',')
                        if text:
                            if current_name:
                                # Save previous author if exists
                                if current_name:
                                    author_info = {
                                        'name': current_name.strip(),
                                        'email': '',
                                        'aff_numbers': current_affs,
                                        'affiliations': [affiliations_map.get(num, '') for num in current_affs]
                                    }
                                    authors.append(author_info)
                                current_name = text
                                current_affs = []
                            else:
                                current_name = text
                    elif element.name == 'sup' and 'ltx_sup' in element.get('class', []):
                        num = element.get_text().strip()
                        if num.isdigit():
                            current_affs.append(num)
                
                # Add the last author
                if current_name:
                    author_info = {
                        'name': current_name.strip(),
                        'email': '',
                        'aff_numbers': current_affs,
                        'affiliations': [affiliations_map.get(num, '') for num in current_affs]
                    }
                    authors.append(author_info)
            
            logger.debug(f"Extracted authors: {authors}")
            
            # Create paper details format
            paper_details = {
                'authors': [f"{author['name']}[{','.join(author['aff_numbers'])}]" if author['aff_numbers'] 
                           else author['name'] for author in authors],
                'affiliations': [f"[{num}] {aff}" for num, aff in sorted(affiliations_map.items())]
            }
            
            logger.debug(f"Paper details: {paper_details}")
            
            return authors, paper_details
            
        except Exception as e:
            logger.error(f"Error extracting author info: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return [], {'authors': [], 'affiliations': []}
        
    def _find_affiliation(self, soup, number):
        """Find affiliation text for a given reference number."""
        affiliations = []
        aff_block = soup.find_all('span', class_='ltx_role_affiliation')
        
        for aff in aff_block:
            if aff.find('sup', text=number):
                affiliations.append(aff.get_text().strip())
        
        return affiliations
        
    def _extract_keywords(self, soup):
        """Extract keywords from HTML"""
        keywords = []
        
        # Try keywords div
        kw_div = soup.find('div', class_='ltx_keywords')
        if kw_div:
            # Remove headers
            for header in kw_div.find_all(['h6', 'strong']):
                header.decompose()
            keywords = [k.strip() for k in kw_div.get_text().split(',')]
            
        # Try meta tags
        if not keywords:
            meta_kw = soup.find('meta', attrs={'name': 'keywords'})
            if meta_kw:
                keywords = [k.strip() for k in meta_kw.get('content', '').split(',')]
                
        return [k for k in keywords if k] 