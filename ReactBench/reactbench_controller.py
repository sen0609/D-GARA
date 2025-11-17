import yaml
import sys
import injector  
import time
import subprocess

class ReactBenchController:
    """
    A test controller that triggers different UI dialogs based on a YAML rules file.
    """
    def __init__(self, library_file='dialog_library.yaml'):
        """
        Initialize the controller and load the dialog library.
        """
        try:
            with open(library_file, 'r', encoding='utf-8') as f:
                self.library = yaml.safe_load(f)['dialog_library']
            print(f"✅ Successfully loaded dialog library: {library_file}")
        except FileNotFoundError:
            print(f"❌ Error: Dialog library file '{library_file}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error: Failed to parse YAML file: {e}")
            sys.exit(1)

    def list_dialogs(self):
        """
        List all available dialogs and their descriptions.
        """
        print("\n--- Available Dialog Library ---")
        for dialog in self.library:
            print(f"  ID: {dialog['id']}\n    Description: {dialog['description']}\n")
        print("--------------------")

    def find_dialog_by_id(self, dialog_id):
        """
        Find a dialog definition by ID.
        """
        for dialog in self.library:
            if dialog['id'] == dialog_id:
                return dialog
        return None

    def trigger_dialog(self, dialog_id):
        """
        Trigger the corresponding dialog by the given ID.
        """
        dialog = self.find_dialog_by_id(dialog_id)
        if not dialog:
            print(f"❌ Error: Dialog with ID '{dialog_id}' not found.")
            return

        print(f"\n🚀 Triggering dialog: {dialog['id']} ({dialog['description']})")
        
        dialog_type = dialog.get('type')
        params = dialog.get('params', {})

        try:
            if dialog_type == 'permission':
                injector.inject_location_permission(**params)
            elif dialog_type == 'notification':
                injector.inject_low_battery_warning(**params)
            elif dialog_type == 'cookie':
                injector.inject_cookie_consent(**params)
            else:
                print(f"🤷‍ Error: Unsupported dialog type '{dialog_type}'.")
                return
            
            print("✅ Injection command sent! Please check the device screen.")

        except TypeError as e:
            print(f"❌ Parameter error: Arguments passed to the injection function do not match the function definition. Please check the YAML file.")
            print(f"   Error details: {e}")
        except Exception as e:
            print(f"❌ Unknown error occurred during injection: {e}")


def adb_launch_package(package_name: str):
    """Generally launch the main entry of an app."""
    print(f"\n🔄 Launching target app: {package_name}")
    try:
        subprocess.run(["adb", "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"], check=True, capture_output=True)
        print("    App launched, waiting 3 seconds...")
        time.sleep(3)
    except subprocess.CalledProcessError:
        print(f"    [Warning] Launching app {package_name} may have failed or is already running. Continuing...")

if __name__ == '__main__':
    controller = ReactBenchController()
    
    if len(sys.argv) < 2 or sys.argv[1] == 'help':
        print("\nReactBench Controller Usage:")
        print("  python reactbench_controller.py list         - List all available dialogs")
        print("  python reactbench_controller.py trigger <id> - Trigger a dialog by specified ID")
        sys.exit(0)

    command = sys.argv[1]

    if command == 'list':
        controller.list_dialogs()
    elif command == 'trigger':
        if len(sys.argv) < 3:
            print("❌ Error: Please provide the dialog ID to trigger.")
            print("   Usage: python reactbench_controller.py trigger <id>")
        else:
            TARGET_APP_PACKAGE = "com.example.adbsmarttest"
            adb_launch_package(TARGET_APP_PACKAGE)
            dialog_id_to_trigger = sys.argv[2]
            controller.trigger_dialog(dialog_id_to_trigger)
    else:
        print(f"❌ Error: Unknown command '{command}'. Use 'help' to see usage.")