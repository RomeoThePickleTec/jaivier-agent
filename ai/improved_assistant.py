# ai/improved_assistant.py - ENHANCED WITH CRUD
"""Enhanced AI assistant with full CRUD operations"""

import json
import re
import logging
from typing import Dict, Optional
import google.generativeai as genai
from config.settings import GEMINI_API_KEY

logger = logging.getLogger(__name__)

if GEMINI_API_KEY and GEMINI_API_KEY != "TU_GEMINI_API_KEY":
    genai.configure(api_key=GEMINI_API_KEY)

class ImprovedAIAssistant:
    def __init__(self):
        self.model = None
        self.system_prompt = self._build_system_prompt()
        self._initialize_model()
    
    def _initialize_model(self):
        if not GEMINI_API_KEY or GEMINI_API_KEY == "TU_GEMINI_API_KEY":
            logger.warning("⚠️ Gemini API Key not configured")
            return
        
        try:
            model_names = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.0-pro']
            for model_name in model_names:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    logger.info(f"✅ Model {model_name} initialized")
                    break
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"❌ Error configuring Gemini: {e}")
            self.model = None
    
    def _build_system_prompt(self) -> str:
        return """
        You are an AI assistant that generates API operations in JSON format for a project management system.
        
        AVAILABLE OPERATIONS:
        - CREATE_PROJECT: Create new project
        - CREATE_SPRINT: Create new sprint (requires project_id)
        - CREATE_TASK: Create new task (optional project_id, sprint_id)
        - LIST_PROJECTS: List all projects
        - LIST_SPRINTS: List sprints (optional project_id filter)
        - LIST_TASKS: List tasks (optional project_id, sprint_id filters)
        - UPDATE_PROJECT: Update project (requires id)
        - UPDATE_SPRINT: Update sprint (requires id)
        - UPDATE_TASK: Update task (requires id)
        - DELETE_PROJECT: Delete project (requires id)
        - DELETE_SPRINT: Delete sprint (requires id)
        - DELETE_TASK: Delete task (requires id)
        
        RESPONSE FORMAT:
        {
            "operations": [
                {
                    "type": "OPERATION_TYPE",
                    "data": {
                        // operation-specific data
                    },
                    "reference": "unique_name" // optional, for referencing in later operations
                }
            ],
            "response_template": "Success message"
        }
        
        FIELD REFERENCE:
        Use "$reference_name.field" to reference data from previous operations.
        Example: "project_id": "$project1.id"
        
        FIELD MAPPINGS:
        Projects: name, description, start_date, end_date, status (active/completed/paused)
        Sprints: name, description, project_id, start_date, end_date, status (active/completed)
        Tasks: title, description, project_id, sprint_id, priority (low/medium/high/critical), status (todo/in_progress/completed), estimated_hours, due_date
        
        EXAMPLES:
        
        "create project called MyApp":
        {
            "operations": [
                {"type": "CREATE_PROJECT", "data": {"name": "MyApp", "description": "New application project"}}
            ],
            "response_template": "✅ Project 'MyApp' created!"
        }
        
        "create sprint for project 5":
        {
            "operations": [
                {"type": "CREATE_SPRINT", "data": {"name": "Sprint 1", "project_id": 5}}
            ],
            "response_template": "✅ Sprint created for project!"
        }
        
        "create project with sprint and 3 tasks":
        {
            "operations": [
                {"type": "CREATE_PROJECT", "data": {"name": "Full Project"}, "reference": "proj1"},
                {"type": "CREATE_SPRINT", "data": {"name": "Initial Sprint", "project_id": "$proj1.id"}, "reference": "sprint1"},
                {"type": "CREATE_TASK", "data": {"title": "Task 1", "project_id": "$proj1.id", "sprint_id": "$sprint1.id"}},
                {"type": "CREATE_TASK", "data": {"title": "Task 2", "project_id": "$proj1.id", "sprint_id": "$sprint1.id"}},
                {"type": "CREATE_TASK", "data": {"title": "Task 3", "project_id": "$proj1.id", "sprint_id": "$sprint1.id"}}
            ],
            "response_template": "✅ Created complete project with sprint and 3 tasks!"
        }
        """
    
    async def generate_operations(self, user_message: str, context: Optional[Dict] = None) -> Dict:
        try:
            if not self.model:
                return self._fallback_operations(user_message, context)
            
            # Prepare context info
            context_info = ""
            if context:
                if context.get("current_project"):
                    proj = context["current_project"]
                    context_info += f"Current project: {proj['name']} (ID: {proj['id']})\n"
                if context.get("current_sprint"):
                    sprint = context["current_sprint"]
                    context_info += f"Current sprint: {sprint['name']} (ID: {sprint['id']})\n"
            
            prompt = f"""
            {self.system_prompt}
            
            USER COMMAND: "{user_message}"
            
            CURRENT CONTEXT:
            {context_info}
            
            Generate the appropriate operations in valid JSON format.
            """
            
            response = self.model.generate_content(prompt)
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                try:
                    operations = json.loads(json_match.group())
                    return operations
                except json.JSONDecodeError:
                    logger.error("Error parsing AI JSON response")
                    return self._fallback_operations(user_message, context)
            else:
                logger.warning("No JSON found in AI response")
                return self._fallback_operations(user_message, context)
                
        except Exception as e:
            logger.error(f"Error in operation generation: {e}")
            return self._fallback_operations(user_message, context)
    
    def _fallback_operations(self, user_message: str, context: Optional[Dict] = None) -> Dict:
        """Fallback operations without AI"""
        message_lower = user_message.lower()
        
        # CREATE OPERATIONS
        if "crear proyecto" in message_lower or "new project" in message_lower:
            name = self._extract_name(user_message, ["proyecto", "project"])
            return {
                "operations": [
                    {"type": "CREATE_PROJECT", "data": {"name": name}}
                ],
                "response_template": f"✅ Project '{name}' created!"
            }
        
        elif "crear sprint" in message_lower or "new sprint" in message_lower:
            name = self._extract_name(user_message, ["sprint"])
            project_id = self._extract_id(user_message, ["project", "proyecto"])
            
            data = {"name": name}
            if project_id:
                data["project_id"] = project_id
            elif context and context.get("current_project"):
                data["project_id"] = context["current_project"]["id"]
            
            return {
                "operations": [
                    {"type": "CREATE_SPRINT", "data": data}
                ],
                "response_template": f"✅ Sprint '{name}' created!"
            }
        
        elif "crear tarea" in message_lower or "new task" in message_lower:
            title = self._extract_name(user_message, ["tarea", "task"])
            return {
                "operations": [
                    {"type": "CREATE_TASK", "data": {"title": title}}
                ],
                "response_template": f"✅ Task '{title}' created!"
            }
        
        # LIST OPERATIONS
        elif any(word in message_lower for word in ["mostrar proyecto", "list project", "ver proyecto"]):
            return {
                "operations": [
                    {"type": "LIST_PROJECTS", "data": {}}
                ],
                "response_template": "📁 Here are the projects:"
            }
        
        elif any(word in message_lower for word in ["mostrar sprint", "list sprint", "ver sprint"]):
            return {
                "operations": [
                    {"type": "LIST_SPRINTS", "data": {}}
                ],
                "response_template": "🏃 Here are the sprints:"
            }
        
        elif any(word in message_lower for word in ["mostrar tarea", "list task", "ver tarea"]):
            return {
                "operations": [
                    {"type": "LIST_TASKS", "data": {}}
                ],
                "response_template": "📋 Here are the tasks:"
            }
        
        # COMPLEX OPERATIONS
        elif "proyecto completo" in message_lower:
            name = self._extract_name(user_message, ["proyecto"])
            return {
                "operations": [
                    {"type": "CREATE_PROJECT", "data": {"name": name}, "reference": "proj1"},
                    {"type": "CREATE_SPRINT", "data": {"name": "Sprint 1", "project_id": "$proj1.id"}, "reference": "sprint1"},
                    {"type": "CREATE_TASK", "data": {"title": "Setup", "project_id": "$proj1.id", "sprint_id": "$sprint1.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Development", "project_id": "$proj1.id", "sprint_id": "$sprint1.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Testing", "project_id": "$proj1.id", "sprint_id": "$sprint1.id"}}
                ],
                "response_template": f"✅ Complete project '{name}' created with sprint and 3 tasks!"
            }
        
        # DEFAULT
        else:
            return {
                "operations": [
                    {"type": "LIST_PROJECTS", "data": {}}
                ],
                "response_template": "Try: 'create project MyApp', 'new sprint', 'list projects'"
            }
    
    def _extract_name(self, message: str, keywords: list) -> str:
        """Extract name from message"""
        message_lower = message.lower()
        
        for keyword in keywords:
            if keyword in message_lower:
                # Extract text after keyword
                parts = message_lower.split(keyword)
                if len(parts) > 1:
                    # Take text after keyword, clean it up
                    name_part = parts[-1].strip()
                    # Remove common stopwords
                    for stop in [" llamado", " called", " named", " de", " para"]:
                        if stop in name_part:
                            name_part = name_part.split(stop)[-1].strip()
                    return name_part.title() if name_part else "New Item"
        
        return "New Item"
    
    def _extract_id(self, message: str, keywords: list) -> Optional[int]:
        """Extract ID from message"""
        # Look for patterns like "project 5", "proyecto 3"
        for keyword in keywords:
            pattern = rf"{keyword}\s+(\d+)"
            match = re.search(pattern, message.lower())
            if match:
                return int(match.group(1))
        return None