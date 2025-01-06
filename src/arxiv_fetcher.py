import arxiv
import pandas as pd
from datetime import datetime
import pytz
import logging
from pathlib import Path
import os
from typing import List, Dict
import urllib.parse

logger = logging.getLogger(__name__)

class ArxivFetcher:
    def __init__(self, config):
        self.config = config
        self.client = arxiv.Client()
        
    def _build_search_query(self) -> str:
        """Build arXiv search query from keywords"""
        # Format each keyword as exact phrase search
        formatted_terms = []
        for keyword in self.config.search_keywords:
            # Handle multi-word terms
            if ' ' in keyword:
                formatted_terms.append(f'"{keyword}"')
            else:
                formatted_terms.append(keyword)
                
        # Join with OR operator
        query = ' OR '.join(formatted_terms)
        logger.info(f"Search query: {query}")
        return query
        
    def fetch_papers(self) -> List[Dict]:
        """Fetch papers from ArXiv"""
        try:
            # Build search query
            query = self._build_search_query()
            
            search = arxiv.Search(
                query=query,
                max_results=self.config.max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            
            papers = []
            for result in self.client.results(search):
                # Ensure dates are timezone-aware
                published_date = result.published.replace(tzinfo=pytz.UTC)
                
                paper = {
                    'title': result.title,
                    'authors': [author.name for author in result.authors],
                    'summary': result.summary,
                    'arxiv_url': result.entry_id,
                    'pdf_url': result.pdf_url,
                    'paper_id': result.entry_id.split('/')[-1],
                    'date': published_date.strftime('%Y-%m-%d'),
                    'date_dt': published_date,
                    'categories': result.categories,
                    'is_org': False,
                    'is_survey': False,
                    'affiliations': []
                }
                papers.append(paper)
                
            logger.info(f"Found {len(papers)} total papers")
            return papers
            
        except Exception as e:
            logger.error(f"Error fetching papers: {e}")
            return [] 