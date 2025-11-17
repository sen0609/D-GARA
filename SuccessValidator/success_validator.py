import yaml
import re
from xml.etree import ElementTree as ET
from typing import Dict, Any, Optional, List


# Make sure you have installed PyYAML: pip install pyyaml


class SuccessValidator:
    """
    A validator for checking if a task is successful based on predefined rules.
    Loads a YAML file that defines the UI conditions required for each task to be considered successful.
    """

    def __init__(self, rules_yaml_path: str):
        """
        Initialize the validator.
        
        Args:
            rules_yaml_path (str): Path to the success_conditions.yaml file.
        """
        self.rules = self._load_rules(rules_yaml_path)

    def _load_rules(self, path: str) -> Dict[str, Any]:
        """
        Load rules from a YAML file.
        
        Args:
            path (str): Path to the YAML file.
        
        Returns:
            Dict[str, Any]: Parsed rules dictionary.
        """
        print(f"🔍 Loading success condition rules from '{path}'...")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                rules = yaml.safe_load(f)
                if not isinstance(rules, dict):
                    print("❌ Error: The top-level structure of the YAML file must be a dictionary (mapping).")
                    return {}
                print(f"✅ Successfully loaded {len(rules)} rules.")
                return rules
        except FileNotFoundError:
            print(f"❌ Error: Rule file '{path}' not found.")
            return {}
        except yaml.YAMLError as e:
            print(f"❌ Error: Failed to parse YAML file '{path}': {e}")
            return {}

    def _find_element(self, root: ET.Element, selector: str) -> Optional[ET.Element]:
        """
        Find the first matching element in the XML tree using a selector.
        Selector format: "key='value'" or 'key="value"'.
        
        Args:
            root (ET.Element): Root node of the XML tree.
            selector (str): String selector for finding the element.
            
        Returns:
            Optional[ET.Element]: The found element or None.
        """
        # Use regex to parse key='value' format
        match = re.match(r"([^=]+)=['\"]([^'\"]+)['\"]", selector)
        if not match:
            print(f"⚠️ Invalid selector format: '{selector}'. Should be key='value'.")
            return None
            
        key, value = match.groups()
        
        # Use XPath to find element; .//* means search anywhere under current node
        xpath = f".//*[@{key}='{value}']"
        return root.find(xpath)


    def _check_condition(self, root: ET.Element, condition: Dict[str, Any]) -> bool:
        """
        Check a single condition and dispatch to the specific check method.
        """
        cond_type = condition.get("type")
        if not cond_type:
            print(f"⚠️ Condition format error, missing 'type': {condition}")
            return False

        # Step 1: Handle 'logic' conditions that do not require a top-level selector
        if cond_type == "any_of":
            sub_conditions = condition.get("sub_conditions", [])
            if not sub_conditions:
                print(f"⚠️ 'any_of' condition missing 'sub_conditions' list.")
                return False
            # Iterate all 'or' conditions; if any succeed, the whole condition succeeds
            for sub_cond in sub_conditions:
                if self._check_condition(root, sub_cond):
                    return True # Success! Return early
            # If all sub-conditions fail, the 'any_of' fails
            return False

        # Step 2: Handle all 'element' conditions that require a selector
        selector = condition.get("selector")
        if not selector:
            print(f"⚠️ Condition format error, type '{cond_type}' missing 'selector': {condition}")
            return False

        element = self._find_element(root, selector)

        if cond_type == "element_exists":
            return element is not None
        
        if cond_type == "element_not_exists":
            return element is None
            
        # --- The following conditions require the element to be found; if not, fail ---
        if element is None:
            return False

        if cond_type == "element_property":
            attr = condition.get("attribute")
            expected_value = condition.get("value")
            if attr is None or expected_value is None:
                print(f"⚠️ 'element_property' condition missing 'attribute' or 'value'.")
                return False
            return element.get(attr) == str(expected_value)

        if cond_type == "element_text_equals":
            return element.get("text") == condition.get("text", "")
            
        if cond_type == "element_text_contains":
            text_to_find = condition.get("text")
            if text_to_find is None: return False
            return str(text_to_find) in element.get("text", "")

        if cond_type == "element_property_contains":
            attr = condition.get("attribute")
            value_to_find = condition.get("value")
            if attr is None or value_to_find is None:
                print(f"⚠️ 'element_property_contains' condition missing 'attribute' or 'value'.")
                return False
            actual_value = element.get(attr, "")
            return str(value_to_find) in actual_value

        # If none of the known cond_type matched
        print(f"⚠️ Unknown condition type: '{cond_type}'")
        return False


    def check(self, rule_key: str, current_xml: str) -> bool:
        """
        Check if the success conditions for the given task are satisfied in the current XML.
        
        Args:
            rule_key (str): The rule key for the task (from tasks.json).
            current_xml (str): The XML layout string of the current UI.
            
        Returns:
            bool: True if all conditions are satisfied, False otherwise.
        """
        if not rule_key in self.rules:
            print(f"⚠️ Warning: No rule found for key '{rule_key}' in the rules file.")
            return False
            
        task_rules = self.rules[rule_key]
        conditions: List[Dict[str, Any]] = task_rules.get("conditions", [])

        if not conditions:
            print(f"⚠️ Warning: Rule '{rule_key}' does not define any 'conditions'.")
            return False # No success conditions defined, cannot determine success

        try:
            root = ET.fromstring(current_xml)
        except ET.ParseError:
            print("❌ Error: Failed to parse current UI XML.")
            return False

        # All conditions must be satisfied (AND)
        for i, condition in enumerate(conditions):
            if not self._check_condition(root, condition):
                # Exit early: if any condition is not satisfied, the task is not successful
                # print(f"  - Condition {i+1} failed: {condition}") # For debugging
                return False
        
        # If the loop completes, all conditions passed
        return True