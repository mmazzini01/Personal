import socket
import time
import threading
from datetime import datetime
import xml.etree.ElementTree as ET
import pandas as pd
import tobii_research as tr
from psychopy import visual, core, event

# Lists to store data
gazepoint_data = []
tobii_data = []

# Flags
running = True
current_stimulus = "none"

def connect_gazepoint():
    try:
        HOST = '127.0.0.1'
        PORT = 4242
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        print("✅ Connected to Gazepoint API")
        return s
    except Exception as e:
        print(f"❌ Error connecting to Gazepoint: {e}")
        return None

def connect_tobii():
    try:
        eyetrackers = tr.find_all_eyetrackers()
        if eyetrackers:
            print(f"✅ Connected to Tobii: {eyetrackers[0].model}")
            return eyetrackers[0]
        else:
            print("❌ No Tobii eyetracker found")
            return None
    except Exception as e:
        print(f"❌ Error connecting to Tobii: {e}")
        return None

def tobii_gaze_callback(gaze_data):
    if running:
        gaze_data["system_time_now"] = int(datetime.now().timestamp() * 1000)
        gaze_data["stimulus"] = current_stimulus
        tobii_data.append(gaze_data)
        print(f"\rGazepoint: {len(gazepoint_data)}, Tobii: {len(tobii_data)}", end='')

def gazepoint_collection(sock):
    try:
        # Enable Gazepoint data streams
        commands = [
            '<SET ID="ENABLE_SEND_DATA" STATE="1" />',
            '<SET ID="ENABLE_SEND_POG_FIX" STATE="1" />',
            '<SET ID="ENABLE_SEND_TIME" STATE="1" />',
            '<SET ID="ENABLE_SEND_EYE_LEFT" STATE="1" />',
            '<SET ID="ENABLE_SEND_EYE_RIGHT" STATE="1" />',
            '<SET ID="ENABLE_SEND_POG_LEFT" STATE="1" />',
            '<SET ID="ENABLE_SEND_POG_RIGHT" STATE="1" />'
        ]
        for cmd in commands:
            sock.send(str.encode(cmd + '\r\n'))

        while running:
            try:
                data = sock.recv(1024).decode(errors='ignore')
                lines = data.strip().split('\r\n')
                for line in lines:
                    if not line.startswith('<REC'):
                        continue
                    root = ET.fromstring(line)
                    now_ms = int(datetime.now().timestamp() * 1000)
                    if root.get('LPOGX') is not None:
                        gaze_data = {
                            'system_time_now': now_ms,
                            'device_time_stamp': float(root.get('TIME', 0)),
                            'left_gaze_x': float(root.get('LPOGX', 0)),
                            'left_gaze_y': float(root.get('LPOGY', 0)),
                            'left_pupil': float(root.get('LPUPILD', 0)),
                            'left_validity': float(root.get('LPOGV', 0)),
                            'right_gaze_x': float(root.get('RPOGX', 0)),
                            'right_gaze_y': float(root.get('RPOGY', 0)),
                            'right_pupil': float(root.get('RPUPILD', 0)),
                            'right_validity': float(root.get('RPOGV', 0)),
                            'stimulus': current_stimulus
                        }
                        gazepoint_data.append(gaze_data)
                        print(f"\rGazepoint: {len(gazepoint_data)}, Tobii: {len(tobii_data)}", end='')
            except OSError:
                break
    except Exception as e:
        print(f"\n❌ Gazepoint collection error: {e}")

def process_tobii_data(data):
    return {
        'system_time_now': data['system_time_now'],
        'device_time_stamp': data.get('device_time_stamp', 0),
        'left_gaze_x': data.get('left_gaze_point_on_display_area', [0,0])[0],
        'left_gaze_y': data.get('left_gaze_point_on_display_area', [0,0])[1],
        'left_pupil': data.get('left_pupil_diameter', 0),
        'left_validity': data.get('left_gaze_point_validity', 0),
        'right_gaze_x': data.get('right_gaze_point_on_display_area', [0,0])[0],
        'right_gaze_y': data.get('right_gaze_point_on_display_area', [0,0])[1],
        'right_pupil': data.get('right_pupil_diameter', 0),
        'right_validity': data.get('right_gaze_point_validity', 0),
        'stimulus': data.get('stimulus', 'none')
    }

def show_stimulus(win, image_stim, sock, stim_name, duration=5.0):
    global current_stimulus
    current_stimulus = stim_name
    print(f"\n🖼️ Showing {stim_name} for {duration} seconds...")

    image_stim.image = stim_name
    image_stim.draw()
    win.flip()

    try:
        sock.send(str.encode(f'<SET ID="USER_EVENT" VALUE="{stim_name}_start" />\r\n'))
    except Exception as e:
        print(f"❌ Failed to send USER_EVENT: {e}")

    start_time = time.time()
    while time.time() - start_time < duration:
        if event.getKeys(['escape']):
            return False
        core.wait(0.1)
    return True

def main():
    global running

    # Connect to trackers
    gp_socket = connect_gazepoint()
    tobii_tracker = connect_tobii()
    if not gp_socket or not tobii_tracker:
        print("❌ Connection failed.")
        return

    # Create window using custom monitor
    win = visual.Window(
        fullscr=True,  # Set this up in Monitor Center
        color="gray",
        units="pix"
    )
    image_stim = visual.ImageStim(win, size=(800, 600))

    # Start threads
    tobii_tracker.subscribe_to(tr.EYETRACKER_GAZE_DATA, tobii_gaze_callback, as_dictionary=True)
    gp_thread = threading.Thread(target=gazepoint_collection, args=(gp_socket,))
    gp_thread.start()

    try:
        win.flip()
        core.wait(1.0)

        if not show_stimulus(win, image_stim, gp_socket, "face.jpg"):
            return
        if not show_stimulus(win, image_stim, gp_socket, "beach.jpg"):
            return

    except Exception as e:
        print(f"\n❌ Experiment error: {e}")

    finally:
        print("\n🛑 Stopping data collection...")
        running = False
        gp_thread.join()

        try:
            gp_socket.send(str.encode('<SET ID="ENABLE_SEND_DATA" STATE="0" />\r\n'))
            gp_socket.close()
        except Exception as e:
            print(f"Gazepoint close error: {e}")

        tobii_tracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA, tobii_gaze_callback)
        win.close()

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if gazepoint_data:
            pd.DataFrame(gazepoint_data).to_csv(f'gazepoint_data_{timestamp}.csv', index=False)
            print(f"✅ Saved Gazepoint data ({len(gazepoint_data)} rows)")

        if tobii_data:
            processed = [process_tobii_data(d) for d in tobii_data]
            pd.DataFrame(processed).to_csv(f'tobii_data_{timestamp}.csv', index=False)
            print(f"✅ Saved Tobii data ({len(processed)} rows)")

        if not gazepoint_data and not tobii_data:
            print("⚠️ No data collected.")

if __name__ == "__main__":
    main()
