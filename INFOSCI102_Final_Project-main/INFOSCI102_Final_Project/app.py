import streamlit as st
import plotly.express as px
from datetime import date
import energy_logic as logic

# Page Configuration
st.set_page_config(
    page_title="Creative Energy Tracker",
    page_icon="🌿",
    layout="wide"
)

st.markdown("""
    <style>
    .main {
        background-color: #f0f4f0;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    h1, h2, h3 {
        color: #2e7d32;
    }
    </style>
    """, unsafe_allow_html=True)

# Sidebar Navigation
st.sidebar.title("🌿 Navigation")
page = st.sidebar.radio("Go to", ["Home", "Log Activity", "View Logs", "Analyze Patterns", "About"])

# Initialize files
logic.create_activity_file_if_needed()
logic.create_log_file_if_needed()

# --- HOME PAGE ---
if page == "Home":
    st.title("Creative Energy Tracker")
    st.subheader("Understand your flow, focus, and fulfillment.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("""
        Welcome to the **Creative Energy Tracker**! This app is designed to help you look beyond 
        traditional productivity metrics. Instead of just tracking 'what' you did, we track 
        'how' it made you feel.
        
        By logging your daily activities and rating them across five key dimensions, you can 
        start to see patterns in your life that were previously invisible.
        """)
    
    with col2:
        st.info("""
        **Why track creative energy?**
        - Productivity is about output. Energy is about sustainability.
        - High-enjoyment activities aren't always meaningful.
        - High-meaning activities can sometimes be stressful.
        - This app helps you find your 'Creative Flow'.
        """)

    st.success("👈 Use the sidebar to start logging your first activity!")

# --- LOG ACTIVITY PAGE ---
elif page == "Log Activity":
    st.title("📝 Log a New Activity")
    
    # Load activities for selection
    activities = logic.load_activities()
    
    with st.form("activity_form"):
        log_date = st.date_input("Date", date.today())
        
        col_act1, col_act2 = st.columns([2, 1])
        with col_act1:
            selected_activity = st.selectbox("Select Activity", activities)
        with col_act2:
            new_activity = st.text_input("Or add new activity")
            
        st.write("---")
        st.write("Rate from 1 (Lowest) to 10 (Highest)")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            energy = st.slider("Energy Level", 1, 10, 5)
            focus = st.slider("Focus Level", 1, 10, 5)
        with c2:
            enjoyment = st.slider("Enjoyment", 1, 10, 5)
            meaning = st.slider("Meaning/Value", 1, 10, 5)
        with c3:
            stress = st.slider("Stress Level", 1, 10, 5)
            
        notes = st.text_area("Optional Notes", placeholder="How did it go?")
        
        submit = st.form_submit_button("Save Activity Log")
        
        if submit:
            # Determine final activity name
            final_activity = new_activity.strip() if new_activity.strip() else selected_activity
            
            # Save new activity to file if provided
            if new_activity.strip():
                logic.add_activity(final_activity)
            
            # Create Log Object
            new_log = logic.ActivityLog(
                str(log_date), final_activity, energy, focus, enjoyment, meaning, stress, notes
            )
            
            # Save to CSV
            logic.save_activity_log(new_log)
            st.success(f"Logged '{final_activity}' successfully!")

# --- VIEW LOGS PAGE ---
elif page == "View Logs":
    st.title("📊 Your Activity Logs")
    
    logs = logic.load_logs()
    
    if not logs:
        st.warning("No logs found. Go to 'Log Activity' to add your first entry!")
    else:
        # Add categories for display
        logs_with_cats = logic.add_categories_to_logs(logs)
        
        # Display as a table (Streamlit handles lists of dicts well)
        st.table(logs_with_cats)
        
        st.write("---")
        st.caption(f"Data is stored locally in `{logic.LOG_FILE}`")

# --- ANALYZE PATTERNS PAGE ---
elif page == "Analyze Patterns":
    st.title("📈 Pattern Analysis")
    
    logs = logic.load_logs()
    
    if not logs:
        st.warning("Not enough data to analyze. Please log some activities first!")
    else:
        # Prepare Data
        logs_with_cats = logic.add_categories_to_logs(logs)
        averages = logic.calculate_activity_averages(logs)
        summary = logic.generate_summary(logs, averages)
        
        # 1. Top Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Logs", len(logs))
        m2.metric("Unique Activities", len(logic.get_unique_activities(logs)))
        m3.metric("Top Energy", logic.find_highest_average(averages, "Avg_Energy")["Activity"])
        
        # 2. Written Summary
        st.subheader("Insight Summary")
        st.write(summary)
        
        # 3. Highs and Lows
        st.write("---")
        st.subheader("Key Activity Highlights")
        h1, h2, h3, h4 = st.columns(4)
        
        with h1:
            act = logic.find_highest_average(averages, "Avg_Energy")
            st.write("**Most Energizing**")
            st.write(f"{act['Activity']} ({act['Avg_Energy']})")
        with h2:
            act = logic.find_highest_average(averages, "Avg_Stress")
            st.write("**Most Stressful**")
            st.write(f"{act['Activity']} ({act['Avg_Stress']})")
        with h3:
            act = logic.find_highest_average(averages, "Avg_Meaning")
            st.write("**Most Meaningful**")
            st.write(f"{act['Activity']} ({act['Avg_Meaning']})")
        with h4:
            act = logic.find_lowest_average(averages, "Avg_Focus")
            st.write("**Lowest Focus**")
            st.write(f"{act['Activity']} ({act['Avg_Focus']})")

        # 4. Tables
        st.write("---")
        st.subheader("Average Ratings by Activity")
        st.dataframe(averages)
        
        # 5. Charts
        st.write("---")
        st.subheader("Visual Analysis")
        
        # Row 1: Bar Charts
        c1, c2 = st.columns(2)
        with c1:
            fig_energy = px.bar(averages, x="Activity", y="Avg_Energy", title="Average Energy by Activity", color_discrete_sequence=['#4CAF50'])
            st.plotly_chart(fig_energy, use_container_width=True)
        with c2:
            fig_stress = px.bar(averages, x="Activity", y="Avg_Stress", title="Average Stress by Activity", color_discrete_sequence=['#f44336'])
            st.plotly_chart(fig_stress, use_container_width=True)
            
        # Row 2: Scatter and Pie
        c3, c4 = st.columns(2)
        with c3:
            fig_scatter = px.scatter(
                logs_with_cats, 
                x="Enjoyment", 
                y="Meaning", 
                color="Category", 
                size="Energy",
                title="Enjoyment vs Meaning (Sized by Energy)",
                hover_name="Activity"
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
        with c4:
            cat_counts = logic.count_categories(logs_with_cats)
            fig_pie = px.pie(cat_counts, values="Count", names="Category", title="Category Breakdown")
            st.plotly_chart(fig_pie, use_container_width=True)

# --- ABOUT PAGE ---
elif page == "About":
    st.title("About the Project")
    st.write("**Student:** Christopher Townsend Jr.")
    st.write("**Course:** INFOSCI 102 - Introduction to Information Science")
    
    st.subheader("Project Inspiration")
    st.write("""
    The Creative Energy Tracker was built to help individuals find their 'Creative Flow'. 
    In a world obsessed with doing more, this app encourages doing what matters. 
    By categorizing activities into groups like 'Creative Flow' and 'Meaningful but Heavy', 
    users can make better decisions about how to spend their limited time and energy.
    """)
    
    st.subheader("Technical Details")
    st.write("""
    This project is built using:
    - **Python**: Core logic and data processing.
    - **Streamlit**: Web interface and interactivity.
    - **Plotly**: Dynamic data visualization.
    - **CSV/OS Modules**: Local data persistence.
    """)
