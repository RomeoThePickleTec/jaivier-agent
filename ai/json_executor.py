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
        elif op_type == "LIST_USERS":
            result = await self._list_users(data)
        elif op_type == "UPDATE_PROJECT":
            result = await self._update_project(data)
        elif op_type == "UPDATE_SPRINT":
            result = await self._update_sprint(data)
        elif op_type == "UPDATE_TASK":
            result = await self._update_task(data)
        elif op_type == "DELETE_PROJECT":
            result = await self._delete_project(data)
        elif op_type == "DELETE_PROJECTS_BY_NAME":
            result = await self._delete_projects_by_name(data)
        elif op_type == "DELETE_SPRINT":
            result = await self._delete_sprint(data)
        elif op_type == "DELETE_SPRINTS_BY_NAME":
            result = await self._delete_sprints_by_name(data)
        elif op_type == "DELETE_TASK":
            result = await self._delete_task(data)
        elif op_type == "ASSIGN_USER_TO_PROJECT":
            result = await self._assign_user_to_project(data)
        elif op_type == "REMOVE_USER_FROM_PROJECT":
            result = await self._remove_user_from_project(data)
        elif op_type == "LIST_PROJECT_MEMBERS":
            result = await self._list_project_members(data)
        elif op_type == "AUTO_ASSIGN_USERS":
            result = await self._auto_assign_users(data)
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
            
            # Fallback: use the data we sent with estimated ID
            project_data["id"] = "New"
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
            
            # Fallback: use the data we sent with estimated ID
            sprint_data["id"] = "New"
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
        
        # If sprint_name is provided but not sprint_id, try to find it
        if data.get("sprint_name") and not data.get("sprint_id"):
            sprints = await self.api_manager.sprints.get_all()
            for sprint in sprints:
                if sprint.get("name", "").lower() == data["sprint_name"].lower():
                    task_data["sprint_id"] = sprint.get("id")
                    break
        
        # AUTO-DETECT: If no sprint_id provided, try to find from context
        if not task_data.get("sprint_id"):
            # Check if there's a sprint mentioned in the description
            description = data.get("description", "").lower()
            title = data.get("title", "").lower()
            
            # Get all sprints to search by name
            sprints = await self.api_manager.sprints.get_all()
            for sprint in sprints:
                sprint_name = sprint.get("name", "").lower()
                # Check if sprint name appears in title or description
                if sprint_name in description or sprint_name in title:
                    task_data["sprint_id"] = sprint.get("id")
                    logger.info(f"Auto-detected sprint: {sprint_name} (ID: {sprint.get('id')})")
                    break
        
        logger.info(f"Creating task with data: {task_data}")
        result = await self.api_manager.tasks.create(task_data)
        logger.info(f"Task creation result: {result}")
        
        if result and not result.get("error"):
            # For successful creation, return the task data we sent with default ID
            task_data["id"] = "New"
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
    
    async def _list_users(self, data: Dict) -> Dict:
        users = await self.api_manager.users.get_all()
        return {"success": True, "data": users, "type": "users"}
    
    # UPDATE OPERATIONS
    async def _update_project(self, data: Dict) -> Dict:
        project_id = data.get("id") or data.get("project_id")
        project_name = data.get("name")
        
        # If no ID but we have a name, search for the project
        if not project_id and project_name:
            try:
                projects = await self.api_manager.projects.get_all()
                for project in projects:
                    if project.get("name", "").lower() == project_name.lower():
                        project_id = project.get("id")
                        break
                
                if not project_id:
                    return {"success": False, "error": f"Project '{project_name}' not found"}
            except Exception as e:
                return {"success": False, "error": f"Error searching for project: {e}"}
        
        if not project_id:
            return {"success": False, "error": "project_id or name required for update"}
        
        try:
            project_id = int(project_id)
            logger.info(f"[EXECUTOR] Updating project {project_id}")
            
            # Get current project data
            current_project = await self.api_manager.projects.get_by_id(project_id)
            if not current_project:
                return {"success": False, "error": f"Project {project_id} not found"}
            
            # Prepare update data - merge with current data
            update_data = {}
            
            # Update fields if provided
            if data.get("name"):
                update_data["name"] = data["name"]
            if data.get("description"):
                update_data["description"] = data["description"]
            if data.get("status"):
                update_data["status"] = self._parse_status(data["status"], "project")
            if data.get("start_date"):
                update_data["start_date"] = self._format_date(data["start_date"])
            if data.get("end_date"):
                update_data["end_date"] = self._format_date(data["end_date"])
            
            # Merge current data with updates (keep existing values for unspecified fields)
            final_data = {
                "name": update_data.get("name", current_project.get("name")),
                "description": update_data.get("description", current_project.get("description", "")),
                "status": update_data.get("status", current_project.get("status", 0)),
                "start_date": update_data.get("start_date", current_project.get("start_date")),
                "end_date": update_data.get("end_date", current_project.get("end_date"))
            }
            
            result = await self.api_manager.projects.update(project_id, final_data)
            
            if result.get("success") or not result.get("error"):
                # Get updated project data
                await asyncio.sleep(0.5)  # Wait for update to process
                updated_project = await self.api_manager.projects.get_by_id(project_id)
                
                return {
                    "success": True,
                    "data": {
                        "id": project_id,
                        "name": final_data["name"],
                        "updated_fields": list(update_data.keys()),
                        "updated": True
                    },
                    "type": "project_updated"
                }
            else:
                return {"success": False, "error": result.get("error", "Update failed")}
                
        except ValueError:
            return {"success": False, "error": "Invalid project ID"}
        except Exception as e:
            logger.error(f"Error in _update_project: {e}")
            return {"success": False, "error": str(e)}
    
    async def _update_sprint(self, data: Dict) -> Dict:
        return {"success": False, "error": "Update not implemented yet"}
    
    async def _update_task(self, data: Dict) -> Dict:
        return {"success": False, "error": "Update not implemented yet"}
    
    # DELETE OPERATIONS
    async def _delete_project(self, data: Dict) -> Dict:
        project_id = data.get("id") or data.get("project_id")
        
        if not project_id:
            return {"success": False, "error": "project_id required for deletion"}
        
        try:
            project_id = int(project_id)
            logger.info(f"[EXECUTOR] Deleting project {project_id}")
            
            # Get project name before deletion for response
            project = await self.api_manager.projects.get_by_id(project_id)
            project_name = project.get("name", f"Project {project_id}") if project else f"Project {project_id}"
            
            result = await self.api_manager.projects.delete(project_id)
            
            if result.get("success"):
                return {
                    "success": True, 
                    "data": {"id": project_id, "name": project_name, "deleted": True}, 
                    "type": "project_deleted"
                }
            else:
                return {"success": False, "error": result.get("error", "Deletion failed")}
                
        except ValueError:
            return {"success": False, "error": "Invalid project ID"}
        except Exception as e:
            logger.error(f"Error in _delete_project: {e}")
            return {"success": False, "error": str(e)}
    
    async def _delete_projects_by_name(self, data: Dict) -> Dict:
        name_pattern = data.get("name_pattern") or data.get("name")
        
        if not name_pattern:
            return {"success": False, "error": "name_pattern required for bulk deletion"}
        
        try:
            # Get all projects
            projects = await self.api_manager.projects.get_all()
            
            # Find projects matching the pattern (case-insensitive)
            matching_projects = []
            for project in projects:
                project_name = project.get("name", "")
                if name_pattern.lower() in project_name.lower():
                    matching_projects.append(project)
            
            if not matching_projects:
                return {
                    "success": False, 
                    "error": f"No projects found matching '{name_pattern}'"
                }
            
            # Delete each matching project
            deleted_projects = []
            failed_deletions = []
            
            for project in matching_projects:
                project_id = project.get("id")
                project_name = project.get("name", f"Project {project_id}")
                
                try:
                    logger.info(f"[EXECUTOR] Bulk deleting project {project_id}: {project_name}")
                    result = await self.api_manager.projects.delete(project_id)
                    
                    if result.get("success"):
                        deleted_projects.append({
                            "id": project_id, 
                            "name": project_name
                        })
                    else:
                        failed_deletions.append({
                            "id": project_id, 
                            "name": project_name,
                            "error": result.get("error", "Unknown error")
                        })
                except Exception as e:
                    failed_deletions.append({
                        "id": project_id, 
                        "name": project_name,
                        "error": str(e)
                    })
            
            return {
                "success": len(deleted_projects) > 0,
                "data": {
                    "deleted": deleted_projects,
                    "failed": failed_deletions,
                    "pattern": name_pattern
                },
                "type": "projects_bulk_deleted"
            }
            
        except Exception as e:
            logger.error(f"Error in _delete_projects_by_name: {e}")
            return {"success": False, "error": str(e)}
    
    async def _delete_sprint(self, data: Dict) -> Dict:
        sprint_id = data.get("id") or data.get("sprint_id")
        sprint_name = data.get("name")
        
        # If no ID but we have a name, search for the sprint
        if not sprint_id and sprint_name:
            try:
                sprints = await self.api_manager.sprints.get_all()
                for sprint in sprints:
                    if sprint.get("name", "").lower() == sprint_name.lower():
                        sprint_id = sprint.get("id")
                        break
                
                if not sprint_id:
                    return {"success": False, "error": f"Sprint '{sprint_name}' not found"}
            except Exception as e:
                return {"success": False, "error": f"Error searching for sprint: {e}"}
        
        if not sprint_id:
            return {"success": False, "error": "sprint_id or name required for deletion"}
        
        try:
            sprint_id = int(sprint_id)
            logger.info(f"[EXECUTOR] Deleting sprint {sprint_id}")
            
            # Get sprint details before deletion for response
            sprint = await self.api_manager.sprints.get_by_id(sprint_id)
            sprint_name = sprint.get("name", f"Sprint {sprint_id}") if sprint else f"Sprint {sprint_id}"
            
            result = await self.api_manager.sprints.delete(sprint_id)
            
            if result.get("success"):
                return {
                    "success": True, 
                    "data": {"id": sprint_id, "name": sprint_name, "deleted": True}, 
                    "type": "sprint_deleted"
                }
            else:
                return {"success": False, "error": result.get("error", "Deletion failed")}
                
        except ValueError:
            return {"success": False, "error": "Invalid sprint ID"}
        except Exception as e:
            logger.error(f"Error in _delete_sprint: {e}")
            return {"success": False, "error": str(e)}
    
    async def _delete_sprints_by_name(self, data: Dict) -> Dict:
        name_pattern = data.get("name_pattern") or data.get("name")
        project_id = data.get("project_id")
        
        if not name_pattern:
            return {"success": False, "error": "name_pattern required for bulk sprint deletion"}
        
        try:
            # Get all sprints (optionally filtered by project)
            sprints = await self.api_manager.sprints.get_all(project_id)
            
            # Find sprints matching the pattern (case-insensitive)
            matching_sprints = []
            for sprint in sprints:
                sprint_name = sprint.get("name", "")
                if name_pattern.lower() in sprint_name.lower():
                    matching_sprints.append(sprint)
            
            if not matching_sprints:
                return {
                    "success": False, 
                    "error": f"No sprints found matching '{name_pattern}'"
                }
            
            # Delete each matching sprint
            deleted_sprints = []
            failed_deletions = []
            
            for sprint in matching_sprints:
                sprint_id = sprint.get("id")
                sprint_name = sprint.get("name", f"Sprint {sprint_id}")
                project_id_info = sprint.get("project_id", "N/A")
                
                try:
                    logger.info(f"[EXECUTOR] Bulk deleting sprint {sprint_id}: {sprint_name}")
                    result = await self.api_manager.sprints.delete(sprint_id)
                    
                    if result.get("success"):
                        deleted_sprints.append({
                            "id": sprint_id, 
                            "name": sprint_name,
                            "project_id": project_id_info
                        })
                    else:
                        failed_deletions.append({
                            "id": sprint_id, 
                            "name": sprint_name,
                            "project_id": project_id_info,
                            "error": result.get("error", "Unknown error")
                        })
                except Exception as e:
                    failed_deletions.append({
                        "id": sprint_id, 
                        "name": sprint_name,
                        "project_id": project_id_info,
                        "error": str(e)
                    })
            
            return {
                "success": len(deleted_sprints) > 0,
                "data": {
                    "deleted": deleted_sprints,
                    "failed": failed_deletions,
                    "pattern": name_pattern
                },
                "type": "sprints_bulk_deleted"
            }
            
        except Exception as e:
            logger.error(f"Error in _delete_sprints_by_name: {e}")
            return {"success": False, "error": str(e)}
    
    async def _delete_task(self, data: Dict) -> Dict:
        task_id = data.get("id") or data.get("task_id")
        task_title = data.get("title") or data.get("name")
        
        # If no ID but we have a title, search for the task
        if not task_id and task_title:
            try:
                tasks = await self.api_manager.tasks.get_all()
                for task in tasks:
                    if task.get("title", "").lower() == task_title.lower():
                        task_id = task.get("id")
                        break
                
                if not task_id:
                    return {"success": False, "error": f"Task '{task_title}' not found"}
            except Exception as e:
                return {"success": False, "error": f"Error searching for task: {e}"}
        
        if not task_id:
            return {"success": False, "error": "task_id or title required for deletion"}
        
        try:
            task_id = int(task_id)
            logger.info(f"[EXECUTOR] Deleting task {task_id}")
            
            # Get task details before deletion for response
            task = await self.api_manager.tasks.get_by_id(task_id)
            task_title = task.get("title", f"Task {task_id}") if task else f"Task {task_id}"
            
            result = await self.api_manager.tasks.delete(task_id)
            
            if result.get("success"):
                # Verify the task was actually deleted by checking if it still exists
                await asyncio.sleep(0.5)  # Wait a moment for the API to process
                verification_task = await self.api_manager.tasks.get_by_id(task_id)
                
                if verification_task:
                    logger.warning(f"Task {task_id} still exists after deletion - API may have failed silently")
                    return {
                        "success": False, 
                        "error": f"Task appears to still exist after deletion (API returned success but task {task_id} is still present)"
                    }
                else:
                    logger.info(f"Task {task_id} successfully verified as deleted")
                    return {
                        "success": True, 
                        "data": {"id": task_id, "title": task_title, "deleted": True}, 
                        "type": "task_deleted"
                    }
            else:
                return {"success": False, "error": result.get("error", "Deletion failed")}
                
        except ValueError:
            return {"success": False, "error": "Invalid task ID"}
        except Exception as e:
            logger.error(f"Error in _delete_task: {e}")
            return {"success": False, "error": str(e)}
    
    # PROJECT MEMBER OPERATIONS
    async def _assign_user_to_project(self, data: Dict) -> Dict:
        project_id = data.get("project_id")
        user_id = data.get("user_id") 
        project_name = data.get("project_name")
        user_name = data.get("user_name")
        role = data.get("role", "member")
        
        try:
            # Resolve project ID if name provided
            if not project_id and project_name:
                projects = await self.api_manager.projects.get_all()
                for project in projects:
                    if project.get("name", "").lower() == project_name.lower():
                        project_id = project.get("id")
                        break
                
                if not project_id:
                    return {"success": False, "error": f"Project '{project_name}' not found"}
            
            # Resolve user ID if name provided
            if not user_id and user_name:
                users = await self.api_manager.users.get_all()
                for user in users:
                    if (user.get("full_name", "").lower() == user_name.lower() or 
                        user.get("username", "").lower() == user_name.lower()):
                        user_id = user.get("id")
                        break
                
                if not user_id:
                    return {"success": False, "error": f"User '{user_name}' not found"}
            
            if not project_id or not user_id:
                return {"success": False, "error": "Both project_id and user_id are required"}
            
            # Get user and project names for response
            user = await self.api_manager.users.get_by_id(user_id)
            project = await self.api_manager.projects.get_by_id(project_id)
            
            user_display = user.get("full_name", user.get("username", f"User {user_id}")) if user else f"User {user_id}"
            project_display = project.get("name", f"Project {project_id}") if project else f"Project {project_id}"
            
            result = await self.api_manager.project_members.assign_user(project_id, user_id, role)
            
            if result.get("success"):
                return {
                    "success": True,
                    "data": {
                        "user_id": user_id,
                        "project_id": project_id,
                        "user_name": user_display,
                        "project_name": project_display,
                        "role": role,
                        "assigned": True
                    },
                    "type": "user_assigned"
                }
            else:
                return {"success": False, "error": result.get("error", "Assignment failed")}
                
        except Exception as e:
            logger.error(f"Error in _assign_user_to_project: {e}")
            return {"success": False, "error": str(e)}
    
    async def _remove_user_from_project(self, data: Dict) -> Dict:
        project_id = data.get("project_id")
        user_id = data.get("user_id")
        
        if not project_id or not user_id:
            return {"success": False, "error": "Both project_id and user_id are required"}
        
        try:
            result = await self.api_manager.project_members.remove_user(project_id, user_id)
            
            if result.get("success"):
                return {
                    "success": True,
                    "data": {"user_id": user_id, "project_id": project_id, "removed": True},
                    "type": "user_removed"
                }
            else:
                return {"success": False, "error": result.get("error", "Removal failed")}
                
        except Exception as e:
            logger.error(f"Error in _remove_user_from_project: {e}")
            return {"success": False, "error": str(e)}
    
    async def _list_project_members(self, data: Dict) -> Dict:
        project_id = data.get("project_id")
        
        if not project_id:
            return {"success": False, "error": "project_id is required"}
        
        try:
            members = await self.api_manager.project_members.get_by_project(project_id)
            
            # Enrich with user details
            enriched_members = []
            for member in members:
                user_id = member.get("user_id")
                if user_id:
                    user = await self.api_manager.users.get_by_id(user_id)
                    if user:
                        enriched_members.append({
                            **member,
                            "user_details": user
                        })
                    else:
                        enriched_members.append(member)
                else:
                    enriched_members.append(member)
            
            return {"success": True, "data": enriched_members, "type": "project_members"}
            
        except Exception as e:
            logger.error(f"Error in _list_project_members: {e}")
            return {"success": False, "error": str(e)}
    
    async def _auto_assign_users(self, data: Dict) -> Dict:
        project_id = data.get("project_id")
        criteria = data.get("criteria", "random")  # random, by_role, least_busy
        count = data.get("count", 2)
        
        if not project_id:
            return {"success": False, "error": "project_id is required"}
        
        try:
            # Get all users
            users = await self.api_manager.users.get_all()
            active_users = [u for u in users if u.get("active", True)]
            
            if not active_users:
                return {"success": False, "error": "No active users available for assignment"}
            
            # Get current project members to avoid duplicates
            current_members = await self.api_manager.project_members.get_by_project(project_id)
            current_user_ids = [m.get("user_id") for m in current_members]
            
            # Filter out already assigned users
            available_users = [u for u in active_users if u.get("id") not in current_user_ids]
            
            if not available_users:
                return {"success": False, "error": "All active users are already assigned to this project"}
            
            # Select users based on criteria
            selected_users = []
            if criteria == "random":
                import random
                selected_users = random.sample(available_users, min(count, len(available_users)))
            elif criteria == "by_role":
                # Prefer developers first, then others
                developers = [u for u in available_users if "developer" in u.get("role", "").lower()]
                others = [u for u in available_users if "developer" not in u.get("role", "").lower()]
                selected_users = (developers + others)[:count]
            else:  # least_busy - simple implementation
                selected_users = available_users[:count]
            
            # Assign selected users
            assignments = []
            for user in selected_users:
                result = await self.api_manager.project_members.assign_user(project_id, user.get("id"), "member")
                if result.get("success"):
                    assignments.append({
                        "user_id": user.get("id"),
                        "user_name": user.get("full_name", user.get("username")),
                        "assigned": True
                    })
            
            return {
                "success": True,
                "data": {
                    "project_id": project_id,
                    "assignments": assignments,
                    "criteria": criteria,
                    "requested_count": count,
                    "actual_count": len(assignments)
                },
                "type": "auto_assignment"
            }
            
        except Exception as e:
            logger.error(f"Error in _auto_assign_users: {e}")
            return {"success": False, "error": str(e)}
    
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
            elif result_type == "users":
                return self._format_users(result["data"])
            elif result_type in ["project", "sprint", "task"]:
                return f"✅ {result_type.title()} created successfully!"
            elif result_type == "project_deleted":
                data = result.get("data", {})
                name = data.get("name", "Project")
                return f"🗑️ **{name}** deleted successfully!"
            elif result_type == "sprint_deleted":
                data = result.get("data", {})
                name = data.get("name", "Sprint")
                return f"🗑️ **{name}** deleted successfully!"
            elif result_type == "task_deleted":
                data = result.get("data", {})
                title = data.get("title", "Task")
                return f"🗑️ **{title}** deleted successfully!"
            elif result_type == "project_updated":
                data = result.get("data", {})
                name = data.get("name", "Project")
                updated_fields = data.get("updated_fields", [])
                fields_text = ", ".join(updated_fields) if updated_fields else "fields"
                return f"✏️ **{name}** updated successfully! ({fields_text})"
            elif result_type == "user_assigned":
                data = result.get("data", {})
                user_name = data.get("user_name", "User")
                project_name = data.get("project_name", "Project")
                role = data.get("role", "member")
                return f"👥 **{user_name}** assigned to **{project_name}** as {role}!"
            elif result_type == "user_removed":
                return f"👥 User removed from project successfully!"
            elif result_type == "project_members":
                return self._format_project_members(result["data"])
            elif result_type == "auto_assignment":
                return self._format_auto_assignment(result["data"])
            elif result_type == "projects_bulk_deleted":
                return self._format_bulk_deletion(result["data"])
            elif result_type == "sprints_bulk_deleted":
                return self._format_bulk_sprint_deletion(result["data"])
        
        # Handle multiple operations with detailed feedback
        if successful:
            # Group by type for better organization
            projects = [r for r in successful if r.get("type") == "project"]
            sprints = [r for r in successful if r.get("type") == "sprint"]
            tasks = [r for r in successful if r.get("type") == "task"]
            bulk_deletions = [r for r in successful if r.get("type") == "projects_bulk_deleted"]
            bulk_sprint_deletions = [r for r in successful if r.get("type") == "sprints_bulk_deleted"]
            
            # Check if this is primarily a deletion operation
            if bulk_deletions:
                # Handle bulk project deletion separately
                return self._format_bulk_deletion(bulk_deletions[0]["data"])
            elif bulk_sprint_deletions:
                # Handle bulk sprint deletion separately
                return self._format_bulk_sprint_deletion(bulk_sprint_deletions[0]["data"])
            
            response_lines = ["🎉 **Creation Summary:**\n"]
            
            # Projects created
            if projects:
                response_lines.append("📁 **Projects:**")
                for proj in projects:
                    data = proj.get("data", {})
                    name = data.get("name", "Unknown Project")
                    proj_id = data.get("id", "N/A")
                    response_lines.append(f"  • {name} (ID: {proj_id})")
                response_lines.append("")
            
            # Sprints created
            if sprints:
                response_lines.append("🏃 **Sprints:**")
                for sprint in sprints:
                    data = sprint.get("data", {})
                    name = data.get("name", "Unknown Sprint")
                    sprint_id = data.get("id", "N/A")
                    project_id = data.get("project_id", "N/A")
                    response_lines.append(f"  • {name} (ID: {sprint_id}, Project: {project_id})")
                response_lines.append("")
            
            # Tasks created
            if tasks:
                response_lines.append("📋 **Tasks:**")
                for task in tasks:
                    data = task.get("data", {})
                    title = data.get("title", "Unknown Task")
                    task_id = data.get("id", "New")
                    sprint_id = data.get("sprint_id", "N/A")
                    priority = ["", "🟢Low", "🔵Med", "🟡High", "🔴Crit"][min(data.get("priority", 2), 4)]
                    response_lines.append(f"  • {title} (ID: {task_id}) {priority}")
                
                if len(tasks) > 5:
                    response_lines.append(f"  ... and {len(tasks) - 5} more tasks")
                response_lines.append("")
            
            # Summary
            total_created = len(successful)
            response_lines.append(f"✅ **Total: {total_created} items created!**")
            
            response = "\n".join(response_lines)
        else:
            response = "❌ No operations completed"
        
        if failed:
            response += f"\n\n❌ **{len(failed)} operations failed**"
            for fail in failed[:3]:  # Show first 3 failures
                error = fail.get("error", "Unknown error")
                response += f"\n  • {error}"
        
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
        
        # Limit to first 10 tasks to avoid message length limits
        MAX_TASKS = 10
        limited_tasks = tasks[:MAX_TASKS]
        
        lines = ["📋 **Tasks:**\n"]
        for t in limited_tasks:
            title = t.get("title", "Unknown")
            tid = t.get("id", "N/A")
            priority = ["", "Low", "Medium", "High", "Critical"][min(t.get("priority", 2), 4)]
            # Simplified formatting to avoid parsing issues
            lines.append(f"• {title} (ID: {tid}) - {priority}")
        
        if len(tasks) > MAX_TASKS:
            lines.append(f"\n... and {len(tasks) - MAX_TASKS} more tasks")
            lines.append(f"Use /tareas for paginated view")
        
        return "\n".join(lines)
    
    def _format_users(self, users: List[Dict]) -> str:
        if not users:
            return "👥 No users found"
        
        lines = ["👥 **Team Members:**\n"]
        
        for u in users:
            # Extract user information
            name = u.get("full_name", u.get("username", "Unknown"))
            uid = u.get("id", "N/A")
            email = u.get("email", "No email")
            role = u.get("role", "Developer")
            work_mode = u.get("work_mode", "Remote")
            active = "🟢" if u.get("active", True) else "🔴"
            
            # Format role nicely
            role_display = role.replace("_", " ").title() if role else "Developer"
            
            # Main line with name, ID and status
            lines.append(f"• {active} **{name}** (ID: {uid})")
            
            # Secondary line with role, work mode and email
            lines.append(f"  📧 {email}")
            lines.append(f"  💼 {role_display} | 🏠 {work_mode}")
            lines.append("")  # Empty line for spacing
        
        # Remove last empty line
        if lines and lines[-1] == "":
            lines.pop()
        
        return "\n".join(lines)
    
    def _format_bulk_deletion(self, data: Dict) -> str:
        deleted = data.get("deleted", [])
        failed = data.get("failed", [])
        pattern = data.get("pattern", "")
        
        lines = [f"🗑️ Bulk Deletion Results for '{pattern}':\n"]
        
        if deleted:
            lines.append(f"✅ Successfully Deleted ({len(deleted)}):")
            for project in deleted:
                name = project.get("name", "Unknown")
                proj_id = project.get("id", "N/A")
                lines.append(f"  • {name} (ID: {proj_id})")
            lines.append("")
        
        if failed:
            lines.append(f"❌ Failed to Delete ({len(failed)}):")
            for project in failed:
                name = project.get("name", "Unknown")
                proj_id = project.get("id", "N/A")
                error = project.get("error", "Unknown error")
                lines.append(f"  • {name} (ID: {proj_id}) - {error}")
            lines.append("")
        
        if not deleted and not failed:
            lines.append("❌ No projects found matching the pattern")
        
        return "\n".join(lines)
    
    def _format_bulk_sprint_deletion(self, data: Dict) -> str:
        deleted = data.get("deleted", [])
        failed = data.get("failed", [])
        pattern = data.get("pattern", "")
        
        lines = [f"🗑️ Bulk Sprint Deletion Results for '{pattern}':\n"]
        
        if deleted:
            lines.append(f"✅ Successfully Deleted ({len(deleted)}):")
            for sprint in deleted:
                name = sprint.get("name", "Unknown")
                sprint_id = sprint.get("id", "N/A")
                project_id = sprint.get("project_id", "N/A")
                lines.append(f"  • {name} (ID: {sprint_id}, Project: {project_id})")
            lines.append("")
        
        if failed:
            lines.append(f"❌ Failed to Delete ({len(failed)}):")
            for sprint in failed:
                name = sprint.get("name", "Unknown")
                sprint_id = sprint.get("id", "N/A")
                project_id = sprint.get("project_id", "N/A")
                error = sprint.get("error", "Unknown error")
                lines.append(f"  • {name} (ID: {sprint_id}, Project: {project_id}) - {error}")
            lines.append("")
        
        if not deleted and not failed:
            lines.append("❌ No sprints found matching the pattern")
        
        return "\n".join(lines)
    
    def _format_project_members(self, members: List[Dict]) -> str:
        if not members:
            return "👥 No members assigned to this project"
        
        lines = ["👥 **Project Members:**\n"]
        
        for member in members:
            user_details = member.get("user_details", {})
            role = member.get("role", "member")
            
            if user_details:
                name = user_details.get("full_name", user_details.get("username", "Unknown"))
                email = user_details.get("email", "No email")
                user_role = user_details.get("role", "Developer")
                active = "🟢" if user_details.get("active", True) else "🔴"
                
                lines.append(f"• {active} **{name}** ({role.title()})")
                lines.append(f"  📧 {email} | 💼 {user_role}")
            else:
                user_id = member.get("user_id", "Unknown")
                lines.append(f"• User ID: {user_id} ({role.title()})")
            
            lines.append("")  # Empty line for spacing
        
        # Remove last empty line
        if lines and lines[-1] == "":
            lines.pop()
        
        return "\n".join(lines)
    
    def _format_auto_assignment(self, data: Dict) -> str:
        assignments = data.get("assignments", [])
        criteria = data.get("criteria", "random")
        requested = data.get("requested_count", 0)
        actual = data.get("actual_count", 0)
        
        lines = [f"🤖 **Auto-Assignment Complete** ({criteria}):\n"]
        
        if assignments:
            lines.append(f"✅ **Assigned {actual}/{requested} users:**")
            for assignment in assignments:
                user_name = assignment.get("user_name", "Unknown")
                lines.append(f"  • {user_name}")
            lines.append("")
        
        if actual < requested:
            lines.append(f"⚠️ Could only assign {actual} of {requested} requested users")
        
        return "\n".join(lines)