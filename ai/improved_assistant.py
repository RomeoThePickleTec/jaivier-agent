# ai/improved_assistant.py - ENHANCED WITH CRUD
"""Enhanced AI assistant with full CRUD operations"""

import json
import re
import logging
from typing import Dict, Optional, List
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
        - UPDATE_USER: Update user (requires id/username, supports: email, full_name, role, work_mode, phone, password_hash)
        - DELETE_PROJECT: Delete project (requires id)
        - DELETE_PROJECTS_BY_NAME: Delete projects by name pattern
        - DELETE_SPRINT: Delete sprint (requires id)
        - DELETE_SPRINTS_BY_NAME: Delete sprints by name pattern
        - DELETE_TASK: Delete task (requires id)
        - DELETE_USER: Delete user (requires id/username)
        - ASSIGN_USER_TO_PROJECT: Assign user to project
        - REMOVE_USER_FROM_PROJECT: Remove user from project (requires project_id/project_name and user_id/user_name)
        - LIST_PROJECT_MEMBERS: List project members
        - AUTO_ASSIGN_USERS: Auto-assign users to project
        - QUERY_STATUS: Answer natural language questions about projects, sprints, tasks with AI analysis
          Required data: query, entity_type, entity_name, entity_id (optional)
          Example: {"type": "QUERY_STATUS", "data": {"query": "cuantas tareas faltan", "entity_type": "project", "entity_name": "JAI-VIER", "entity_id": 173}}
        
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
        
        "cuántas tareas faltan del proyecto JAI-VIER":
        {
            "operations": [
                {"type": "QUERY_STATUS", "data": {"query": "cuántas tareas faltan del proyecto JAI-VIER", "entity_type": "project", "entity_name": "JAI-VIER"}}
            ],
            "response_template": "📋 Checking pending tasks for project JAI-VIER..."
        }
        
        "busca tareas con nombre X y ponles nombres con sentido":
        {
            "operations": [
                {"type": "LIST_TASKS", "data": {"project_id": 173, "title": "X"}, "reference": "tasks_to_rename"},
                {"type": "UPDATE_TASK", "data": {"id": "$tasks_to_rename.tasks[0].id", "title": "Setup initial project configuration"}},
                {"type": "UPDATE_TASK", "data": {"id": "$tasks_to_rename.tasks[1].id", "title": "Implement user authentication module"}},
                {"type": "UPDATE_TASK", "data": {"id": "$tasks_to_rename.tasks[2].id", "title": "Design database schema structure"}}
            ],
            "response_template": "✅ Tasks renamed with meaningful names!"
        }
        
        IMPORTANT GUIDELINES:
        - ALWAYS create individual CREATE_TASK operations for each task mentioned
        - DO NOT include task lists in sprint descriptions - create separate tasks instead
        - When creating complex projects, break down tasks into individual operations
        - Example: If a sprint mentions "setup, authentication, database", create 3 separate CREATE_TASK operations
        - When renaming tasks, use SPECIFIC and MEANINGFUL names like "Setup authentication system", "Configure database connections", "Implement user login flow"
        - DO NOT use generic names like "Rename this task" - always be specific about what the task should accomplish
        """
    
    async def generate_operations(self, user_message: str, context: Optional[Dict] = None) -> Dict:
        try:
            # For query operations, always use fallback to ensure proper entity extraction
            message_lower = user_message.lower()
            if any(phrase in message_lower for phrase in [
                "como va", "como está", "cómo va", "cómo está", "que tal va", "qué tal va",
                "how is", "status of", "estado de", "estado del", "que necesita", "qué necesita",
                "progress", "progreso", "resumen", "summary", "oye y el", "hey and the"
            ]):
                return self._fallback_operations(user_message, context)
            
            # For complex project creation, also use fallback for better detection
            if (("proyecto completo" in message_lower) or
                (any(word in message_lower for word in ["crear proyecto", "crea el proyecto", "new project"]) and 
                 any(word in message_lower for word in ["sprint", "tareas", "tasks", "objetivo", "tecnolog"]) and
                 len(user_message) > 200)):
                return self._fallback_operations(user_message, context)
            
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
        
        elif any(word in message_lower for word in ["eliminar usuario", "delete user", "borrar usuario"]):
            # Extract user ID, username or name
            user_id = self._extract_id(user_message, ["user", "usuario"])
            username = self._extract_name_after_keyword(user_message, ["usuario", "user", "llamado", "named"])
            
            # Also try to extract from patterns like "eliminar usuario Juan"
            if not username and not user_id:
                # Look for pattern "eliminar usuario [name]"
                pattern_match = re.search(r"(?:eliminar|delete|borrar)\s+usuario\s+(\w+)", message_lower)
                if pattern_match:
                    username = pattern_match.group(1)
            
            if user_id:
                return {
                    "operations": [
                        {"type": "DELETE_USER", "data": {"id": user_id}}
                    ],
                    "response_template": f"🗑️ User {user_id} deleted!"
                }
            elif username:
                return {
                    "operations": [
                        {"type": "DELETE_USER", "data": {"username": username}}
                    ],
                    "response_template": f"🗑️ User '{username}' deleted!"
                }
            else:
                return {
                    "operations": [],
                    "response_template": "❌ Please specify user ID or username (e.g., 'delete user 5' or 'eliminar usuario Juan')"
                }
        
        elif any(word in message_lower for word in ["actualizar usuario", "update user", "modificar usuario", "cambiar usuario", "editar usuario", "edit user"]):
            # Extract user info
            user_id = self._extract_id(user_message, ["user", "usuario"])
            username = self._extract_name_after_keyword(user_message, ["usuario", "user"])
            
            # Extract what to update
            update_data = {}
            
            # Extract fields to update
            if any(phrase in message_lower for phrase in ["email a", "email to", "correo a"]):
                new_email = self._extract_update_value(user_message, ["email a", "email to", "correo a"])
                if new_email:
                    update_data["email"] = new_email
            
            if any(phrase in message_lower for phrase in ["nombre a", "name to", "full_name a"]):
                new_name = self._extract_update_value(user_message, ["nombre a", "name to", "full_name a"])
                if new_name:
                    update_data["full_name"] = new_name
            
            if any(phrase in message_lower for phrase in ["rol a", "role to", "como"]):
                new_role = self._extract_update_value(user_message, ["rol a", "role to", "como"])
                if new_role:
                    update_data["role"] = new_role
            
            if any(phrase in message_lower for phrase in ["work_mode a", "modo a", "trabajo a"]):
                new_work_mode = self._extract_update_value(user_message, ["work_mode a", "modo a", "trabajo a"])
                if new_work_mode:
                    update_data["work_mode"] = new_work_mode.upper()
            
            if any(phrase in message_lower for phrase in ["telefono a", "phone to", "tel a"]):
                new_phone = self._extract_update_value(user_message, ["telefono a", "phone to", "tel a"])
                if new_phone:
                    update_data["phone"] = new_phone
            
            if any(phrase in message_lower for phrase in ["password a", "contraseña a"]):
                new_password = self._extract_update_value(user_message, ["password a", "contraseña a"])
                if new_password:
                    update_data["password_hash"] = new_password
            
            if user_id:
                update_data["id"] = user_id
            elif username:
                update_data["username"] = username
            
            if update_data and (user_id or username):
                return {
                    "operations": [
                        {"type": "UPDATE_USER", "data": update_data}
                    ],
                    "response_template": f"✏️ User updated successfully!"
                }
            else:
                return {
                    "operations": [],
                    "response_template": "❌ Please specify user and what to update (e.g., 'update user John email to new@email.com' or 'actualizar usuario 5 rol a admin')"
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
        
        elif any(phrase in message_lower for phrase in ["asignar usuario", "assign user", "agregar usuario al proyecto", "add user to project", "añadele al proyecto", "añadir al proyecto"]):
            # Extract project info
            project_id = self._extract_id(user_message, ["project", "proyecto"])
            project_name = self._extract_name_after_keyword(user_message, ["proyecto", "project"])
            
            # Extract multiple users - look for patterns like "aram, fer caves, y aaron hernandez"
            users_to_assign = self._extract_multiple_users(user_message)
            
            if not users_to_assign:
                # Fallback to single user extraction
                user_id = self._extract_id(user_message, ["user", "usuario"])
                user_name = self._extract_name_after_keyword(user_message, ["usuario", "user"])
                if user_id or user_name:
                    users_to_assign = [{"user_id": user_id, "user_name": user_name}]
            
            project_data = {}
            if project_id:
                project_data["project_id"] = project_id
            elif project_name:
                project_data["project_name"] = project_name
            
            if users_to_assign and (project_data.get("project_id") or project_data.get("project_name")):
                operations = []
                for user_info in users_to_assign:
                    operation_data = {**project_data, **user_info}
                    operations.append({"type": "ASSIGN_USER_TO_PROJECT", "data": operation_data})
                
                return {
                    "operations": operations,
                    "response_template": f"👥 Assigning {len(users_to_assign)} users to project!"
                }
            
            return {
                "operations": [],
                "response_template": "❌ Please specify both users and project (e.g., 'assign users John, Mary to project WebApp')"
            }
        
        elif any(phrase in message_lower for phrase in ["asignar automaticamente", "auto assign", "asignacion automatica", "auto-assign", "usuario al azar", "user randomly", "al azar"]):
            project_id = self._extract_id(user_message, ["project", "proyecto"])
            project_name = self._extract_name_after_keyword(user_message, ["proyecto", "project"])
            
            # Special pattern for "añadele a [project] a un usuario"
            if not project_name:
                pattern_match = re.search(r"añadele?\s+a\s+(\w+)\s+a\s+", message_lower)
                if pattern_match:
                    project_name = pattern_match.group(1)
            
            # Extract count
            count = 2  # default
            # Look for patterns like "1 usuario", "2 users", "1 solo", "un usuario", etc.
            count_patterns = [
                r"(\d+)\s*usuario",
                r"(\d+)\s*user",
                r"(\d+)\s*solo",
                r"un\s+usuario",  # "un usuario" = 1 user
                r"una\s+persona",  # "una persona" = 1 person
            ]
            
            for pattern in count_patterns:
                count_match = re.search(pattern, message_lower)
                if count_match:
                    if pattern in [r"un\s+usuario", r"una\s+persona"]:
                        count = 1  # "un usuario" means 1
                    else:
                        count = int(count_match.group(1))
                    break
            
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
        
        elif any(phrase in message_lower for phrase in ["remover usuario", "remove user", "eliminar usuario del proyecto", "quitar usuario", "sacar usuario", "remove from project"]):
            # Extract project info
            project_id = self._extract_id(user_message, ["project", "proyecto"])
            project_name = self._extract_name_after_keyword(user_message, ["proyecto", "project"])
            
            # Special pattern for "remover/quitar a [user] del proyecto [project]"
            if not project_name:
                # Look for "del proyecto [name]" pattern
                pattern_match = re.search(r"del proyecto\s+(\w+)", message_lower)
                if pattern_match:
                    project_name = pattern_match.group(1)
                
                # Also look for "proyecto [name]" pattern
                if not project_name:
                    pattern_match = re.search(r"proyecto\s+(\w+)", message_lower)
                    if pattern_match:
                        project_name = pattern_match.group(1)
            
            # Extract multiple users - look for patterns like "remover a aram, fer caves del proyecto"
            users_to_remove = self._extract_multiple_users(user_message)
            
            if not users_to_remove:
                # Fallback to single user extraction
                user_id = self._extract_id(user_message, ["user", "usuario"])
                user_name = self._extract_name_after_keyword(user_message, ["usuario", "user", "a "])
                if user_id or user_name:
                    users_to_remove = [{"user_id": user_id, "user_name": user_name}]
            
            project_data = {}
            if project_id:
                project_data["project_id"] = project_id
            elif project_name:
                project_data["project_name"] = project_name
            
            if users_to_remove and (project_data.get("project_id") or project_data.get("project_name")):
                operations = []
                for user_info in users_to_remove:
                    operation_data = {**project_data, **user_info}
                    operations.append({"type": "REMOVE_USER_FROM_PROJECT", "data": operation_data})
                
                return {
                    "operations": operations,
                    "response_template": f"👥 Removing {len(users_to_remove)} users from project!"
                }
            
            return {
                "operations": [],
                "response_template": "❌ Please specify both users and project to remove (e.g., 'remove user John from project WebApp')"
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
        
        # CREATE OPERATIONS - Check for creation keywords first
        elif any(word in message_lower for word in ["crear proyecto", "new project", "crea el proyecto", "create project"]):
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
        
        # LIST OPERATIONS - Only if explicitly asking to list, not just mentioning users
        elif any(phrase in message_lower for phrase in ["mostrar usuario", "list user", "ver usuario", "mostrar equipo", "ver equipo", "list team"]) and not any(create_word in message_lower for create_word in ["crear", "create", "crea", "new"]):
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
        
        # COMPLEX OPERATIONS - Detect detailed project descriptions
        elif (("proyecto completo" in message_lower or "proyecto con tareas" in message_lower) or
              # Detect detailed projects with sprints mentioned
              (any(word in message_lower for word in ["crear proyecto", "crea el proyecto", "new project"]) and 
               any(word in message_lower for word in ["sprint", "tareas", "tasks", "objetivo", "tecnolog"]) and
               len(user_message) > 200)):
            name = self._extract_name(user_message, ["proyecto"])
            
            # Try to extract sprint information from the message
            sprint_operations = []
            task_operations = []
            
            # Detect number of sprints mentioned
            sprint_count = 3  # default
            if "4 sprints" in message_lower or "sprint: 4" in message_lower:
                sprint_count = 4
            elif "2 sprints" in message_lower or "sprint: 2" in message_lower:
                sprint_count = 2
            elif "5 sprints" in message_lower or "sprint: 5" in message_lower:
                sprint_count = 5
            
            # Base operations
            operations = [
                {"type": "CREATE_PROJECT", "data": {"name": name}, "reference": "proj1"}
            ]
            
            # Create sprints based on detected information
            if "hardware" in message_lower and "dashboard" in message_lower:
                # SmartPlant specific sprints
                operations.extend([
                    {"type": "CREATE_SPRINT", "data": {"name": "Sprint 1 - Hardware y pruebas", "project_id": "$proj1.id"}, "reference": "sprint1"},
                    {"type": "CREATE_SPRINT", "data": {"name": "Sprint 2 - Lógica de riego", "project_id": "$proj1.id"}, "reference": "sprint2"},
                    {"type": "CREATE_SPRINT", "data": {"name": "Sprint 3 - Comunicación + dashboard", "project_id": "$proj1.id"}, "reference": "sprint3"},
                    {"type": "CREATE_SPRINT", "data": {"name": "Sprint 4 - Optimización y deploy", "project_id": "$proj1.id"}, "reference": "sprint4"},
                ])
                
                # SmartPlant specific tasks
                operations.extend([
                    # Sprint 1 tasks
                    {"type": "CREATE_TASK", "data": {"title": "Configurar entorno ESP32 (drivers + IDE)", "project_id": "$proj1.id", "sprint_id": "$sprint1.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Leer humedad de suelo y clima (DHT22)", "project_id": "$proj1.id", "sprint_id": "$sprint1.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Activar bomba vía relé", "project_id": "$proj1.id", "sprint_id": "$sprint1.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Test por puerto serial", "project_id": "$proj1.id", "sprint_id": "$sprint1.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Diagrama eléctrico/documentación", "project_id": "$proj1.id", "sprint_id": "$sprint1.id"}},
                    
                    # Sprint 2 tasks
                    {"type": "CREATE_TASK", "data": {"title": "Definir umbral de humedad", "project_id": "$proj1.id", "sprint_id": "$sprint2.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Activar bomba automáticamente", "project_id": "$proj1.id", "sprint_id": "$sprint2.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Añadir temporizador para evitar riegos repetidos", "project_id": "$proj1.id", "sprint_id": "$sprint2.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Configurable por archivo .py", "project_id": "$proj1.id", "sprint_id": "$sprint2.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Probar sin conexión a PC", "project_id": "$proj1.id", "sprint_id": "$sprint2.id"}},
                    
                    # Sprint 3 tasks  
                    {"type": "CREATE_TASK", "data": {"title": "Enviar datos por HTTP o MQTT", "project_id": "$proj1.id", "sprint_id": "$sprint3.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Crear dashboard en React + Firebase", "project_id": "$proj1.id", "sprint_id": "$sprint3.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Mostrar temperatura, humedad, estado del suelo", "project_id": "$proj1.id", "sprint_id": "$sprint3.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Historial de riegos", "project_id": "$proj1.id", "sprint_id": "$sprint3.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Autenticación básica", "project_id": "$proj1.id", "sprint_id": "$sprint3.id"}},
                    
                    # Sprint 4 tasks
                    {"type": "CREATE_TASK", "data": {"title": "Optimización de código y performance", "project_id": "$proj1.id", "sprint_id": "$sprint4.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Deploy y configuración final", "project_id": "$proj1.id", "sprint_id": "$sprint4.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Testing integral del sistema", "project_id": "$proj1.id", "sprint_id": "$sprint4.id"}},
                ])
                
                return {
                    "operations": operations,
                    "response_template": f"✅ Complete SmartPlant project '{name}' created with 4 sprints and 18 tasks!"
                }
            else:
                # Generic complete project
                operations.extend([
                    {"type": "CREATE_SPRINT", "data": {"name": "Sprint 1 - Fundaciones", "project_id": "$proj1.id"}, "reference": "sprint1"},
                    {"type": "CREATE_SPRINT", "data": {"name": "Sprint 2 - Desarrollo", "project_id": "$proj1.id"}, "reference": "sprint2"},
                    {"type": "CREATE_SPRINT", "data": {"name": "Sprint 3 - Deploy", "project_id": "$proj1.id"}, "reference": "sprint3"},
                    {"type": "CREATE_TASK", "data": {"title": "Setup del proyecto", "project_id": "$proj1.id", "sprint_id": "$sprint1.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Configuración inicial", "project_id": "$proj1.id", "sprint_id": "$sprint1.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Autenticación", "project_id": "$proj1.id", "sprint_id": "$sprint1.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Base de datos", "project_id": "$proj1.id", "sprint_id": "$sprint1.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Funcionalidad principal", "project_id": "$proj1.id", "sprint_id": "$sprint2.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "API endpoints", "project_id": "$proj1.id", "sprint_id": "$sprint2.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Frontend components", "project_id": "$proj1.id", "sprint_id": "$sprint2.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Testing", "project_id": "$proj1.id", "sprint_id": "$sprint2.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Deploy setup", "project_id": "$proj1.id", "sprint_id": "$sprint3.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Documentation", "project_id": "$proj1.id", "sprint_id": "$sprint3.id"}},
                    {"type": "CREATE_TASK", "data": {"title": "Optimizations", "project_id": "$proj1.id", "sprint_id": "$sprint3.id"}}
                ])
                
                return {
                    "operations": operations,
                    "response_template": f"✅ Complete project '{name}' created with 3 sprints and 11 tasks!"
                }
        
        # QUERY OPERATIONS - Natural language status questions
        elif any(phrase in message_lower for phrase in [
            "como va", "como está", "cómo va", "cómo está", "que tal va", "qué tal va",
            "how is", "status of", "estado de", "estado del", "que necesita", "qué necesita",
            "progress", "progreso", "resumen", "summary", "oye y el", "hey and the",
            "cuantas tareas", "cuántas tareas", "how many tasks", "tareas faltan", "tareas pendientes",
            "tareas quedan", "tasks left", "tasks remaining", "cuantas quedan", "cuántas quedan",
            "dame los nombres", "cuales son las tareas", "cuáles son las tareas", "que tareas", "qué tareas",
            "lista de tareas", "names of tasks", "task names", "show me tasks"
        ]):
            # Use the original message for better entity extraction
            query = user_message
            original_message = user_message
            
            # Determine entity type and name from query
            entity_type = "general"
            entity_name = ""
            entity_id = None
            
            if any(word in message_lower for word in ["proyecto", "project"]):
                entity_type = "project"
                # Extract project name or ID - look for patterns like "proyecto JAI-VIER"
                import re
                
                # Try to extract project name preserving original case
                original_match = re.search(r"proyecto\s+([a-zA-Z0-9\-_]+)", original_message, re.IGNORECASE)
                if original_match:
                    entity_name = original_match.group(1)
                else:
                    # Try other patterns
                    patterns = [
                        r"project\s+([a-zA-Z0-9\-_]+)",
                        r"el\s+proyecto\s+([a-zA-Z0-9\-_]+)"
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, original_message, re.IGNORECASE)
                        if match:
                            entity_name = match.group(1)
                            break
                
                # Fallback to original method if regex didn't work
                if not entity_name:
                    for keyword in ["proyecto", "project"]:
                        if keyword in message_lower:
                            parts = message_lower.split(keyword)
                            if len(parts) > 1:
                                name_part = parts[-1].strip()
                                # Clean up common words
                                for stop in [" como va", " cómo va", " how is", " status"]:
                                    if stop in name_part:
                                        name_part = name_part.split(stop)[0].strip()
                                entity_name = name_part.upper() if name_part else ""
                                break
            
            elif any(word in message_lower for word in ["sprint"]):
                entity_type = "sprint"
                # Extract sprint name
                if "sprint" in message_lower:
                    parts = message_lower.split("sprint")
                    if len(parts) > 1:
                        name_part = parts[-1].strip()
                        for stop in [" como va", " cómo va", " how is", " status"]:
                            if stop in name_part:
                                name_part = name_part.split(stop)[0].strip()
                        entity_name = name_part.title() if name_part else ""
            
            elif any(word in message_lower for word in ["tarea", "task"]):
                entity_type = "task"
                # Extract task name
                for keyword in ["tarea", "task"]:
                    if keyword in message_lower:
                        parts = message_lower.split(keyword)
                        if len(parts) > 1:
                            name_part = parts[-1].strip()
                            for stop in [" como va", " cómo va", " how is", " status", " que necesita", " qué necesita"]:
                                if stop in name_part:
                                    name_part = name_part.split(stop)[0].strip()
                            entity_name = name_part.title() if name_part else ""
                            break
            
            # Try to extract ID if present
            import re
            id_match = re.search(r'\b(\d+)\b', message_lower)
            if id_match:
                entity_id = int(id_match.group(1))
            
            # Debug logging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"[FALLBACK] Extracted entity_type='{entity_type}', entity_name='{entity_name}', entity_id={entity_id}")
            logger.info(f"[FALLBACK] Original message: '{original_message}'")
            logger.info(f"[FALLBACK] Message lower: '{message_lower}'")
            
            return {
                "operations": [
                    {
                        "type": "QUERY_STATUS", 
                        "data": {
                            "query": query,
                            "entity_type": entity_type,
                            "entity_name": entity_name,
                            "entity_id": entity_id
                        }
                    }
                ],
                "response_template": f"🤖 Analyzing {entity_type} status..."
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
        
        # Special handling for "crea el proyecto: ProjectName" pattern
        if "crea el proyecto:" in message_lower:
            parts = message_lower.split("crea el proyecto:")
            if len(parts) > 1:
                name_part = parts[1].strip()
                # Extract just the first line/name
                if "\n" in name_part:
                    name_part = name_part.split("\n")[0].strip()
                return name_part.title() if name_part else "New Item"
        
        for keyword in keywords:
            if keyword in message_lower:
                # Extract text after keyword
                parts = message_lower.split(keyword)
                if len(parts) > 1:
                    # Take text after keyword, clean it up
                    name_part = parts[-1].strip()
                    # Remove common stopwords
                    for stop in [" llamado", " called", " named", " de", " para", ":"]:
                        if stop in name_part:
                            name_part = name_part.split(stop)[-1].strip()
                    # Extract just the first line if it's multiline
                    if "\n" in name_part:
                        name_part = name_part.split("\n")[0].strip()
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
    
    def _extract_multiple_users(self, message: str) -> List[Dict]:
        """Extract multiple users from patterns like 'aram, fer caves, y aaron hernandez'"""
        message_lower = message.lower()
        users = []
        
        logger.info(f"Extracting users from message: {message}")
        
        # Look for patterns after "usuarios" or "al proyecto"  
        patterns = [
            r"añadele\s+al?\s+proyecto\s+\w+\s+a\s+los?\s+usuarios?\s+(.+)",  # Assignment pattern
            r"al?\s+proyecto\s+\w+\s+a\s+los?\s+usuarios?\s+(.+)",
            r"usuarios?\s+(.+?)\s+al?\s+proyecto",
            r"a\s+los?\s+usuarios?\s+(.+?)\s+al?\s+proyecto", 
            r"del proyecto\s+\w+\s+(.+)",  # Removal pattern: "del proyecto fittrack fercaves AlfredoFonseca..."
            r"proyecto\s+\w+\s+(.+)",      # Removal pattern: "proyecto fittrack fercaves AlfredoFonseca..."
            r"estos\s+usuarios?\s+del\s+proyecto\s+\w+\s+(.+)",  # "estos usuarios del proyecto fittrack fercaves..."
            r"usuarios?\s+(.+)"  # Simple fallback
        ]
        
        user_list_text = None
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, message_lower)
            if match:
                user_list_text = match.group(1).strip()
                logger.info(f"Pattern {i} matched: {pattern} -> {user_list_text}")
                break
        
        if user_list_text:
            # Split by common separators
            separators = [",", " y ", " and ", ";"]
            user_names = [user_list_text]
            
            for sep in separators:
                new_names = []
                for name in user_names:
                    new_names.extend([n.strip() for n in name.split(sep) if n.strip()])
                user_names = new_names
            
            # Clean up and create user objects
            for name in user_names:
                name = name.strip()
                if name and len(name) > 1:  # Skip empty or single char names
                    users.append({"user_name": name.title()})
                    logger.info(f"Added user: {name.title()}")
        
        logger.info(f"Extracted {len(users)} users: {users}")
        return users