
# Filename: ReactBench/injector.py (Final Version)

import subprocess
import threading
import queue
import time
import re

def execute_adb_command(device_serial: str, command_args: list):
    """
    A standardized function to execute any ADB command.
    Args:
        device_serial (str): Target device serial number.
        command_args (list): List of ADB command arguments (e.g., ["shell", "input", "tap", "100", "200"]).
    """
    try:
        # Build the full command, e.g.: ['adb', '-s', 'emulator-5554', 'shell', 'input', 'keyevent', '4']
        command = ["adb", "-s", device_serial] + command_args
        print(f"  > [Injector] Executing: {' '.join(command)}")
        # Execute the command, set utf-8 encoding, ignore decode errors for robustness
        subprocess.run(
            command, 
            check=True, 
            capture_output=True, 
            text=True, 
            encoding='utf-8', 
            errors='ignore'
        )
        return True
    except Exception as e:
        # In actual use, comment out the line below if you don't want to see failure logs
        print(f"  > [Injector] ADB command execution failed: {e}")
        return False

def inject_interference(device_serial: str, package_name: str, activity_name: str, params: dict):
    """
    Inject an interference by starting an Activity with parameters.
    """
    component = f"{package_name}/.{activity_name}"
    command_args = ["shell", "am", "start", "-n", component]

    for key, value in params.items():
        escaped_value = str(value).replace("'", "'\\''")
        command_args.extend(["--es", key, f"'{escaped_value}'"])
    execute_adb_command(device_serial, command_args)


class LogMonitor:
    def __init__(self, device_serial: str, tag: str, output_file: str):
        self.device_serial = device_serial
        self.tag = tag
        self.output_file = output_file
        self.process = None
        self.thread = None
        self._stop_event = threading.Event()

    def _run(self):
        """Function executed by thread, responsible for reading logcat and writing to file."""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                clear_command = ["adb", "-s", self.device_serial, "logcat", "-c"]
                subprocess.run(clear_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                command = ["adb", "-s", self.device_serial, "logcat", "-s", self.tag]
                self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')

                while not self._stop_event.is_set():
                    try:
                        line = self.process.stdout.readline()
                        
                        if line and self.tag in line:
                            event = line.split(f"{self.tag}:")[-1].strip()
                            if event:
                                print(f"  > [LogMonitor] Successfully captured event: '{event}'")
                                f.write(event)
                                f.flush()
                                break 
                        elif not line:

                            break

                            
                    except (IOError, ValueError):
                        break
        except IOError as e:
            print(f"❌ [LogMonitor] Unable to open or write to file {self.output_file}: {e}")
        finally:
            if self.process and self.process.poll() is None:
                self.process.terminate()

    def start(self):
        """Start monitoring."""
        print(f"  > [LogMonitor][{self.device_serial}] Started, monitoring events and preparing to write to '{self.output_file}'...")
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run)
        self.thread.start()

    def stop(self):
        """Stop monitoring and ensure all content is written to file."""
        if self.thread and self.thread.is_alive():
            self._stop_event.set()
            self.thread.join(timeout=2) 
            print(f"  > [LogMonitor][{self.device_serial}] Stopped.")
        
        if self.process and self.process.poll() is None:
            self.process.terminate()