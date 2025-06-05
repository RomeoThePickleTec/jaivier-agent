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
        
        # Collect task data for date calculations
        tasks_for_estimation = []
        project_ref = None
        
        for i, operation in enumerate(operations):
            try:
                result = await self._execute_operation(operation, user_id)
                results.append(result)
                logger.info(f"[EXECUTOR] Operation {i+1}: {result.get('success', False)}")
                
                # Collect task and project data for estimation
                if operation.get("type") == "CREATE_PROJECT":
                    project_ref = operation.get("reference")
                elif operation.get("type") == "CREATE_TASK":
                    task_data = operation.get("data", {})
                    sprint_id_ref = task_data.get("sprint_id", "")
                    if isinstance(sprint_id_ref, str) and sprint_id_ref.startswith("$"):
                        sprint_ref = sprint_id_ref.split(".")[0][1:]  # Remove $ and .id
                    else:
                        sprint_ref = "sprint1"
                    
                    tasks_for_estimation.append({
                        'title': task_data.get('title', ''),
                        'description': task_data.get('description', ''),
                        'sprint_ref': sprint_ref,
                        'estimated_hours': self._estimate_task_hours(
                            task_data.get('title', ''), 
                            task_data.get('description', '')
                        )
                    })
                    
            except Exception as e:
                logger.error(f"[EXECUTOR] Error in operation {i+1}: {e}")
                results.append({"success": False, "error": str(e)})
        
        # Update dates if we have tasks and a project
        if tasks_for_estimation and project_ref and self.created_items.get(project_ref):
            try:
                await self._update_project_and_sprint_dates(tasks_for_estimation, project_ref)
                logger.info(f"[EXECUTOR] Updated dates for project {project_ref} based on {len(tasks_for_estimation)} tasks")
            except Exception as e:
                logger.error(f"[EXECUTOR] Error updating dates: {e}")
        
        return self._generate_response(results, operations_json)
    
    async def _update_project_and_sprint_dates(self, tasks_data: List[Dict], project_ref: str):
        """Update project and sprint dates based on task estimations"""
        try:
            # Calculate realistic dates
            date_calculations = self._calculate_project_dates(tasks_data)
            
            # Update project dates
            project_data = self.created_items.get(project_ref)
            if project_data and project_data.get("id"):
                project_id = project_data["id"]
                project_updates = {
                    "start_date": date_calculations["project"]["start_date"],
                    "end_date": date_calculations["project"]["end_date"]
                }
                
                # Get current project data and merge
                current_project = await self.api_manager.projects.get_by_id(project_id)
                if current_project:
                    final_data = {
                        "name": current_project.get("name"),
                        "description": current_project.get("description", ""),
                        "status": current_project.get("status", 0),
                        **project_updates
                    }
                    
                    await self.api_manager.projects.update(project_id, final_data)
                    logger.info(f"Updated project {project_id} dates: {project_updates['start_date']} to {project_updates['end_date']}")
            
            # Update sprint dates
            for sprint_ref, sprint_dates in date_calculations["sprints"].items():
                sprint_data = self.created_items.get(sprint_ref)
                if sprint_data and sprint_data.get("id"):
                    sprint_id = sprint_data["id"]
                    sprint_updates = {
                        "start_date": sprint_dates["start_date"],
                        "end_date": sprint_dates["end_date"]
                    }
                    
                    # Get current sprint data and merge
                    current_sprint = await self.api_manager.sprints.get_by_id(sprint_id)
                    if current_sprint:
                        final_data = {
                            "name": current_sprint.get("name"),
                            "description": current_sprint.get("description", ""),
                            "project_id": current_sprint.get("project_id"),
                            "status": current_sprint.get("status", 0),
                            **sprint_updates
                        }
                        
                        await self.api_manager.sprints.update(sprint_id, final_data)
                        logger.info(f"Updated sprint {sprint_id} ({sprint_ref}) dates: {sprint_updates['start_date']} to {sprint_updates['end_date']} ({sprint_dates['duration_days']} days, {sprint_dates['estimated_hours']} hours)")
                        
        except Exception as e:
            logger.error(f"Error updating project and sprint dates: {e}")
    
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
        elif op_type == "UPDATE_USER":
            result = await self._update_user(data)
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
        elif op_type == "DELETE_USER":
            result = await self._delete_user(data)
        elif op_type == "ASSIGN_USER_TO_PROJECT":
            result = await self._assign_user_to_project(data)
        elif op_type == "REMOVE_USER_FROM_PROJECT":
            result = await self._remove_user_from_project(data)
        elif op_type == "LIST_PROJECT_MEMBERS":
            result = await self._list_project_members(data)
        elif op_type == "AUTO_ASSIGN_USERS":
            result = await self._auto_assign_users(data)
        elif op_type == "QUERY_STATUS":
            result = await self._query_status(data)
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
        # Handle estimated_hours safely - use intelligent estimation if not provided
        estimated_hours = data.get("estimated_hours")
        if estimated_hours is not None:
            try:
                estimated_hours = int(estimated_hours)
            except (ValueError, TypeError):
                # Use intelligent estimation based on task title and description
                estimated_hours = self._estimate_task_hours(
                    data.get("title", ""), 
                    data.get("description", "")
                )
        else:
            # Use intelligent estimation based on task title and description
            estimated_hours = self._estimate_task_hours(
                data.get("title", ""), 
                data.get("description", "")
            )
        
        task_data = {
            "title": data.get("title", "New Task"),
            "description": data.get("description", "Created by bot"),
            "priority": self._parse_priority(data.get("priority", "medium")),
            "status": self._parse_status(data.get("status", "todo"), "task"),
            "estimated_hours": estimated_hours,
            "due_date": self._format_date(data.get("due_date")) or (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        
        # Add optional IDs (safely handle conversions)
        project_id = data.get("project_id")
        if project_id is not None:
            try:
                task_data["project_id"] = int(project_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid project_id: {project_id}")
        
        sprint_id = data.get("sprint_id")
        if sprint_id is not None:
            try:
                task_data["sprint_id"] = int(sprint_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid sprint_id: {sprint_id}")
        
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
    
    async def _update_user(self, data: Dict) -> Dict:
        user_id = data.get("id") or data.get("user_id")
        username = data.get("username")
        user_name = data.get("user_name")
        
        # If no ID but we have a username or name, search for the user
        if not user_id and (username or user_name):
            try:
                users = await self.api_manager.users.get_all()
                search_term = username or user_name
                for user in users:
                    if (user.get("username", "").lower() == search_term.lower() or 
                        user.get("full_name", "").lower() == search_term.lower()):
                        user_id = user.get("id")
                        break
                
                if not user_id:
                    return {"success": False, "error": f"User '{search_term}' not found"}
            except Exception as e:
                return {"success": False, "error": f"Error searching for user: {e}"}
        
        if not user_id:
            return {"success": False, "error": "user_id, username, or user_name required for update"}
        
        try:
            user_id = int(user_id)
            logger.info(f"[EXECUTOR] Updating user {user_id}")
            
            # Get current user data
            current_user = await self.api_manager.users.get_by_id(user_id)
            if not current_user:
                return {"success": False, "error": f"User {user_id} not found"}
            
            # Prepare update data - merge with current data
            update_data = {}
            
            # Update fields if provided
            if data.get("username"):
                update_data["username"] = data["username"]
            if data.get("email"):
                update_data["email"] = data["email"]
            if data.get("full_name"):
                update_data["full_name"] = data["full_name"]
            if data.get("password_hash"):
                update_data["password_hash"] = data["password_hash"]
            if data.get("work_mode"):
                update_data["work_mode"] = data["work_mode"].upper()  # Ensure uppercase
            if data.get("phone"):
                update_data["phone"] = data["phone"]
            if data.get("role"):
                update_data["role"] = data["role"]
            if data.get("active") is not None:
                update_data["active"] = data["active"]
            
            # Merge current data with updates (keep existing values for unspecified fields)
            final_data = {
                "username": update_data.get("username", current_user.get("username")),
                "email": update_data.get("email", current_user.get("email", "")),
                "full_name": update_data.get("full_name", current_user.get("full_name", "")),
                "password_hash": update_data.get("password_hash", current_user.get("password_hash", "")),
                "work_mode": update_data.get("work_mode", current_user.get("work_mode", "REMOTE")),
                "phone": update_data.get("phone", current_user.get("phone", "")),
                "role": update_data.get("role", current_user.get("role", "developer")),
                "active": update_data.get("active", current_user.get("active", True))
            }
            
            result = await self.api_manager.users.update(user_id, final_data)
            
            if result.get("success") or not result.get("error"):
                # Get updated user data
                await asyncio.sleep(0.5)  # Wait for update to process
                updated_user = await self.api_manager.users.get_by_id(user_id)
                
                return {
                    "success": True,
                    "data": {
                        "id": user_id,
                        "username": final_data["username"],
                        "full_name": final_data["full_name"],
                        "updated_fields": list(update_data.keys()),
                        "updated": True
                    },
                    "type": "user_updated"
                }
            else:
                return {"success": False, "error": result.get("error", "Update failed")}
                
        except ValueError:
            return {"success": False, "error": "Invalid user ID"}
        except Exception as e:
            logger.error(f"Error in _update_user: {e}")
            return {"success": False, "error": str(e)}
    
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
    
    async def _delete_user(self, data: Dict) -> Dict:
        user_id = data.get("id") or data.get("user_id")
        username = data.get("username")
        user_name = data.get("user_name")
        
        # If no ID but we have a username or name, search for the user
        if not user_id and (username or user_name):
            try:
                users = await self.api_manager.users.get_all()
                search_term = username or user_name
                for user in users:
                    if (user.get("username", "").lower() == search_term.lower() or 
                        user.get("full_name", "").lower() == search_term.lower()):
                        user_id = user.get("id")
                        break
                
                if not user_id:
                    return {"success": False, "error": f"User '{search_term}' not found"}
            except Exception as e:
                return {"success": False, "error": f"Error searching for user: {e}"}
        
        if not user_id:
            return {"success": False, "error": "user_id, username, or user_name required for deletion"}
        
        try:
            user_id = int(user_id)
            logger.info(f"[EXECUTOR] Deleting user {user_id}")
            
            # Get user details before deletion for response
            user = await self.api_manager.users.get_by_id(user_id)
            user_display = user.get("full_name", user.get("username", f"User {user_id}")) if user else f"User {user_id}"
            username_display = user.get("username", f"user_{user_id}") if user else f"user_{user_id}"
            
            result = await self.api_manager.users.delete(user_id)
            
            if result.get("success"):
                return {
                    "success": True, 
                    "data": {
                        "id": user_id, 
                        "username": username_display,
                        "full_name": user_display, 
                        "deleted": True
                    }, 
                    "type": "user_deleted"
                }
            else:
                return {"success": False, "error": result.get("error", "Deletion failed")}
                
        except ValueError:
            return {"success": False, "error": "Invalid user ID"}
        except Exception as e:
            logger.error(f"Error in _delete_user: {e}")
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
            
            # Resolve user ID if name provided (with fuzzy matching)
            if not user_id and user_name:
                users = await self.api_manager.users.get_all()
                found_user = None
                logger.info(f"Searching for user '{user_name}' among {len(users)} users")
                
                # Try exact matches first
                for user in users:
                    full_name = user.get("full_name", "")
                    username = user.get("username", "")
                    logger.info(f"Checking exact match: '{user_name.lower()}' vs full_name='{full_name.lower()}' username='{username.lower()}'")
                    if (full_name.lower() == user_name.lower() or username.lower() == user_name.lower()):
                        found_user = user
                        logger.info(f"EXACT MATCH FOUND: {user}")
                        break
                
                # If no exact match, try partial matches
                if not found_user:
                    logger.info(f"No exact match found, trying partial matches for '{user_name}'")
                    user_name_lower = user_name.lower()
                    for user in users:
                        full_name = user.get("full_name", "").lower()
                        username = user.get("username", "").lower()
                        logger.info(f"Checking partial match: '{user_name_lower}' vs full_name='{full_name}' username='{username}'")
                        
                        # Check if user_name is contained in full_name or username
                        if (user_name_lower in full_name or 
                            user_name_lower in username or
                            full_name in user_name_lower or
                            username in user_name_lower):
                            found_user = user
                            logger.info(f"PARTIAL MATCH FOUND: {user}")
                            break
                
                if found_user:
                    user_id = found_user.get("id")
                    logger.info(f"Found user: {found_user.get('full_name', found_user.get('username'))} (ID: {user_id}) for search term '{user_name}'")
                else:
                    # Return available users for better error message
                    available_users = [f"{u.get('full_name', u.get('username', 'Unknown'))} (ID: {u.get('id')})" for u in users]
                    return {
                        "success": False, 
                        "error": f"User '{user_name}' not found. Available users: {', '.join(available_users)}"
                    }
            
            # Final validation - ensure we have both required fields
            if not project_id or not user_id:
                return {"success": False, "error": "Both project_id and user_id are required"}
            
            # If user_id is still a string at this point, it means resolution failed
            if isinstance(user_id, str):
                # Get available users for helpful error message
                users = await self.api_manager.users.get_all()
                available_users = [f"{u.get('full_name', u.get('username', 'Unknown'))} (ID: {u.get('id')})" for u in users]
                return {
                    "success": False, 
                    "error": f"Could not resolve user '{user_id}' to a valid user ID. Available users: {', '.join(available_users[:5])}..."  # Limit to first 5 to avoid long messages
                }
            
            # Convert to integers
            try:
                project_id = int(project_id)
                user_id = int(user_id)
            except ValueError:
                return {"success": False, "error": "Invalid project_id or user_id"}
            
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
        project_name = data.get("project_name")
        user_name = data.get("user_name")
        
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
            
            # Resolve user ID if name provided (with fuzzy matching)
            if not user_id and user_name:
                users = await self.api_manager.users.get_all()
                found_user = None
                logger.info(f"Searching for user '{user_name}' to remove from project")
                
                # Try exact matches first
                for user in users:
                    full_name = user.get("full_name", "")
                    username = user.get("username", "")
                    if (full_name.lower() == user_name.lower() or username.lower() == user_name.lower()):
                        found_user = user
                        logger.info(f"EXACT MATCH FOUND for removal: {user}")
                        break
                
                # If no exact match, try partial matches
                if not found_user:
                    logger.info(f"No exact match found, trying partial matches for removal '{user_name}'")
                    user_name_lower = user_name.lower()
                    for user in users:
                        full_name = user.get("full_name", "").lower()
                        username = user.get("username", "").lower()
                        
                        # Check if user_name is contained in full_name or username
                        if (user_name_lower in full_name or 
                            user_name_lower in username or
                            full_name in user_name_lower or
                            username in user_name_lower):
                            found_user = user
                            logger.info(f"PARTIAL MATCH FOUND for removal: {user}")
                            break
                
                if found_user:
                    user_id = found_user.get("id")
                    logger.info(f"Found user for removal: {found_user.get('full_name', found_user.get('username'))} (ID: {user_id}) for search term '{user_name}'")
                else:
                    # Return available users for better error message
                    available_users = [f"{u.get('full_name', u.get('username', 'Unknown'))} (ID: {u.get('id')})" for u in users]
                    return {
                        "success": False, 
                        "error": f"User '{user_name}' not found for removal. Available users: {', '.join(available_users)}"
                    }
            
            # Final validation - ensure we have both required fields
            if not project_id or not user_id:
                return {"success": False, "error": "Both project_id and user_id are required for removal"}
            
            # If user_id is still a string at this point, it means resolution failed
            if isinstance(user_id, str):
                # Get available users for helpful error message
                users = await self.api_manager.users.get_all()
                available_users = [f"{u.get('full_name', u.get('username', 'Unknown'))} (ID: {u.get('id')})" for u in users]
                return {
                    "success": False, 
                    "error": f"Could not resolve user '{user_id}' to a valid user ID for removal. Available users: {', '.join(available_users[:5])}..."
                }
            
            # Convert to integers
            try:
                project_id = int(project_id)
                user_id = int(user_id)
            except ValueError:
                return {"success": False, "error": "Invalid project_id or user_id for removal"}
            
            # Get user and project names for response
            user = await self.api_manager.users.get_by_id(user_id)
            project = await self.api_manager.projects.get_by_id(project_id)
            
            user_display = user.get("full_name", user.get("username", f"User {user_id}")) if user else f"User {user_id}"
            project_display = project.get("name", f"Project {project_id}") if project else f"Project {project_id}"
            
            result = await self.api_manager.project_members.remove_user(project_id, user_id)
            
            if result.get("success"):
                return {
                    "success": True,
                    "data": {
                        "user_id": user_id,
                        "project_id": project_id,
                        "user_name": user_display,
                        "project_name": project_display,
                        "removed": True
                    },
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
        count = data.get("count") or data.get("num_users", 2)  # Support both field names
        
        logger.info(f"Auto-assign: project_id={project_id}, count={count}, criteria={criteria}, data={data}")
        
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
    
    async def _query_status(self, data: Dict) -> Dict:
        """Handle natural language queries about project status with AI analysis"""
        try:
            query = data.get("query", "")
            entity_type = data.get("entity_type", "project")  # project, sprint, task, general
            entity_name = data.get("entity_name", "")
            entity_id = data.get("entity_id")
            
            logger.info(f"Processing natural query: '{query}' for {entity_type} '{entity_name}' (ID: {entity_id})")
            
            # Gather relevant data based on query
            context_data = await self._gather_context_for_query(entity_type, entity_name, entity_id)
            
            if not context_data:
                return {
                    "success": False,
                    "error": f"No se encontró información para {entity_type} '{entity_name}'"
                }
            
            # Generate AI analysis
            ai_response = await self._generate_ai_analysis(query, context_data, entity_type)
            
            return {
                "success": True,
                "data": {
                    "query": query,
                    "entity_type": entity_type,
                    "entity_name": entity_name,
                    "analysis": ai_response,
                    "context": context_data
                },
                "type": "query_response"
            }
            
        except Exception as e:
            logger.error(f"Error in _query_status: {e}")
            return {"success": False, "error": str(e)}
    
    async def _gather_context_for_query(self, entity_type: str, entity_name: str, entity_id: int = None) -> Dict:
        """Gather relevant data for the query context"""
        try:
            context = {"entity_type": entity_type, "entity_name": entity_name}
            
            if entity_type == "project":
                # Find project by name or ID
                if entity_id:
                    project_id = entity_id
                else:
                    projects = await self.api_manager.projects.get_all()
                    project = None
                    
                    logger.info(f"Searching for project '{entity_name}' among {len(projects)} projects")
                    logger.info(f"Available projects: {[p.get('name') for p in projects]}")
                    
                    # First try exact match
                    for p in projects:
                        if p.get("name", "").lower() == entity_name.lower():
                            project = p
                            project_id = p.get("id")
                            logger.info(f"Found exact match: {p.get('name')} (ID: {project_id})")
                            break
                    
                    # If no exact match, try fuzzy matching
                    if not project and entity_name:
                        logger.info(f"No exact match found, trying fuzzy matching for '{entity_name}'")
                        for p in projects:
                            project_name = p.get("name", "").lower()
                            search_name = entity_name.lower()
                            
                            # Check if search name is contained in project name or vice versa
                            if search_name in project_name or project_name in search_name:
                                project = p
                                project_id = p.get("id")
                                logger.info(f"Found fuzzy match (containment): {p.get('name')} (ID: {project_id})")
                                break
                            
                            # Check for similar names (ignoring hyphens, underscores, spaces)
                            clean_project = project_name.replace("-", "").replace("_", "").replace(" ", "")
                            clean_search = search_name.replace("-", "").replace("_", "").replace(" ", "")
                            
                            if clean_search in clean_project or clean_project in clean_search:
                                project = p
                                project_id = p.get("id")
                                logger.info(f"Found fuzzy match (cleaned): {p.get('name')} (ID: {project_id})")
                                break
                    
                    if not project:
                        return None
                
                # Get full project data with sprints and tasks using the specific endpoint
                logger.info(f"Getting full project data for project ID: {project_id}")
                project_with_details = await self._get_project_with_details(project_id)
                
                if not project_with_details:
                    return None
                
                context["project"] = project_with_details
                
                # Extract sprints and tasks from the detailed project data
                sprints = project_with_details.get("sprints", [])
                context["sprints"] = sprints
                
                # Extract all tasks from all sprints
                tasks = []
                for sprint in sprints:
                    sprint_tasks = sprint.get("tasks", [])
                    tasks.extend(sprint_tasks)
                
                context["tasks"] = tasks
                logger.info(f"Found {len(tasks)} tasks in {len(sprints)} sprints for project {project_with_details.get('name')}")
                
                # Get project members
                members = await self.api_manager.project_members.get_by_project(project_id)
                context["members"] = members
                
                # Calculate statistics
                logger.info(f"Calculating stats for project {project_with_details.get('name')} with {len(tasks)} tasks, {len(sprints)} sprints, {len(members)} members")
                context["stats"] = self._calculate_project_stats(project_with_details, sprints, tasks, members)
                logger.info(f"Project stats calculated: {context['stats']}")
                
            elif entity_type == "sprint":
                # Find sprint by name
                sprints = await self.api_manager.sprints.get_all()
                sprint = None
                for s in sprints:
                    if s.get("name", "").lower() == entity_name.lower():
                        sprint = s
                        break
                
                if not sprint:
                    return None
                
                sprint_id = sprint.get("id")
                project_id = sprint.get("project_id")
                context["sprint"] = sprint
                
                # Get project info
                project = await self.api_manager.projects.get_by_id(project_id)
                context["project"] = project
                
                # Get tasks for this sprint
                tasks = await self.api_manager.tasks.get_all(project_id, sprint_id)
                context["tasks"] = tasks
                
                # Calculate sprint statistics
                context["stats"] = self._calculate_sprint_stats(sprint, tasks)
                
            elif entity_type == "task":
                # Find task by name
                tasks = await self.api_manager.tasks.get_all()
                task = None
                for t in tasks:
                    if t.get("title", "").lower() == entity_name.lower():
                        task = t
                        break
                
                if not task:
                    return None
                
                context["task"] = task
                
                # Get project and sprint info
                project_id = task.get("project_id")
                sprint_id = task.get("sprint_id")
                
                if project_id:
                    project = await self.api_manager.projects.get_by_id(project_id)
                    context["project"] = project
                
                if sprint_id:
                    sprint = await self.api_manager.sprints.get_by_id(sprint_id)
                    context["sprint"] = sprint
                
            elif entity_type == "general":
                # General overview
                projects = await self.api_manager.projects.get_all()
                sprints = await self.api_manager.sprints.get_all()
                tasks = await self.api_manager.tasks.get_all()
                users = await self.api_manager.users.get_all()
                
                context["projects"] = projects
                context["sprints"] = sprints
                context["tasks"] = tasks
                context["users"] = users
                context["stats"] = self._calculate_general_stats(projects, sprints, tasks, users)
            
            return context
            
        except Exception as e:
            logger.error(f"Error gathering context: {e}")
            return None
    
    async def _get_project_with_details(self, project_id: int) -> Dict:
        """Get full project data with sprints and tasks using specific endpoint"""
        try:
            # Use the specific endpoint that returns complete project data
            result = await self.api_manager.client._make_request("GET", f"/projectlist/{project_id}")
            
            if isinstance(result, dict) and not result.get('error'):
                logger.info(f"Successfully retrieved project details for ID {project_id}")
                return result
            else:
                logger.error(f"Error retrieving project details: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Exception getting project details for ID {project_id}: {e}")
            return None
    
    def _calculate_project_stats(self, project: Dict, sprints: List[Dict], tasks: List[Dict], members: List[Dict]) -> Dict:
        """Calculate project statistics"""
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.get("status") == 2])  # Completed status
        in_progress_tasks = len([t for t in tasks if t.get("status") == 1])  # In progress status
        todo_tasks = len([t for t in tasks if t.get("status") == 0])  # Todo status
        
        total_hours = sum(t.get("estimated_hours", 8) for t in tasks)
        completed_hours = sum(t.get("estimated_hours", 8) for t in tasks if t.get("status") == 2)
        
        progress_percentage = round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)
        hours_progress = round((completed_hours / total_hours * 100) if total_hours > 0 else 0, 1)
        
        active_sprints = len([s for s in sprints if s.get("status") == 0])
        completed_sprints = len([s for s in sprints if s.get("status") == 1])
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": in_progress_tasks,
            "todo_tasks": todo_tasks,
            "progress_percentage": progress_percentage,
            "total_hours": total_hours,
            "completed_hours": completed_hours,
            "hours_progress": hours_progress,
            "total_sprints": len(sprints),
            "active_sprints": active_sprints,
            "completed_sprints": completed_sprints,
            "team_size": len(members)
        }
    
    def _calculate_sprint_stats(self, sprint: Dict, tasks: List[Dict]) -> Dict:
        """Calculate sprint statistics"""
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.get("status") == 2])
        in_progress_tasks = len([t for t in tasks if t.get("status") == 1])
        todo_tasks = len([t for t in tasks if t.get("status") == 0])
        
        total_hours = sum(t.get("estimated_hours", 8) for t in tasks)
        completed_hours = sum(t.get("estimated_hours", 8) for t in tasks if t.get("status") == 2)
        
        progress_percentage = round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)
        
        # Check if sprint is overdue
        end_date = sprint.get("end_date")
        is_overdue = False
        if end_date:
            try:
                from datetime import datetime
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                is_overdue = end_dt < datetime.now()
            except:
                pass
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": in_progress_tasks,
            "todo_tasks": todo_tasks,
            "progress_percentage": progress_percentage,
            "total_hours": total_hours,
            "completed_hours": completed_hours,
            "is_overdue": is_overdue
        }
    
    def _calculate_general_stats(self, projects: List[Dict], sprints: List[Dict], tasks: List[Dict], users: List[Dict]) -> Dict:
        """Calculate general system statistics"""
        active_projects = len([p for p in projects if p.get("status") == 0])
        active_sprints = len([s for s in sprints if s.get("status") == 0])
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.get("status") == 2])
        
        active_users = len([u for u in users if u.get("active", True)])
        
        return {
            "total_projects": len(projects),
            "active_projects": active_projects,
            "total_sprints": len(sprints),
            "active_sprints": active_sprints,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "active_users": active_users,
            "overall_progress": round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)
        }
    
    async def _generate_ai_analysis(self, query: str, context_data: Dict, entity_type: str) -> str:
        """Generate AI analysis and recommendations"""
        try:
            # Import here to avoid circular imports
            import google.generativeai as genai
            from config.settings import GEMINI_API_KEY
            
            if not GEMINI_API_KEY or GEMINI_API_KEY == "TU_GEMINI_API_KEY":
                return self._generate_fallback_analysis(query, context_data, entity_type)
            
            # Prepare context for AI
            ai_prompt = self._build_analysis_prompt(query, context_data, entity_type)
            
            # Debug logging
            logger.info(f"AI Analysis Debug - Entity: {entity_type}")
            logger.info(f"AI Analysis Debug - Context Stats: {context_data.get('stats', {})}")
            
            # Generate AI response
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(ai_prompt)
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating AI analysis: {e}")
            return self._generate_fallback_analysis(query, context_data, entity_type)
    
    def _build_analysis_prompt(self, query: str, context_data: Dict, entity_type: str) -> str:
        """Build prompt for AI analysis"""
        stats = context_data.get("stats", {})
        
        if entity_type == "project":
            project = context_data.get("project", {})
            prompt = f"""
            Eres un asistente de gestión de proyectos experto. Un usuario pregunta: "{query}"
            
            INFORMACIÓN DEL PROYECTO:
            - Nombre: {project.get('name', 'N/A')}
            - Descripción: {project.get('description', 'N/A')}
            - Estado: {['Activo', 'Completado', 'Pausado'][project.get('status', 0)]}
            - Fecha inicio: {project.get('start_date', 'N/A')}
            - Fecha fin: {project.get('end_date', 'N/A')}
            
            ESTADÍSTICAS:
            - Total tareas: {stats.get('total_tasks', 0)}
            - Tareas completadas: {stats.get('completed_tasks', 0)}
            - Tareas en progreso: {stats.get('in_progress_tasks', 0)}
            - Tareas pendientes: {stats.get('todo_tasks', 0)}
            - Progreso: {stats.get('progress_percentage', 0)}%
            - Horas totales: {stats.get('total_hours', 0)}
            - Horas completadas: {stats.get('completed_hours', 0)}
            - Sprints totales: {stats.get('total_sprints', 0)}
            - Sprints activos: {stats.get('active_sprints', 0)}
            - Tamaño del equipo: {stats.get('team_size', 0)}
            
            TAREAS DEL PROYECTO:"""
            
            # Add task information to the prompt
            tasks = context_data.get("tasks", [])
            if tasks:
                for task in tasks[:20]:  # Limit to prevent prompt overflow
                    status_text = ["Pendiente", "En progreso", "Completada"][task.get("status", 0)]
                    prompt += f"""
            - "{task.get('title', 'Sin título')}" (Status: {status_text})"""
            
            prompt += f"""
            
            INSTRUCCIONES PARA DIFERENTES TIPOS DE PREGUNTAS:

            1. PREGUNTAS DE CONTEO (responder SOLO el número, SIN análisis):
            - "cuántas tareas faltan" → "{stats.get('todo_tasks', 0)} tareas pendientes"
            - "cuántas tareas quedan" → "{stats.get('todo_tasks', 0) + stats.get('in_progress_tasks', 0)} tareas restantes"  
            - "cuántas tareas hay" → "{stats.get('total_tasks', 0)} tareas en total"
            - "cuántas tareas completadas" → "{stats.get('completed_tasks', 0)} tareas completadas"

            2. PREGUNTAS DE LISTADO (RESPONDER EXCLUSIVAMENTE LA LISTA):
            Si la pregunta contiene "dame los nombres", "cuáles son", "que tareas", "lista de tareas":
            - Buscar ÚNICAMENTE las tareas con status 0 (pendientes)
            - Responder EXCLUSIVAMENTE:
            "Tareas pendientes del proyecto [NOMBRE]:
            • [Título tarea 1]  
            • [Título tarea 2]
            • [Título tarea 3]"
            - TERMINAR LA RESPUESTA AHÍ
            - PROHIBIDO: análisis, recomendaciones, explicaciones, contexto adicional

            3. PREGUNTAS DE ANÁLISIS (dar análisis completo SOLO si NO es pregunta de listado):
            - "como va el proyecto" → Análisis detallado
            - "estado del proyecto" → Resumen con recomendaciones  
            - "resumen del proyecto" → Análisis completo

            REGLA CRÍTICA: Si detectas palabras como "dame los nombres", "cuáles son las tareas", es TIPO 2, NO análisis.
            
            Proporciona un análisis detallado que incluya:
            1. Estado actual del proyecto
            2. Progreso y tendencias
            3. Posibles problemas o riesgos
            4. Recomendaciones específicas
            5. Próximos pasos sugeridos
            
            Responde en español de forma natural y conversacional.
            """
            
        elif entity_type == "sprint":
            sprint = context_data.get("sprint", {})
            prompt = f"""
            Eres un asistente de gestión de proyectos experto. Un usuario pregunta: "{query}"
            
            INFORMACIÓN DEL SPRINT:
            - Nombre: {sprint.get('name', 'N/A')}
            - Descripción: {sprint.get('description', 'N/A')}
            - Estado: {['Activo', 'Completado'][sprint.get('status', 0)]}
            - Fecha inicio: {sprint.get('start_date', 'N/A')}
            - Fecha fin: {sprint.get('end_date', 'N/A')}
            
            ESTADÍSTICAS:
            - Total tareas: {stats.get('total_tasks', 0)}
            - Tareas completadas: {stats.get('completed_tasks', 0)}
            - Tareas en progreso: {stats.get('in_progress_tasks', 0)}
            - Tareas pendientes: {stats.get('todo_tasks', 0)}
            - Progreso: {stats.get('progress_percentage', 0)}%
            - Horas totales: {stats.get('total_hours', 0)}
            - Horas completadas: {stats.get('completed_hours', 0)}
            - ¿Retrasado?: {stats.get('is_overdue', False)}
            
            Proporciona un análisis que incluya:
            1. Estado actual del sprint
            2. Progreso hacia los objetivos
            3. Riesgos de no cumplir la fecha límite
            4. Recomendaciones para mejorar el flujo
            5. Tareas que requieren atención inmediata
            
            Responde en español de forma natural y conversacional.
            """
            
        else:  # general
            prompt = f"""
            Eres un asistente de gestión de proyectos experto. Un usuario pregunta: "{query}"
            
            RESUMEN GENERAL:
            - Proyectos totales: {stats.get('total_projects', 0)}
            - Proyectos activos: {stats.get('active_projects', 0)}
            - Sprints activos: {stats.get('active_sprints', 0)}
            - Tareas totales: {stats.get('total_tasks', 0)}
            - Tareas completadas: {stats.get('completed_tasks', 0)}
            - Usuarios activos: {stats.get('active_users', 0)}
            - Progreso general: {stats.get('overall_progress', 0)}%
            
            Proporciona un análisis general que incluya:
            1. Estado general de todos los proyectos
            2. Tendencias y patrones
            3. Áreas que necesitan atención
            4. Recomendaciones de mejora
            5. Sugerencias de optimización
            
            Responde en español de forma natural y conversacional.
            """
        
        return prompt
    
    def _generate_fallback_analysis(self, query: str, context_data: Dict, entity_type: str) -> str:
        """Generate fallback analysis when AI is not available"""
        stats = context_data.get("stats", {})
        query_lower = query.lower()
        
        if entity_type == "project":
            project = context_data.get("project", {})
            progress = stats.get("progress_percentage", 0)
            
            # Check for specific task count questions - give direct, short answers
            if any(phrase in query_lower for phrase in ["cuantas tareas faltan", "cuántas tareas faltan", "tareas pendientes"]):
                pending_tasks = stats.get('todo_tasks', 0)
                return f"📋 {pending_tasks} tareas pendientes en el proyecto {project.get('name', 'N/A')}"
            
            elif any(phrase in query_lower for phrase in ["cuantas tareas quedan", "cuántas tareas quedan", "tasks remaining"]):
                remaining_tasks = stats.get('todo_tasks', 0) + stats.get('in_progress_tasks', 0)
                return f"📋 {remaining_tasks} tareas restantes en el proyecto {project.get('name', 'N/A')}"
            
            elif any(phrase in query_lower for phrase in ["cuantas tareas hay", "cuántas tareas hay", "total tareas"]):
                total_tasks = stats.get('total_tasks', 0)
                return f"📋 {total_tasks} tareas en total en el proyecto {project.get('name', 'N/A')}"
            
            elif any(phrase in query_lower for phrase in ["cuantas tareas completadas", "cuántas tareas completadas", "tareas completadas"]):
                completed_tasks = stats.get('completed_tasks', 0)
                return f"📋 {completed_tasks} tareas completadas en el proyecto {project.get('name', 'N/A')}"
            
            elif any(phrase in query_lower for phrase in ["dame los nombres", "cuales son las tareas", "cuáles son las tareas", "que tareas faltan", "qué tareas faltan", "lista de tareas"]):
                tasks = context_data.get('tasks', [])
                pending_tasks = [t for t in tasks if t.get('status') == 0]  # Status 0 = pending
                
                if "pendientes" in query_lower or "faltan" in query_lower or "faltantes" in query_lower:
                    if not pending_tasks:
                        return f"📋 No hay tareas pendientes en el proyecto {project.get('name', 'N/A')}"
                    
                    task_names = [f"• {t.get('title', 'Sin título')}" for t in pending_tasks]
                    return f"📋 Tareas pendientes del proyecto {project.get('name', 'N/A')}:\n\n" + "\n".join(task_names)
                else:
                    # All tasks
                    if not tasks:
                        return f"📋 No hay tareas en el proyecto {project.get('name', 'N/A')}"
                    
                    task_names = [f"• {t.get('title', 'Sin título')}" for t in tasks]
                    return f"📋 Todas las tareas del proyecto {project.get('name', 'N/A')}:\n\n" + "\n".join(task_names)
            
            # Default project analysis
            analysis = f"📊 **Estado del Proyecto {project.get('name', 'N/A')}**\n\n"
            analysis += f"**Progreso general:** {progress}% completado\n"
            analysis += f"**Tareas:** {stats.get('completed_tasks', 0)}/{stats.get('total_tasks', 0)} completadas\n"
            analysis += f"**Sprints:** {stats.get('active_sprints', 0)} activos de {stats.get('total_sprints', 0)} totales\n"
            analysis += f"**Equipo:** {stats.get('team_size', 0)} miembros\n\n"
            
            if progress < 30:
                analysis += "🔥 **Recomendaciones:**\n- El proyecto está en etapa inicial\n- Enfocar en completar las tareas del primer sprint\n- Asegurar que el equipo tenga claridad en los objetivos"
            elif progress < 70:
                analysis += "⚡ **Recomendaciones:**\n- Buen progreso, mantener el ritmo\n- Revisar si hay tareas bloqueadas\n- Considerar planificación del siguiente sprint"
            else:
                analysis += "🚀 **Recomendaciones:**\n- Excelente progreso\n- Preparar actividades de cierre\n- Documentar lecciones aprendidas"
                
        elif entity_type == "sprint":
            sprint = context_data.get("sprint", {})
            progress = stats.get("progress_percentage", 0)
            
            analysis = f"🏃 **Estado del Sprint {sprint.get('name', 'N/A')}**\n\n"
            analysis += f"**Progreso:** {progress}% completado\n"
            analysis += f"**Tareas:** {stats.get('completed_tasks', 0)}/{stats.get('total_tasks', 0)} completadas\n"
            
            if stats.get("is_overdue"):
                analysis += "⚠️ **ALERTA:** Sprint retrasado\n"
            
            if progress < 50:
                analysis += "\n**Recomendaciones:**\n- Acelerar el ritmo de trabajo\n- Identificar y resolver bloqueadores\n- Considerar reasignar tareas"
            else:
                analysis += "\n**Recomendaciones:**\n- Buen progreso hacia la meta\n- Preparar review del sprint\n- Planificar retrospectiva"
        
        else:  # general
            analysis = f"📈 **Resumen General del Sistema**\n\n"
            analysis += f"**Proyectos activos:** {stats.get('active_projects', 0)}\n"
            analysis += f"**Sprints en ejecución:** {stats.get('active_sprints', 0)}\n"
            analysis += f"**Progreso global:** {stats.get('overall_progress', 0)}%\n"
            analysis += f"**Equipo activo:** {stats.get('active_users', 0)} usuarios\n\n"
            analysis += "**Recomendaciones:**\n- Revisar proyectos con bajo progreso\n- Balancear carga de trabajo del equipo\n- Planificar próximos sprints"
        
        return analysis
    
    # UTILITY METHODS
    def _calculate_project_dates(self, tasks_data: List[Dict], start_date: datetime = None) -> Dict:
        """Calculate realistic project and sprint dates based on task estimations"""
        if not start_date:
            start_date = datetime.now()
        
        # Constants for estimation
        HOURS_PER_DAY = 6  # Productive hours per developer per day
        DAYS_PER_WEEK = 5  # Working days
        HOURS_PER_WEEK = HOURS_PER_DAY * DAYS_PER_WEEK  # 30 hours per week
        
        # Group tasks by sprint
        sprint_tasks = {}
        for task in tasks_data:
            sprint_ref = task.get('sprint_ref', 'sprint1')
            if sprint_ref not in sprint_tasks:
                sprint_tasks[sprint_ref] = []
            sprint_tasks[sprint_ref].append(task)
        
        # Calculate dates for each sprint
        current_date = start_date
        sprint_dates = {}
        total_project_hours = 0
        
        for sprint_ref, tasks in sprint_tasks.items():
            # Calculate total hours for this sprint
            sprint_hours = 0
            for task in tasks:
                estimated_hours = task.get('estimated_hours', 8)
                if isinstance(estimated_hours, str):
                    # Parse text-based estimations
                    if 'simple' in estimated_hours.lower() or 'básica' in estimated_hours.lower():
                        estimated_hours = 4
                    elif 'complex' in estimated_hours.lower() or 'compleja' in estimated_hours.lower():
                        estimated_hours = 16
                    elif 'medium' in estimated_hours.lower() or 'media' in estimated_hours.lower():
                        estimated_hours = 8
                    else:
                        estimated_hours = 8
                
                sprint_hours += estimated_hours
            
            # Calculate sprint duration (assuming parallel work)
            # With multiple developers, tasks can be done in parallel
            num_developers = min(3, len(tasks))  # Assume max 3 devs per sprint
            sprint_duration_hours = sprint_hours / max(1, num_developers)
            sprint_duration_weeks = max(1, sprint_duration_hours / HOURS_PER_WEEK)
            sprint_duration_days = int(sprint_duration_weeks * 7)
            
            # Add buffer time (20% for testing, reviews, etc.)
            sprint_duration_days = int(sprint_duration_days * 1.2)
            
            sprint_start = current_date
            sprint_end = current_date + timedelta(days=sprint_duration_days)
            
            sprint_dates[sprint_ref] = {
                'start_date': sprint_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                'end_date': sprint_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                'estimated_hours': sprint_hours,
                'duration_days': sprint_duration_days
            }
            
            total_project_hours += sprint_hours
            current_date = sprint_end + timedelta(days=2)  # 2-day buffer between sprints
        
        # Calculate overall project dates
        project_end = current_date - timedelta(days=2)  # Remove last buffer
        project_duration_days = (project_end - start_date).days
        
        return {
            'project': {
                'start_date': start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                'end_date': project_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                'total_hours': total_project_hours,
                'duration_days': project_duration_days
            },
            'sprints': sprint_dates
        }
    
    def _estimate_task_hours(self, task_title: str, task_description: str = "") -> int:
        """Estimate hours for a task based on title and description"""
        title_lower = task_title.lower()
        desc_lower = task_description.lower()
        
        # Task complexity patterns
        simple_patterns = ['setup', 'config', 'install', 'basic', 'simple', 'crear', 'añadir']
        medium_patterns = ['component', 'page', 'api', 'endpoint', 'form', 'auth', 'database', 'model']
        complex_patterns = ['integration', 'deploy', 'optimization', 'testing', 'security', 'performance', 'animation']
        
        # Check for keywords in title
        if any(pattern in title_lower for pattern in complex_patterns):
            return 16  # 2 days
        elif any(pattern in title_lower for pattern in medium_patterns):
            return 12  # 1.5 days
        elif any(pattern in title_lower for pattern in simple_patterns):
            return 6   # 0.75 days
        
        # Check description if available
        if desc_lower:
            if any(pattern in desc_lower for pattern in complex_patterns):
                return 16
            elif any(pattern in desc_lower for pattern in medium_patterns):
                return 12
            elif any(pattern in desc_lower for pattern in simple_patterns):
                return 6
        
        # Default estimation
        return 8  # 1 day
    
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
            elif result_type == "user_deleted":
                data = result.get("data", {})
                full_name = data.get("full_name", "User")
                username = data.get("username", "")
                if username and username != full_name:
                    return f"🗑️ **{full_name}** ({username}) deleted successfully!"
                else:
                    return f"🗑️ **{full_name}** deleted successfully!"
            elif result_type == "project_updated":
                data = result.get("data", {})
                name = data.get("name", "Project")
                updated_fields = data.get("updated_fields", [])
                fields_text = ", ".join(updated_fields) if updated_fields else "fields"
                return f"✏️ **{name}** updated successfully! ({fields_text})"
            elif result_type == "user_updated":
                data = result.get("data", {})
                username = data.get("username", "User")
                full_name = data.get("full_name", "")
                updated_fields = data.get("updated_fields", [])
                fields_text = ", ".join(updated_fields) if updated_fields else "fields"
                display_name = full_name if full_name else username
                return f"✏️ **{display_name}** ({username}) updated successfully! ({fields_text})"
            elif result_type == "user_assigned":
                data = result.get("data", {})
                user_name = data.get("user_name", "User")
                project_name = data.get("project_name", "Project")
                role = data.get("role", "member")
                return f"👥 **{user_name}** assigned to **{project_name}** as {role}!"
            elif result_type == "user_removed":
                data = result.get("data", {})
                user_name = data.get("user_name", "User")
                project_name = data.get("project_name", "Project")
                return f"👥 **{user_name}** removed from **{project_name}** successfully!"
            elif result_type == "project_members":
                return self._format_project_members(result["data"])
            elif result_type == "auto_assignment":
                return self._format_auto_assignment(result["data"])
            elif result_type == "projects_bulk_deleted":
                return self._format_bulk_deletion(result["data"])
            elif result_type == "sprints_bulk_deleted":
                return self._format_bulk_sprint_deletion(result["data"])
            elif result_type == "query_response":
                return self._format_query_response(result["data"])
        
        # Handle multiple operations with detailed feedback
        if successful:
            # Group by type for better organization
            projects = [r for r in successful if r.get("type") == "project"]
            sprints = [r for r in successful if r.get("type") == "sprint"]
            tasks = [r for r in successful if r.get("type") == "task"]
            assignments = [r for r in successful if r.get("type") == "user_assigned"]
            bulk_deletions = [r for r in successful if r.get("type") == "projects_bulk_deleted"]
            bulk_sprint_deletions = [r for r in successful if r.get("type") == "sprints_bulk_deleted"]
            
            # Check if this is primarily a deletion operation
            if bulk_deletions:
                # Handle bulk project deletion separately
                return self._format_bulk_deletion(bulk_deletions[0]["data"])
            elif bulk_sprint_deletions:
                # Handle bulk sprint deletion separately
                return self._format_bulk_sprint_deletion(bulk_sprint_deletions[0]["data"])
            elif assignments and not projects and not sprints and not tasks:
                # Handle multiple assignments separately
                return self._format_multiple_assignments(assignments)
            
            # Check for multiple removals
            removals = [r for r in successful if r.get("type") == "user_removed"]
            if removals and not projects and not sprints and not tasks and not assignments:
                # Handle multiple removals separately
                return self._format_multiple_removals(removals)
            
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
            
            # Add estimation summary if available
            if tasks:
                total_estimated_hours = sum(task.get("data", {}).get("estimated_hours", 8) for task in tasks)
                total_estimated_days = round(total_estimated_hours / 6, 1)  # 6 productive hours per day
                response_lines.append(f"⏱️ **Estimated effort:** {total_estimated_hours}h ({total_estimated_days} days)")
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
    
    def _format_multiple_removals(self, removals: List[Dict]) -> str:
        if not removals:
            return "❌ No users removed"
        
        successful = [r for r in removals if r.get("success")]
        failed = [r for r in removals if not r.get("success")]
        
        lines = ["👥 **User Removal Results:**\n"]
        
        if successful:
            # Group by project
            project_removals = {}
            for removal in successful:
                data = removal.get("data", {})
                project_name = data.get("project_name", "Unknown Project")
                user_name = data.get("user_name", "Unknown User")
                
                if project_name not in project_removals:
                    project_removals[project_name] = []
                project_removals[project_name].append(user_name)
            
            for project, users in project_removals.items():
                lines.append(f"✅ **{project}:**")
                for user in users:
                    lines.append(f"  • {user} removed")
                lines.append("")
        
        if failed:
            lines.append(f"❌ **Failed Removals ({len(failed)}):**")
            for failure in failed:
                error = failure.get("error", "Unknown error")
                lines.append(f"  • {error}")
        
        return "\n".join(lines)
    
    def _format_multiple_assignments(self, assignments: List[Dict]) -> str:
        if not assignments:
            return "❌ No assignments completed"
        
        successful = [a for a in assignments if a.get("success")]
        failed = [a for a in assignments if not a.get("success")]
        
        lines = ["👥 **User Assignment Results:**\n"]
        
        if successful:
            # Group by project
            project_assignments = {}
            for assignment in successful:
                data = assignment.get("data", {})
                project_name = data.get("project_name", "Unknown Project")
                user_name = data.get("user_name", "Unknown User")
                
                if project_name not in project_assignments:
                    project_assignments[project_name] = []
                project_assignments[project_name].append(user_name)
            
            for project, users in project_assignments.items():
                lines.append(f"✅ **{project}:**")
                for user in users:
                    lines.append(f"  • {user}")
                lines.append("")
        
        if failed:
            lines.append(f"❌ **Failed Assignments ({len(failed)}):**")
            for failure in failed:
                error = failure.get("error", "Unknown error")
                lines.append(f"  • {error}")
        
        return "\n".join(lines)
    
    def _format_query_response(self, data: Dict) -> str:
        """Format AI query response"""
        analysis = data.get("analysis", "")
        entity_type = data.get("entity_type", "")
        entity_name = data.get("entity_name", "")
        
        if analysis:
            # If we have AI analysis, return it directly
            return analysis
        else:
            # Fallback if no AI analysis
            return f"📊 Status information for {entity_type} '{entity_name}' is being processed..."