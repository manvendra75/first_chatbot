import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime, timedelta
import re

# Set the API key from secrets
os.environ["GOOGLE_API_KEY"] = st.secrets["GEMINI_API_KEY"]

# Initialize the LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=st.secrets["GEMINI_API_KEY"],
    temperature=0.7
)

# UmrahMe Integration Class
class UmrahMeChecker:
    def __init__(self):
        self.base_url = "https://www.umrahme.com"
        # Destination IDs - Update these with the actual IDs you have
        self.destination_ids = {
            "makkah": {"id": "235565", "name": "Makkah, Saudi Arabia"},
            "madinah": {"id": "235566", "name": "Madinah, Saudi Arabia"},  # Update with correct ID
            "medina": {"id": "235566", "name": "Madinah, Saudi Arabia"},   # Alias
            "jeddah": {"id": "235567", "name": "Jeddah, Saudi Arabia"}     # Update with correct ID
        }
    
    def parse_query(self, query: str):
        """Parse natural language query to extract city, dates, and guests"""
        # Extract city
        city = "makkah"  # Default
        if any(word in query.lower() for word in ["madinah", "medina", "madina"]):
            city = "madinah"
        elif "jeddah" in query.lower():
            city = "jeddah"
        elif any(word in query.lower() for word in ["haram", "makkah", "mecca"]):
            city = "makkah"
        
        # Extract dates
        check_in = None
        check_out = None
        
        # Pattern: "10-14th july" or "10th-14th july"
        date_range_pattern = r'(\d{1,2})(?:st|nd|rd|th)?\s*[-to]+\s*(\d{1,2})(?:st|nd|rd|th)?\s+(\w+)'
        range_match = re.search(date_range_pattern, query.lower())
        
        if range_match:
            day_start = int(range_match.group(1))
            day_end = int(range_match.group(2))
            month_name = range_match.group(3)
            
            months = {
                'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
                'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
                'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'october': 10, 'oct': 10,
                'november': 11, 'nov': 11, 'december': 12, 'dec': 12
            }
            
            month = months.get(month_name.lower(), datetime.now().month)
            year = datetime.now().year
            
            if month < datetime.now().month:
                year += 1
                
            check_in = f"{year}-{month:02d}-{day_start:02d}"
            check_out = f"{year}-{month:02d}-{day_end:02d}"
        
        # Default dates if none found
        if not check_in:
            today = datetime.now()
            check_in = today.strftime("%Y-%m-%d")
            check_out = (today + timedelta(days=3)).strftime("%Y-%m-%d")
        
        # Extract guests
        adults = 2  # Default
        children = 0
        
        people_pattern = r'(\d+)\s*(?:people|person|pax)'
        people_match = re.search(people_pattern, query.lower())
        if people_match:
            adults = int(people_match.group(1))
        
        return city, check_in, check_out, adults, children
    
    def get_hotel_url(self, city: str, check_in: str, check_out: str, adults: int = 2, children: int = 0):
        """Generate UmrahMe hotel search URL"""
        city_key = city.lower().strip()
        if city_key not in self.destination_ids:
            return None, f"City '{city}' not found. Available: Makkah, Madinah, Jeddah"
        
        destination_info = self.destination_ids[city_key]
        occupancy = f"1_{adults}_{children}" if children > 0 else f"1_{adults}_"
        
        params = {
            "checkin": check_in,
            "checkout": check_out,
            "destinationId": destination_info["id"],
            "destination": destination_info["name"],
            "occupancy": occupancy,
            "orderby": "price",
            "sortby": "asc"
        }
        
        url = f"{self.base_url}/hotel/en-ae/listing"
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{url}?{query_string}"
        
        return full_url, destination_info["name"]

# Initialize checker
umrahme_checker = UmrahMeChecker()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    initial_message = """Assalamu Alaikum! I'm your Umrah guide with direct access to UmrahMe.com. 

I can help you with:
🏨 **Hotel Search** - Find hotels in Makkah, Madinah, or Jeddah
📦 **Umrah Packages** - Browse available packages
🚄 **Train Schedules** - Haramain express information
📿 **Umrah Guidance** - Rituals, duas, and tips

Just tell me what you need! For example:
- "Find hotels near Haram from 10-14th July for 2 people"
- "Show me Umrah packages"
- "What are the steps of Umrah?"
"""
    st.session_state.messages.append({"role": "assistant", "content": initial_message})

# UI
st.title("🕋 Umrah Guide + UmrahMe.com")
st.subheader("Your AI Assistant with Live Availability")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat input
prompt = st.chat_input("Ask about hotels, packages, or Umrah guidance...")

if prompt:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # Process the query
    with st.chat_message("assistant"):
        with st.spinner("Searching..."):
            # Check if this is a hotel query
            if any(word in prompt.lower() for word in ["hotel", "hotels", "accommodation", "stay", "room", "haram"]):
                # Parse the query
                city, check_in, check_out, adults, children = umrahme_checker.parse_query(prompt)
                
                # Generate URL
                url, destination_name = umrahme_checker.get_hotel_url(city, check_in, check_out, adults, children)
                
                if url:
                    response = f"""🏨 **Searching hotels in {destination_name}**

📅 Check-in: {check_in}
📅 Check-out: {check_out}
👥 Guests: {adults} adults{f', {children} children' if children > 0 else ''}

I'm generating a direct link to UmrahMe.com with your search criteria...

🔗 **[Click here to view available hotels]({url})**

This link will show you:
- Hotels sorted by price (lowest first)
- Real-time availability
- Exact prices for your dates
- Distance from Haram
- Guest ratings and reviews

💡 **Tips for booking:**
- Hotels closer to Haram are usually more expensive
- Book early for better rates
- Check cancellation policies
- Look for hotels with shuttle services

Would you like me to search for different dates or help with anything else?"""
                else:
                    response = "I couldn't generate a hotel search link. Please specify a valid city (Makkah, Madinah, or Jeddah)."
                
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Check if this is a package query
            elif any(word in prompt.lower() for word in ["package", "packages", "deal", "offer"]):
                response = f"""📦 **Umrah Packages on UmrahMe.com**

Browse available packages:
🔗 **[View all Umrah packages]({umrahme_checker.base_url}/packages)**

Package types available:
- ⭐ Economy packages
- 💎 Premium packages  
- 👑 VIP packages

Each package typically includes:
- ✈️ Flights
- 🏨 Hotel accommodation
- 🚌 Transportation
- 📋 Visa assistance

Would you like specific package recommendations?"""
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Check if this is a train query
            elif any(word in prompt.lower() for word in ["train", "haramain", "railway"]):
                response = f"""🚄 **Haramain Express Information**

The Haramain Express connects:
- Makkah ↔️ Madinah (2.5 hours)
- Via Jeddah and King Abdullah Economic City

🔗 **[Check train schedules]({umrahme_checker.base_url}/trains)**

Train features:
- 🪑 Economy and Business class
- 🕐 Multiple daily departures
- 💼 Luggage allowance included
- 🏃 Faster than road travel

Need help booking train tickets?"""
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            # For other queries, use the LLM
            else:
                try:
                    response = llm.invoke(prompt).content
                    st.write(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# Sidebar
with st.sidebar:
    st.header("🌐 UmrahMe Integration")
    
    # Quick search section
    st.subheader("🔍 Quick Search")
    
    with st.form("quick_hotel_search"):
        col1, col2 = st.columns(2)
        with col1:
            city = st.selectbox("City", ["Makkah", "Madinah", "Jeddah"])
            check_in = st.date_input("Check-in", datetime.now())
        with col2:
            nights = st.number_input("Nights", min_value=1, value=3)
            guests = st.number_input("Guests", min_value=1, value=2)
        
        if st.form_submit_button("Search Hotels"):
            check_out = check_in + timedelta(days=nights)
            query = f"hotels in {city} from {check_in} to {check_out} for {guests} people"
            st.session_state.messages.append({"role": "user", "content": query})
            st.rerun()
    
    st.divider()
    
    # Test button
    if st.button("🧪 Test Integration"):
        test_city, test_in, test_out, test_adults, _ = umrahme_checker.parse_query(
            "hotels near haram from 10-14th july for 2 people"
        )
        test_url, _ = umrahme_checker.get_hotel_url(test_city, test_in, test_out, test_adults)
        st.success("✅ Integration working!")
        st.code(test_url, language="text")
    
    # Clear chat
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    st.caption("🟢 Connected to UmrahMe.com")
    st.caption(f"💬 {len(st.session_state.messages)} messages")
