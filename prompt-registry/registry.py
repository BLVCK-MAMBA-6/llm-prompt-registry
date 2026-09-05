import yaml
import json
import os
import hashlib
from datetime import datetime

class PromptRegistry:
    def __init__(self, config_path="config.yaml", prompts_dir="prompts", audit_log_path="audit_log.json"):
        self.prompts_dir = prompts_dir
        self.audit_log_path = audit_log_path
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found at {config_path}")
            
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
            
        if not os.path.exists(self.audit_log_path):
            with open(self.audit_log_path, 'w') as file:
                json.dump([], file)
                
        print(f"✅ PromptRegistry initialized. Loaded {len(self.config)} prompt definitions.")

    def _get_version_for_user(self, prompt_name: str, user_id: str = None) -> str:
        prompt_config = self.config[prompt_name]
        if prompt_config.get('ab_test', {}).get('enabled') and user_id:
            split = prompt_config['ab_test']['split_percentage']
            variant_a = prompt_config['ab_test']['variant_a']
            variant_b = prompt_config['ab_test']['variant_b']
            hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 100
            if hash_val < split:
                return variant_a
            else:
                return variant_b
        return prompt_config['active_version']

    def get(self, prompt_name: str, user_id: str = None, **variables) -> str:
        if prompt_name not in self.config:
            raise ValueError(f"Prompt '{prompt_name}' does not exist in the registry.")
        
        version_to_use = self._get_version_for_user(prompt_name, user_id)
        file_path = os.path.join(self.prompts_dir, prompt_name, f"{version_to_use}.yaml")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Version file for '{prompt_name}' ({version_to_use}) not found.")
            
        with open(file_path, 'r') as file:
            prompt_data = yaml.safe_load(file)
            
        template = prompt_data.get('template')
        if not template:
            raise ValueError(f"No 'template' key found in {file_path}")
            
        try:
            return template.format(**variables)
        except KeyError as e:
            raise ValueError(f"Missing required variable for prompt '{prompt_name}': {e}")

    def change_version(self, prompt_name: str, new_version: str):
        if prompt_name not in self.config:
            raise ValueError(f"Prompt '{prompt_name}' does not exist.")
            
        old_version = self.config[prompt_name]['active_version']
        self.config[prompt_name]['active_version'] = new_version
        
        with open("config.yaml", 'w') as file:
            yaml.dump(self.config, file, default_flow_style=False)
            
        self._log_action("VERSION_CHANGE", prompt_name, old_version, new_version)
        print(f"🔄 Changed '{prompt_name}' from {old_version} to {new_version}")

    def rollback(self, prompt_name: str):
        if not os.path.exists(self.audit_log_path):
            print("⚠️ No audit log found. Cannot rollback.")
            return
            
        with open(self.audit_log_path, 'r') as file:
            logs = json.load(file)
            
        for log in reversed(logs):
            if log['prompt_name'] == prompt_name and log['action'] == 'VERSION_CHANGE':
                old_version = log['old_version']
                self.change_version(prompt_name, old_version)
                print(f"⏪ Rolled back '{prompt_name}' to {old_version}")
                return
                
        print(f"⚠️ No previous version found in logs for '{prompt_name}'")

    def _log_action(self, action: str, prompt_name: str, old_version: str, new_version: str):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "prompt_name": prompt_name,
            "old_version": old_version,
            "new_version": new_version
        }
        
        with open(self.audit_log_path, 'r') as file:
            logs = json.load(file)
            
        logs.append(log_entry)
        
        with open(self.audit_log_path, 'w') as file:
            json.dump(logs, file, indent=2)

    def get_metadata(self, prompt_name: str) -> dict:
        if prompt_name not in self.config:
            raise ValueError(f"Prompt '{prompt_name}' does not exist.")
            
        active_version = self.config[prompt_name]['active_version']
        file_path = os.path.join(self.prompts_dir, prompt_name, f"{active_version}.yaml")
        
        with open(file_path, 'r') as file:
            prompt_data = yaml.safe_load(file)
            
        return {
            "prompt_name": prompt_name,
            "active_version": active_version,
            "metadata": prompt_data.get("metadata", {})
        }

    def get_versions(self, prompt_name: str) -> list:
        """Returns a list of all available versions for a prompt."""
        prompt_dir = os.path.join(self.prompts_dir, prompt_name)
        if not os.path.exists(prompt_dir):
            return []
            
        versions = []
        for file in os.listdir(prompt_dir):
            if file.endswith('.yaml'):
                versions.append(file.replace('.yaml', ''))
                
        return sorted(versions)