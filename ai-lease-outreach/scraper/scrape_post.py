# scrape_post.py - Scrapes likers/commenters from Instagram post URLs

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import time
import random
import re
import requests
import json
from typing import List, Dict, Optional, Set
from urllib.parse import urlparse

class PostScraper:
    def __init__(self, driver):
        self.driver = driver
        self.scraped_users = set()
        
    def extract_post_id_from_url(self, post_url: str) -> Optional[str]:
        """Extract post ID from Instagram URL"""
        try:
            # Pattern for Instagram post URLs
            patterns = [
                r'/p/([A-Za-z0-9_-]+)',
                r'/reel/([A-Za-z0-9_-]+)',
                r'/tv/([A-Za-z0-9_-]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, post_url)
                if match:
                    return match.group(1)
            return None
        except Exception as e:
            print(f"Error extracting post ID: {e}")
            return None
    
    def random_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Random delay to simulate human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def scroll_element(self, element, pixels: int = 300):
        """Scroll within an element"""
        try:
            self.driver.execute_script(f"arguments[0].scrollTop += {pixels}", element)
            self.random_delay(1, 3)
        except Exception as e:
            print(f"Error scrolling element: {e}")
    
    def extract_username_from_link(self, href: str) -> Optional[str]:
        """Extract username from Instagram profile link"""
        try:
            if not href or 'instagram.com' not in href:
                return None
                
            # Remove query parameters and fragments
            clean_url = href.split('?')[0].split('#')[0]
            
            # Pattern to match Instagram usernames
            username_match = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)/?$', clean_url)
            
            if username_match:
                username = username_match.group(1)
                
                # Filter out non-username paths
                invalid_paths = [
                    'p', 'reel', 'tv', 'stories', 'explore', 'accounts', 
                    'direct', 'privacy', 'help', 'about', 'careers',
                    'press', 'api', 'jobs', 'blog', 'terms', 'developer'
                ]
                
                if username.lower() not in invalid_paths and len(username) > 0:
                    return username
                    
            return None
        except Exception as e:
            print(f"Error extracting username: {e}")
            return None
    
    def scrape_post_likers(self, post_url: str, max_likers: int = 500) -> List[str]:
        """Scrape users who liked a specific post"""
        print(f"Scraping likers from: {post_url}")
        likers = set()
        
        try:
            # Navigate to post
            self.driver.get(post_url)
            self.random_delay(3, 5)
            
            # Look for likes count and click it
            likes_selectors = [
                "a[href*='/liked_by/'] span",
                "section a span",
                "article section a span",
                "button span[title*='like']"
            ]
            
            likes_clicked = False
            for selector in likes_selectors:
                try:
                    likes_element = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    
                    # Check if this looks like a likes count
                    likes_text = likes_element.text
                    if any(word in likes_text.lower() for word in ['like', 'likes']) or likes_text.isdigit():
                        likes_element.click()
                        likes_clicked = True
                        print(f"Clicked on likes: {likes_text}")
                        break
                        
                except (TimeoutException, NoSuchElementException):
                    continue
            
            if not likes_clicked:
                # Try alternative approach - look for likes in the post HTML
                try:
                    # Find and click any link that contains liked_by
                    liked_by_link = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='liked_by']"))
                    )
                    liked_by_link.click()
                    likes_clicked = True
                    print("Clicked liked_by link")
                except TimeoutException:
                    print("Could not find likes to click")
                    return []
            
            if likes_clicked:
                self.random_delay(2, 4)
                
                # Wait for likers modal to appear
                try:
                    likers_modal = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='dialog']"))
                    )
                    print("Likers modal opened")
                except TimeoutException:
                    print("Likers modal did not appear")
                    return []
                
                # Scroll and collect likers
                scroll_attempts = 0
                max_scroll_attempts = 20
                last_count = 0
                no_progress_count = 0
                
                while len(likers) < max_likers and scroll_attempts < max_scroll_attempts:
                    # Find user links in the modal
                    user_links = likers_modal.find_elements(By.CSS_SELECTOR, "a[href*='/']")
                    
                    for link in user_links:
                        try:
                            href = link.get_attribute("href")
                            username = self.extract_username_from_link(href)
                            
                            if username and username not in likers:
                                likers.add(username)
                                
                        except Exception as e:
                            continue
                    
                    current_count = len(likers)
                    print(f"Found {current_count} likers so far...")
                    
                    # Check for progress
                    if current_count == last_count:
                        no_progress_count += 1
                        if no_progress_count > 3:  # No progress for 3 attempts
                            print("No more likers found, stopping...")
                            break
                    else:
                        no_progress_count = 0
                    
                    last_count = current_count
                    
                    # Scroll down in the modal
                    self.scroll_element(likers_modal, 300)
                    scroll_attempts += 1
                    
                    self.random_delay(2, 4)
            
        except Exception as e:
            print(f"Error scraping likers: {e}")
        
        likers_list = list(likers)
        print(f"Successfully scraped {len(likers_list)} likers")
        return likers_list
    
    def scrape_post_commenters(self, post_url: str, max_commenters: int = 200) -> List[Dict]:
        """Scrape users who commented on a specific post"""
        print(f"Scraping commenters from: {post_url}")
        commenters = []
        seen_usernames = set()
        
        try:
            # Navigate to post
            self.driver.get(post_url)
            self.random_delay(3, 5)
            
            # Try to load more comments
            load_more_attempts = 0
            max_load_attempts = 5
            
            while load_more_attempts < max_load_attempts:
                try:
                    # Look for "View all comments" or "Load more comments" button
                    load_more_selectors = [
                        "button[aria-label*='comment']",
                        "button span:contains('View')",
                        "button:contains('more')",
                        "button[type='button'] span"
                    ]
                    
                    loaded_more = False
                    for selector in load_more_selectors:
                        try:
                            load_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                            button_text = load_button.text.lower()
                            
                            if any(phrase in button_text for phrase in ['view', 'load', 'more', 'comment']):
                                load_button.click()
                                loaded_more = True
                                print(f"Clicked: {button_text}")
                                self.random_delay(2, 4)
                                break
                                
                        except (NoSuchElementException, Exception):
                            continue
                    
                    if not loaded_more:
                        break
                        
                    load_more_attempts += 1
                    
                except Exception as e:
                    break
            
            # Scroll down to load more comments
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self.random_delay(2, 3)
            
            # Parse comments using BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find comment sections
            comment_patterns = [
                {'tag': 'article', 'attrs': {}},
                {'tag': 'div', 'attrs': {'role': 'button'}},
                {'tag': 'div', 'attrs': {'class': re.compile('.*comment.*', re.I)}},
                {'tag': 'li', 'attrs': {'role': 'menuitem'}}
            ]
            
            for pattern in comment_patterns:
                comment_elements = soup.find_all(pattern['tag'], pattern['attrs'])
                
                for element in comment_elements:
                    # Look for user links within comment elements
                    user_links = element.find_all('a', href=re.compile(r'/[^/]+/?$'))
                    
                    for link in user_links:
                        href = link.get('href', '')
                        username = self.extract_username_from_link(f"https://instagram.com{href}")
                        
                        if username and username not in seen_usernames:
                            seen_usernames.add(username)
                            
                            # Try to extract the comment text
                            comment_text = ""
                            comment_span = link.find_next('span')
                            if comment_span:
                                comment_text = comment_span.get_text(strip=True)
                            
                            commenters.append({
                                'username': username,
                                'comment': comment_text[:200],  # Limit comment length
                                'profile_url': f"https://instagram.com/{username}"
                            })
                            
                            if len(commenters) >= max_commenters:
                                break
                    
                    if len(commenters) >= max_commenters:
                        break
                        
                if len(commenters) >= max_commenters:
                    break
            
            # Alternative method: Use Selenium to find comment elements directly
            if len(commenters) < 10:  # If we didn't find many comments, try direct method
                try:
                    comment_elements = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/']")
                    
                    for element in comment_elements:
                        try:
                            href = element.get_attribute("href")
                            username = self.extract_username_from_link(href)
                            
                            if username and username not in seen_usernames:
                                seen_usernames.add(username)
                                commenters.append({
                                    'username': username,
                                    'comment': "",
                                    'profile_url': href
                                })
                                
                                if len(commenters) >= max_commenters:
                                    break
                                    
                        except Exception:
                            continue
                            
                except Exception as e:
                    print(f"Error in alternative comment scraping: {e}")
            
        except Exception as e:
            print(f"Error scraping commenters: {e}")
        
        print(f"Successfully scraped {len(commenters)} commenters")
        return commenters
    
    def scrape_followers(self, username: str, max_followers: int = 500) -> List[str]:
        """Scrape followers from a user's profile"""
        print(f"Scraping followers from @{username}")
        followers = set()
        
        try:
            # Navigate to profile
            profile_url = f"https://www.instagram.com/{username}/"
            self.driver.get(profile_url)
            self.random_delay(3, 5)
            
            # Find and click followers link
            followers_selectors = [
                f"a[href='/{username}/followers/']",
                "a[href*='followers']",
                "span:contains('followers')"
            ]
            
            followers_clicked = False
            for selector in followers_selectors:
                try:
                    followers_link = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    followers_link.click()
                    followers_clicked = True
                    print("Clicked followers link")
                    break
                except (TimeoutException, NoSuchElementException):
                    continue
            
            if not followers_clicked:
                print("Could not find followers link")
                return []
            
            self.random_delay(3, 5)
            
            # Wait for followers modal
            try:
                followers_modal = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='dialog']"))
                )
                print("Followers modal opened")
            except TimeoutException:
                print("Followers modal did not appear")
                return []
            
            # Scroll and collect followers
            scroll_attempts = 0
            max_scroll_attempts = 25
            last_count = 0
            no_progress_count = 0
            
            while len(followers) < max_followers and scroll_attempts < max_scroll_attempts:
                # Find user links in the modal
                user_links = followers_modal.find_elements(By.CSS_SELECTOR, "a[href*='/']")
                
                for link in user_links:
                    try:
                        href = link.get_attribute("href")
                        username = self.extract_username_from_link(href)
                        
                        if username and username not in followers:
                            followers.add(username)
                            
                    except Exception:
                        continue
                
                current_count = len(followers)
                print(f"Found {current_count} followers so far...")
                
                # Check for progress
                if current_count == last_count:
                    no_progress_count += 1
                    if no_progress_count > 3:  # No progress for 3 attempts
                        print("No more followers found, stopping...")
                        break
                else:
                    no_progress_count = 0
                
                last_count = current_count
                
                # Scroll down in the modal
                self.scroll_element(followers_modal, 300)
                scroll_attempts += 1
                
                self.random_delay(2, 4)
        
        except Exception as e:
            print(f"Error scraping followers: {e}")
        
        followers_list = list(followers)
        print(f"Successfully scraped {len(followers_list)} followers")
        return followers_list

# Usage example
if __name__ == "__main__":
    from login import InstagramLogin
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    username = os.getenv('INSTAGRAM_USERNAME')
    password = os.getenv('INSTAGRAM_PASSWORD')
    
    if not username or not password:
        print("Please set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD environment variables")
        exit(1)
    
    # Login first
    login_manager = InstagramLogin(username, password)
    
    if login_manager.login():
        # Create scraper with the logged-in driver
        scraper = PostScraper(login_manager.driver)
        
        # Example: Scrape likers from a post
        post_url = input("Enter Instagram post URL: ").strip()
        
        if post_url:
            likers = scraper.scrape_post_likers(post_url, max_likers=100)
            print(f"Found {len(likers)} likers: {likers[:10]}...")  # Show first 10
            
            commenters = scraper.scrape_post_commenters(post_url, max_commenters=50)
            print(f"Found {len(commenters)} commenters")
            for commenter in commenters[:5]:  # Show first 5
                print(f"@{commenter['username']}: {commenter['comment'][:50]}...")
        
        input("Press Enter to close...")
        login_manager.close()
    else:
        print("Failed to log in")
