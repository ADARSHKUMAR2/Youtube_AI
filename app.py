import streamlit as st
import asyncio
import os
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# Import your agent functions and Pydantic models
from agent import run_youtube_agent, run_channel_agent, YouTubeResearchReport, ChannelDeepDiveReport

load_dotenv(override=True)

# 1. Page Configuration
st.set_page_config(
    page_title="YouTube AI Researcher", 
    page_icon="📺", 
    layout="wide" 
)

# 2. Database Connection
@st.cache_resource
def get_database():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri)
    db = client.youtube_agent_db
    return db.searches

searches_collection = get_database()

# 3. Session State Management (Auto-loads the most recent search)
if "current_report" not in st.session_state:
    latest_search = searches_collection.find_one(sort=[("timestamp", -1)])
    if latest_search:
        # Determine which Pydantic model to use based on the saved type
        report_type = latest_search.get("type", "video_report") # defaults to video for older records
        if report_type == "video_report":
            st.session_state.current_report = YouTubeResearchReport(**latest_search["report_data"])
        elif report_type == "channel_report":
            st.session_state.current_report = ChannelDeepDiveReport(**latest_search["report_data"])
    else:
        st.session_state.current_report = None

# --- SIDEBAR: SEARCH HISTORY ---
with st.sidebar:
    st.header("🕰️ Recent Searches")
    
    recent_searches = list(searches_collection.find().sort("timestamp", -1).limit(15))
    
    if not recent_searches:
        st.info("No search history yet.")
    else:
        for item in recent_searches:
            # Prefix with an icon depending on if it's a video or channel search
            is_channel = item.get("type") == "channel_report"
            icon = "📺" if is_channel else "🎥"
            button_label = item["user_query"][:30] + "..." if len(item["user_query"]) > 30 else item["user_query"]
            
            if st.button(f"{icon} {button_label}", key=str(item["_id"]), use_container_width=True):
                # Reconstruct the correct Pydantic object
                if is_channel:
                    st.session_state.current_report = ChannelDeepDiveReport(**item["report_data"])
                else:
                    st.session_state.current_report = YouTubeResearchReport(**item["report_data"])

# --- MAIN WINDOW ---
st.title("📺 YouTube AI Research Agent")
st.markdown("Powered by **GitHub Models** & **MongoDB**.")
st.divider()

# Create two tabs for the two different modes
tab1, tab2 = st.tabs(["🎥 Single Video Research", "📺 Channel Deep Dive"])

with tab1:
    user_query = st.text_area(
        "What would you like to research?", 
        placeholder="e.g., Find a recent video about Quantum Computing and summarize its transcript.",
        height=100,
        key="video_query"
    )

    if st.button("Generate Video Report", type="primary", key="video_btn"):
        if not user_query.strip():
            st.warning("⚠️ Please enter a topic.")
        else:
            with st.spinner("🤖 Agent is researching the video..."):
                try:
                    report = asyncio.run(run_youtube_agent(user_query))
                    st.session_state.current_report = report
                    
                    # Save to DB with explicit type
                    searches_collection.insert_one({
                        "user_query": user_query,
                        "type": "video_report",
                        "report_data": report.model_dump(), 
                        "timestamp": datetime.now()
                    })
                    st.success("✨ Research Complete!")
                    st.rerun() # Refresh page to show data below
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

with tab2:
    channel_query = st.text_input(
        "Enter a YouTube Channel Name or Handle:", 
        placeholder="e.g., Marques Brownlee or @mkbhd",
        key="channel_query"
    )

    if st.button("Analyze Channel", type="primary", key="channel_btn"):
        if not channel_query.strip():
            st.warning("⚠️ Please enter a channel name.")
        else:
            with st.spinner("🤖 Agent is analyzing the channel's recent videos..."):
                try:
                    report = asyncio.run(run_channel_agent(channel_query))
                    st.session_state.current_report = report
                    
                    # Save to DB with explicit type
                    searches_collection.insert_one({
                        "user_query": f"Channel Analysis: {channel_query}",
                        "type": "channel_report",
                        "report_data": report.model_dump(), 
                        "timestamp": datetime.now()
                    })
                    st.success("✨ Channel Analysis Complete!")
                    st.rerun() # Refresh page to show data below
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

# --- RENDER THE DATA ---
st.divider()

if st.session_state.current_report:
    report = st.session_state.current_report
    
    # ---------------------------------------------------------
    # RENDERING FOR A SINGLE VIDEO REPORT
    # ---------------------------------------------------------
    if isinstance(report, YouTubeResearchReport):
        st.header(report.topic)
        
        # 1. Video Player & Metrics Row
        if report.source_urls:
            main_url = report.source_urls[0]
            st.video(main_url)
            
            st.markdown("### 📊 Video Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(label="Channel Subs", value=report.channel_subscribers)
            with col2:
                st.metric(label="👍 Likes", value=report.like_count)
            with col3:
                st.metric(label="💬 Comments", value=report.comment_count)
            with col4:
                st.link_button("🔗 Open on YouTube", main_url, use_container_width=True)
                
            st.divider()

            # 2. Pandas Graph
            st.markdown("### 📈 Engagement Graph")
            def safe_int(value):
                try:
                    return int(str(value).replace(',', ''))
                except (ValueError, TypeError):
                    return 0
                    
            chart_data = pd.DataFrame({
                "Count": [safe_int(report.like_count), safe_int(report.comment_count)]
            }, index=["👍 Likes", "💬 Comments"])
            
            st.bar_chart(chart_data, color="#FF0000") 
            st.divider()

        # 3. Audience Sentiment
        st.subheader("🗣️ Audience Sentiment")
        sentiment_text = report.audience_sentiment.lower() if report.audience_sentiment else "not analyzed"
        if "positive" in sentiment_text or "praise" in sentiment_text:
            st.success(f"**{report.audience_sentiment}**")
        elif "negative" in sentiment_text or "skeptical" in sentiment_text or "scam" in sentiment_text:
            st.warning(f"**{report.audience_sentiment}**")
        else:
            st.info(f"**{report.audience_sentiment}**")
            
        st.divider()
        
        # 4. Text Summary & Takeaways
        st.subheader("📝 Detailed Summary")
        st.info(report.summary)
        
        st.subheader("🔑 Key Takeaways")
        for takeaway in report.key_takeaways:
            st.markdown(f"- {takeaway}")
        
        st.divider()
        
        # 5. Sources
        st.subheader("🔗 All Sources Analyzed")
        if report.source_urls:
            for url in report.source_urls:
                st.markdown(f"📺 [{url}]({url})")
        else:
            st.write("No sources provided.")

    # ---------------------------------------------------------
    # RENDERING FOR A CHANNEL DEEP DIVE REPORT
    # ---------------------------------------------------------
    elif isinstance(report, ChannelDeepDiveReport):
        st.header(f"📺 Channel Analysis: {report.channel_name}")
        
        st.subheader("🎯 Overarching Narrative")
        st.info(report.overarching_theme)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📋 Recent Topics")
            for topic in report.recent_topics:
                st.markdown(f"- {topic}")
        with col2:
            st.subheader("👥 Target Audience")
            st.write(report.target_audience)