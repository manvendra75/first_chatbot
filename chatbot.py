import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime, timedelta
import re
from rag_system import UmrahRAGSystem, initialize_rag_system
import json

# Set the API key from secrets
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

# Initialize the LLM
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    openai_api_key=st.secrets["OPENAI_API_KEY"],
    temperature=0.7
)

# Initialize RAG system
@st.cache_resource
def get_rag_system():
    return initialize_rag_system(st.secrets["OPENAI_API_KEY"])

# UmrahMe Integration Class (existing code)
class UmrahMeChecker:
    def __init__(self):
        self.base_url = "https://www.umrahme.com"
        self.destination_ids = {
            "makkah": {"id": "235565", "name": "Makkah, Saudi Arabia"},
            "madinah": {"id": "235566", "name": "Madinah, Saudi Arabia"},
            "medina": {"id": "235566", "name": "Madinah, Saudi Arabia"},
            "jeddah": {"id": "235567", "name": "Jeddah, Saudi Arabia"}
        }
    
    def parse_query(self, query: str):
        """Parse natural language query to extract city, dates, and guests"""
        city = "makkah"
        if any(word in query.lower() for word in ["madinah", "medina", "madina"]):
            city = "madinah"
        elif "jeddah" in query.lower():
            city = "jeddah"
        elif any(word in query.lower() for word in ["haram", "makkah", "mecca"]):
            city = "makkah"
        
        check_in = None
        check_out = None
        
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
        
        if not check_in:
            today = datetime.now()
            check_in = today.strftime("%Y-%m-%d")
            check_out = (today + timedelta(days=3)).strftime("%Y-%m-%d")
        
        adults = 2
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

# Enhanced Query Processor with RAG
class EnhancedQueryProcessor:
    def __init__(self, rag_system):
        self.rag = rag_system
        self.umrahme = umrahme_checker
    
    def process_query(self, query: str):
        """Process query and determine the best response approach"""
        query_lower = query.lower()
        
        # Check query type
        if any(word in query_lower for word in ["ritual", "tawaf", "sai", "ihram", "miqat", "step", "perform", "how to"]):
            return self.handle_ritual_query(query)
        
        elif any(word in query_lower for word in ["attraction", "visit", "see", "shopping", "restaurant", "cafe", "places"]):
            return self.handle_attraction_query(query)
        
        elif any(word in query_lower for word in ["hotel", "accommodation", "stay", "room", "kaaba view", "haram view"]):
            return self.handle_hotel_query(query)
        
        elif any(word in query_lower for word in ["review", "experience", "stayed", "visited", "recommend"]):
            return self.handle_review_query(query)
        
        elif any(word in query_lower for word in ["package", "deal", "offer"]):
            return self.handle_package_query(query)
        
        elif any(word in query_lower for word in ["train", "haramain", "railway"]):
            return self.handle_train_query(query)
        
        else:
            # Use RAG for general queries
            return self.handle_general_query(query)
    
    def handle_ritual_query(self, query: str):
        """Handle ritual-related queries using RAG"""
        result = self.rag.query(query, filter_dict={"type": "ritual_guide"})
        
        response = f"📿 **Umrah Ritual Guidance**\n\n{result['answer']}\n\n"
        
        if result.get('sources'):
            response += "📚 **Sources:**\n"
            for source in result['sources'][:3]:
                response += f"- {source['metadata'].get('section', 'Unknown')} from Nusuk.sa\n"
        
        return response
    
    def handle_attraction_query(self, query: str):
        """Handle attraction queries using RAG"""
        city = "makkah" if "makkah" in query.lower() or "mecca" in query.lower() else "madinah"
        
        category = None
        if "shopping" in query.lower():
            category = "shopping"
        elif "restaurant" in query.lower() or "food" in query.lower():
            category = "restaurants"
        
        result = self.rag.query_attractions(city, category)
        
        response = f"🏛️ **{city.title()} Attractions & Services**\n\n{result['answer']}\n\n"
        
        if result.get('sources'):
            response += "📍 **Information from:**\n"
            for source in result['sources'][:3]:
                response += f"- {source['metadata'].get('section', 'General').replace('_', ' ').title()}\n"
        
        return response
    
    def handle_hotel_query(self, query: str):
        """Handle hotel queries with both RAG and UmrahMe integration"""
        # First, check if user wants specific criteria hotels from our database
        if any(word in query.lower() for word in ["kaaba view", "haram view", "walking distance", "shuttle"]):
            city = "makkah" if "makkah" in query.lower() or not "madinah" in query.lower() else "madinah"
            
            filters = {
                "city": city,
                "has_kaaba_view": "kaaba view" in query.lower(),
                "walking_distance": "walking distance" in query.lower()
            }
            
            # Remove False values from filters
            filters = {k: v for k, v in filters.items() if v}
            
            result = self.rag.query_hotels(**filters)
            
            response = f"🏨 **Hotels in {city.title()} - From Our Database**\n\n"
            response += result['answer'] + "\n\n"
            
            # Also provide UmrahMe link
            city_param, check_in, check_out, adults, children = self.umrahme.parse_query(query)
            url, destination_name = self.umrahme.get_hotel_url(city_param, check_in, check_out, adults, children)
            
            if url:
                response += f"🔗 **[View live availability on UmrahMe.com]({url})**\n\n"
                response += "💡 **Note:** The hotels above are from our database. Check UmrahMe for real-time availability and current prices."
        
        else:
            # For general hotel queries, use UmrahMe
            city, check_in, check_out, adults, children = self.umrahme.parse_query(query)
            url, destination_name = self.umrahme.get_hotel_url(city, check_in, check_out, adults, children)
            
            if url:
                response = f"""🏨 **Searching hotels in {destination_name}**

📅 Check-in: {check_in}
📅 Check-out: {check_out}
👥 Guests: {adults} adults{f', {children} children' if children > 0 else ''}

🔗 **[Click here to view available hotels]({url})**

This link will show you:
- Hotels sorted by price (lowest first)
- Real-time availability
- Exact prices for your dates
- Distance from Haram
- Guest ratings and reviews

💡 **Special Hotel Categories Available:**
- 🕋 Kaaba view rooms
- 🕌 Haram view rooms
- 🚶 Haram in walking distance
- 🚌 Free shuttle to Haram
- 🤲 Haram-connected prayer hall

Would you like me to search for hotels with specific features?"""
            else:
                response = "I couldn't generate a hotel search link. Please specify a valid city (Makkah, Madinah, or Jeddah)."
        
        return response
    
    def handle_review_query(self, query: str):
        """Handle review queries using Reddit data from RAG"""
        result = self.rag.query(query, filter_dict={"type": "user_review"})
        
        response = f"💬 **User Reviews & Experiences**\n\n{result['answer']}\n\n"
        
        if result.get('sources'):
            response += "🔍 **From Reddit discussions:**\n"
            for source in result['sources'][:3]:
                response += f"- r/{source['metadata'].get('subreddit', 'unknown')} (Score: {source['metadata'].get('score', 0)})\n"
        
        response += "\n💡 **Note:** These are user experiences from Reddit. Individual experiences may vary."
        
        return response
    
    def handle_package_query(self, query: str):
        """Handle package queries"""
        response = f"""📦 **Umrah Packages on UmrahMe.com**

Browse available packages:
🔗 **[View all Umrah packages]({self.umrahme.base_url}/packages)**

Package types available:
- ⭐ Economy packages
- 💎 Premium packages  
- 👑 VIP packages

Each package typically includes:
- ✈️ Flights
- 🏨 Hotel accommodation
- 🚌 Transportation
- 📋 Visa assistance

Would you like specific package recommendations based on your budget or preferences?"""
        
        return response
    
    def handle_train_query(self, query: str):
        """Handle train queries"""
        response = f"""🚄 **Haramain Express Information**

The Haramain Express connects:
- Makkah ↔️ Madinah (2.5 hours)
- Via Jeddah and King Abdullah Economic City

🔗 **[Check train schedules]({self.umrahme.base_url}/trains)**

Train features:
- 🪑 Economy and Business class
- 🕐 Multiple daily departures
- 💼 Luggage allowance included
- 🏃 Faster than road travel

Need help booking train tickets?"""
        
        return response
    
    def handle_general_query(self, query: str):
        """Handle general queries using RAG"""
        result = self.rag.query(query)
        
        response = result['answer']
        
        if result.get('sources'):
            response += "\n\n📚 **Sources:** Information compiled from Nusuk.sa and user experiences."
        
        return response

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    initial_message = """Assalamu Alaikum! I'm your enhanced Umrah guide with access to:

🕋 **Comprehensive Umrah Information**
- Detailed ritual guides from Nusuk.sa
- Step-by-step instructions for all Umrah rites
- Makkah & Madinah attractions and services

🏨 **Hotel Database & Live Search**
- Curated hotels with special features (Kaaba view, walking distance, etc.)
- Direct integration with UmrahMe.com for live availability
- User reviews from Reddit communities

📦 **Complete Travel Planning**
- Umrah packages
- Haramain Express train information
- Shopping and dining recommendations

Just ask me anything! For example:
- "Explain the steps of Tawaf"
- "Show me hotels with Kaaba view"
- "What are the best restaurants in Madinah?"
- "Find hotels from 10-14th July for 4 people"
"""
    st.session_state.messages.append({"role": "assistant", "content": initial_message})

# Initialize RAG system status
if "rag_status" not in st.session_state:
    st.session_state.rag_status = "initializing"

# UI
st.title("🕋 Enhanced Umrah Guide with RAG")
st.subheader("AI Assistant with Knowledge Base + Live Availability")

# Show RAG system status in sidebar
with st.sidebar:
    st.header("🤖 System Status")
    
    if st.session_state.rag_status == "initializing":
        with st.spinner("Loading knowledge base..."):
            rag_system = get_rag_system()
            if rag_system:
                st.session_state.rag_status = "ready"
                st.session_state.query_processor = EnhancedQueryProcessor(rag_system)
            else:
                st.session_state.rag_status = "error"
    
    if st.session_state.rag_status == "ready":
        st.success("✅ Knowledge base loaded")
        st.info("📚 Sources available:\n- Nusuk.sa rituals\n- Destination guides\n- Hotel database\n- Reddit reviews")
    elif st.session_state.rag_status == "error":
        st.error("❌ Failed to load knowledge base")
        if st.button("🔄 Retry"):
            st.session_state.rag_status = "initializing"
            st.rerun()
    
    st.divider()
    
    # Quick search section
    st.subheader("🔍 Quick Actions")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📿 Umrah Steps"):
            st.session_state.messages.append({"role": "user", "content": "What are the complete steps of Umrah?"})
            st.rerun()
        
        if st.button("🕋 Kaaba View Hotels"):
            st.session_state.messages.append({"role": "user", "content": "Show me hotels with Kaaba view in Makkah"})
            st.rerun()
    
    with col2:
        if st.button("🏛️ Makkah Attractions"):
            st.session_state.messages.append({"role": "user", "content": "What attractions should I visit in Makkah?"})
            st.rerun()
        
        if st.button("🍽️ Madinah Food"):
            st.session_state.messages.append({"role": "user", "content": "Best restaurants in Madinah?"})
            st.rerun()
    
    st.divider()
    
    # Hotel search form
    with st.form("quick_hotel_search"):
        st.subheader("🏨 Hotel Search")
        city = st.selectbox("City", ["Makkah", "Madinah", "Jeddah"])
        check_in = st.date_input("Check-in", datetime.now())
        nights = st.number_input("Nights", min_value=1, value=3)
        guests = st.number_input("Guests", min_value=1, value=2)
        
        special_features = st.multiselect(
            "Special Features",
            ["Kaaba view", "Haram view", "Walking distance", "Free shuttle"]
        )
        
        if st.form_submit_button("Search Hotels"):
            check_out = check_in + timedelta(days=nights)
            query = f"hotels in {city} from {check_in} to {check_out} for {guests} people"
            if special_features:
                query += f" with {' and '.join(special_features)}"
            st.session_state.messages.append({"role": "user", "content": query})
            st.rerun()
    
    # Clear chat
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    st.caption("🟢 Connected to UmrahMe.com")
    st.caption(f"📚 Knowledge base: {'Ready' if st.session_state.rag_status == 'ready' else 'Loading...'}")
    st.caption(f"💬 {len(st.session_state.messages)} messages")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat input
prompt = st.chat_input("Ask about rituals, hotels, attractions, or anything Umrah-related...")

if prompt and st.session_state.rag_status == "ready":
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # Process the query
    with st.chat_message("assistant"):
        with st.spinner("Searching knowledge base..."):
            try:
                response = st.session_state.query_processor.process_query(prompt)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"Error: {str(e)}")
                fallback_response = "I encountered an error. Let me try a simpler approach..."
                
                # Fallback to basic LLM
                try:
                    llm_response = llm.invoke(prompt).content
                    st.write(llm_response)
                    st.session_state.messages.append({"role": "assistant", "content": llm_response})
                except Exception as e2:
                    st.error(f"Fallback error: {str(e2)}")

elif prompt and st.session_state.rag_status != "ready":
    st.warning("⏳ Please wait for the knowledge base to load before asking questions.")
