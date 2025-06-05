# ai/json_executor.py - COMPLETE CRUD VERSION
"""Ejecutor completo con operaciones CRUD"""

import json
import logging
import asyncio
from typing import Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class JSONExecutor:
    def __init__(self, api_manager, context_manager):
        self.api_manager = api_manager
        self.context_manager = context_manager
        self.created_items = {}  # Store created items for reference
        
    async def execute_operations(self, operations_json: Dict, user_id: int, update) -> str:
        operations = operations_json.get("operations", [])
        self.created_items = {}  # Reset for each execution
        
        results = []
        logger.info(f"[EXECUTOR] Executing {len(operations)} operations")
        
        for i, operation in enumerate(operations):
            try:
                result = await self._execute_operation(operation, user_id)
                results.append(result)
                logger.info(f"[EXECUTOR] Operation {i+1}: {result.get('success', False)}")
            except Exception as e:
                logger.error(f"[EXECUTOR] Error in operation {i+1}: {e}")
                results.append({"success": False, "error": str(e)})
        
        return self._generate_response(results, operations_json)
    
    async def _execute_operation(self, operation: Dict, user_id: int) -> Dict:
        op_type = operation.get("type")
        data = operation.get("data", {})
        reference = operation.get("reference")
        
        # Resolve references
        data = self._resolve_references(data)
        
        logger.info(f"[EXECUTOR] Executing {op_type}")
        
        # Route to appropriate handler
        if op_type == "CREATE_PROJECT":
            result = await self._create_project(data, user_id)
        elif op_type == "CREATE_SPRINT":
            result = await self._create_sprint(data, user_id)
        elif op_type == "CREATE_TASK":
            result = await self._create_task(data, user_id)
        elif op_type == "LIST_PROJECTS":
            result = await self._list_projects()
        elif op_type == "LIST_SPRINTS":
            result = await self._list_sprints(data)
        elif op_type == "LIST_TASKS":
            result = await self._list_tasks(data)
        elif op_type == "UPDATE_PROJECT":
            result = await self._update_project(data)
        elif op_type == "UPDATE_SPRINT":
            result = await self._update_sprint(data)
        elif op_type == "UPDATE_TASK":
            result = await self._update_task(data)
        elif op_type == "DELETE_PROJECT":
            result = await self._delete_project(data)
        elif op_type == "DELETE_SPRINT":
            result = await self._delete_sprint(data)
        elif op_type == "DELETE_TASK":
            result = await self._delete_task(data)
        else:
            result = {"success": False, "error": f"Unknown operation: {op_type}"}
        
        # Store reference for later operations
        if reference and result.get("success") and result.get("data"):
            self.created_items[reference] = result["data"]
        
        return result
    
    def _resolve_references(self, data: Dict) -> Dict:
        """Resolve $reference.field patterns"""
        resolved = {}
        for key, value in data.items():
            if isinstance(value, str) and value.startswith("$"):
                ref = value[1:]  # Remove $
                if "." in ref:
                    ref_name, field = ref.split(".", 1)
                    if ref_name in self.created_items:
                        resolved[key] = self.created_items[ref_name].get(field)
                else:
                    if ref in self.created_items:
                        resolved[key] = self.created_items[ref].get("id")
            else:
                resolved[key] = value
        return resolved
    
    # CREATE OPERATIONS
    async def _create_project(self, data: Dict, user_id: int) -> Dict:
        project_data = {
            "name": data.get("name", "New Project"),
            "description": data.get("description", "Created by bot"),
            "start_date": self._format_date(data.get("start_date")) or datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_date": self._format_date(data.get("end_date")) or (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": self._parse_status(data.get("status", "active"), "project")
        }
        
        result = await self.api_manager.projects.create(project_data)
        
        if result and not result.get("error"):
            # Get the created project with real ID
            await asyncio.sleep(0.5)  # Wait for creation
            projects = await self.api_manager.projects.get_all()
            for project in projects:
                if project.get("name") == project_data["name"]:
                    return {"success": True, "data": project, "type": "project"}
            
            return {"success": True, "data": project_data, "type": "project"}
        else:
            return {"success": False, "error": result.get("error", "Creation failed")}
    
    async def _create_sprint(self, data: Dict, user_id: int) -> Dict:
        if not data.get("project_id"):
            return {"success": False, "error": "project_id required"}
        
        sprint_data = {
            "name": data.get("name", "New Sprint"),
            "description": data.get("description", "Created by bot"),
            "project_id": int(data["project_id"]),
            "start_date": self._format_date(data.get("start_date")) or datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_date": self._format_date(data.get("end_date")) or (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": self._parse_status(data.get("status", "active"), "sprint")
        }
        
        result = await self.api_manager.sprints.create(sprint_data)
        
        if result and not result.get("error"):
            await asyncio.sleep(0.5)
            sprints = await self.api_manager.sprints.get_all(sprint_data["project_id"])
            for sprint in sprints:
                if sprint.get("name") == sprint_data["name"]:
                    return {"success": True, "data": sprint, "type": "sprint"}
            
            return {"success": True, "data": sprint_data, "type": "sprint"}
        else:
            return {"success": False, "error": result.get("error", "Creation failed")}
    
    async def _create_task(self, data: Dict, user_id: int) -> Dict:
        task_data = {
            "title": data.get("title", "New Task"),
            "description": data.get("description", "Created by bot"),
            "priority": self._parse_priority(data.get("priority", "medium")),
            "status": self._parse_status(data.get("status", "todo"), "task"),
            "estimated_hours": int(data.get("estimated_hours", 8)),
            "due_date": self._format_date(data.get("due_date")) or (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        
        # Add optional IDs
        if data.get("project_id"):
            task_data["project_id"] = int(data["project_id"])
        if data.get("sprint_id"):
            task_data["sprint_id"] = int(data["sprint_id"])
        
        result = await self.api_manager.tasks.create(task_data)
        
        if result and not result.get("error"):
            return {"success": True, "data": task_data, "type": "task"}
        else:
            return {"success": False, "error": result.get("error", "Creation failed")}
    
    # LIST OPERATIONS
    async def _list_projects(self) -> Dict:
        projects = await self.api_manager.projects.get_all()
        return {"success": True, "data": projects, "type": "projects"}
    
    async def _list_sprints(self, data: Dict) -> Dict:
        project_id = data.get("project_id")
        sprints = await self.api_manager.sprints.get_all(project_id)
        return {"success": True, "data": sprints, "type": "sprints"}
    
    async def _list_tasks(self, data: Dict) -> Dict:
        project_id = data.get("project_id")
        sprint_id = data.get("sprint_id")
        tasks = await self.api_manager.tasks.get_all(project_id, sprint_id)
        return {"success": True, "data": tasks, "type": "tasks"}
    
    # UPDATE OPERATIONS (simplified - would need real endpoints)
    async def _update_project(self, data: Dict) -> Dict:
        return {"success": False, "error": "Update not implemented yet"}
    
    async def _update_sprint(self, data: Dict) -> Dict:
        return {"success": False, "error": "Update not implemented yet"}
    
    async def _update_task(self, data: Dict) -> Dict:
        return {"success": False, "error": "Update not implemented yet"}
    
    # DELETE OPERATIONS (simplified - would need real endpoints)
    async def _delete_project(self, data: Dict) -> Dict:
        return {"success": False, "error": "Delete not implemented yet"}
    
    async def _delete_sprint(self, data: Dict) -> Dict:
        return {"success": False, "error": "Delete not implemented yet"}
    
    async def _delete_task(self, data: Dict) -> Dict:
        return {"success": False, "error": "Delete not implemented yet"}
    
    # UTILITY METHODS
    def _format_date(self, date_str: str) -> str:
        if not date_str:
            return None
        if "T" in date_str:
            return date_str
        return f"{date_str}T00:00:00Z"
    
    def _parse_status(self, status: str, entity_type: str) -> int:
        if isinstance(status, int):
            return status
        
        status_maps = {
            "project": {"active": 0, "completed": 1, "paused": 2},
            "sprint": {"active": 0, "completed": 1, "closed": 1},
            "task": {"todo": 0, "in_progress": 1, "completed": 2}
        }
        
        return status_maps.get(entity_type, {}).get(status.lower(), 0)
    
    def _parse_priority(self, priority: str) -> int:
        if isinstance(priority, int):
            return priority
        
        priority_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        return priority_map.get(priority.lower(), 2)
    
    def _generate_response(self, results: List[Dict], operations_json: Dict) -> str:
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        
        # Handle specific operation types
        if len(results) == 1 and successful:
            result = successful[0]
            result_type = result.get("type", "")
            
            if result_type == "projects":
                return self._format_projects(result["data"])
            elif result_type == "sprints":
                return self._format_sprints(result["data"])
            elif result_type == "tasks":
                return self._format_tasks(result["data"])
            elif result_type in ["project", "sprint", "task"]:
                return f"✅ {result_type.title()} created successfully!"
        
        # Handle multiple operations
        if successful:
            created_items = []
            for result in successful:
                if result.get("type") in ["project", "sprint", "task"]:
                    created_items.append(result["type"])
            
            if created_items:
                response = f"✅ Created: {', '.join(created_items)}"
            else:
                response = f"✅ {len(successful)} operations completed"
        else:
            response = "❌ No operations completed"
        
        if failed:
            response += f"\n❌ {len(failed)} failed"
        
        return response
    
    def _format_projects(self, projects: List[Dict]) -> str:
        if not projects:
            return "📁 No projects found"
        
        lines = ["📁 **Projects:**\n"]
        for p in projects:
            name = p.get("name", "Unknown")
            pid = p.get("id", "N/A")
            status = "Active" if p.get("status") == 0 else "Completed"
            lines.append(f"• {name} (ID: {pid}) - {status}")
        
        return "\n".join(lines)
    
    def _format_sprints(self, sprints: List[Dict]) -> str:
        if not sprints:
            return "🏃 No sprints found"
        
        lines = ["🏃 **Sprints:**\n"]
        for s in sprints:
            name = s.get("name", "Unknown")
            sid = s.get("id", "N/A")
            lines.append(f"• {name} (ID: {sid})")
        
        return "\n".join(lines)
    
    def _format_tasks(self, tasks: List[Dict]) -> str:
        if not tasks:
            return "📋 No tasks found"
        
        lines = ["📋 **Tasks:**\n"]
        for t in tasks:
            title = t.get("title", "Unknown")
            tid = t.get("id", "N/A")
            priority = ["", "Low", "Medium", "High", "Critical"][t.get("priority", 2)]
            lines.append(f"• {title} (ID: {tid}) - {priority}")
        
        return "\n".join(lines)