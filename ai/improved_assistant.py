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
        - DELETE_PROJECTS_BY_NAME: Delete projects by name pattern
        - DELETE_SPRINT: Delete sprint (requires id)
        - DELETE_SPRINTS_BY_NAME: Delete sprints by name pattern
        - DELETE_TASK: Delete task (requires id)
        - ASSIGN_USER_TO_PROJECT: Assign user to project
        - REMOVE_USER_FROM_PROJECT: Remove user from project
        - LIST_PROJECT_MEMBERS: List project members
        - AUTO_ASSIGN_USERS: Auto-assign users to project
        
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
        
        IMPORTANT: When referencing projects or sprints by name, use the IDs from the AVAILABLE PROJECTS/SPRINTS list provided in the context.
        For tasks, always include sprint_id if a sprint is mentioned by name.
        
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
                
                # Add available projects and sprints
                if context.get("available_projects"):
                    context_info += "\nAVAILABLE PROJECTS:\n"
                    for proj in context["available_projects"]:
                        context_info += f"- {proj.get('name')} (ID: {proj.get('id')})\n"
                
                if context.get("available_sprints"):
                    context_info += "\nAVAILABLE SPRINTS:\n"
                    for sprint in context["available_sprints"]:
                        context_info += f"- {sprint.get('name')} (ID: {sprint.get('id')}, Project: {sprint.get('project_id')})\n"
            
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
        
        # DELETE OPERATIONS
        if any(word in message_lower for word in ["eliminar proyecto", "delete project", "borrar proyecto"]):
            project_id = self._extract_id(user_message, ["project", "proyecto"])
            if project_id:
                return {
                    "operations": [
                        {"type": "DELETE_PROJECT", "data": {"id": project_id}}
                    ],
                    "response_template": f"🗑️ Project {project_id} deleted!"
                }
            else:
                return {
                    "operations": [],
                    "response_template": "❌ Please specify project ID (e.g., 'delete project 5')"
                }
        
        elif any(phrase in message_lower for phrase in ["eliminar todos los proyectos", "delete all projects", "borrar todos los proyectos", "eliminame todos", "elminame todos"]):
            # Extract name pattern from the message
            name_pattern = self._extract_name_pattern(user_message)
            if name_pattern:
                return {
                    "operations": [
                        {"type": "DELETE_PROJECTS_BY_NAME", "data": {"name_pattern": name_pattern}}
                    ],
                    "response_template": f"🗑️ Deleting all projects matching '{name_pattern}'"
                }
            else:
                return {
                    "operations": [],
                    "response_template": "❌ Please specify what projects to delete (e.g., 'delete all projects with React')"
                }
        
        elif any(word in message_lower for word in ["eliminar sprint", "delete sprint", "borrar sprint"]):
            # Extract sprint ID or name
            sprint_id = self._extract_id(user_message, ["sprint"])
            sprint_name = self._extract_name_after_keyword(user_message, ["llamado", "named"])
            
            if sprint_id:
                return {
                    "operations": [
                        {"type": "DELETE_SPRINT", "data": {"id": sprint_id}}
                    ],
                    "response_template": f"🗑️ Sprint {sprint_id} deleted!"
                }
            elif sprint_name:
                return {
                    "operations": [
                        {"type": "DELETE_SPRINT", "data": {"name": sprint_name}}
                    ],
                    "response_template": f"🗑️ Sprint '{sprint_name}' deleted!"
                }
            else:
                return {
                    "operations": [],
                    "response_template": "❌ Please specify sprint ID or name (e.g., 'delete sprint 5' or 'elimina el sprint llamado TestSprint')"
                }
        
        elif any(phrase in message_lower for phrase in ["eliminar todos los sprints", "delete all sprints", "borrar todos los sprints", "eliminame todos los sprints", "elminame todos los sprints"]):
            # Extract name pattern from the message
            name_pattern = self._extract_name_pattern_sprint(user_message)
            project_id = self._extract_id(user_message, ["project", "proyecto"])
            
            if name_pattern:
                data = {"name_pattern": name_pattern}
                if project_id:
                    data["project_id"] = project_id
                return {
                    "operations": [
                        {"type": "DELETE_SPRINTS_BY_NAME", "data": data}
                    ],
                    "response_template": f"🗑️ Deleting all sprints matching '{name_pattern}'"
                }
            else:
                return {
                    "operations": [],
                    "response_template": "❌ Please specify what sprints to delete (e.g., 'delete all sprints with Test')"
                }
        
        elif any(word in message_lower for word in ["eliminar tarea", "delete task", "borrar tarea"]):
            # Extract task ID or title
            task_id = self._extract_id(user_message, ["task", "tarea"])
            task_title = self._extract_name_after_keyword(user_message, ["llamada", "llamado", "named", "titled"]) or self._extract_name(user_message, ["tarea", "task"])
            
            # Check if user wants to delete ALL tasks with the same name
            delete_all = any(phrase in message_lower for phrase in ["todas las tareas", "all tasks", "elimina todas"])
            
            if task_id:
                return {
                    "operations": [
                        {"type": "DELETE_TASK", "data": {"id": task_id}}
                    ],
                    "response_template": f"🗑️ Task {task_id} deleted!"
                }
            elif task_title and delete_all:
                return {
                    "operations": [
                        {"type": "DELETE_TASKS_BY_NAME", "data": {"name_pattern": task_title}}
                    ],
                    "response_template": f"🗑️ Deleting all tasks with name '{task_title}'"
                }
            elif task_title:
                return {
                    "operations": [
                        {"type": "DELETE_TASK", "data": {"title": task_title}}
                    ],
                    "response_template": f"🗑️ Task '{task_title}' deleted!"
                }
            else:
                return {
                    "operations": [],
                    "response_template": "❌ Please specify task ID or title (e.g., 'delete task 5' or 'elimina la tarea llamada Setup')"
                }
        
        elif any(word in message_lower for word in ["actualizar proyecto", "update project", "modificar proyecto", "cambiar proyecto"]):
            # Extract project ID or name
            project_id = self._extract_id(user_message, ["project", "proyecto"])
            project_name = self._extract_name_after_keyword(user_message, ["llamado", "named"]) or self._extract_name(user_message, ["proyecto", "project"])
            
            # Extract what to update
            update_data = {}
            
            # Extract new name
            if any(phrase in message_lower for phrase in ["nombre a", "name to", "renombrar a", "rename to"]):
                new_name = self._extract_update_value(user_message, ["nombre a", "name to", "renombrar a", "rename to"])
                if new_name:
                    update_data["name"] = new_name
            
            # Extract new description
            if any(phrase in message_lower for phrase in ["descripción a", "description to", "descripcion a"]):
                new_desc = self._extract_update_value(user_message, ["descripción a", "description to", "descripcion a"])
                if new_desc:
                    update_data["description"] = new_desc
            
            # Extract new status
            if any(phrase in message_lower for phrase in ["estado a", "status to", "marcar como"]):
                new_status = self._extract_update_value(user_message, ["estado a", "status to", "marcar como"])
                if new_status:
                    update_data["status"] = new_status
            
            if project_id:
                update_data["id"] = project_id
            elif project_name:
                update_data["name"] = project_name  # Use as search key if no new name provided
            
            if update_data and (project_id or project_name):
                return {
                    "operations": [
                        {"type": "UPDATE_PROJECT", "data": update_data}
                    ],
                    "response_template": f"✏️ Project updated successfully!"
                }
            else:
                return {
                    "operations": [],
                    "response_template": "❌ Please specify project and what to update (e.g., 'update project 5 name to NewName' or 'actualizar proyecto llamado OldName descripción a New description')"
                }
        
        elif any(phrase in message_lower for phrase in ["asignar usuario", "assign user", "agregar usuario al proyecto", "add user to project"]):
            # Extract user and project info
            user_id = self._extract_id(user_message, ["user", "usuario"])
            project_id = self._extract_id(user_message, ["project", "proyecto"])
            user_name = self._extract_name_after_keyword(user_message, ["usuario", "user"])
            project_name = self._extract_name_after_keyword(user_message, ["proyecto", "project"])
            
            data = {}
            if user_id:
                data["user_id"] = user_id
            elif user_name:
                data["user_name"] = user_name
            
            if project_id:
                data["project_id"] = project_id
            elif project_name:
                data["project_name"] = project_name
            
            if data.get("user_id") or data.get("user_name"):
                if data.get("project_id") or data.get("project_name"):
                    return {
                        "operations": [
                            {"type": "ASSIGN_USER_TO_PROJECT", "data": data}
                        ],
                        "response_template": "👥 User assigned to project!"
                    }
            
            return {
                "operations": [],
                "response_template": "❌ Please specify both user and project (e.g., 'assign user John to project WebApp')"
            }
        
        elif any(phrase in message_lower for phrase in ["asignar automaticamente", "auto assign", "asignacion automatica", "auto-assign"]):
            project_id = self._extract_id(user_message, ["project", "proyecto"])
            project_name = self._extract_name_after_keyword(user_message, ["proyecto", "project"])
            
            # Extract count
            count = 2  # default
            count_match = re.search(r"(\d+)\s*usuario", message_lower)
            if count_match:
                count = int(count_match.group(1))
            
            data = {"count": count}
            if project_id:
                data["project_id"] = project_id
            elif project_name:
                data["project_name"] = project_name
            
            if data.get("project_id") or data.get("project_name"):
                return {
                    "operations": [
                        {"type": "AUTO_ASSIGN_USERS", "data": data}
                    ],
                    "response_template": f"🤖 Auto-assigning {count} users to project!"
                }
            else:
                return {
                    "operations": [],
                    "response_template": "❌ Please specify project for auto-assignment (e.g., 'auto assign 3 users to project WebApp')"
                }
        
        elif any(phrase in message_lower for phrase in ["mostrar miembros", "members of project", "ver equipo del proyecto", "project members"]):
            project_id = self._extract_id(user_message, ["project", "proyecto"])
            project_name = self._extract_name_after_keyword(user_message, ["proyecto", "project"])
            
            data = {}
            if project_id:
                data["project_id"] = project_id
            elif project_name:
                data["project_name"] = project_name
            
            if data.get("project_id") or data.get("project_name"):
                return {
                    "operations": [
                        {"type": "LIST_PROJECT_MEMBERS", "data": data}
                    ],
                    "response_template": "👥 Here are the project members:"
                }
            else:
                return {
                    "operations": [],
                    "response_template": "❌ Please specify project (e.g., 'show members of project WebApp')"
                }
        
        # CREATE OPERATIONS
        elif "crear proyecto" in message_lower or "new project" in message_lower:
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
        elif any(word in message_lower for word in ["mostrar usuario", "list user", "ver usuario", "usuarios", "users", "equipo", "team", "mostrar equipo", "ver equipo"]):
            return {
                "operations": [
                    {"type": "LIST_USERS", "data": {}}
                ],
                "response_template": "👥 Here are the team members:"
            }
        
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
    
    def _extract_name_pattern(self, message: str) -> Optional[str]:
        """Extract name pattern for bulk operations"""
        message_lower = message.lower()
        
        # Look for patterns like "que digan X", "with X", "containing X"
        patterns = [
            r"que digan\s+([^\n]+)",
            r"que contengan\s+([^\n]+)", 
            r"with\s+([^\n]+)",
            r"containing\s+([^\n]+)",
            r"llamados\s+([^\n]+)",
            r"named\s+([^\n]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                return match.group(1).strip()
        
        # Fallback: look for text after "proyectos" 
        if "proyectos" in message_lower:
            parts = message_lower.split("proyectos")
            if len(parts) > 1:
                remaining = parts[-1].strip()
                # Remove common stopwords
                for stop in ["que digan", "que contengan", "llamados", "con"]:
                    if remaining.startswith(stop):
                        remaining = remaining[len(stop):].strip()
                return remaining if remaining else None
        
        return None
    
    def _extract_name_after_keyword(self, message: str, keywords: list) -> Optional[str]:
        """Extract name after specific keywords like 'llamado' or 'named'"""
        message_lower = message.lower()
        
        for keyword in keywords:
            if keyword in message_lower:
                parts = message_lower.split(keyword)
                if len(parts) > 1:
                    name_part = parts[-1].strip()
                    # Remove common stopwords and clean up
                    for stop in [" el", " la", " un", " una", " de", " para"]:
                        if name_part.startswith(stop):
                            name_part = name_part[len(stop):].strip()
                    return name_part.title() if name_part else None
        
        return None
    
    def _extract_name_pattern_sprint(self, message: str) -> Optional[str]:
        """Extract name pattern for bulk sprint operations"""
        message_lower = message.lower()
        
        # Look for patterns like "que digan X", "with X", "containing X"
        patterns = [
            r"que digan\s+([^\n]+)",
            r"que contengan\s+([^\n]+)", 
            r"with\s+([^\n]+)",
            r"containing\s+([^\n]+)",
            r"llamados\s+([^\n]+)",
            r"named\s+([^\n]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                return match.group(1).strip()
        
        # Fallback: look for text after "sprints" 
        if "sprints" in message_lower:
            parts = message_lower.split("sprints")
            if len(parts) > 1:
                remaining = parts[-1].strip()
                # Remove common stopwords
                for stop in ["que digan", "que contengan", "llamados", "con"]:
                    if remaining.startswith(stop):
                        remaining = remaining[len(stop):].strip()
                return remaining if remaining else None
        
        return None
    
    def _extract_update_value(self, message: str, keywords: list) -> Optional[str]:
        """Extract value after update keywords like 'name to X' or 'descripción a Y'"""
        message_lower = message.lower()
        
        for keyword in keywords:
            if keyword in message_lower:
                parts = message_lower.split(keyword)
                if len(parts) > 1:
                    value_part = parts[-1].strip()
                    # Clean up - remove common trailing words
                    for stop in [" del proyecto", " of project", " y ", " and "]:
                        if stop in value_part:
                            value_part = value_part.split(stop)[0].strip()
                    return value_part.title() if value_part else None
        
        return None