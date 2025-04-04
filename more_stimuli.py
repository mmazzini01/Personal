from psychopy import visual, core, event
import tobii_research as tr
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import random
from PIL import Image

eye_trackers = tr.find_all_eyetrackers()
if not eye_trackers:
    print("No eye tracker found!")
    core.quit()

eye_tracker = eye_trackers[0]  # first available eye tracker

# initialize psychopy window
win = visual.Window(size=[1536, 864], fullscr=True, color="Gray", units="pix", waitBlanking=True)

# List to store gaze data
gaze_data_list = []
# Define stimuli: 3 images and 3 texts
stimuli = [
    {"type": "text", "content": "First Text", "name": "Text_1"},
    {"type": "image", "content": "face.jpg", "name": "Image_1"},
    {"type": "image", "content": "beach.jpg", "name": "Image_2"}
]

def gaze_data_callback(gaze_data):
    """Logs gaze data in real-time and assigns current stimulus."""
    global gaze_data_list, current_stimulus

    timestamp = core.Clock()
    left_gaze = gaze_data.get("left_gaze_point_on_display_area")
    right_gaze = gaze_data.get("right_gaze_point_on_display_area")
    left_point_validity = gaze_data.get("left_gaze_point_validity")
    right_point_validity = gaze_data.get("right_gaze_point_validity")


    if left_gaze and right_gaze:
        left_x, left_y = left_gaze
        right_x, right_y = right_gaze

        # Store gaze data with current stimulus name
        gaze_data_list.append({
            "Timestamp": timestamp.getTime(),
            "Left Gaze X": left_x,
            "Left Gaze Y": left_y,
            "Right Gaze X": right_x,
            "Right Gaze Y": right_y,
            "Left Gaze Validity": left_point_validity,
            "Right Gaze Validity": right_point_validity,
            "Event Flag": current_stimulus
        })

# Subscribe to gaze data stream
eye_tracker.subscribe_to(tr.EYETRACKER_GAZE_DATA, gaze_data_callback, as_dictionary=True)

# Present stimuli in random order
random.shuffle(stimuli)
for stimulus in stimuli:
    current_stimulus = stimulus["name"]  # Track current stimulus name

    if stimulus["type"] == "text":
        text_stimulus = visual.TextStim(win, text=stimulus["content"], color="black", pos=(0, 0), height=40)
        text_stimulus.draw()
    elif stimulus["type"] == "image":
        image_stimulus = visual.ImageStim(win, image=stimulus["content"], pos=(0, 0), size=(800, 600))
        image_stimulus.draw()

    win.flip()

    # Wait for space key press to exit the stimulus
    event.waitKeys(keyList=["space"])
     

# Stop data collection
eye_tracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA, gaze_data_callback)

# Save gaze data to a CSV file
if gaze_data_list:
    df = pd.DataFrame(gaze_data_list)
    df.to_csv("gaze_data.csv", index=False)
else:
    print("No gaze data recorded!")

# Close PsychoPy window and exit
win.close()

##############################################
#########    classify fixations     ##########
##############################################

# Load dataset
df = pd.read_csv("gaze_data.csv")

# Compute average gaze coordinates (assuming binocular tracking)
df['x_avg'] = (df['Left Gaze X'] + df['Right Gaze X']) / 2
df['y_avg'] = (df['Left Gaze Y'] + df['Right Gaze Y']) / 2

# Define parameters based on your screen resolution (1536x864)
window_size = 40 # Number of frames in the sliding window
dispersion_threshold = 0.05 # Pixels (adjusted for 1536x864 screen)

# Initialize classification column
df['Movement'] = 'saccade'

# Apply I-DT algorithm
for i in range(len(df) - window_size):
    window_x = df['x_avg'].iloc[i : i + window_size]
    window_y = df['y_avg'].iloc[i : i + window_size]

    dispersion = (window_x.max() - window_x.min()) + (window_y.max() - window_y.min())

    if dispersion < dispersion_threshold:
        df.loc[i : i + window_size, 'Movement'] = 'fixation'

# Save the classified dataset
df.to_csv("classified_gaze_data.csv", index=False)

##############################################
######## create heatmap of fixation ##########
##############################################

for stimulus in stimuli:
    if stimulus["type"] == "image":
        stimulus_name = stimulus["name"]
        stimulus_file = stimulus["content"]

        # Load eye-tracking data
        df = pd.read_csv("classified_gaze_data.csv")

        # Filter only fixations during the stimulus presentation
        mask = (df["Event Flag"] == stimulus_name) & (df["Movement"] == "fixation") & (df["Left Gaze Validity"] == 1) & (df["Right Gaze Validity"] == 1)
        fixations = df[mask]

        # Remove missing data
        fixations = fixations.dropna(subset=["Left Gaze X", "Left Gaze Y", "Right Gaze X", "Right Gaze Y"])

        # Screen and image parameters
        SCREEN_WIDTH, SCREEN_HEIGHT = 1536, 864  # Screen resolution
        IMAGE_X, IMAGE_Y = 368, 132
        IMAGE_WIDTH, IMAGE_HEIGHT = 800, 600  # Image dimensions on the screen

        # Load the stimulus image
        stimulus_img = Image.open(stimulus_file)

        # Convert gaze coordinates from screen to image
        fixations["Left Gaze X"] = fixations["Left Gaze X"] * SCREEN_WIDTH
        fixations["Left Gaze Y"] = (1 - fixations["Left Gaze Y"]) * SCREEN_HEIGHT  # Flip Y-axis

        fixations["Right Gaze X"] = fixations["Right Gaze X"] * SCREEN_WIDTH
        fixations["Right Gaze Y"] = (1 - fixations["Right Gaze Y"]) * SCREEN_HEIGHT  # Flip Y-axis

        # Filter only fixations within the image
        fixations = fixations[
            (fixations["Left Gaze X"] >= IMAGE_X) & (fixations["Left Gaze X"] <= IMAGE_X + IMAGE_WIDTH) &
            (fixations["Left Gaze Y"] >= IMAGE_Y) & (fixations["Left Gaze Y"] <= IMAGE_Y + IMAGE_HEIGHT)
        ]

        # Convert coordinates relative to the image
        fixations["Image Gaze X"] = fixations["Left Gaze X"] - IMAGE_X
        fixations["Image Gaze Y"] = fixations["Left Gaze Y"] - IMAGE_Y

        # Combine data from both eyes
        gaze_x = np.concatenate([fixations["Image Gaze X"], fixations["Right Gaze X"] - IMAGE_X])
        gaze_y = np.concatenate([fixations["Image Gaze Y"], fixations["Right Gaze Y"] - IMAGE_Y])

        # Create the heatmap
        plt.figure(figsize=(8, 6))
        sns.kdeplot(x=gaze_x, y=gaze_y, cmap="Reds", fill=True, alpha=0.6)

        # Overlay the stimulus image
        plt.imshow(stimulus_img, extent=[0, IMAGE_WIDTH, 0, IMAGE_HEIGHT], aspect='auto')

        # Formatting
        plt.xlabel("X (pixel)")
        plt.ylabel("Y (pixel)")
        plt.title(f"Heatmap Fixations for {stimulus_name}")

        # Save and show
        plt.savefig(f"fixation_heatmap_{stimulus_name}.png", dpi=300)
        plt.show()


'''
##############################################

# Load dataset (assuming it's a CSV file with columns: 'time', 'x_left', 'y_left', 'x_right', 'y_right')
df = pd.read_csv("gaze_data.csv")

# Compute average gaze coordinates (assuming binocular tracking)
df['x_avg'] = (df['x_left'] + df['x_right']) / 2
df['y_avg'] = (df['y_left'] + df['y_right']) / 2

# Compute time difference between frames
df['dt'] = df['time'].diff().fillna(0)  # Time difference between frames

# Compute velocity (Euclidean distance between consecutive gaze points)
df['dx'] = df['x_avg'].diff().fillna(0)
df['dy'] = df['y_avg'].diff().fillna(0)
df['velocity'] = np.sqrt(df['dx']**2 + df['dy']**2) / df['dt']

# Compute velocity threshold (5 times the median absolute deviation, following Engbert & Kliegl, 2003)
threshold = 5 * np.median(np.abs(df['velocity'] - np.median(df['velocity'])))

# Classify fixations and saccades
df['event'] = np.where(df['velocity'] > threshold, 'saccade', 'fixation')

# Save the classified dataset
df.to_csv("classified_gaze_data.csv", index=False)

# Print a summary
print(df[['time', 'x_avg', 'y_avg', 'velocity', 'event']].head(20))

'''


'''
# Add variables to store previous gaze points for both eyes
prev_left_x, prev_left_y, prev_right_x, prev_right_y, prev_time = None, None, None, None, None

# Define a velocity threshold for saccade detection (adjust as needed)
FIXATION_VELOCITY_THRESHOLD = 30  # Pixels per second (example)

def classify_eye_movement(left_x, left_y, right_x, right_y, timestamp):
    global prev_left_x, prev_left_y, prev_right_x, prev_right_y, prev_time

    # If it's the first sample, store initial values and return "Fixation"
    if prev_left_x is None or prev_right_x is None:
        prev_left_x, prev_left_y, prev_right_x, prev_right_y, prev_time = left_x, left_y, right_x, right_y, timestamp
        return "Fixation"

    # Compute time difference
    delta_t = (timestamp - prev_time) / 1000000  # Convert microseconds to sec
    if delta_t == 0:
        return "Fixation"

    # Compute Euclidean distances for both eyes
    left_distance = np.sqrt((left_x - prev_left_x) ** 2 + (left_y - prev_left_y) ** 2)
    right_distance = np.sqrt((right_x - prev_right_x) ** 2 + (right_y - prev_right_y) ** 2)

    # Compute velocity (distance / time) for both eyes
    left_velocity = left_distance / delta_t
    right_velocity = right_distance / delta_t

    # Update previous values
    prev_left_x, prev_left_y, prev_right_x, prev_right_y, prev_time = left_x, left_y, right_x, right_y, timestamp

    # Use the **higher velocity** of the two eyes for classification
    max_velocity = max(left_velocity, right_velocity)

    if max_velocity > FIXATION_VELOCITY_THRESHOLD:
        return "Saccade"
    else:
        return "Fixation"
'''