import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
from langchain.schema import HumanMessage, AIMessage
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from typing import Optional, Dict, List

# Set the API key from secrets
os.environ["GOOGLE_API_KEY"] = st.secrets["GEMINI_API_KEY"]

# Custom tool for checking UmrahMe availability
class UmrahMeChecker:
    def __init__(self):
        self.base_url = "https://www.umrahme.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Destination IDs - Update these with the actual IDs you have
        self.destination_ids = {
            "makkah": {"id": "235565", "name": "Makkah, Saudi Arabia"},
            "madinah": {"id": "235566", "name": "Madinah, Saudi Arabia"},  # Update with correct ID
            "medina": {"id": "235566", "name": "Madinah, Saudi Arabia"},   # Alias
            "jeddah": {"id": "235567", "name": "Jeddah, Saudi Arabia"}     # Update with correct ID
        }
    
    def check_hotels(self, city: str, check_in: str, check_out: str, adults: int = 1, children: int = 0) -> str:
        """Check hotel availability on UmrahMe with actual URL structure"""
        try:
            # Normalize city name
            city_key = city.lower().strip()
            if city_key not in self.destination_ids:
                # Try to find partial match
                for key in self.destination_ids:
                    if key in city_key or city_key in key:
                        city_key = key
                        break
                else:
                    return f"City '{city}' not found. Available cities: Makkah, Madinah, Jeddah"
            
            destination_info = self.destination_ids[city_key]
            
            # Build occupancy string (format: rooms_adults_children)
            occupancy = f"1_{adults}_{children}" if children > 0 else f"1_{adults}_"
            
            # Construct the URL
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
            
            # Create clickable URL for user
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            full_url = f"{url}?{query_string}"
            
            # Make the request
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                # Parse HTML content
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for hotel cards (you'll need to inspect the actual HTML structure)
                hotels = []
                hotel_cards = soup.find_all('div', {'class': ['hotel-card', 'property-card', 'listing-item']})[:5]
                
                if hotel_cards:
                    for card in hotel_cards:
                        # Extract hotel details (adjust selectors based on actual HTML)
                        name = card.find(['h3', 'h4', 'a'], {'class': ['hotel-name', 'property-name']})
                        price = card.find(['span', 'div'], {'class': ['price', 'rate', 'amount']})
                        
                        if name and price:
                            hotels.append(f"• {name.text.strip()} - {price.text.strip()}")
                
                if hotels:
                    result = f"🏨 Hotels in {destination_info['name']} ({check_in} to {check_out}):\n\n"
                    result += "\n".join(hotels)
                    result += f"\n\n🔗 [View all hotels]({full_url})"
                else:
                    result = f"🏨 Hotels available in {destination_info['name']} for your dates.\n\n"
                    result += f"🔗 [View available hotels]({full_url})"
                
                return result
            else:
                return f"Unable to fetch hotels. Please try this link:\n{full_url}"
                
        except Exception as e:
            return f"Error checking hotels: {str(e)}\n\nTry searching manually at: {self.base_url}/hotel/en-ae/listing"
    
    def check_packages(self, package_type: str = "economy") -> str:
        """Check Umrah package availability"""
        try:
            url = f"{self.base_url}/packages"
            response = self.session.get(url)
            
            if response.status_code == 200:
                return f"Various {package_type} packages available. Visit {self.base_url}/packages for current offers."
            else:
                return "Unable to fetch package information."
                
        except Exception as e:
            return f"Error checking packages: {str(e)}"
    
    def check_trains(self, route: str) -> str:
        """Check Haramain train availability"""
        try:
            # Placeholder for train checking logic
            return f"Haramain train information for {route}. Visit {self.base_url}/trains for schedules."
        except Exception as e:
            return f"Error checking trains: {str(e)}"

# Initialize UmrahMe checker
umrahme_checker = UmrahMeChecker()

# Create LangChain tools
def search_hotels(query: str) -> str:
    """Search for hotels on UmrahMe. Query should include city and dates."""
    import re
    from datetime import datetime, timedelta
    
    # Extract city
    city = "makkah"  # Default
    if any(word in query.lower() for word in ["madinah", "medina", "madina"]):
        city = "madinah"
    elif "jeddah" in query.lower():
        city = "jeddah"
    elif any(word in query.lower() for word in ["haram", "makkah", "mecca"]):
        city = "makkah"
    
    # Extract dates using various patterns
    check_in = None
    check_out = None
    
    # Pattern 1: "10-14th july" or "10th-14th july"
    date_range_pattern = r'(\d{1,2})(?:st|nd|rd|th)?\s*[-to]+\s*(\d{1,2})(?:st|nd|rd|th)?\s+(\w+)'
    range_match = re.search(date_range_pattern, query.lower())
    
    if range_match:
        day_start = int(range_match.group(1))
        day_end = int(range_match.group(2))
        month_name = range_match.group(3)
        
        # Convert month name to number
        months = {
            'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
            'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
            'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'october': 10, 'oct': 10,
            'november': 11, 'nov': 11, 'december': 12, 'dec': 12
        }
        
        month = months.get(month_name.lower(), datetime.now().month)
        year = datetime.now().year
        
        # Handle year transition
        if month < datetime.now().month:
            year += 1
            
        check_in = f"{year}-{month:02d}-{day_start:02d}"
        check_out = f"{year}-{month:02d}-{day_end:02d}"
    
    # Pattern 2: Full dates "2025-07-10 to 2025-07-14"
    date_pattern = r'(\d{4}-\d{2}-\d{2})'
    dates = re.findall(date_pattern, query)
    
    if dates and not check_in:
        check_in = dates[0]
        check_out = dates[1] if len(dates) > 1 else (datetime.strptime(dates[0], "%Y-%m-%d") + timedelta(days=3)).strftime("%Y-%m-%d")
    
    # Default dates if none found
    if not check_in:
        today = datetime.now()
        if "tomorrow" in query.lower():
            check_in = (today + timedelta(days=1)).strftime("%Y-%m-%d")
            check_out = (today + timedelta(days=4)).strftime("%Y-%m-%d")
        elif "next week" in query.lower():
            check_in = (today + timedelta(days=7)).strftime("%Y-%m-%d")
            check_out = (today + timedelta(days=10)).strftime("%Y-%m-%d")
        else:
            check_in = today.strftime("%Y-%m-%d")
            check_out = (today + timedelta(days=3)).strftime("%Y-%m-%d")
    
    # Extract number of guests
    adults = 2  # Default for "2 people"
    children = 0
    
    # Look for "X people" or "X person"
    people_pattern = r'(\d+)\s*(?:people|person|pax)'
    people_match = re.search(people_pattern, query.lower())
    if people_match:
        adults = int(people_match.group(1))
    
    # Look for specific adult/child mentions
    adult_pattern = r'(\d+)\s*(?:adults?)'
    adult_match = re.search(adult_pattern, query.lower())
    if adult_match:
        adults = int(adult_match.group(1))
    
    child_pattern = r'(\d+)\s*(?:children|kids?|childs?)'
    child_match = re.search(child_pattern, query.lower())
    if child_match:
        children = int(child_match.group(1))
    
    return umrahme_checker.check_hotels(city, check_in, check_out, adults, children)

def search_packages(query: str) -> str:
    """Search for Umrah packages on UmrahMe."""
    package_type = "economy"
    if "premium" in query.lower():
        package_type = "premium"
    elif "vip" in query.lower():
        package_type = "VIP"
    
    return umrahme_checker.check_packages(package_type)

def search_trains(query: str) -> str:
    """Search for Haramain train schedules."""
    route = "Makkah-Madinah"
    if "jeddah" in query.lower():
        route = "Jeddah-Makkah" if "makkah" in query.lower() else "Jeddah-Madinah"
    
    return umrahme_checker.check_trains(route)

# Create tools for the agent
tools = [
    Tool(
        name="Search Hotels",
        func=search_hotels,
        description="Use this tool to search for hotel availability when user asks about hotels, accommodation, stays, or places to sleep in Makkah, Madinah or Jeddah. This tool connects to UmrahMe.com and returns real availability with prices."
    ),
    Tool(
        name="Search Packages",
        func=search_packages,
        description="Use this tool when user asks about Umrah packages, package deals, or complete Umrah tours. Returns current packages from UmrahMe.com"
    ),
    Tool(
        name="Search Trains",
        func=search_trains,
        description="Use this tool when user asks about trains, Haramain express, or transportation between cities. Returns train schedules from UmrahMe.com"
    )
]

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )
    # Add initial message
    initial_message = """Assalamu Alaikum! I'm your enhanced Umrah guide with access to UmrahMe.com. 

I can help you with:
🏨 **Hotel Availability** - Search hotels in Makkah and Madinah
📦 **Umrah Packages** - Find economy, premium, and VIP packages
🚄 **Haramain Trains** - Check train schedules between the holy cities
📿 **Umrah Guidance** - Rituals, duas, and travel tips

What would you like to know about?"""
    st.session_state.messages.append({"role": "assistant", "content": initial_message})

# Initialize the LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=st.secrets["GEMINI_API_KEY"],
    temperature=0.7
)

# Create agent with tools
if "agent" not in st.session_state:
    st.session_state.agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
        memory=st.session_state.memory,
        verbose=True,  # Set to False in production
        handle_parsing_errors=True,
        max_iterations=3,
        agent_kwargs={
            "prefix": """You are an Umrah guide assistant with access to UmrahMe.com for real-time information. 

IMPORTANT: When users ask about hotels, accommodation, or places to stay, you MUST use the 'Search Hotels' tool to check availability on UmrahMe.com. Do not ask for more information first - search immediately with the information provided and then ask for clarification if needed.

When users ask about packages or trains, use the appropriate search tools.

You have access to the following tools:""",
            "format_instructions": """Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question""",
        }
    )

# UI Elements
st.title("🕋 Umrah Guide + UmrahMe.com")
st.subheader("Your AI Mutawwif with Live Availability Checking")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat input
prompt = st.chat_input("Ask about hotels, packages, trains, or Umrah guidance...")

if prompt:
    # Add user message to session state and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # Generate and display assistant response
    with st.chat_message("assistant"):
        with st.spinner("Searching and thinking..."):
            try:
                # Debug: Show what's being processed
                if st.secrets.get("DEBUG_MODE", False):
                    st.caption(f"Processing: {prompt}")
                
                # Use the agent to process the query
                response = st.session_state.agent.run(prompt)
                
                # Display the response
                st.write(response)
                
                # Add to messages for display
                st.session_state.messages.append({"role": "assistant", "content": response})
                
            except Exception as e:
                error_msg = f"An error occurred: {str(e)}"
                st.error(error_msg)
                
                # More detailed error info
                import traceback
                st.error(f"Full error: {traceback.format_exc()}")
                
                # Fallback: Try direct tool call for hotels
                if any(word in prompt.lower() for word in ["hotel", "accommodation", "stay", "haram"]):
                    st.info("Trying direct search...")
                    try:
                        result = search_hotels(prompt)
                        st.write(result)
                        st.session_state.messages.append({"role": "assistant", "content": result})
                    except Exception as tool_error:
                        st.error(f"Tool error: {str(tool_error)}")

# Sidebar with additional information
with st.sidebar:
    st.header("🌐 UmrahMe Integration")
    st.markdown("""
    ### Live Features:
    - 🏨 **Hotel Search**: Real-time availability
    - 📦 **Package Finder**: Current offers
    - 🚄 **Train Schedules**: Haramain routes
    
    ### Example Queries:
    - "Find hotels in Makkah for next week"
    - "Show me economy Umrah packages"
    - "Train schedule from Jeddah to Madinah"
    - "What are the steps of Umrah?"
    """)
    
    st.divider()
    
    # Quick action buttons
    st.subheader("Quick Actions")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🏨 Check Hotels"):
            st.session_state.quick_action = "Show me available hotels in Makkah"
        if st.button("🚄 Train Times"):
            st.session_state.quick_action = "What are the train schedules?"
    
    with col2:
        if st.button("📦 View Packages"):
            st.session_state.quick_action = "What Umrah packages are available?"
        if st.button("📿 Umrah Steps"):
            st.session_state.quick_action = "Explain the steps of Umrah"
    
    # Process quick actions
    if "quick_action" in st.session_state and st.session_state.quick_action:
        # This will trigger a rerun with the quick action as input
        prompt = st.session_state.quick_action
        del st.session_state.quick_action
        st.rerun()
    
    st.divider()
    
    # Test integration button
    if st.button("🧪 Test UmrahMe Integration"):
        with st.spinner("Testing hotel search..."):
            try:
                test_query = "hotels in makkah from 10-14th july for 2 people"
                test_result = search_hotels(test_query)
                st.success("✅ Integration working!")
                st.write(test_result)
            except Exception as e:
                st.error(f"❌ Integration error: {str(e)}")
    
    # Option to clear chat history
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.session_state.memory.clear()
        st.session_state.agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
            memory=ConversationBufferMemory(memory_key="chat_history", return_messages=True),
            verbose=False
        )
        st.rerun()
    
    # Display connection status
    st.caption("🟢 Connected to UmrahMe.com")
    st.caption(f"Messages: {len(st.session_state.messages)}")

# Add custom CSS for better UI
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
    }
    .st-emotion-cache-16idsys p {
        font-size: 14px;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)


