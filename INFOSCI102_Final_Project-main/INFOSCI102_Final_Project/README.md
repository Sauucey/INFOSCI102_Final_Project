# Creative Energy Tracker

**Author:** Christopher Townsend Jr.

This project is a beginner-friendly Python-based Streamlit web application designed to help users understand how different activities affect their energy, focus, enjoyment, meaning, and stress levels over time. It provides tools to log activities, view historical data, and analyze patterns through summaries and interactive charts.

## What I Built

The Creative Energy Tracker is a web application that allows users to:
*   Log daily activities with detailed ratings across five dimensions: Energy, Focus, Enjoyment, Meaning, and Stress.
*   Add custom activities to a persistent list.
*   View all logged activities in a clear, tabular format.
*   Analyze activity patterns through various metrics, including total logs, unique activities, most energizing/stressful/meaningful activities, and average ratings.
*   Visualize data with interactive Plotly charts, such as average energy/stress/meaning by activity, enjoyment vs. meaning scatter plot, and category breakdown pie chart.
*   Receive an automatic written summary of their activity patterns.

## Inputs

Users provide input through the Streamlit web interface:
*   **Date:** Selection of the activity date.
*   **Activity:** Selection from a preset list or entry of a new custom activity.
*   **Ratings (1-10):** Energy, Focus, Enjoyment, Meaning, and Stress levels.
*   **Notes:** Optional textual notes about the activity.

## Outputs

The application generates the following outputs:
*   **`activities.txt`:** A text file storing the list of available activities.
*   **`energy_logs.csv`:** A CSV file storing all logged activity entries.
*   **Web Interface:** Display of logged data, analytical summaries, and interactive charts within the Streamlit application.

## How to Run the Project

To run the Creative Energy Tracker, follow these steps:

1.  **Ensure Python is installed:** This project requires Python 3.x.
2.  **Install `pip`:** Python's package installer.
3.  **Clone or download the project files.**
4.  **Navigate to the project directory** in VScode, terminal, or command prompt
.
5.  **Set up a virtual environment (recommended):**
    ```bash
        python -m venv .venv

    # On Windows PowerShell:

    .\.venv\Scripts\Activate.ps1
    
    # On macOS/Linux or Windows Git Bash:
    source .venv/bin/activate
    ```
6.  **Install required packages:**
    ```bash
    pip install -r requirements.txt
    ```
7.  **Launch the Streamlit application:**
    ```bash
    streamlit run app.py
    ```
    Your web browser should automatically open to the application.

## File Structure

```
creative-energy-tracker/
├── app.py                  # Main Streamlit web application
├── energy_logic.py         # Core logic for data handling, analysis, and classification
├── requirements.txt        # Lists Python dependencies
├── README.md               # Project overview and setup instructions
├── replication_ai_usage.md # Detailed document on AI usage and replication steps
├── activities.txt          # (Automatically created) Stores custom and default activities
└── energy_logs.csv         # (Automatically created) Stores all logged activity data
```

For detailed information on the development process and AI assistance used, please refer to [replication_ai_usage.md](replication_ai_usage.md).
