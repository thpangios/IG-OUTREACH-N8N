# bio_filter.py - Extracts bios and filters using keyword analysis or GPT scoring

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import time
import random
import re
import json
import requests
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import openai
from openai import OpenAI

@dataclass
class ProfileData:
    username: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    follower_count: Optional[int] = None
    following_count: Optional[int] = None
    post_count: Optional[int] = None
    is_verified: bool = False
    is_business_account: bool = False
    is_private: bool = False
    profile_pic_url: Optional[str] = None
    external_url: Optional[str] = None
    location: Optional[str] = None
    category: Optional[str] = None

@dataclass
class LeadScore:
    username: str
    keyword_score: int
    gpt_score: Optional[int] = None
    is_qualified: bool = False
    matched_keywords: List[str] = None
    gpt_analysis: Optional[Dict] = None
    confidence: str = "low"  # low, medium, high

class BioFilter:
    def __init__(self, driver, openai_api_key: Optional[str] = None):
        self.driver = driver
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        
        # Real estate keywords for filtering
        self.real_estate_keywords = {
            'primary': [
                'realtor', 'real estate agent', 'real estate broker', 'broker',
                'realty', 'real estate', 'properties', 'property agent',
                'estate agent', 'listing agent', 'buyer agent', 'selling agent'
            ],
            'secondary': [
                'homes', 'house', 'housing', 'residential', 'commercial',
                'investment property', 'property investment', 'mortgage',
                'lending', 'loan officer', 'first time buyer', 'home buyer',
                'seller', 'buying', 'selling', 'listings', 'mls'
            ],
            'location_indicators': [
                'license', 'licensed', 'dre', 're/max', 'remax', 'coldwell banker',
                'keller williams', 'century 21', 'sotheby', 'compass real estate',
                'exp realty', 'berkshire hathaway', 'weichert'
            ],
            'industry_terms': [
                'crs', 'gri', 'abr', 'srs', 'luxury homes', 'luxury real estate',
                'commercial real estate', 'investment advisor', 'property manager',
                'real estate developer', 'real estate investor', 'flip', 'flipping'
            ]
        }
        
        # Keywords that might indicate non-real-estate professionals
        self.exclusion_keywords = [
            'photographer', 'photography', 'interior design', 'home decor',
            'architecture', 'contractor', 'construction', 'renovation',
            'mortgage broker only', 'insurance', 'lawyer', 'attorney',
            'student', 'looking for', 'seeking', 'buyer only', 'renter'
        ]
    
    def random_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Random delay to simulate human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def parse_count_string(self, count_str: str) -> int:
        """Parse follower/following count strings like '1.2K' or '1M'"""
        try:
            if not count_str:
                return 0
                
            count_str = count_str.replace(',', '').lower().strip()
            
            if 'k' in count_str:
                return int(float(count_str.replace('k', '')) * 1000)
            elif 'm' in count_str:
                return int(float(count_str.replace('m', '')) * 1000000)
            else:
                return int(re.sub(r'[^\d]', '', count_str))
        except (ValueError, AttributeError):
            return 0
    
    def extract_profile_data(self, username: str) -> Optional[ProfileData]:
        """Extract comprehensive profile data from Instagram profile"""
        try:
            profile_url = f"https://www.instagram.com/{username}/"
            print(f"Extracting profile data for @{username}")
            
            self.driver.get(profile_url)
            self.random_delay(3, 5)
            
            # Check if profile exists and is accessible
            if "Page Not Found" in self.driver.title or "not found" in self.driver.current_url:
                print(f"Profile @{username} not found")
                return None
            
            # Parse page with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            
            profile_data = ProfileData(username=username)
            
            # Extract basic info from meta tags (more reliable)
            meta_description = soup.find("meta", {"name": "description"})
            if meta_description:
                content = meta_description.get("content", "")
                
                # Extract follower count from meta description
                follower_match = re.search(r'(\d+(?:,\d+)*|\d+\.?\d*[KM]?)\s*Followers', content, re.IGNORECASE)
                if follower_match:
                    profile_data.follower_count = self.parse_count_string(follower_match.group(1))
                
                # Extract following count
                following_match = re.search(r'(\d+(?:,\d+)*|\d+\.?\d*[KM]?)\s*Following', content, re.IGNORECASE)
                if following_match:
                    profile_data.following_count = self.parse_count_string(following_match.group(1))
                
                # Extract posts count
                posts_match = re.search(r'(\d+(?:,\d+)*|\d+\.?\d*[KM]?)\s*Posts', content, re.IGNORECASE)
                if posts_match:
                    profile_data.post_count = self.parse_count_string(posts_match.group(1))
            
            # Try to extract from page elements directly
            try:
                # Look for stats elements
                stat_elements = self.driver.find_elements(By.CSS_SELECTOR, "span[title], a[href*='followers'] span, a[href*='following'] span")
                
                for element in stat_elements:
                    try:
                        text = element.text.strip()
                        title = element.get_attribute("title") or ""
                        parent_text = element.find_element(By.XPATH, "..").text.lower()
                        
                        # Use title attribute if available (more accurate)
                        count_text = title if title else text
                        
                        if "follower" in parent_text and profile_data.follower_count == 0:
                            profile_data.follower_count = self.parse_count_string(count_text)
                        elif "following" in parent_text and profile_data.following_count == 0:
                            profile_data.following_count = self.parse_count_string(count_text)
                        elif "post" in parent_text and profile_data.post_count == 0:
                            profile_data.post_count = self.parse_count_string(count_text)
                            
                    except Exception:
                        continue
                        
            except Exception:
                pass
            
            # Extract bio
            bio_selectors = [
                "span[dir='auto']",  # Common bio selector
                "div.-vDIg span",
                "div[class*='bio'] span",
                "article div span",
                "h1 + div span"  # Often bio is after the name
            ]
            
            for selector in bio_selectors:
                try:
                    bio_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in bio_elements:
                        text = element.text.strip()
                        
                        # Bio heuristics: longer than name, contains meaningful content
                        if (len(text) > 10 and 
                            len(text) < 500 and 
                            not text.isdigit() and
                            any(keyword in text.lower() for keyword in 
                                self.real_estate_keywords['primary'] + 
                                self.real_estate_keywords['secondary'])):
                            profile_data.bio = text
                            break
                    
                    if profile_data.bio:
                        break
                        
                except Exception:
                    continue
            
            # If no bio found with keywords, try to get any bio
            if not profile_data.bio:
                try:
                    bio_elements = self.driver.find_elements(By.CSS_SELECTOR, "span[dir='auto']")
                    for element in bio_elements:
                        text = element.text.strip()
                        if 20 < len(text) < 300 and not text.isdigit():
                            profile_data.bio = text
                            break
                except Exception:
                    pass
            
            # Extract full name
            try:
                name_selectors = ["h2", "h1", "span[dir='auto']:first-child"]
                for selector in name_selectors:
                    name_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in name_elements:
                        text = element.text.strip()
                        if text and text != username and len(text) < 100:
                            profile_data.full_name = text
                            break
                    if profile_data.full_name:
                        break
            except Exception:
                pass
            
            # Check if verified
            try:
                verified_element = self.driver.find_element(By.CSS_SELECTOR, "span[title='Verified']")
                if verified_element:
                    profile_data.is_verified = True
            except NoSuchElementException:
                pass
            
            # Check if business account
            try:
                # Look for business category or "Contact" button
                business_indicators = [
                    "div[class*='category']",
                    "button[aria-label='Contact']",
                    "span:contains('Business')",
                    "div:contains('Category:')"
                ]
                
                for indicator in business_indicators:
                    try:
                        if self.driver.find_elements(By.CSS_SELECTOR, indicator):
                            profile_data.is_business_account = True
                            break
                    except:
                        continue
                        
            except Exception:
                pass
            
            # Check if private
            try:
                private_indicators = [
                    "span:contains('This account is private')",
                    "h2:contains('This Account is Private')",
                    "div:contains('private')"
                ]
                
                for indicator in private_indicators:
                    try:
                        if self.driver.find_elements(By.CSS_SELECTOR, indicator):
                            profile_data.is_private = True
                            break
                    except:
                        continue
            except Exception:
                pass
            
            # Extract external URL
            try:
                link_elements = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='http']:not([href*='instagram.com'])")
                for link in link_elements:
                    href = link.get_attribute("href")
                    if href and "instagram.com" not in href:
                        profile_data.external_url = href
                        break
            except Exception:
                pass
            
            print(f"Extracted data for @{username}: {profile_data.follower_count} followers, Bio: {profile_data.bio[:50] if profile_data.bio else 'None'}...")
            return profile_data
            
        except Exception as e:
            print(f"Error extracting profile for @{username}: {e}")
            return None
    
    def keyword_score_profile(self, profile_data: ProfileData) -> LeadScore:
        """Score profile based on keyword matching"""
        if not profile_data.bio:
            return LeadScore(
                username=profile_data.username,
                keyword_score=0,
                matched_keywords=[],
                is_qualified=False
            )
        
        bio_lower = profile_data.bio.lower()
        matched_keywords = []
        score = 0
        
        # Primary keywords (high weight)
        for keyword in self.real_estate_keywords['primary']:
            if keyword.lower() in bio_lower:
                matched_keywords.append(keyword)
                score += 20
        
        # Secondary keywords (medium weight)
        for keyword in self.real_estate_keywords['secondary']:
            if keyword.lower() in bio_lower:
                matched_keywords.append(keyword)
                score += 10
        
        # Location/company indicators (medium weight)
        for keyword in self.real_estate_keywords['location_indicators']:
            if keyword.lower() in bio_lower:
                matched_keywords.append(keyword)
                score += 15
        
        # Industry terms (low weight)
        for keyword in self.real_estate_keywords['industry_terms']:
            if keyword.lower() in bio_lower:
                matched_keywords.append(keyword)
                score += 5
        
        # Check for exclusion keywords (negative score)
        for keyword in self.exclusion_keywords:
            if keyword.lower() in bio_lower:
                score -= 10
        
        # Bonus for business account
        if profile_data.is_business_account:
            score += 10
        
        # Bonus for external URL (often real estate websites)
        if profile_data.external_url:
            score += 5
        
        # Follower count bonus (established agents likely have more followers)
        if profile_data.follower_count:
            if profile_data.follower_count > 1000:
                score += 5
            if profile_data.follower_count > 5000:
                score += 10
        
        # Cap the score at 100
        score = min(100, max(0, score))
        
        # Determine confidence based on matched keywords and score
        confidence = "low"
        if len(matched_keywords) >= 3 or score >= 60:
            confidence = "high"
        elif len(matched_keywords) >= 1 or score >= 30:
            confidence = "medium"
        
        is_qualified = score >= 40 and len(matched_keywords) > 0
        
        return LeadScore(
            username=profile_data.username,
            keyword_score=score,
            matched_keywords=matched_keywords,
            is_qualified=is_qualified,
            confidence=confidence
        )
    
    def gpt_score_profile(self, profile_data: ProfileData) -> Optional[Dict]:
        """Use GPT to analyze and score profile"""
        if not self.openai_client or not profile_data.bio:
            return None
        
        try:
            prompt = f"""
            Analyze this Instagram profile to determine if this person is a real estate professional:

            Username: @{profile_data.username}
            Full Name: {profile_data.full_name or 'Not provided'}
            Bio: "{profile_data.bio}"
            Followers: {profile_data.follower_count or 'Unknown'}
            Following: {profile_data.following_count or 'Unknown'}
            Posts: {profile_data.post_count or 'Unknown'}
            Business Account: {profile_data.is_business_account}
            Verified: {profile_data.is_verified}
            External URL: {profile_data.external_url or 'None'}

            Please analyze this profile and respond with a JSON object containing:
            {{
                "lead_score": <number 0-100>,
                "agent_type": "<realtor|broker|investor|lender|property_manager|other>",
                "market_focus": "<residential|commercial|luxury|investment|mixed|unknown>",
                "confidence": "<high|medium|low>",
                "reasoning": "<brief explanation>",
                "is_real_estate_professional": <true|false>,
                "key_indicators": ["<list of key phrases or factors that influenced the decision>"]
            }}

            Base your analysis on:
            1. Professional terminology in bio
            2. Real estate company mentions
            3. License mentions or credentials
            4. Market specialization indicators
            5. Business account status and follower count
            """

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at identifying real estate professionals from social media profiles. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=400
            )
            
            analysis = json.loads(response.choices[0].message.content)
            print(f"GPT analysis for @{profile_data.username}: {analysis['lead_score']}/100 - {analysis['confidence']}")
            
            return analysis
            
        except Exception as e:
            print(f"Error in GPT analysis: {e}")
            return None
    
    def analyze_profile(self, username: str) -> Optional[LeadScore]:
        """Complete profile analysis combining keyword and GPT scoring"""
        # Extract profile data
        profile_data = self.extract_profile_data(username)
        if not profile_data:
            return None
        
        # Keyword scoring
        lead_score = self.keyword_score_profile(profile_data)
        
        # GPT scoring (if available)
        if self.openai_client and profile_data.bio:
            gpt_analysis = self.gpt_score_profile(profile_data)
            if gpt_analysis:
                lead_score.gpt_score = gpt_analysis.get('lead_score', 0)
                lead_score.gpt_analysis = gpt_analysis
                
                # Update overall qualification based on combined scores
                combined_score = (lead_score.keyword_score + (lead_score.gpt_score or 0)) / 2
                lead_score.is_qualified = combined_score >= 50 or (
                    lead_score.keyword_score >= 40 and (lead_score.gpt_score or 0) >= 60
                )
                
                # Update confidence based on GPT analysis
                if gpt_analysis.get('confidence') == 'high':
                    lead_score.confidence = 'high'
                elif gpt_analysis.get('confidence') == 'medium' and lead_score.confidence != 'high':
                    lead_score.confidence = 'medium'
        
        return lead_score
    
    def batch_analyze_profiles(self, usernames: List[str]) -> List[LeadScore]:
        """Analyze multiple profiles with rate limiting"""
        results = []
        
        for i, username in enumerate(usernames):
            try:
                print(f"Analyzing {i+1}/{len(usernames)}: @{username}")
                
                lead_score = self.analyze_profile(username)
                if lead_score:
                    results.append(lead_score)
                    
                    if lead_score.is_qualified:
                        print(f"✅ Qualified lead: @{username} (Score: {lead_score.keyword_score})")
                    else:
                        print(f"❌ Not qualified: @{username} (Score: {lead_score.keyword_score})")
                
                # Rate limiting between profiles
                self.random_delay(2, 5)
                
            except Exception as e:
                print(f"Error analyzing @{username}: {e}")
                continue
        
        qualified_leads = [lead for lead in results if lead.is_qualified]
        print(f"\n🎯 Analysis complete: {len(qualified_leads)}/{len(results)} leads qualified")
        
        return results

# Usage example
if __name__ == "__main__":
    from login import InstagramLogin
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    instagram_username = os.getenv('INSTAGRAM_USERNAME')
    instagram_password = os.getenv('INSTAGRAM_PASSWORD')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    if not instagram_username or not instagram_password:
        print("Please set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD environment variables")
        exit(1)
    
    # Login first
    login_manager = InstagramLogin(instagram_username, instagram_password)
    
    if login_manager.login():
        # Create bio filter with the logged-in driver
        bio_filter = BioFilter(login_manager.driver, openai_api_key)
        
        # Example: Analyze some usernames
        test_usernames = input("Enter usernames to analyze (comma-separated): ").strip().split(',')
        test_usernames = [u.strip().replace('@', '') for u in test_usernames if u.strip()]
        
        if test_usernames:
            results = bio_filter.batch_analyze_profiles(test_usernames)
            
            print("\n" + "="*50)
            print("ANALYSIS RESULTS:")
            print("="*50)
            
            for result in results:
                if result.is_qualified:
                    print(f"\n✅ @{result.username}")
                    print(f"   Keyword Score: {result.keyword_score}/100")
                    if result.gpt_score:
                        print(f"   GPT Score: {result.gpt_score}/100")
                    print(f"   Confidence: {result.confidence}")
                    print(f"   Keywords: {', '.join(result.matched_keywords[:5])}")
                    if result.gpt_analysis:
                        print(f"   Agent Type: {result.gpt_analysis.get('agent_type', 'Unknown')}")
                        print(f"   Market Focus: {result.gpt_analysis.get('market_focus', 'Unknown')}")
        
        input("Press Enter to close...")
        login_manager.close()
    else:
        print("Failed to log in")
