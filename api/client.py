# api/client.py - COMPLETE FIXED VERSION
"""Cliente API para Jaivier"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class APIClient:
    """Cliente API principal"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = None
        self.access_token = None
        self.authenticated = False
        
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        headers = {'Content-Type': 'application/json'}
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        return headers
    
    async def _make_request(self, method: str, path: str, data: Optional[Dict] = None, params: Optional[Dict] = None):
        url = f"{self.base_url}{path}"
        session = await self._get_session()
        headers = self._get_headers()
        
        request_id = f"{method}_{int(datetime.now().timestamp())}"
        logger.info(f"[{request_id}] {method} {url}")
        
        try:
            async with session.request(method=method, url=url, json=data, params=params, headers=headers) as response:
                logger.info(f"[{request_id}] Response: {response.status}")
                
                if response.status == 200:
                    try:
                        return await response.json()
                    except:
                        return {"success": True, "data": await response.text()}
                
                elif response.status == 201:
                    try:
                        return await response.json()
                    except:
                        return {"success": True, "created": True}
                
                elif response.status == 204:
                    return {"success": True}
                
                elif response.status in [400, 401, 404, 500]:
                    try:
                        error_data = await response.json()
                        return {"error": error_data.get('error', f'HTTP {response.status}'), "status": response.status}
                    except:
                        return {"error": f"HTTP {response.status}", "status": response.status}
                
                else:
                    return {"error": f"HTTP {response.status}", "status": response.status}
                    
        except asyncio.TimeoutError:
            return {"error": "Request timeout", "timeout": True}
        except Exception as e:
            return {"error": str(e), "request_failed": True}
    
    async def authenticate(self, username: str, password: str) -> bool:
        auth_data = {"username": username, "password": password}
        result = await self._make_request('POST', '/auth/login', auth_data)
        
        if result.get('error'):
            logger.error(f"Auth error: {result['error']}")
            return False
        
        access_token = result.get('accessToken') or result.get('access_token') or result.get('token')
        
        if access_token:
            self.access_token = access_token
            self.authenticated = True
            logger.info("✅ Authentication successful")
            return True
        else:
            logger.error("❌ No access token received")
            return False
    
    async def health_check(self) -> bool:
        try:
            result = await self._make_request('GET', '/userlist')
            return not result.get('error')
        except:
            return False


class ProjectsAPI:
    def __init__(self, client: APIClient):
        self.client = client
        self.base_path = "/projectlist"
    
    async def get_all(self) -> List[Dict]:
        result = await self.client._make_request('GET', self.base_path)
        
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            if result.get('error'):
                logger.error(f"Error getting projects: {result['error']}")
                return []
            return result.get('data', [])
        else:
            return []
    
    async def create(self, project_data: Dict) -> Optional[Dict]:
        return await self.client._make_request('POST', self.base_path, project_data)


class SprintsAPI:
    def __init__(self, client: APIClient):
        self.client = client
        self.base_path = "/sprintlist"
    
    async def get_all(self, project_id: Optional[int] = None) -> List[Dict]:
        params = {'project_id': project_id} if project_id else {}
        result = await self.client._make_request('GET', self.base_path, params=params)
        
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            if result.get('error'):
                return []
            return result.get('data', [])
        else:
            return []
    
    async def create(self, sprint_data: Dict) -> Optional[Dict]:
        return await self.client._make_request('POST', self.base_path, sprint_data)


class TasksAPI:
    def __init__(self, client: APIClient):
        self.client = client
        self.base_path = "/tasklist"
    
    async def get_all(self, project_id: Optional[int] = None, sprint_id: Optional[int] = None) -> List[Dict]:
        params = {}
        if project_id:
            params['project_id'] = project_id
        if sprint_id:
            params['sprint_id'] = sprint_id
        
        result = await self.client._make_request('GET', self.base_path, params=params)
        
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            if result.get('error'):
                return []
            return result.get('data', [])
        else:
            return []
    
    async def create(self, task_data: Dict) -> Optional[Dict]:
        return await self.client._make_request('POST', self.base_path, task_data)


class UsersAPI:
    def __init__(self, client: APIClient):
        self.client = client
        self.base_path = "/userlist"
    
    async def get_all(self) -> List[Dict]:
        result = await self.client._make_request('GET', self.base_path)
        
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            if result.get('error'):
                logger.error(f"Error getting users: {result['error']}")
                return []
            return result.get('data', [])
        else:
            return []
    
    async def create(self, user_data: Dict) -> Optional[Dict]:
        return await self.client._make_request('POST', self.base_path, user_data)


class APIManager:
    def __init__(self, base_url: str):
        self.client = APIClient(base_url)
        self.projects = ProjectsAPI(self.client)
        self.sprints = SprintsAPI(self.client)
        self.tasks = TasksAPI(self.client)
        self.users = UsersAPI(self.client)
        self.authenticated = False
    
    async def initialize(self, username: str = None, password: str = None) -> bool:
        from config.settings import DEFAULT_USERNAME, DEFAULT_PASSWORD
        
        username = username or DEFAULT_USERNAME
        password = password or DEFAULT_PASSWORD
        
        try:
            success = await self.client.authenticate(username, password)
            self.authenticated = success
            return success
        except Exception as e:
            logger.error(f"Error initializing API Manager: {e}")
            self.authenticated = False
            return False
    
    async def health_check(self) -> bool:
        return await self.client.health_check()
    
    async def close(self):
        await self.client.close()