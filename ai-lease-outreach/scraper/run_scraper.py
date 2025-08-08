# run_scraper.py - Orchestrates pipeline: login → scrape → filter → export to CSV or call webhook

import os
import sys
import json
import csv
import requests
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
import argparse
import logging

# Import our modules
from login import InstagramLogin
from scrape_post import PostScraper
from bio_filter import BioFilter, ProfileData, LeadScore

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'scraper_run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RealEstateLeadScraper:
    def __init__(self, config: Dict):
        self.config = config
        self.instagram_login = None
        self.post_scraper = None
        self.bio_filter = None
        self.results = {
            'scraped_users': [],
            'qualified_leads': [],
            'job_stats': {
                'start_time': None,
                'end_time': None,
                'total_scraped': 0,
                'total_qualified': 0,
                'qualification_rate': 0.0
            }
        }
    
    def setup(self) -> bool:
        """Initialize all components"""
        try:
            logger.info("Setting up Instagram scraper...")
            
            # Initialize Instagram login
            self.instagram_login = InstagramLogin(
                username=self.config['instagram']['username'],
                password=self.config['instagram']['password'],
                headless=self.config.get('headless', False)
            )
            
            # Login to Instagram
            if not self.instagram_login.login():
                logger.error("Failed to login to Instagram")
                return False
            
            # Initialize scrapers
            self.post_scraper = PostScraper(self.instagram_login.driver)
            self.bio_filter = BioFilter(
                driver=self.instagram_login.driver,
                openai_api_key=self.config.get('openai_api_key')
            )
            
            logger.info("Setup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            return False
    
    def scrape_users_from_post(self, post_url: str, max_users: int = 200) -> List[str]:
        """Scrape users from a specific post (likers and commenters)"""
        logger.info(f"Scraping users from post: {post_url}")
        all_users = set()
        
        try:
            # Scrape likers
            if self.config['scraping']['include_likers']:
                logger.info("Scraping post likers...")
                likers = self.post_scraper.scrape_post_likers(
                    post_url, 
                    max_likers=self.config['scraping']['max_likers']
                )
                all_users.update(likers)
                logger.info(f"Found {len(likers)} likers")
            
            # Scrape commenters
            if self.config['scraping']['include_commenters']:
                logger.info("Scraping post commenters...")
                commenters_data = self.post_scraper.scrape_post_commenters(
                    post_url,
                    max_commenters=self.config['scraping']['max_commenters']
                )
                commenters = [c['username'] for c in commenters_data]
                all_users.update(commenters)
                logger.info(f"Found {len(commenters)} commenters")
            
            users_list = list(all_users)[:max_users]
            logger.info(f"Total unique users scraped: {len(users_list)}")
            
            return users_list
            
        except Exception as e:
            logger.error(f"Error scraping users from post: {e}")
            return []
    
    def scrape_followers_from_account(self, username: str, max_followers: int = 500) -> List[str]:
        """Scrape followers from a specific account"""
        logger.info(f"Scraping followers from @{username}")
        
        try:
            followers = self.post_scraper.scrape_followers(username, max_followers)
            logger.info(f"Found {len(followers)} followers from @{username}")
            return followers
        except Exception as e:
            logger.error(f"Error scraping followers from @{username}: {e}")
            return []
    
    def analyze_and_filter_users(self, usernames: List[str]) -> List[LeadScore]:
        """Analyze and filter users for real estate professionals"""
        logger.info(f"Analyzing {len(usernames)} users for real estate qualifications...")
        
        try:
            results = self.bio_filter.batch_analyze_profiles(usernames)
            qualified_leads = [lead for lead in results if lead.is_qualified]
            
            logger.info(f"Analysis complete: {len(qualified_leads)}/{len(results)} leads qualified")
            
            return results
        except Exception as e:
            logger.error(f"Error analyzing users: {e}")
            return []
    
    def export_to_csv(self, leads: List[LeadScore], filename: Optional[str] = None) -> str:
        """Export qualified leads to CSV"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"real_estate_leads_{timestamp}.csv"
        
        try:
            qualified_leads = [lead for lead in leads if lead.is_qualified]
            
            if not qualified_leads:
                logger.warning("No qualified leads to export")
                return ""
            
            # Prepare data for CSV
            csv_data = []
            for lead in qualified_leads:
                row = {
                    'username': lead.username,
                    'keyword_score': lead.keyword_score,
                    'gpt_score': lead.gpt_score or 0,
                    'confidence': lead.confidence,
                    'matched_keywords': ', '.join(lead.matched_keywords),
                    'profile_url': f"https://instagram.com/{lead.username}",
                    'is_qualified': lead.is_qualified
                }
                
                # Add GPT analysis data if available
                if lead.gpt_analysis:
                    row.update({
                        'agent_type': lead.gpt_analysis.get('agent_type', ''),
                        'market_focus': lead.gpt_analysis.get('market_focus', ''),
                        'gpt_reasoning': lead.gpt_analysis.get('reasoning', ''),
                        'key_indicators': ', '.join(lead.gpt_analysis.get('key_indicators', []))
                    })
                else:
                    row.update({
                        'agent_type': '',
                        'market_focus': '',
                        'gpt_reasoning': '',
                        'key_indicators': ''
                    })
                
                csv_data.append(row)
            
            # Write to CSV
            df = pd.DataFrame(csv_data)
            df.to_csv(filename, index=False)
            
            logger.info(f"Exported {len(qualified_leads)} qualified leads to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return ""
    
    def send_webhook(self, leads: List[LeadScore]) -> bool:
        """Send qualified leads to webhook URL"""
        webhook_url = self.config.get('webhook_url')
        
        if not webhook_url:
            logger.info("No webhook URL configured, skipping webhook")
            return True
        
        try:
            qualified_leads = [lead for lead in leads if lead.is_qualified]
            
            if not qualified_leads:
                logger.info("No qualified leads to send to webhook")
                return True
            
            # Prepare payload
            payload = {
                'timestamp': datetime.now().isoformat(),
                'total_leads': len(qualified_leads),
                'job_config': self.config.get('job_name', 'Instagram Scraping Job'),
                'leads': []
            }
            
            for lead in qualified_leads:
                lead_data = {
                    'username': lead.username,
                    'profile_url': f"https://instagram.com/{lead.username}",
                    'keyword_score': lead.keyword_score,
                    'gpt_score': lead.gpt_score,
                    'confidence': lead.confidence,
                    'matched_keywords': lead.matched_keywords,
                    'is_qualified': lead.is_qualified
                }
                
                if lead.gpt_analysis:
                    lead_data.update({
                        'agent_type': lead.gpt_analysis.get('agent_type'),
                        'market_focus': lead.gpt_analysis.get('market_focus'),
                        'reasoning': lead.gpt_analysis.get('reasoning')
                    })
                
                payload['leads'].append(lead_data)
            
            # Send webhook
            response = requests.post(
                webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully sent {len(qualified_leads)} leads to webhook")
                return True
            else:
                logger.error(f"Webhook failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending webhook: {e}")
            return False
    
    def run_scraping_job(self, job_config: Dict) -> Dict:
        """Execute a complete scraping job"""
        self.results['job_stats']['start_time'] = datetime.now().isoformat()
        logger.info(f"Starting scraping job: {job_config.get('name', 'Unnamed Job')}")
        
        try:
            all_scraped_users = []
            
            # Scrape from posts
            if job_config.get('post_urls'):
                for post_url in job_config['post_urls']:
                    users = self.scrape_users_from_post(
                        post_url, 
                        max_users=job_config.get('max_users_per_post', 200)
                    )
                    all_scraped_users.extend(users)
            
            # Scrape from accounts (followers)
            if job_config.get('target_accounts'):
                for account in job_config['target_accounts']:
                    followers = self.scrape_followers_from_account(
                        account,
                        max_followers=job_config.get('max_followers_per_account', 500)
                    )
                    all_scraped_users.extend(followers)
            
            # Remove duplicates
            unique_users = list(set(all_scraped_users))
            self.results['scraped_users'] = unique_users
            self.results['job_stats']['total_scraped'] = len(unique_users)
            
            logger.info(f"Scraped {len(unique_users)} unique users")
            
            # Analyze and filter users
            if unique_users:
                analysis_results = self.analyze_and_filter_users(unique_users)
                qualified_leads = [lead for lead in analysis_results if lead.is_qualified]
                
                self.results['qualified_leads'] = analysis_results
                self.results['job_stats']['total_qualified'] = len(qualified_leads)
                self.results['job_stats']['qualification_rate'] = (
                    len(qualified_leads) / len(unique_users) * 100 if unique_users else 0
                )
                
                # Export results
                if self.config.get('export_csv', True):
                    csv_filename = self.export_to_csv(analysis_results)
                    self.results['csv_file'] = csv_filename
                
                # Send webhook
                if self.config.get('webhook_url'):
                    webhook_success = self.send_webhook(analysis_results)
                    self.results['webhook_sent'] = webhook_success
            
            self.results['job_stats']['end_time'] = datetime.now().isoformat()
            
            # Log summary
            stats = self.results['job_stats']
            logger.info("="*50)
            logger.info("JOB SUMMARY:")
            logger.info(f"Total Users Scraped: {stats['total_scraped']}")
            logger.info(f"Qualified Leads: {stats['total_qualified']}")
            logger.info(f"Qualification Rate: {stats['qualification_rate']:.1f}%")
            logger.info("="*50)
            
            return self.results
            
        except Exception as e:
            logger.error(f"Scraping job failed: {e}")
            self.results['error'] = str(e)
            return self.results
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.instagram_login:
                self.instagram_login.close()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

def load_config(config_file: str = None) -> Dict:
    """Load configuration from file or environment variables"""
    load_dotenv()
    
    config = {
        'instagram': {
            'username': os.getenv('INSTAGRAM_USERNAME'),
            'password': os.getenv('INSTAGRAM_PASSWORD')
        },
        'openai_api_key': os.getenv('OPENAI_API_KEY'),
        'webhook_url': os.getenv('N8N_WEBHOOK_URL'),
        'headless': os.getenv('HEADLESS', 'false').lower() == 'true',
        'export_csv': True,
        'scraping': {
            'include_likers': True,
            'include_commenters': True,
            'max_likers': 200,
            'max_commenters': 100
        }
    }
    
    # Load from config file if provided
    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
    
    return config

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='Instagram Real Estate Lead Scraper')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--post-url', help='Instagram post URL to scrape')
    parser.add_argument('--account', help='Instagram account to scrape followers from')
    parser.add_argument('--max-users', type=int, default=200, help='Maximum users to scrape')
    parser.add_argument('--output', help='Output CSV filename')
    parser.add_argument('--job-name', default='CLI Job', help='Job name for logging')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Validate required config
    if not config['instagram']['username'] or not config['instagram']['password']:
        logger.error("Instagram credentials not provided. Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD environment variables.")
        sys.exit(1)
    
    # Create scraper
    scraper = RealEstateLeadScraper(config)
    
    try:
        # Setup
        if not scraper.setup():
            logger.error("Failed to setup scraper")
            sys.exit(1)
        
        # Prepare job configuration
        job_config = {
            'name': args.job_name,
            'max_users_per_post': args.max_users,
            'max_followers_per_account': args.max_users
        }
        
        if args.post_url:
            job_config['post_urls'] = [args.post_url]
        
        if args.account:
            job_config['target_accounts'] = [args.account.replace('@', '')]
        
        if not job_config.get('post_urls') and not job_config.get('target_accounts'):
            logger.error("Please provide either --post-url or --account")
            sys.exit(1)
        
        # Run job
        results = scraper.run_scraping_job(job_config)
        
        # Save results
        if args.output:
            scraper.export_to_csv(results['qualified_leads'], args.output)
        
        print(f"\n✅ Job completed successfully!")
        print(f"📊 Scraped: {results['job_stats']['total_scraped']} users")
        print(f"🎯 Qualified: {results['job_stats']['total_qualified']} leads")
        print(f"📈 Success Rate: {results['job_stats']['qualification_rate']:.1f}%")
        
        if results.get('csv_file'):
            print(f"💾 Results saved to: {results['csv_file']}")
        
    except KeyboardInterrupt:
        logger.info("Job interrupted by user")
    except Exception as e:
        logger.error(f"Job failed: {e}")
        sys.exit(1)
    finally:
        scraper.cleanup()

if __name__ == "__main__":
    main()
