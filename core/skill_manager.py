import importlib.util
import os
import json
from .utils import get_resource_dir

class SkillManager:
    def __init__(self):
        self.skills = {}
        self.load_skills()

    def load_skills(self):
        skills_dir = os.path.join(get_resource_dir(), "skills")
        config_path = os.path.join(get_resource_dir(), "skills.json")
        
        enabled_skills = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    enabled_skills = json.load(f)
            except Exception:
                pass
                
        if not os.path.exists(skills_dir):
            return
            
        for filename in os.listdir(skills_dir):
            if filename.endswith(".py"):
                module_name = filename[:-3]
                if enabled_skills.get(module_name, False):
                    filepath = os.path.join(skills_dir, filename)
                    spec = importlib.util.spec_from_file_location(module_name, filepath)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        try:
                            spec.loader.exec_module(module)
                            if hasattr(module, "TOOL_SCHEMA") and hasattr(module, "execute"):
                                self.skills[module_name] = module
                        except Exception as e:
                            print(f"Failed to load skill {module_name}: {e}")

    def get_tools_schema(self):
        tools = []
        for name, module in self.skills.items():
            schema = module.TOOL_SCHEMA
            tools.append({
                "type": "function",
                "function": {
                    "name": schema["name"],
                    "description": schema["description"],
                    "parameters": schema["parameters"]
                }
            })
        return tools

    def execute_skill(self, name, args, pet_instance, memory_manager):
        if name in self.skills:
            try:
                return self.skills[name].execute(pet_instance=pet_instance, memory_manager=memory_manager, **args)
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Skill {name} not found or disabled."}
