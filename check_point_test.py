# check_point_test.py
import time
import sys
import os

# Import configuration and modules
import csv
import config
from ocr_engine import DigitOCR
from data_save import DataRecorder
# [Removed] import data_save_10s_interval 
from geometry_utils import point_to_line_segment_distance


def add_relative_time_column(csv_path):
    """Add a relative_time column using the first timestamp as the baseline."""
    if not csv_path or not os.path.exists(csv_path):
        return

    with open(csv_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    if not rows or 'time' not in fieldnames:
        return

    # Avoid duplicate column
    if 'relative_time' in fieldnames:
        return

    try:
        baseline_time = float(rows[0]['time'])
    except (TypeError, ValueError):
        return

    # Add new column at the end
    new_fieldnames = fieldnames + ['relative_time']

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)

        writer.writeheader()

        for row in rows:
            try:
                current_time = float(row['time'])
                relative_time = current_time - baseline_time
            except (TypeError, ValueError):
                relative_time = 0.0

            row['relative_time'] = f"{relative_time:.6f}"

            writer.writerow(row)

# Try to import the plotting module
try:
    import plot_total
    PLOT_AVAILABLE = True
except ImportError:
    PLOT_AVAILABLE = False
    print("[System] Warning: plot_total module not found. Plotting disabled.")

# ==========================================
# Hardware Interface (OCR)
# ==========================================
class RealHardware:
    def __init__(self):
        print("[System] Initializing OCR Engine...")
        self.ocr = DigitOCR(training_mode=False)

    def get_data(self):
        # Read raw data
        raw_x = self.ocr.read_region(0)
        raw_z = self.ocr.read_region(1)
        raw_s = self.ocr.read_region(2)
        
        # Convert data
        val_x = self.ocr.safe_float(raw_x)
        val_z = self.ocr.safe_float(raw_z)
        val_s = self.ocr.safe_float(raw_s)
        
        return (val_x, 0.0, val_z), val_s

# ==========================================
# Helper Function: Manual Stop, Save & Plot
# ==========================================
def manual_stop_and_save(recorder):
    """
    Adapts to the new DataRecorder interface.
    Manually detaches the session, closes the file, and triggers plotting.
    """
    if not recorder.is_recording:
        return None
        
    # Get handle and path, reset recorder internal state
    handle, path = recorder.detach_current_session()
    
    if handle:
        try:
            # 1. Close the file to ensure data is written to disk
            handle.close()
            print(f"[Record] File saved (Test Script): {path}")

            # 2. Add derived relative_time column using the first timestamp as baseline
            if path and os.path.exists(path):
                add_relative_time_column(path)
             
            # 3. Trigger Plotting [Added]
            if PLOT_AVAILABLE and path and os.path.exists(path):
                print(f"[Plot] Generating plot for: {os.path.basename(path)}...")
                plot_total.plot_track_data(path)
                 
            return path
        except Exception as e:
            print(f"[Record] Failed to close/plot file: {e}")
    return None

# ==========================================
# Main Program
# ==========================================
def main():
    hardware = RealHardware()
    recorder = DataRecorder()
    headers = ['time', 'x', 'y', 'z', 'speed']
    
    # State Definitions
    STATE_WAIT_AT_START = 0
    STATE_READY = 1
    STATE_RACING = 2
    STATE_FINISHED = 3
    
    current_state = STATE_WAIT_AT_START
    race_start_time = 0
    
    print("="*60)
    print("      AUTO TRACK RECORDER (Updated)      ")
    print("="*60)
    print(f"Trigger Dist : {config.TRIGGER_DIST} m")
    print(f"Min Lap Time : {config.MIN_LAP_TIME} s")
    print(f"FPS Limit    : {config.LIMIT_FPS}")
    print("-" * 60)
    print(">>> Please drive car to the start line area <<<")
    print("-" * 60)

    try:
        while True:
            cycle_start = time.time()
            
            # --- A. Get Data ---
            pos, speed = hardware.get_data()
            now = time.time()
            
            # --- B. Calculate Distance ---
            dist_to_start = point_to_line_segment_distance(pos, config.START_LINE)
            dist_to_finish = point_to_line_segment_distance(pos, config.FINISH_LINE)
            
            # --- C. State Machine Logic ---
            
            # [0] Waiting at Start
            if current_state == STATE_WAIT_AT_START:
                if dist_to_start <= config.TRIGGER_DIST:
                    current_state = STATE_READY
                    print(f"\n[Ready] Car Online (Dist: {dist_to_start:.2f}m)")
                else:
                    sys.stdout.write(f"\r[Wait] Dist to Start: {dist_to_start:.1f}m")
                    sys.stdout.flush()

            # [1] Ready to Go
            elif current_state == STATE_READY:
                # Logic: Dist increases > threshold -> Left start -> Race Starts
                if dist_to_start > config.TRIGGER_DIST:
                    current_state = STATE_RACING
                    race_start_time = now
                    print(f"\n[GO!] Car Left Start Line, Timing Started!")
                    
                    recorder.start_new_session(headers)
                    recorder.log_step([now, pos[0], pos[1], pos[2], speed])

            # [2] Racing
            elif current_state == STATE_RACING:
                recorder.log_step([now, pos[0], pos[1], pos[2], speed])
                elapsed = now - race_start_time
                
                sys.stdout.write(f"\r[Racing] T:{elapsed:.1f}s | Speed:{speed:.0f} | Dist Finish:{dist_to_finish:.1f}m")
                sys.stdout.flush()
                
                # Check Finish Line
                if dist_to_finish <= config.TRIGGER_DIST:
                    
                    # Validate: Minimum Lap Time (Prevent immediate re-trigger)
                    if elapsed < config.MIN_LAP_TIME:
                        print(f"\n\n[Reset] Finish Triggered too early ({elapsed:.1f}s). Ignored.")
                        recorder.discard_recording()
                        
                        # Rollback State
                        current_state = STATE_READY
                        time.sleep(1.0)
                        print("[Ready] Please restart...")
                    else:
                        current_state = STATE_FINISHED
                        print(f"\n\n[Finish] Race Finished! Time: {elapsed:.3f}s")
                        break

            # --- D. FPS Control ---
            elapsed_cycle = time.time() - cycle_start
            sleep_time = max(0, (1.0 / config.LIMIT_FPS) - elapsed_cycle)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n[Stop] Interrupted by User")
        if current_state == STATE_RACING:
            # [Modified] Use manual save helper
            manual_stop_and_save(recorder)

    finally:
        # --- E. Post-Race Processing ---
        if current_state == STATE_FINISHED:
            print("\n" + "="*40)
            print("Saving data and generating plot...")

            # [Modified] Call helper to save CSV and generate Plot
            full_csv_path = manual_stop_and_save(recorder)
            
            if full_csv_path:
                print(f"[System] Process Complete. Data saved to: {full_csv_path}")
            
            print("="*60)
            print("Test Flow Ended.")

if __name__ == "__main__":
    main()