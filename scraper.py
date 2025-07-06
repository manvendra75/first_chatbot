import requests
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict, Any
import logging
from datetime import datetime
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UmrahDataScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.data = {
            "rituals": [],
            "destinations": [],
            "hotels": [],
            "reddit_reviews": []
        }
    
    def scrape_nusuk_rituals(self):
        """Scrape Umrah rituals from Nusuk.sa"""
        logger.info("Scraping Nusuk rituals...")
        
        ritual_sections = [
            {"url": "https://www.nusuk.sa/rituals", "section": "main"},
            {"url": "https://www.nusuk.sa/rituals#entrance", "section": "entrance"},
            {"url": "https://www.nusuk.sa/rituals#access", "section": "access"},
            {"url": "https://www.nusuk.sa/rituals#miqat", "section": "miqat"},
            {"url": "https://www.nusuk.sa/rituals#ihram", "section": "ihram"},
            {"url": "https://www.nusuk.sa/rituals#sanctuary", "section": "sanctuary"},
            {"url": "https://www.nusuk.sa/rituals#tawaf", "section": "tawaf"},
            {"url": "https://www.nusuk.sa/rituals#sai", "section": "sai"},
            {"url": "https://www.nusuk.sa/rituals#ziyarah", "section": "ziyarah"}
        ]
        
        for ritual in ritual_sections:
            try:
                response = self.session.get(ritual["url"])
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract content based on section
                content_data = {
                    "section": ritual["section"],
                    "url": ritual["url"],
                    "title": "",
                    "content": "",
                    "sub_sections": []
                }
                
                # Try to find the main content area
                main_content = soup.find('main') or soup.find('div', {'class': re.compile('content|main')})
                
                if main_content:
                    # Extract title
                    title = main_content.find('h1') or main_content.find('h2')
                    if title:
                        content_data["title"] = title.get_text(strip=True)
                    
                    # Extract paragraphs and lists
                    for elem in main_content.find_all(['p', 'ul', 'ol', 'h3', 'h4']):
                        text = elem.get_text(strip=True)
                        if text:
                            if elem.name in ['h3', 'h4']:
                                content_data["sub_sections"].append({"heading": text, "content": []})
                            else:
                                if content_data["sub_sections"]:
                                    content_data["sub_sections"][-1]["content"].append(text)
                                else:
                                    content_data["content"] += text + "\n"
                
                self.data["rituals"].append(content_data)
                logger.info(f"Scraped ritual section: {ritual['section']}")
                time.sleep(1)  # Be respectful to the server
                
            except Exception as e:
                logger.error(f"Error scraping ritual {ritual['section']}: {str(e)}")
    
    def scrape_nusuk_destinations(self):
        """Scrape destination information from Nusuk.sa"""
        logger.info("Scraping Nusuk destinations...")
        
        destinations = [
            {
                "city": "makkah",
                "urls": [
                    "https://www.nusuk.sa/destination/makkah",
                    "https://www.nusuk.sa/destination/makkah#the-grand-mosque",
                    "https://www.nusuk.sa/destination/makkah#the-grand-mosque-services",
                    "https://www.nusuk.sa/destination/makkah#holy-sites",
                    "https://www.nusuk.sa/destination/makkah#shopping",
                    "https://www.nusuk.sa/destination/makkah#restaurants-and-cafes"
                ]
            },
            {
                "city": "madina",
                "urls": [
                    "https://www.nusuk.sa/destination/madina",
                    "https://www.nusuk.sa/destination/madina#prophet-mosque-services",
                    "https://www.nusuk.sa/destination/madina#attractions",
                    "https://www.nusuk.sa/destination/madina#shopping",
                    "https://www.nusuk.sa/destination/madina#restaurants-and-cafes"
                ]
            }
        ]
        
        for dest in destinations:
            city_data = {
                "city": dest["city"],
                "sections": []
            }
            
            for url in dest["urls"]:
                try:
                    response = self.session.get(url)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    section_data = {
                        "url": url,
                        "section": url.split('#')[-1] if '#' in url else "main",
                        "content": ""
                    }
                    
                    # Extract content
                    main_content = soup.find('main') or soup.find('div', {'class': re.compile('content|main')})
                    if main_content:
                        section_data["content"] = main_content.get_text(strip=True)
                    
                    city_data["sections"].append(section_data)
                    logger.info(f"Scraped {dest['city']} - {section_data['section']}")
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error scraping destination {url}: {str(e)}")
            
            self.data["destinations"].append(city_data)
    
    def scrape_funadiq_hotels(self):
        """Scrape hotel data from Funadiq"""
        logger.info("Scraping Funadiq hotels...")
        
        cities = [
            {"name": "makkah", "url": "https://www.funadiq.com/properties_makkah"},
            {"name": "madinah", "url": "https://www.funadiq.com/properties_madinah"}
        ]
        
        for city in cities:
            try:
                response = self.session.get(city["url"])
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find hotel listings
                hotels = soup.find_all('div', class_=re.compile('hotel|property|listing'))
                
                for hotel in hotels:
                    hotel_data = {
                        "city": city["name"],
                        "name": "",
                        "area": "",
                        "stars": 0,
                        "distance_to_haram": "",
                        "price": "",
                        "amenities": [],
                        "room_types": [],
                        "source": "funadiq"
                    }
                    
                    # Extract hotel name
                    name_elem = hotel.find(['h2', 'h3', 'h4'], class_=re.compile('title|name'))
                    if name_elem:
                        hotel_data["name"] = name_elem.get_text(strip=True)
                    
                    # Extract area
                    area_elem = hotel.find(text=re.compile('Area|District|Location'))
                    if area_elem:
                        hotel_data["area"] = area_elem.parent.get_text(strip=True)
                    
                    # Extract stars
                    stars_elem = hotel.find(class_=re.compile('star|rating'))
                    if stars_elem:
                        stars_text = stars_elem.get_text(strip=True)
                        stars_match = re.search(r'(\d+)', stars_text)
                        if stars_match:
                            hotel_data["stars"] = int(stars_match.group(1))
                    
                    # Extract distance to Haram
                    distance_elem = hotel.find(text=re.compile('meter|km|Haram'))
                    if distance_elem:
                        hotel_data["distance_to_haram"] = distance_elem.parent.get_text(strip=True)
                    
                    # Extract special room types
                    for room_type in ["Kaaba view", "Haram view", "walking distance", "shuttle", "prayer hall"]:
                        if hotel.find(text=re.compile(room_type, re.I)):
                            hotel_data["room_types"].append(room_type)
                    
                    if hotel_data["name"]:  # Only add if we found a name
                        self.data["hotels"].append(hotel_data)
                
                logger.info(f"Scraped {len(hotels)} hotels from {city['name']}")
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error scraping Funadiq {city['name']}: {str(e)}")
    
    def scrape_reddit_reviews(self):
        """Scrape Reddit posts about Umrah experiences"""
        logger.info("Scraping Reddit reviews...")
        
        # Note: For production, you should use Reddit API with proper authentication
        # This is a simplified example
        subreddits = ["islam", "hajj", "saudiarabia", "muslimlounge"]
        search_terms = ["umrah", "makkah hotel", "madinah hotel", "umrah experience"]
        
        reddit_data = []
        
        for subreddit in subreddits:
            for term in search_terms:
                try:
                    # Using Reddit's JSON endpoint (limited without API key)
                    url = f"https://www.reddit.com/r/{subreddit}/search.json?q={term}&restrict_sr=1&limit=10"
                    response = self.session.get(url, headers={'User-Agent': 'UmrahBot/1.0'})
                    
                    if response.status_code == 200:
                        data = response.json()
                        posts = data.get('data', {}).get('children', [])
                        
                        for post in posts:
                            post_data = post.get('data', {})
                            reddit_post = {
                                "title": post_data.get('title', ''),
                                "content": post_data.get('selftext', ''),
                                "subreddit": subreddit,
                                "score": post_data.get('score', 0),
                                "created": datetime.fromtimestamp(post_data.get('created_utc', 0)).isoformat(),
                                "url": f"https://reddit.com{post_data.get('permalink', '')}",
                                "search_term": term
                            }
                            
                            if reddit_post["title"] and reddit_post["content"]:
                                reddit_data.append(reddit_post)
                        
                        logger.info(f"Found {len(posts)} posts for '{term}' in r/{subreddit}")
                        time.sleep(2)  # Respect rate limits
                        
                except Exception as e:
                    logger.error(f"Error scraping Reddit {subreddit}/{term}: {str(e)}")
        
        self.data["reddit_reviews"] = reddit_data
    
    def save_data(self, filename="umrah_scraped_data.json"):
        """Save scraped data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        logger.info(f"Data saved to {filename}")
    
    def scrape_all(self):
        """Run all scraping functions"""
        logger.info("Starting comprehensive scraping...")
        
        self.scrape_nusuk_rituals()
        self.scrape_nusuk_destinations()
        self.scrape_funadiq_hotels()
        self.scrape_reddit_reviews()
        
        self.save_data()
        logger.info("Scraping completed!")
        
        # Print summary
        print(f"\nScraping Summary:")
        print(f"- Rituals: {len(self.data['rituals'])} sections")
        print(f"- Destinations: {len(self.data['destinations'])} cities")
        print(f"- Hotels: {len(self.data['hotels'])} properties")
        print(f"- Reddit Reviews: {len(self.data['reddit_reviews'])} posts")

if __name__ == "__main__":
    scraper = UmrahDataScraper()
    scraper.scrape_all()
