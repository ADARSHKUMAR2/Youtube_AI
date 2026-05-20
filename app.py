import streamlit as st
import asyncio
import os
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import pandas as pd

# Import your agent and Pydantic model
from agent import run_youtube_agent, YouTubeResearchReport

load_dotenv(override=True)

# 1. Page Configuration
st.set_page_config(
    page_title="YouTube AI Researcher", 
    page_icon="📺", 
    layout="wide" # Changed to wide to accommodate the sidebar beautifully
)

# 2. Database Connection (Cached so it doesn't reconnect every click)
@st.cache_resource
def get_database():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri)
    # We create a database called "youtube_agent_db" and a collection called "searches"
    db = client.youtube_agent_db
    return db.searches

searches_collection = get_database()

# 3. Session State Management
# This keeps the current report on screen even if you interact with the sidebar
if "current_report" not in st.session_state:
    st.session_state.current_report = None

# --- SIDEBAR: SEARCH HISTORY ---
with st.sidebar:
    st.header("🕰️ Recent Searches")
    
    # Fetch the 10 most recent searches, sorted by newest first
    recent_searches = list(searches_collection.find().sort("timestamp", -1).limit(10))
    
    if not recent_searches:
        st.info("No search history yet.")
    else:
        for item in recent_searches:
            # Create a button for each past search
            # We use a snippet of the query as the button label
            button_label = item["user_query"][:30] + "..." if len(item["user_query"]) > 30 else item["user_query"]
            
            if st.button(f"🔍 {button_label}", key=str(item["_id"]), use_container_width=True):
                # When clicked, reconstruct the Pydantic object from the database dictionary!
                st.session_state.current_report = YouTubeResearchReport(**item["report_data"])

# --- MAIN WINDOW ---
st.title("📺 YouTube AI Research Agent")
st.markdown("Powered by **GitHub Models** & **MongoDB**.")
st.divider()

user_query = st.text_area(
    "What would you like to research?", 
    placeholder="e.g., Find a recent video about Quantum Computing and summarize its transcript.",
    height=100
)

# Action Button: Generate a NEW search
if st.button("Generate Research Report", type="primary"):
    if not user_query.strip():
        st.warning("⚠️ Please enter a topic to research.")
    else:
        with st.spinner("🤖 Agent is thinking... (Searching YouTube & Reading Transcripts)"):
            try:
                # 1. Run the AI
                report = asyncio.run(run_youtube_agent(user_query))
                
                # 2. Save to Session State for display
                st.session_state.current_report = report
                
                # 3. Save to MongoDB (Pydantic's model_dump() makes this a 1-liner!)
                searches_collection.insert_one({
                    "user_query": user_query,
                    "report_data": report.model_dump(), 
                    "timestamp": datetime.now()
                })
                
                st.success("✨ Research Complete & Saved to Database!")
                
            except Exception as e:
                st.error(f"❌ An error occurred during research:\n\n{str(e)}")

# --- RENDER THE DATA ---
# We render whatever is in the session state, whether it was just generated or clicked from the sidebar
if st.session_state.current_report:
    report = st.session_state.current_report
    
    st.header(report.topic)
    
    st.subheader("📝 Detailed Summary")
    st.info(report.summary)
    
    st.subheader("🔑 Key Takeaways")
    for takeaway in report.key_takeaways:
        st.markdown(f"- {takeaway}")
    
    st.divider()
    
    st.subheader("🔗 All Sources Analyzed")
    if report.source_urls:
        for url in report.source_urls:
            st.markdown(f"📺 [{url}]({url})")
    else:
        st.write("No sources provided.")

    if report.source_urls:
        main_url = report.source_urls[0]
        
        # Draw the embedded YouTube video
        st.video(main_url)
        
        # Display the stats in a clean 4-column layout
        st.markdown("### 📊 Video Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(label="Channel Subs", value=report.channel_subscribers)
        with col2:
            st.metric(label="👍 Likes", value=report.like_count)
        with col3:
            st.metric(label="💬 Comments", value=report.comment_count)
        with col4:
            # A clean button to open the video on YouTube directly
            st.link_button("🔗 Open on YouTube", main_url, use_container_width=True)
            
        st.divider()
    # -------------------------------------

        st.markdown("### 📈 Engagement Graph")
        
        # 1. Helper function to safely convert string API data to integers
        def safe_int(value):
            try:
                # Remove any commas just in case, and convert to integer
                return int(str(value).replace(',', ''))
            except (ValueError, TypeError):
                return 0 # Default to 0 if the data is missing or says "N/A"
                
        # 2. Create the Pandas DataFrame
        chart_data = pd.DataFrame({
            "Count": [safe_int(report.like_count), safe_int(report.comment_count)]
        }, index=["👍 Likes", "💬 Comments"])
        
        # 3. Draw the Streamlit Bar Chart
        st.bar_chart(chart_data, color="#FF0000") # YouTube Red!
        
        st.divider()
    