# login.py - Safe Instagram login using undetected ChromeDriver

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import random
import json
import os
from fake_useragent import UserAgent

class InstagramLogin:
    def __init__(self, username: str, password: str, headless: bool = False):
        self.username = username
        self.password = password
        self.headless = headless
        self.driver = None
        self.ua = UserAgent()
        
    def setup_driver(self):
        """Initialize Chrome driver with stealth settings"""
        options = uc.ChromeOptions()
        
        if self.headless:
            options.add_argument('--headless=new')
            
        # Stealth options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins-discovery')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        
        # Random user agent
        options.add_argument(f'--user-agent={self.ua.random}')
        
        # Random viewport
        viewports = [(1366, 768), (1920, 1080), (1440, 900), (1536, 864)]
        width, height = random.choice(viewports)
        options.add_argument(f'--window-size={width},{height}')
        
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = uc.Chrome(options=options)
        
        # Execute script to hide webdriver property
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Additional stealth measures
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": self.ua.random
        })
        
        return self.driver
    
    def human_type(self, element, text: str):
        """Simulate human typing with random delays"""
        element.clear()
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
    
    def random_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Random delay to simulate human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def save_cookies(self, filepath: str = "cookies.json"):
        """Save cookies for session persistence"""
        try:
            cookies = self.driver.get_cookies()
            with open(filepath, 'w') as f:
                json.dump(cookies, f)
            print(f"Cookies saved to {filepath}")
        except Exception as e:
            print(f"Error saving cookies: {e}")
    
    def load_cookies(self, filepath: str = "cookies.json"):
        """Load saved cookies"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    cookies = json.load(f)
                
                for cookie in cookies:
                    try:
                        self.driver.add_cookie(cookie)
                    except Exception:
                        continue  # Skip invalid cookies
                        
                print(f"Cookies loaded from {filepath}")
                return True
        except Exception as e:
            print(f"Error loading cookies: {e}")
        
        return False
    
    def check_login_status(self) -> bool:
        """Check if already logged in"""
        try:
            # Navigate to Instagram homepage
            self.driver.get("https://www.instagram.com/")
            self.random_delay(3, 5)
            
            # Check for profile icon or other logged-in indicators
            profile_indicators = [
                "svg[aria-label='New post']",
                "svg[aria-label='Home']",
                "a[href*='/accounts/edit/']",
                "button[aria-label='New post']"
            ]
            
            for indicator in profile_indicators:
                try:
                    if self.driver.find_element(By.CSS_SELECTOR, indicator):
                        print("Already logged in!")
                        return True
                except NoSuchElementException:
                    continue
                    
            return False
            
        except Exception as e:
            print(f"Error checking login status: {e}")
            return False
    
    def handle_suspicious_login_attempt(self) -> bool:
        """Handle 'Suspicious Login Attempt' challenge"""
        try:
            # Look for "It was me" button
            it_was_me_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'It was me') or contains(text(), 'It Was Me')]"))
            )
            it_was_me_button.click()
            self.random_delay(2, 4)
            print("Handled 'It was me' challenge")
            return True
        except TimeoutException:
            pass
        
        # Look for "Not Now" button for phone verification
        try:
            not_now_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now') or contains(text(), 'Not now')]"))
            )
            not_now_button.click()
            self.random_delay(2, 4)
            print("Skipped phone verification")
            return True
        except TimeoutException:
            pass
            
        return False
    
    def login(self) -> bool:
        """Main login method with comprehensive error handling"""
        try:
            print("Setting up Chrome driver...")
            self.setup_driver()
            
            # Try to use saved cookies first
            self.driver.get("https://www.instagram.com/")
            self.random_delay(2, 4)
            
            if self.load_cookies():
                self.driver.refresh()
                self.random_delay(3, 5)
                
                if self.check_login_status():
                    return True
            
            print("Navigating to login page...")
            self.driver.get("https://www.instagram.com/accounts/login/")
            self.random_delay(3, 6)
            
            # Accept cookies if prompted
            try:
                accept_cookies = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Allow')]"))
                )
                accept_cookies.click()
                self.random_delay(1, 2)
            except TimeoutException:
                pass  # No cookies dialog
            
            # Wait for login form to load
            print("Waiting for login form...")
            username_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            password_input = self.driver.find_element(By.NAME, "password")
            
            # Human-like typing
            print("Entering credentials...")
            self.human_type(username_input, self.username)
            self.random_delay(1, 2)
            self.human_type(password_input, self.password)
            self.random_delay(1, 2)
            
            # Submit login form
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            print("Waiting for login to process...")
            self.random_delay(5, 8)
            
            # Handle potential challenges
            current_url = self.driver.current_url
            
            # Check for two-factor authentication
            if "challenge" in current_url:
                print("2FA or challenge detected. Manual intervention may be required.")
                self.handle_suspicious_login_attempt()
                self.random_delay(3, 5)
            
            # Check if login was successful
            if self.check_login_status():
                print("Login successful!")
                self.save_cookies()
                return True
            else:
                print("Login failed - still on login page or challenge")
                return False
                
        except TimeoutException as e:
            print(f"Timeout during login: {e}")
            return False
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def close(self):
        """Close the driver"""
        if self.driver:
            self.driver.quit()
            print("Driver closed")

# Usage example
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    username = os.getenv('INSTAGRAM_USERNAME')
    password = os.getenv('INSTAGRAM_PASSWORD')
    
    if not username or not password:
        print("Please set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD environment variables")
        exit(1)
    
    login_manager = InstagramLogin(username, password)
    
    if login_manager.login():
        print("Successfully logged in to Instagram!")
        time.sleep(5)  # Keep browser open briefly
    else:
        print("Failed to log in to Instagram")
    
    login_manager.close()
