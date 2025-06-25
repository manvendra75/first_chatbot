import streamlit as st
from datetime import datetime, timedelta
import re

st.title("🕋 UmrahMe Hotel Finder")

# Simple query input
query = st.text_input("Try: 'hotels near haram from 10-14th july for 2 people'")

if query and any(word in query.lower() for word in ["hotel", "hotels", "haram", "stay"]):
    # Parse dates from query
    date_range_pattern = r'(\d{1,2})(?:st|nd|rd|th)?\s*[-to]+\s*(\d{1,2})(?:st|nd|rd|th)?\s+(\w+)'
    range_match = re.search(date_range_pattern, query.lower())
    
    if range_match:
        day_start = int(range_match.group(1))
        day_end = int(range_match.group(2))
        month_name = range_match.group(3)
        
        months = {'july': 7, 'jul': 7}
        month = months.get(month_name.lower(), 7)
        year = 2025
        
        check_in = f"{year}-{month:02d}-{day_start:02d}"
        check_out = f"{year}-{month:02d}-{day_end:02d}"
    else:
        check_in = datetime.now().strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    
    # Extract guests
    adults = 2
    people_match = re.search(r'(\d+)\s*(?:people|person)', query.lower())
    if people_match:
        adults = int(people_match.group(1))
    
    # Generate URL
    base_url = "https://www.umrahme.com/hotel/en-ae/listing"
    params = {
        "checkin": check_in,
        "checkout": check_out,
        "destinationId": "235565",
        "destination": "Makkah, Saudi Arabia",
        "occupancy": f"1_{adults}_",
        "orderby": "price",
        "sortby": "asc"
    }
    
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    full_url = f"{base_url}?{query_string}"
    
    # Display result
    st.success("✅ Found your search!")
    st.write(f"📅 Check-in: {check_in}")
    st.write(f"📅 Check-out: {check_out}")
    st.write(f"👥 Guests: {adults}")
    st.write("🔗 Click below to see available hotels:")
    st.markdown(f"[**View Hotels on UmrahMe.com**]({full_url})")
    
    # Show the generated URL
    with st.expander("See generated URL"):
        st.code(full_url, language="text")

elif query:
    st.info("This demo only handles hotel searches. Try asking about hotels!")

# Test section
st.divider()
st.subheader("Test Patterns")
test_queries = [
    "hotels near haram from 10-14th july for 2 people",
    "find hotels in makkah for 3 people",
    "accommodation from july 10 to july 14"
]

for tq in test_queries:
    if st.button(f"Test: {tq}"):
        st.rerun()
