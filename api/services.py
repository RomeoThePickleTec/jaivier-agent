# api/services.py
"""Servicios específicos para cada entidad de la API"""

from typing import List, Dict, Optional
from .client import APIClient

class UserService:
    """Servicio para manejo de usuarios"""
    
    def __init__(self, client: APIClient):
        self.client = client
        self.base_path = "/userlist"
    
    async def get_all(self) -> List[Dict]:
        """Obtener todos los usuarios"""
        result = await self.client._make_request("GET", self.base_path)
        return result if isinstance(result, list) else []
    
    async def get_by_id(self, user_id: int) -> Optional[Dict]:
        """Obtener usuario por ID"""
        users = await self.get_all()
        return next((user for user in users if user.get('id') == user_id), None)
    
    async def create(self, user_data: Dict) -> Dict:
        """Crear un nuevo usuario"""
        return await self.client._make_request("POST", self.base_path, user_data)
    
    async def update(self, user_id: int, user_data: Dict) -> Dict:
        """Actualizar un usuario"""
        return await self.client._make_request("PUT", f"{self.base_path}/{user_id}", user_data)
    
    async def delete(self, user_id: int) -> Dict:
        """Eliminar un usuario"""
        return await self.client._make_request("DELETE", f"{self.base_path}/{user_id}")

class ProjectService:
    """Servicio para manejo de proyectos"""
    
    def __init__(self, client: APIClient):
        self.client = client
        self.base_path = "/projectlist"
    
    async def get_all(self) -> List[Dict]:
        """Obtener todos los proyectos"""
        result = await self.client._make_request("GET", self.base_path)
        return result if isinstance(result, list) else []
    
    async def get_by_id(self, project_id: int) -> Optional[Dict]:
        """Obtener proyecto por ID"""
        projects = await self.get_all()
        return next((project for project in projects if project.get('id') == project_id), None)
    
    async def create(self, project_data: Dict) -> Dict:
        """Crear un nuevo proyecto"""
        return await self.client._make_request("POST", self.base_path, project_data)
    
    async def update(self, project_id: int, project_data: Dict) -> Dict:
        """Actualizar un proyecto"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"Updating project {project_id} with data: {project_data}")
            result = await self.client._make_request("PUT", f"{self.base_path}/{project_id}", project_data)
            logger.info(f"Update API response: {result} (type: {type(result)})")
            
            # Handle different response types
            if isinstance(result, dict):
                if result.get('success') == True and not result.get('error'):
                    logger.info(f"Project {project_id} updated successfully")
                    return {"success": True, "updated": True}
                elif result.get('error'):
                    logger.error(f"Failed to update project {project_id}: {result.get('error')}")
                    return result
                else:
                    logger.info(f"Project {project_id} updated successfully")
                    return {"success": True, "updated": True}
            else:
                # Handle unexpected response types
                logger.warning(f"Unexpected response type {type(result)}: {result}")
                return {"success": True, "updated": True}
                
        except Exception as e:
            logger.error(f"Error updating project {project_id}: {e}")
            return {"error": str(e), "success": False}
    
    async def delete(self, project_id: int) -> Dict:
        """Eliminar un proyecto"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"Deleting project {project_id}")
            result = await self.client._make_request("DELETE", f"{self.base_path}/{project_id}")
            logger.info(f"Delete API response: {result} (type: {type(result)})")
            
            # Handle different response types
            if isinstance(result, dict):
                if result.get('success') == True and not result.get('error'):
                    logger.info(f"Project {project_id} deleted successfully")
                    return {"success": True, "deleted": True}
                elif result.get('error'):
                    logger.error(f"Failed to delete project {project_id}: {result.get('error')}")
                    return result
                else:
                    logger.info(f"Project {project_id} deleted successfully")
                    return {"success": True, "deleted": True}
            else:
                # Handle unexpected response types
                logger.warning(f"Unexpected response type {type(result)}: {result}")
                return {"success": True, "deleted": True}
                
        except Exception as e:
            logger.error(f"Error deleting project {project_id}: {e}")
            return {"error": str(e), "success": False}

class SprintService:
    """Servicio para manejo de sprints"""
    
    def __init__(self, client: APIClient):
        self.client = client
        self.base_path = "/sprintlist"
    
    async def get_all(self, project_id: Optional[int] = None) -> List[Dict]:
        """Obtener todos los sprints"""
        endpoint = self.base_path
        if project_id:
            endpoint += f"?project_id={project_id}"
        
        result = await self.client._make_request("GET", endpoint)
        return result if isinstance(result, list) else []
    
    async def get_by_id(self, sprint_id: int) -> Optional[Dict]:
        """Obtener sprint por ID"""
        sprints = await self.get_all()
        return next((sprint for sprint in sprints if sprint.get('id') == sprint_id), None)
    
    async def create(self, sprint_data: Dict) -> Dict:
        """Crear un nuevo sprint"""
        return await self.client._make_request("POST", self.base_path, sprint_data)
    
    async def update(self, sprint_id: int, sprint_data: Dict) -> Dict:
        """Actualizar un sprint"""
        return await self.client._make_request("PUT", f"{self.base_path}/{sprint_id}", sprint_data)
    
    async def delete(self, sprint_id: int) -> Dict:
        """Eliminar un sprint"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"Deleting sprint {sprint_id}")
            result = await self.client._make_request("DELETE", f"{self.base_path}/{sprint_id}")
            logger.info(f"Delete API response: {result} (type: {type(result)})")
            
            # Handle different response types
            if isinstance(result, dict):
                if result.get('success') == True and not result.get('error'):
                    logger.info(f"Sprint {sprint_id} deleted successfully")
                    return {"success": True, "deleted": True}
                elif result.get('error'):
                    logger.error(f"Failed to delete sprint {sprint_id}: {result.get('error')}")
                    return result
                else:
                    logger.info(f"Sprint {sprint_id} deleted successfully")
                    return {"success": True, "deleted": True}
            else:
                # Handle unexpected response types
                logger.warning(f"Unexpected response type {type(result)}: {result}")
                return {"success": True, "deleted": True}
                
        except Exception as e:
            logger.error(f"Error deleting sprint {sprint_id}: {e}")
            return {"error": str(e), "success": False}

class TaskService:
    """Servicio para manejo de tareas"""
    
    def __init__(self, client: APIClient):
        self.client = client
        self.base_path = "/tasklist"
    
    async def get_all(self, project_id: Optional[int] = None, sprint_id: Optional[int] = None) -> List[Dict]:
        """Obtener todas las tareas"""
        endpoint = self.base_path
        params = []
        
        if project_id:
            params.append(f"project_id={project_id}")
        if sprint_id:
            params.append(f"sprint_id={sprint_id}")
        
        if params:
            endpoint += "?" + "&".join(params)
        
        result = await self.client._make_request("GET", endpoint)
        return result if isinstance(result, list) else []
    
    async def get_by_id(self, task_id: int) -> Optional[Dict]:
        """Obtener tarea por ID"""
        tasks = await self.get_all()
        return next((task for task in tasks if task.get('id') == task_id), None)
    
    async def create(self, task_data: Dict) -> Dict:
        """Crear una nueva tarea"""
        return await self.client._make_request("POST", self.base_path, task_data)
    
    async def update(self, task_id: int, task_data: Dict) -> Dict:
        """Actualizar una tarea"""
        return await self.client._make_request("PUT", f"{self.base_path}/{task_id}", task_data)
    
    async def delete(self, task_id: int) -> Dict:
        """Eliminar una tarea"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"Deleting task {task_id}")
            result = await self.client._make_request("DELETE", f"{self.base_path}/{task_id}")
            logger.info(f"Delete API response: {result} (type: {type(result)})")
            
            # Handle different response types
            if isinstance(result, dict):
                if result.get('success') == True and not result.get('error'):
                    logger.info(f"Task {task_id} deleted successfully")
                    return {"success": True, "deleted": True}
                elif result.get('error'):
                    logger.error(f"Failed to delete task {task_id}: {result.get('error')}")
                    return result
                else:
                    logger.info(f"Task {task_id} deleted successfully")
                    return {"success": True, "deleted": True}
            else:
                # Handle unexpected response types
                logger.warning(f"Unexpected response type {type(result)}: {result}")
                return {"success": True, "deleted": True}
                
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            return {"error": str(e), "success": False}
    
    async def assign_to_user(self, task_id: int, user_id: int) -> Dict:
        """Asignar tarea a un usuario"""
        assignment_data = {
            "task_id": task_id,
            "user_id": user_id
        }
        return await self.client._make_request("POST", "/asignee", assignment_data)

class ProjectMemberService:
    """Servicio para manejo de miembros de proyectos"""
    
    def __init__(self, client: APIClient):
        self.client = client
        self.base_path = "/projectmember"
    
    async def get_all(self) -> List[Dict]:
        """Obtener todos los miembros de proyectos"""
        result = await self.client._make_request("GET", self.base_path)
        return result if isinstance(result, list) else []
    
    async def get_by_project(self, project_id: int) -> List[Dict]:
        """Obtener miembros de un proyecto específico"""
        result = await self.client._make_request("GET", f"{self.base_path}/project/{project_id}")
        return result if isinstance(result, list) else []
    
    async def get_by_user(self, user_id: int) -> List[Dict]:
        """Obtener proyectos de un usuario específico"""
        result = await self.client._make_request("GET", f"{self.base_path}/user/{user_id}")
        return result if isinstance(result, list) else []
    
    async def assign_user(self, project_id: int, user_id: int, role: str = "member") -> Dict:
        """Asignar un usuario a un proyecto"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            assignment_data = {
                "project_id": project_id,
                "user_id": user_id,
                "role": role
            }
            
            logger.info(f"Assigning user {user_id} to project {project_id} as {role}")
            result = await self.client._make_request("POST", self.base_path, assignment_data)
            logger.info(f"Assignment API response: {result} (type: {type(result)})")
            
            if isinstance(result, dict):
                if result.get('success') == True and not result.get('error'):
                    logger.info(f"User {user_id} assigned to project {project_id} successfully")
                    return {"success": True, "assigned": True}
                elif result.get('error'):
                    logger.error(f"Failed to assign user {user_id} to project {project_id}: {result.get('error')}")
                    return result
                else:
                    logger.info(f"User {user_id} assigned to project {project_id} successfully")
                    return {"success": True, "assigned": True}
            else:
                logger.warning(f"Unexpected response type {type(result)}: {result}")
                return {"success": True, "assigned": True}
                
        except Exception as e:
            logger.error(f"Error assigning user {user_id} to project {project_id}: {e}")
            return {"error": str(e), "success": False}
    
    async def remove_user(self, project_id: int, user_id: int) -> Dict:
        """Remover un usuario de un proyecto"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"Removing user {user_id} from project {project_id}")
            result = await self.client._make_request("DELETE", f"{self.base_path}/{project_id}/{user_id}")
            
            if isinstance(result, dict):
                if result.get('success') == True and not result.get('error'):
                    return {"success": True, "removed": True}
                else:
                    return result
            else:
                return {"success": True, "removed": True}
                
        except Exception as e:
            logger.error(f"Error removing user {user_id} from project {project_id}: {e}")
            return {"error": str(e), "success": False}

class APIManager:
    """Manager principal que agrupa todos los servicios"""
    
    def __init__(self, base_url: str):
        from .client import APIClient
        self.client = APIClient(base_url)
        self.users = UserService(self.client)
        self.projects = ProjectService(self.client)
        self.sprints = SprintService(self.client)
        self.tasks = TaskService(self.client)
        self.project_members = ProjectMemberService(self.client)
        self._authenticated = False
    
    async def initialize(self, username: str = None, password: str = None) -> bool:
        """Inicializar y autenticar el cliente"""
        if not username or not password:
            raise ValueError("Username and password are required for authentication")
        
        # No default credentials anymore - must be provided explicitly
        
        try:
            success = await self.client.authenticate(username, password)
            if success:
                self._authenticated = True
                health = await self.client.health_check()
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Authentication: {success}, Health: {health}")
                return health
            return False
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error initializing API Manager: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self._authenticated = False
            return False
    
    async def close(self):
        """Cerrar todas las conexiones"""
        await self.client.close()
    
    @property
    def authenticated(self) -> bool:
        """Verificar si está autenticado"""
        return self._authenticated
    
    async def health_check(self) -> bool:
        """Verificar salud de la conexión"""
        return await self.client.health_check()