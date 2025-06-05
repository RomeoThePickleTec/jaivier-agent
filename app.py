import logging
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import google.generativeai as genai
import re

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuración
TELEGRAM_BOT_TOKEN = "8054295560:AAGGaiqV7Un5TM_2yemt1XrFnvTrbzDnYKE"
GEMINI_API_KEY = "TU_GEMINI_API_KEY"  # Reemplaza con tu API key
API_BASE_URL = "http://220.158.78.114:8081"

# Credenciales por defecto
DEFAULT_USERNAME = "djeison"
DEFAULT_PASSWORD = "Hello123"

# Configurar Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

class JaivierAPIClient:
    """Cliente para interactuar con la API de Jaivier con autenticación"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None
        self.access_token = None
        self.refresh_token = None
        self.headers = {
            'Content-Type': 'application/json'
        }
        
    async def _ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        if self.session:
            await self.session.close()
    
    async def login(self, username: str = DEFAULT_USERNAME, password: str = DEFAULT_PASSWORD) -> bool:
        """Realizar login y obtener tokens de acceso"""
        await self._ensure_session()
        
        login_data = {
            "username": username,
            "password": password
        }
        
        try:
            logger.info(f"Intentando login con usuario: {username}")
            url = f"{self.base_url}/auth/login"
            
            async with self.session.post(url, json=login_data) as response:
                logger.info(f"Login response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    
                    self.access_token = data.get('accessToken') or data.get('access_token')
                    self.refresh_token = data.get('refreshToken') or data.get('refresh_token')
                    
                    if self.access_token:
                        # Actualizar headers con el token
                        self.headers['Authorization'] = f'Bearer {self.access_token}'
                        logger.info(f"Login exitoso. Token: {self.access_token[:20]}...")
                        return True
                    else:
                        logger.error("Token no encontrado en la respuesta de login")
                        logger.error(f"Respuesta completa: {data}")
                        return False
                else:
                    error_text = await response.text()
                    logger.error(f"Error en login {response.status}: {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Excepción durante login: {e}")
            return False
    
    async def refresh_access_token(self) -> bool:
        """Refrescar el token de acceso usando el refresh token"""
        if not self.refresh_token:
            logger.warning("No hay refresh token disponible")
            return False
        
        await self._ensure_session()
        
        try:
            url = f"{self.base_url}/auth/refresh"
            
            # El refresh token puede enviarse como string o en un objeto
            async with self.session.post(url, json=self.refresh_token) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    new_access_token = data.get('accessToken') or data.get('access_token')
                    if new_access_token:
                        self.access_token = new_access_token
                        self.headers['Authorization'] = f'Bearer {self.access_token}'
                        logger.info("Token refrescado exitosamente")
                        return True
                else:
                    logger.error(f"Error refrescando token: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error refrescando token: {e}")
            return False
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None, retry_auth: bool = True):
        """Realizar petición HTTP con manejo de autenticación automático"""
        await self._ensure_session()
        
        # Si no tenemos token, intentar login
        if not self.access_token:
            logger.info("No hay token de acceso, intentando login...")
            if not await self.login():
                return {"error": "No se pudo autenticar con la API"}
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.info(f"Haciendo petición: {method} {url}")
            logger.debug(f"Headers: {self.headers}")
            if data:
                logger.debug(f"Data: {data}")
            
            async with self.session.request(method, url, json=data, headers=self.headers) as response:
                logger.info(f"Respuesta: {response.status}")
                
                # Si hay error 401 (Unauthorized), intentar refrescar token
                if response.status == 401 and retry_auth:
                    logger.warning("Token expirado, intentando refrescar...")
                    
                    if await self.refresh_access_token():
                        # Reintentar la petición original
                        logger.info("Reintentando petición con token refrescado...")
                        return await self._make_request(method, endpoint, data, retry_auth=False)
                    else:
                        # Si falla el refresh, intentar login completo
                        logger.warning("Refresh falló, intentando login completo...")
                        if await self.login():
                            return await self._make_request(method, endpoint, data, retry_auth=False)
                        else:
                            return {"error": "No se pudo renovar la autenticación"}
                
                if response.status == 200 or response.status == 201:
                    try:
                        content_type = response.headers.get('content-type', '')
                        if 'application/json' in content_type:
                            result = await response.json()
                            logger.debug(f"Respuesta JSON: {type(result)} - {result}")
                            return result  # Devolver directamente, puede ser lista o dict
                        else:
                            # Respuesta vacía o no JSON
                            logger.info("Respuesta exitosa sin contenido JSON")
                            return {"success": True}
                    except Exception as json_error:
                        logger.warning(f"Error parseando JSON: {json_error}")
                        return {"success": True}
                        
                elif response.status == 204:
                    # No content - operación exitosa
                    return {"success": True}
                    
                else:
                    error_text = await response.text()
                    logger.error(f"API Error {response.status}: {error_text}")
                    return {"error": f"API Error {response.status}: {error_text}"}
                    
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return {"error": str(e)}
    
    # Métodos para usuarios
    async def get_users(self) -> List[Dict]:
        result = await self._make_request("GET", "/userlist")
        return result if isinstance(result, list) else []
    
    async def create_user(self, user_data: Dict) -> Dict:
        return await self._make_request("POST", "/userlist", user_data)
    
    # Métodos para proyectos
    async def get_projects(self) -> List[Dict]:
        result = await self._make_request("GET", "/projectlist")
        return result if isinstance(result, list) else []
    
    async def create_project(self, project_data: Dict) -> Dict:
        return await self._make_request("POST", "/projectlist", project_data)
    
    async def get_project_by_id(self, project_id: int) -> Dict:
        return await self._make_request("GET", f"/projectlist/{project_id}")
    
    # Métodos para sprints
    async def get_sprints(self, project_id: int = None) -> List[Dict]:
        endpoint = "/sprintlist"
        if project_id:
            endpoint += f"?project_id={project_id}"
        result = await self._make_request("GET", endpoint)
        return result if isinstance(result, list) else []
    
    async def create_sprint(self, sprint_data: Dict) -> Dict:
        return await self._make_request("POST", "/sprintlist", sprint_data)
    
    # Métodos para tareas
    async def get_tasks(self, project_id: int = None, sprint_id: int = None) -> List[Dict]:
        endpoint = "/tasklist"
        params = []
        if project_id:
            params.append(f"project_id={project_id}")
        if sprint_id:
            params.append(f"sprint_id={sprint_id}")
        if params:
            endpoint += "?" + "&".join(params)
        
        result = await self._make_request("GET", endpoint)
        return result if isinstance(result, list) else []
    
    async def create_task(self, task_data: Dict) -> Dict:
        return await self._make_request("POST", "/tasklist", task_data)
    
    async def assign_task(self, task_id: int, user_id: int) -> Dict:
        return await self._make_request("POST", "/asignee", {
            "task_id": task_id,
            "user_id": user_id
        })
    
    async def health_check(self) -> bool:
        """Verificar si la API está disponible y autenticada"""
        result = await self._make_request("GET", "/userlist")
        # Verificar si hay error o si es una respuesta válida
        if isinstance(result, dict) and result.get("error"):
            return False
        return True  # Si no hay error, la conexión es buena

class AIAssistant:
    """Asistente de IA para interpretar comandos de voz"""
    
    def __init__(self):
        self.system_prompt = """
        Eres un asistente para el sistema de gestión de proyectos Jaivier (similar a Jira).
        Tu trabajo es interpretar comandos en lenguaje natural y extraer información estructurada.
        
        Tipos de operaciones disponibles:
        1. CREAR_PROYECTO - Crear un nuevo proyecto
        2. CREAR_SPRINT - Crear un nuevo sprint
        3. CREAR_TAREA - Crear una nueva tarea
        4. CREAR_USUARIO - Crear un nuevo usuario
        5. ASIGNAR_TAREA - Asignar una tarea a un usuario
        6. LISTAR_PROYECTOS - Mostrar proyectos existentes
        7. LISTAR_TAREAS - Mostrar tareas
        8. CREAR_PROYECTO_COMPLETO - Crear un proyecto con sprints y tareas
        
        Estados de tareas: 0=TODO, 1=IN_PROGRESS, 2=COMPLETED
        Prioridades: 1=BAJA, 2=MEDIA, 3=ALTA, 4=CRÍTICA
        Estados de proyectos: 0=ACTIVO, 1=COMPLETADO, 2=PAUSADO
        
        Responde SIEMPRE en formato JSON con esta estructura:
        {
            "accion": "TIPO_DE_ACCION",
            "parametros": {
                // parámetros específicos según la acción
            },
            "respuesta_usuario": "Respuesta amigable para el usuario"
        }
        """
    
    async def interpret_command(self, user_message: str, context: Dict = None) -> Dict:
        try:
            prompt = f"""
            {self.system_prompt}
            
            Comando del usuario: "{user_message}"
            
            Contexto actual: {json.dumps(context or {}, indent=2)}
            
            Interpreta el comando y responde en JSON.
            """
            
            response = model.generate_content(prompt)
            
            # Extraer JSON de la respuesta
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {
                    "accion": "ERROR",
                    "parametros": {},
                    "respuesta_usuario": "No pude entender tu comando. ¿Podrías ser más específico?"
                }
        except Exception as e:
            logger.error(f"Error in AI interpretation: {e}")
            return {
                "accion": "ERROR",
                "parametros": {},
                "respuesta_usuario": "Hubo un error procesando tu comando."
            }

class JaivierBot:
    """Bot principal de Telegram para Jaivier"""
    
    def __init__(self):
        self.api_client = JaivierAPIClient(API_BASE_URL)
        self.ai_assistant = AIAssistant()
        self.user_sessions = {}  # Para mantener contexto por usuario
        self.authenticated = False
    
    async def initialize(self):
        """Inicializar el bot y autenticarse"""
        logger.info("Iniciando autenticación con la API...")
        
        try:
            success = await self.api_client.login()
            if success:
                self.authenticated = True
                logger.info("✅ Bot autenticado exitosamente con la API")
                
                # Verificar conectividad
                health = await self.api_client.health_check()
                if health:
                    logger.info("✅ Verificación de salud exitosa")
                else:
                    logger.warning("⚠️ Problemas con la verificación de salud")
            else:
                logger.error("❌ Error autenticando el bot con la API")
                self.authenticated = False
        except Exception as e:
            logger.error(f"❌ Error durante la inicialización: {e}")
            self.authenticated = False
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        if not self.authenticated:
            await update.message.reply_text(
                "⚠️ El bot está teniendo problemas de conexión con la API. "
                "Reintentando autenticación..."
            )
            await self.initialize()
            
            if not self.authenticated:
                await update.message.reply_text(
                    "❌ No se pudo establecer conexión con la API de Jaivier. "
                    "Por favor contacta al administrador."
                )
                return
        
        welcome_message = f"""
🚀 ¡Bienvenido a Jaivier Bot!

✅ **Estado:** Conectado y autenticado
🔗 **API:** {API_BASE_URL}
👤 **Usuario:** {DEFAULT_USERNAME}

Soy tu asistente para gestionar proyectos, tareas y sprints.

**Comandos disponibles:**
• /proyectos - Ver todos los proyectos
• /usuarios - Ver todos los usuarios
• /status - Verificar estado de conexión
• /ayuda - Ver guía completa

**También puedes hablarme naturalmente:**
• "Crea un proyecto llamado Mi App"
• "Quiero hacer una tarea para revisar el código"
• "Asigna la tarea 5 a Juan"
• "Crea un proyecto completo para una app móvil con 3 sprints"

¡Empecemos! ¿Qué necesitas hacer hoy?
        """
        await update.message.reply_text(welcome_message)
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /status para verificar conexión"""
        await update.message.reply_text("🔍 Verificando estado de la conexión...")
        
        try:
            # Verificar autenticación
            health = await self.api_client.health_check()
            
            if health:
                # Obtener estadísticas básicas
                users = await self.api_client.get_users()
                projects = await self.api_client.get_projects()
                
                # Verificar tipos de respuesta
                users_count = len(users) if isinstance(users, list) else 0
                projects_count = len(projects) if isinstance(projects, list) else 0
                
                status_message = f"""
✅ **Estado: CONECTADO**

🔗 **API:** {API_BASE_URL}
👤 **Usuario:** {DEFAULT_USERNAME}
🔑 **Token:** Válido

📊 **Estadísticas:**
• 👥 Usuarios: {users_count}
• 📁 Proyectos: {projects_count}

🕐 **Último check:** {datetime.now().strftime('%H:%M:%S')}
                """
            else:
                status_message = f"""
❌ **Estado: DESCONECTADO**

🔗 **API:** {API_BASE_URL}
👤 **Usuario:** {DEFAULT_USERNAME}
🔑 **Token:** Inválido o expirado

🔄 Reintentando autenticación...
                """
                
                # Intentar reconectar
                await self.initialize()
                
                if self.authenticated:
                    status_message += "\n\n✅ **Reconexión exitosa!**"
                else:
                    status_message += "\n\n❌ **Error en reconexión**"
            
            await update.message.reply_text(status_message)
            
        except Exception as e:
            logger.error(f"Error en comando status: {e}")
            await update.message.reply_text(f"❌ Error verificando estado: {str(e)}")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /ayuda"""
        help_text = """
📚 **Guía de Jaivier Bot**

**Comandos de voz naturales:**

🏗️ **Proyectos:**
• "Crea un proyecto llamado [nombre]"
• "Nuevo proyecto para [descripción]"
• "Muestra todos los proyectos"

🏃 **Sprints:**
• "Crea un sprint para el proyecto [nombre]"
• "Nuevo sprint de 2 semanas"

📋 **Tareas:**
• "Crea una tarea para [descripción]"
• "Nueva tarea: [título] con prioridad alta"
• "Asigna la tarea [ID] a [usuario]"

👥 **Usuarios:**
• "Crea un usuario llamado [nombre]"
• "Nuevo desarrollador [nombre]"

🎯 **Proyecto Completo:**
• "Crea un proyecto completo para [descripción] con [X] sprints"
• "Genera un proyecto para una app móvil con tareas y sprints"

**Estados y Prioridades:**
• Estados: TODO, EN PROGRESO, COMPLETADO
• Prioridades: BAJA, MEDIA, ALTA, CRÍTICA

**Comandos del sistema:**
• /status - Verificar conexión con la API
• /proyectos - Listar proyectos
• /usuarios - Listar usuarios
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def list_projects(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Listar todos los proyectos"""
        if not self.authenticated:
            await update.message.reply_text("❌ Bot no autenticado. Usa /status para verificar conexión.")
            return
            
        projects = await self.api_client.get_projects()
        
        if not projects:
            await update.message.reply_text("📂 No hay proyectos disponibles.")
            return
        
        message = "📁 **Proyectos disponibles:**\n\n"
        for project in projects:
            status_emoji = "🟢" if project.get('status') == 0 else "🔴" if project.get('status') == 1 else "⏸️"
            message += f"{status_emoji} **{project.get('name', 'Sin nombre')}** (ID: {project.get('id')})\n"
            message += f"   📝 {project.get('description', 'Sin descripción')}\n\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def list_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Listar todos los usuarios"""
        if not self.authenticated:
            await update.message.reply_text("❌ Bot no autenticado. Usa /status para verificar conexión.")
            return
            
        users = await self.api_client.get_users()
        
        if not users:
            await update.message.reply_text("👥 No hay usuarios disponibles.")
            return
        
        message = "👥 **Usuarios disponibles:**\n\n"
        for user in users:
            active_emoji = "✅" if user.get('active', True) else "❌"
            message += f"{active_emoji} **{user.get('full_name', user.get('username', 'Sin nombre'))}** (ID: {user.get('id')})\n"
            message += f"   📧 {user.get('email', 'Sin email')}\n"
            message += f"   👤 {user.get('username', 'Sin username')}\n\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar mensajes de texto naturales"""
        if not self.authenticated:
            await update.message.reply_text(
                "❌ Bot no autenticado. Usa /status para verificar conexión."
            )
            return
            
        user_id = update.effective_user.id
        user_message = update.message.text
        
        try:
            # Obtener contexto del usuario
            if user_id not in self.user_sessions:
                users_data = await self.api_client.get_users()
                projects_data = await self.api_client.get_projects()
                
                self.user_sessions[user_id] = {
                    "last_projects": projects_data if isinstance(projects_data, list) else [],
                    "last_users": users_data if isinstance(users_data, list) else []
                }
            
            context_data = self.user_sessions[user_id]
            
            # Mostrar que estamos procesando
            await update.message.reply_text("🤔 Procesando tu solicitud...")
            
            # Interpretar comando con IA
            ai_response = await self.ai_assistant.interpret_command(user_message, context_data)
            
            # Ejecutar acción
            await self.execute_action(ai_response, update, context)
            
            # Actualizar contexto
            users_data = await self.api_client.get_users()
            projects_data = await self.api_client.get_projects()
            
            self.user_sessions[user_id]["last_projects"] = projects_data if isinstance(projects_data, list) else []
            self.user_sessions[user_id]["last_users"] = users_data if isinstance(users_data, list) else []
            
        except Exception as e:
            logger.error(f"Error en handle_message: {e}")
            await update.message.reply_text(f"❌ Error procesando mensaje: {str(e)}")
    
    async def execute_action(self, ai_response: Dict, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ejecutar la acción interpretada por la IA"""
        accion = ai_response.get("accion")
        parametros = ai_response.get("parametros", {})
        respuesta_usuario = ai_response.get("respuesta_usuario", "")
        
        try:
            if accion == "CREAR_PROYECTO":
                result = await self.create_project(parametros)
                if result.get("error"):
                    await update.message.reply_text(f"❌ Error creando proyecto: {result['error']}")
                else:
                    await update.message.reply_text(f"✅ {respuesta_usuario}\n\n📁 Proyecto creado: **{parametros.get('name')}**")
            
            elif accion == "CREAR_SPRINT":
                result = await self.create_sprint(parametros)
                if result.get("error"):
                    await update.message.reply_text(f"❌ Error creando sprint: {result['error']}")
                else:
                    await update.message.reply_text(f"✅ {respuesta_usuario}\n\n🏃 Sprint creado: **{parametros.get('name')}**")
            
            elif accion == "CREAR_TAREA":
                result = await self.create_task(parametros)
                if result.get("error"):
                    await update.message.reply_text(f"❌ Error creando tarea: {result['error']}")
                else:
                    await update.message.reply_text(f"✅ {respuesta_usuario}\n\n📋 Tarea creada: **{parametros.get('title')}**")
            
            elif accion == "CREAR_USUARIO":
                result = await self.create_user(parametros)
                if result.get("error"):
                    await update.message.reply_text(f"❌ Error creando usuario: {result['error']}")
                else:
                    await update.message.reply_text(f"✅ {respuesta_usuario}\n\n👤 Usuario creado: **{parametros.get('full_name')}**")
            
            elif accion == "ASIGNAR_TAREA":
                result = await self.assign_task(parametros)
                if result.get("error"):
                    await update.message.reply_text(f"❌ Error asignando tarea: {result['error']}")
                else:
                    await update.message.reply_text(f"✅ {respuesta_usuario}")
            
            elif accion == "LISTAR_PROYECTOS":
                await self.list_projects(update, context)
            
            elif accion == "LISTAR_TAREAS":
                await self.list_tasks(update, context, parametros)
            
            elif accion == "CREAR_PROYECTO_COMPLETO":
                await self.create_complete_project(parametros, update)
            
            else:
                await update.message.reply_text(respuesta_usuario)
                
        except Exception as e:
            logger.error(f"Error executing action {accion}: {e}")
            await update.message.reply_text(f"❌ Error ejecutando la acción: {str(e)}")
    
    async def create_project(self, parametros: Dict) -> Dict:
        """Crear un nuevo proyecto"""
        project_data = {
            "name": parametros.get("name", "Nuevo Proyecto"),
            "description": parametros.get("description", ""),
            "start_date": parametros.get("start_date", datetime.now().isoformat()),
            "end_date": parametros.get("end_date", (datetime.now() + timedelta(days=30)).isoformat()),
            "status": parametros.get("status", 0)  # ACTIVO por defecto
        }
        
        return await self.api_client.create_project(project_data)
    
    async def create_sprint(self, parametros: Dict) -> Dict:
        """Crear un nuevo sprint"""
        sprint_data = {
            "name": parametros.get("name", "Nuevo Sprint"),
            "description": parametros.get("description", ""),
            "start_date": parametros.get("start_date", datetime.now().isoformat()),
            "end_date": parametros.get("end_date", (datetime.now() + timedelta(days=14)).isoformat()),
            "project_id": parametros.get("project_id"),
            "status": parametros.get("status", 0)
        }
        
        return await self.api_client.create_sprint(sprint_data)
    
    async def create_task(self, parametros: Dict) -> Dict:
        """Crear una nueva tarea"""
        task_data = {
            "title": parametros.get("title", "Nueva Tarea"),
            "description": parametros.get("description", ""),
            "due_date": parametros.get("due_date", (datetime.now() + timedelta(days=7)).isoformat()),
            "priority": parametros.get("priority", 2),  # MEDIA por defecto
            "status": parametros.get("status", 0),  # TODO por defecto
            "estimated_hours": parametros.get("estimated_hours", 8),
            "project_id": parametros.get("project_id"),
            "sprint_id": parametros.get("sprint_id"),
            "subtasks": parametros.get("subtasks", [])
        }
        
        return await self.api_client.create_task(task_data)
    
    async def create_user(self, parametros: Dict) -> Dict:
        """Crear un nuevo usuario"""
        user_data = {
            "username": parametros.get("username", f"user_{int(datetime.now().timestamp())}"),
            "email": parametros.get("email", f"user_{int(datetime.now().timestamp())}@example.com"),
            "full_name": parametros.get("full_name", "Nuevo Usuario"),
            "role": parametros.get("role", 1),  # DEVELOPER por defecto
            "work_mode": parametros.get("work_mode", "REMOTE"),
            "active": True
        }
        
        return await self.api_client.create_user(user_data)
    
    async def assign_task(self, parametros: Dict) -> Dict:
        """Asignar una tarea a un usuario"""
        task_id = parametros.get("task_id")
        user_id = parametros.get("user_id")
        
        if not task_id or not user_id:
            return {"error": "Faltan task_id o user_id"}
        
        return await self.api_client.assign_task(task_id, user_id)
    
    async def list_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE, parametros: Dict):
        """Listar tareas con filtros opcionales"""
        tasks = await self.api_client.get_tasks(
            project_id=parametros.get("project_id"),
            sprint_id=parametros.get("sprint_id")
        )
        
        if not tasks:
            await update.message.reply_text("📋 No hay tareas disponibles.")
            return
        
        message = "📋 **Tareas disponibles:**\n\n"
        for task in tasks:
            priority_emoji = "🔴" if task.get('priority') == 4 else "🟡" if task.get('priority') == 3 else "🟢"
            status_emoji = "⏳" if task.get('status') == 1 else "✅" if task.get('status') == 2 else "📝"
            
            message += f"{status_emoji} {priority_emoji} **{task.get('title', 'Sin título')}** (ID: {task.get('id')})\n"
            message += f"   📝 {task.get('description', 'Sin descripción')[:50]}...\n\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def create_complete_project(self, parametros: Dict, update: Update):
        """Crear un proyecto completo con sprints y tareas"""
        await update.message.reply_text("🚀 Creando proyecto completo...")
        
        # 1. Crear el proyecto
        project_result = await self.create_project(parametros)
        if project_result.get("error"):
            await update.message.reply_text(f"❌ Error creando proyecto: {project_result['error']}")
            return
        
        project_id = project_result.get("id")
        await update.message.reply_text(f"✅ Proyecto creado: **{parametros.get('name')}**")
        
        # 2. Crear sprints
        num_sprints = parametros.get("num_sprints", 3)
        sprint_ids = []
        
        for i in range(num_sprints):
            sprint_data = {
                "name": f"Sprint {i+1}",
                "description": f"Sprint {i+1} del proyecto {parametros.get('name')}",
                "project_id": project_id,
                "start_date": (datetime.now() + timedelta(days=i*14)).isoformat(),
                "end_date": (datetime.now() + timedelta(days=(i+1)*14)).isoformat()
            }
            
            sprint_result = await self.create_sprint(sprint_data)
            if not sprint_result.get("error"):
                sprint_ids.append(sprint_result.get("id"))
                await update.message.reply_text(f"🏃 Sprint {i+1} creado")
        
        # 3. Crear tareas distribuidas en los sprints
        tasks_per_sprint = parametros.get("tasks_per_sprint", 5)
        all_users = await self.api_client.get_users()
        
        task_templates = [
            "Análisis de requerimientos",
            "Diseño de la arquitectura",
            "Implementación del backend",
            "Desarrollo del frontend",
            "Pruebas unitarias",
            "Integración de APIs",
            "Revisión de código",
            "Documentación",
            "Testing de QA",
            "Deploy y configuración"
        ]
        
        for sprint_idx, sprint_id in enumerate(sprint_ids):
            for task_idx in range(tasks_per_sprint):
                if task_idx < len(task_templates):
                    task_title = f"{task_templates[task_idx]} - Sprint {sprint_idx + 1}"
                else:
                    task_title = f"Tarea {task_idx + 1} - Sprint {sprint_idx + 1}"
                
                task_data = {
                    "title": task_title,
                    "description": f"Descripción de {task_title}",
                    "project_id": project_id,
                    "sprint_id": sprint_id,
                    "priority": (task_idx % 4) + 1,  # Rotar prioridades
                    "estimated_hours": 8
                }
                
                task_result = await self.create_task(task_data)
                
                # Asignar a un usuario aleatorio si hay usuarios disponibles
                if not task_result.get("error") and all_users:
                    user = all_users[task_idx % len(all_users)]
                    await self.api_client.assign_task(task_result.get("id"), user.get("id"))
        
        await update.message.reply_text(f"""
🎉 **¡Proyecto completo creado exitosamente!**

📁 **Proyecto:** {parametros.get('name')}
🏃 **Sprints:** {len(sprint_ids)} sprints de 2 semanas
📋 **Tareas:** {len(sprint_ids) * tasks_per_sprint} tareas distribuidas
👥 **Asignaciones:** Tareas asignadas automáticamente

¡Tu proyecto está listo para empezar a trabajar!
        """)
    
    async def cleanup(self):
        """Limpiar recursos"""
        await self.api_client.close()

# Función principal
def main():
    """Función principal del bot"""
    
    async def init_and_run():
        """Inicializar bot y ejecutar"""
        bot = JaivierBot()
        
        # Inicializar autenticación
        print("🔐 Autenticando con la API de Jaivier...")
        await bot.initialize()
        
        if not bot.authenticated:
            print("❌ Error: No se pudo autenticar con la API")
            print(f"   Verifica que la API esté ejecutándose en: {API_BASE_URL}")
            print(f"   Y que las credenciales sean correctas: {DEFAULT_USERNAME}")
            return
        
        print("✅ Autenticación exitosa!")
        
        # Crear aplicación
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Agregar manejadores
        app.add_handler(CommandHandler("start", bot.start))
        app.add_handler(CommandHandler("ayuda", bot.help_command))
        app.add_handler(CommandHandler("help", bot.help_command))
        app.add_handler(CommandHandler("status", bot.status))
        app.add_handler(CommandHandler("proyectos", bot.list_projects))
        app.add_handler(CommandHandler("usuarios", bot.list_users))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
        
        # Manejar cleanup al cerrar
        async def cleanup_on_shutdown(application):
            print("🧹 Cerrando conexiones...")
            await bot.cleanup()
        
        app.post_shutdown = cleanup_on_shutdown
        
        print("🤖 Jaivier Bot iniciado y listo para recibir comandos!")
        print(f"🔗 API: {API_BASE_URL}")
        print(f"👤 Usuario: {DEFAULT_USERNAME}")
        print("📱 Busca @Jaivier21Bot en Telegram")
        print("Presiona Ctrl+C para detener el bot")
        
        # Ejecutar bot
        app.run_polling()
    
    # Ejecutar función async
    try:
        asyncio.run(init_and_run())
    except KeyboardInterrupt:
        print("\n👋 Bot detenido por el usuario")
    except Exception as e:
        print(f"❌ Error ejecutando el bot: {e}")

if __name__ == '__main__':
    main()