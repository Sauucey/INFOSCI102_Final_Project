import csv
import os

# Constants
LOG_FILE = "energy_logs.csv"
ACTIVITY_FILE = "activities.txt"

DEFAULT_ACTIVITIES = [
    "Studying",
    "Coding",
    "Photography",
    "Gym",
    "Walking",
    "Socializing",
    "Gaming",
    "Watching videos",
    "Creative work",
    "Planning future goals",
    "Resting"
]

class ActivityLog:
    """A class representing a single activity log entry."""
    def __init__(self, date, activity, energy, focus, enjoyment, meaning, stress, notes):
        self.date = date
        self.activity = activity
        self.energy = int(energy)
        self.focus = int(focus)
        self.enjoyment = int(enjoyment)
        self.meaning = int(meaning)
        self.stress = int(stress)
        self.notes = notes

    def to_dict(self):
        """Converts the object to a dictionary for CSV saving."""
        return {
            "Date": self.date,
            "Activity": self.activity,
            "Energy": self.energy,
            "Focus": self.focus,
            "Enjoyment": self.enjoyment,
            "Meaning": self.meaning,
            "Stress": self.stress,
            "Notes": self.notes
        }

def create_activity_file_if_needed():
    """Creates the activities.txt file with default values if it doesn't exist."""
    if not os.path.exists(ACTIVITY_FILE):
        with open(ACTIVITY_FILE, "w") as f:
            for activity in DEFAULT_ACTIVITIES:
                f.write(activity + "\n")

def create_log_file_if_needed():
    """Creates the energy_logs.csv file with headers if it doesn't exist."""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Activity", "Energy", "Focus", "Enjoyment", "Meaning", "Stress", "Notes"])

def load_activities():
    """Reads activities from the text file and returns them as a list."""
    create_activity_file_if_needed()
    activities = []
    with open(ACTIVITY_FILE, "r") as f:
        for line in f:
            activity = line.strip()
            if activity:
                activities.append(activity)
    return sorted(activities)

def add_activity(new_activity):
    """Adds a new custom activity to the text file if it's not already there."""
    activities = load_activities()
    if new_activity not in activities:
        with open(ACTIVITY_FILE, "a") as f:
            f.write(new_activity + "\n")

def save_activity_log(log_obj):
    """Appends a new activity log entry to the CSV file."""
    create_log_file_if_needed()
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Activity", "Energy", "Focus", "Enjoyment", "Meaning", "Stress", "Notes"])
        writer.writerow(log_obj.to_dict())

def load_logs():
    """Loads all logs from the CSV file and returns them as a list of dictionaries."""
    create_log_file_if_needed()
    logs = []
    with open(LOG_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric strings to integers
            row["Energy"] = int(row["Energy"])
            row["Focus"] = int(row["Focus"])
            row["Enjoyment"] = int(row["Enjoyment"])
            row["Meaning"] = int(row["Meaning"])
            row["Stress"] = int(row["Stress"])
            logs.append(row)
    return logs

def get_unique_activities(logs):
    """Returns a set of all unique activity names found in the logs."""
    unique_acts = set()
    for log in logs:
        unique_acts.add(log["Activity"])
    return unique_acts

def classify_activity(energy, focus, enjoyment, meaning, stress):
    """Classifies an activity based on its ratings using conditional logic."""
    if energy >= 7 and focus >= 7 and enjoyment >= 7 and meaning >= 7 and stress <= 5:
        return "Creative Flow"
    elif energy >= 7 and enjoyment >= 7 and stress <= 4:
        return "Energizing"
    elif energy <= 4 and stress >= 7:
        return "Draining"
    elif meaning >= 7 and stress >= 7:
        return "Meaningful but Heavy"
    elif enjoyment >= 7 and focus <= 4:
        return "Fun but Distracting"
    else:
        return "Neutral or Mixed"

def add_categories_to_logs(logs):
    """Adds a 'Category' key to each log dictionary in the list."""
    for log in logs:
        log["Category"] = classify_activity(
            log["Energy"], 
            log["Focus"], 
            log["Enjoyment"], 
            log["Meaning"], 
            log["Stress"]
        )
    return logs

def calculate_activity_averages(logs):
    """Calculates average ratings for each unique activity using a dictionary."""
    activity_data = {} # activity_name -> {sum_energy: X, count: Y, ...}
    
    for log in logs:
        name = log["Activity"]
        if name not in activity_data:
            activity_data[name] = {
                "Energy_Sum": 0, "Focus_Sum": 0, "Enjoyment_Sum": 0, 
                "Meaning_Sum": 0, "Stress_Sum": 0, "Count": 0
            }
        
        activity_data[name]["Energy_Sum"] += log["Energy"]
        activity_data[name]["Focus_Sum"] += log["Focus"]
        activity_data[name]["Enjoyment_Sum"] += log["Enjoyment"]
        activity_data[name]["Meaning_Sum"] += log["Meaning"]
        activity_data[name]["Stress_Sum"] += log["Stress"]
        activity_data[name]["Count"] += 1
        
    averages = []
    for name, data in activity_data.items():
        count = data["Count"]
        averages.append({
            "Activity": name,
            "Avg_Energy": round(data["Energy_Sum"] / count, 2),
            "Avg_Focus": round(data["Focus_Sum"] / count, 2),
            "Avg_Enjoyment": round(data["Enjoyment_Sum"] / count, 2),
            "Avg_Meaning": round(data["Meaning_Sum"] / count, 2),
            "Avg_Stress": round(data["Stress_Sum"] / count, 2),
            "Count": count
        })
    return averages

def find_highest_average(averages, metric):
    """Finds the activity with the highest average for a specific metric."""
    if not averages:
        return None
    highest = averages[0]
    for item in averages:
        if item[metric] > highest[metric]:
            highest = item
    return highest

def find_lowest_average(averages, metric):
    """Finds the activity with the lowest average for a specific metric."""
    if not averages:
        return None
    lowest = averages[0]
    for item in averages:
        if item[metric] < lowest[metric]:
            lowest = item
    return lowest

def count_categories(logs):
    """Counts occurrences of each category using a dictionary."""
    counts = {}
    for log in logs:
        cat = log["Category"]
        counts[cat] = counts.get(cat, 0) + 1
    
    # Convert to list of dicts for easier plotting
    result = []
    for cat, count in counts.items():
        result.append({"Category": cat, "Count": count})
    return result

def generate_summary(logs, averages):
    """Generates a short written summary based on the analyzed data."""
    if not logs:
        return "No data available yet. Start logging your activities!"
    
    total_logs = len(logs)
    unique_count = len(get_unique_activities(logs))
    
    best_energy = find_highest_average(averages, "Avg_Energy")
    best_meaning = find_highest_average(averages, "Avg_Meaning")
    worst_stress = find_highest_average(averages, "Avg_Stress")
    
    summary = f"You have recorded {total_logs} sessions across {unique_count} different activities. "
    
    if best_energy:
        summary += f"Your most energizing activity is '{best_energy['Activity']}' with an average score of {best_energy['Avg_Energy']}. "
    
    if best_meaning:
        summary += f"You find '{best_meaning['Activity']}' to be your most meaningful pursuit. "
        
    if worst_stress:
        summary += f"Be mindful that '{worst_stress['Activity']}' tends to be your most stressful activity. "
        
    return summary
