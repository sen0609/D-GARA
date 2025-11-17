import yaml
import random
import injector

class RuleEngine:
    def __init__(self, rules_file_path, library_file_path, seed: int, logger, device_serial,max_interferences: int =999):
        self.rules = self._load_yaml(rules_file_path, 'rules')
        self.rules.sort(key=lambda r: r.get('priority', 99))
        self.interference_library = self._load_yaml(library_file_path, 'interference_library')
        self.rng = random.Random(seed)
        self.companion_app_package = "com.example.adbsmarttest"
        self.triggered_rules = set()
        self.logger = logger
        self.device_serial = device_serial
        self.max_interferences = max_interferences
        self.interference_count = 0
        self.interference_to_rule_map = {}
        for rule in self.rules:
            for action in rule.get('actions', []):
                if action.get('type') == 'inject_interference':
                    interference_id = action.get('interference_id')
                    if interference_id:
                        self.interference_to_rule_map[interference_id] = rule


    def _load_yaml(self, file_path, key):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f).get(key, [])
        except Exception as e:
            print(f"❌ Failed to load file '{file_path}': {e}")
            return []
    
    def _check_conditions(self, conditions, state, step_number: int):
        """
        [Refactored] Check if all conditions are satisfied. All logic is now handled inside the engine.
        """
        for condition in conditions.get('all', []):
            cond_type = condition.get('type')

            min_step = condition.get('min_step', 0)
            if step_number < min_step:
                return False

            if cond_type == 'current_activity_is':
                expected_activity = condition.get('value')
                if not expected_activity or state.get('current_activity') != expected_activity:
                    return False
            
            if cond_type == 'semantic_element_exists':
                keywords = condition.get('keywords', [])
                threshold = condition.get('match_threshold', 1.0)
                
                ui_elements = state.get('all_ui_elements', [])
                if not ui_elements: return False

                screen_text_blob = ""
                for elem in ui_elements:
                    screen_text_blob += elem.get('text', '') + " "
                    screen_text_blob += elem.get('resource_id', '') + " "
                    screen_text_blob += elem.get('content_desc', '') + " "
                
                screen_text_blob = screen_text_blob.lower()
                found_count = sum(1 for keyword in keywords if keyword.lower() in screen_text_blob)
                
                if not (found_count >= len(keywords) * threshold):
                    return False
        
        return True

    def _execute_actions(self, rule_id: str, actions: list):
        for action in actions:
            if action.get('type') == 'inject_interference':
                random= self.rng.random() *2
                if random >= action.get('trigger_probability', 1.0):
                    print("Random value:", random)
                    print("Probability:", action.get('trigger_probability', 1.0))
                    print("  > [Engine] Rule matched, but probability not triggered.")
                    continue
                print("Random value:", random)
                print("Probability:", action.get('trigger_probability', 1.0))
                interference_id = action.get('interference_id')
                interference_def = next((item for item in self.interference_library if item["id"] == interference_id), None)
                
                if interference_def:
                    activity_name = interference_def.get('target_activity')
                    params = interference_def.get('params', {})
                    if activity_name:
                        injector.inject_interference(self.device_serial, self.companion_app_package, activity_name, params)
                        self.logger.log_event("interference_injected", {"rule_id": rule_id, "interference_id": interference_id, "params": params})
                        self.triggered_rules.add(rule_id)
                        self.interference_count += 1
                        return interference_def 
        return None

    def evaluate_and_interfere(self,current_task: dict, current_state, step_number: int):
        if self.interference_count >= self.max_interferences:
            if self.max_interferences > 0: 
                print(f"  > [Engine] Maximum interference limit reached ({self.max_interferences}), no more interference will be injected this round or later.")
                self.max_interferences = -1 
            return None
        if current_state.get("is_interference_active"):
            print("  > [Engine] Detected popup active, skipping this round trigger.")
            return None
        target_rule_ids = current_task.get('target_rule_ids', [])
        print("Target rule ID list for this evaluation:", target_rule_ids)
        if not target_rule_ids:
            print("  > [Engine] No target rules specified for current task.")
            return None

        rules_by_id = {rule['id']: rule for rule in self.rules}

        for rule_id in target_rule_ids:
            rule = rules_by_id.get(rule_id)

            if not rule:
                print(f"  > [Engine] Warning: Rule with ID '{rule_id}' not found in rule library.")
                continue
            
            if rule.get('once', True) and rule_id in self.triggered_rules:
                print(f"  > [Engine] Rule '{rule_id}' is one-time and has already been triggered, skipping.")
                continue
            
            if self._check_conditions(rule.get('conditions', {}), current_state, step_number):
                print(f"  > [Engine] Target rule '{rule_id}' conditions matched!")
                return self._execute_actions(rule_id, rule.get('actions', []))

        print("  > [Engine] No rules matched.")
        return None

    def execute_post_actions_for_event(self, event: str):
        """
        This is a callback function called by LogMonitor.
        It is triggered in a background thread, independent of the Agent main loop.
        """
        print(f"  > [Engine-Callback] Received event '{event}', starting to process post actions...")
        if not self.active_interference or 'post_actions' not in self.active_interference:
            print(f"  > [Engine-Callback] No interference with post actions, ignoring event.")
            return

        post_actions = self.active_interference.get('post_actions', {})
        event_key = f"EVENT:{event}"

        if event_key in post_actions:
            actions_to_run = post_actions[event_key]
            print(f"  > [Engine-Callback] Match successful! Preparing to execute {len(actions_to_run)} post actions...")
            for action in actions_to_run:
                if action.get('type') == 'log':
                    print(f"  > [Post-Action Log]: {action.get('message')}")
                elif action.get('type') == 'adb':
                    command_str = action.get('command')
                    if command_str:
                        injector.execute_adb_command(self.device_serial, command_str.split())
            
            self.active_interference = None
        else:
            print(f"  > [Engine-Callback] Event '{event}' has no configured post actions in current interference.")
