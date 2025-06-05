# ai/assistant.py
"""Asistente de IA para interpretar comandos de voz"""

import json
import re
import logging
from typing import Dict, Optional, List
import google.generativeai as genai
from config.settings import GEMINI_API_KEY, TaskStatus, TaskPriority, ProjectStatus

logger = logging.getLogger(__name__)

# Configurar Gemini
if GEMINI_API_KEY and GEMINI_API_KEY != "TU_GEMINI_API_KEY":
    genai.configure(api_key=GEMINI_API_KEY)

class AIAssistant:
    """Asistente de IA para interpretar comandos de voz"""
    
    def __init__(self):
        self.model = None
        self.system_prompt = self._build_system_prompt()
        self._initialize_model()
    
    def _initialize_model(self):
        """Inicializar el modelo de IA"""
        if not GEMINI_API_KEY or GEMINI_API_KEY == "TU_GEMINI_API_KEY":
            logger.warning("⚠️ API Key de Gemini no configurada. Usando fallback simple.")
            self.model = None
            return
        
        try:
            # Probar diferentes nombres de modelo
            model_names = [
                'gemini-1.5-flash',  # Modelo más reciente
                'gemini-1.5-pro',
                'gemini-pro-latest',
                'gemini-1.0-pro'
            ]
            
            for model_name in model_names:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    logger.info(f"✅ Modelo {model_name} inicializado correctamente")
                    break
                except Exception as e:
                    logger.debug(f"Modelo {model_name} no disponible: {e}")
                    continue
            
            if not self.model:
                logger.error("❌ No se pudo inicializar ningún modelo de Gemini")
                
        except Exception as e:
            logger.error(f"❌ Error configurando Gemini: {e}")
            self.model = None
    
    def _build_system_prompt(self) -> str:
        """Construir el prompt del sistema"""
        return f"""
        Eres un asistente para el sistema de gestión de proyectos Jaivier (similar a Jira).
        Tu trabajo es interpretar comandos en lenguaje natural y extraer información estructurada.
        
        Tipos de operaciones disponibles:
        1. CREAR_PROYECTO - Crear un nuevo proyecto
        2. CREAR_SPRINT - Crear un nuevo sprint
        3. CREAR_TAREA - Crear una nueva tarea
        4. CREAR_USUARIO - Crear un nuevo usuario
        5. ASIGNAR_TAREA - Asignar una tarea a un usuario
        6. LISTAR_PROYECTOS - Mostrar proyectos existentes
        7. LISTAR_USUARIOS - Mostrar usuarios existentes
        8. LISTAR_TAREAS - Mostrar tareas
        9. CREAR_PROYECTO_COMPLETO - Crear un proyecto con sprints y tareas
        10. OBTENER_ESTADISTICAS - Mostrar estadísticas del sistema
        
        Estados de tareas: {TaskStatus.TODO}=TODO, {TaskStatus.IN_PROGRESS}=IN_PROGRESS, {TaskStatus.COMPLETED}=COMPLETED
        Prioridades: {TaskPriority.LOW}=BAJA, {TaskPriority.MEDIUM}=MEDIA, {TaskPriority.HIGH}=ALTA, {TaskPriority.CRITICAL}=CRÍTICA
        Estados de proyectos: {ProjectStatus.ACTIVE}=ACTIVO, {ProjectStatus.COMPLETED}=COMPLETADO, {ProjectStatus.PAUSED}=PAUSADO
        
        Para CREAR_PROYECTO_COMPLETO, incluye:
        - num_sprints: número de sprints (default: 3)
        - tasks_per_sprint: tareas por sprint (default: 5)
        
        Responde SIEMPRE en formato JSON con esta estructura:
        {{
            "accion": "TIPO_DE_ACCION",
            "parametros": {{
                // parámetros específicos según la acción
            }},
            "respuesta_usuario": "Respuesta amigable para el usuario"
        }}
        
        Ejemplos de interpretación:
        - "Crea un proyecto llamado Mi App" → CREAR_PROYECTO con name="Mi App"
        - "Nueva tarea para revisar código" → CREAR_TAREA con title="Revisar código"
        - "Asigna la tarea 5 a Juan" → ASIGNAR_TAREA con task_id=5, buscar user por nombre "Juan"
        - "Muestra todos los proyectos" → LISTAR_PROYECTOS
        - "Crea un proyecto completo para app móvil con 4 sprints" → CREAR_PROYECTO_COMPLETO
        """
    
    async def interpret_command(self, user_message: str, context: Optional[Dict] = None) -> Dict:
        """Interpretar comando del usuario con contexto mejorado"""
        try:
            # Si no hay modelo de IA, usar fallback simple
            if not self.model:
                return self._simple_fallback_interpretation(user_message, context)
            
            # Preparar contexto mejorado para la IA
            context_summary = ""
            if context:
                if context.get("current_project"):
                    context_summary += f"Proyecto actual: {context['current_project']['name']} (ID: {context['current_project']['id']})\n"
                if context.get("current_sprint"):
                    context_summary += f"Sprint actual: {context['current_sprint']['name']} (ID: {context['current_sprint']['id']})\n"
                if context.get("conversation_history"):
                    recent_history = context["conversation_history"][-3:]
                    context_summary += "Mensajes recientes:\n"
                    for msg in recent_history:
                        context_summary += f"- Usuario: {msg['user_message']}\n"
                        if msg.get('action_taken'):
                            context_summary += f"  Acción: {msg['action_taken']}\n"
            
            prompt = f"""
            {self.system_prompt}
            
            Comando del usuario: "{user_message}"
            
            Contexto de conversación:
            {context_summary}
            
            Proyectos disponibles: {json.dumps(context.get('last_projects', [])[:5] if context else [], indent=2)}
            Usuarios disponibles: {json.dumps(context.get('last_users', [])[:5] if context else [], indent=2)}
            
            IMPORTANTE: Si el usuario menciona múltiples ítems (separados por comas, "y", bullets, etc.), 
            incluye TODOS en el array correspondiente:
            - Para tareas múltiples: "parametros": {{"titles": ["tarea1", "tarea2", "tarea3"]}}
            - Para sprints múltiples: "parametros": {{"names": ["sprint1", "sprint2"]}}
            
            Si hay un proyecto/sprint actual en el contexto, úsalo automáticamente.
            
            Interpreta el comando y responde en JSON válido.
            """
            
            response = self.model.generate_content(prompt)
            
            # Extraer JSON de la respuesta
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                try:
                    parsed_response = json.loads(json_match.group())
                    
                    if not all(key in parsed_response for key in ["accion", "parametros", "respuesta_usuario"]):
                        raise ValueError("Estructura JSON incompleta")
                    
                    # Post-procesar con contexto
                    parsed_response = self._post_process_response(parsed_response, context)
                    
                    return parsed_response
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Error parseando JSON de IA: {e}")
                    return self._simple_fallback_interpretation(user_message, context)
                    
            else:
                logger.warning("No se encontró JSON válido en respuesta de IA")
                return self._simple_fallback_interpretation(user_message, context)
                
        except Exception as e:
            logger.error(f"Error en interpretación de IA: {e}")
            return self._simple_fallback_interpretation(user_message, context)
    
    def _simple_fallback_interpretation(self, user_message: str, context: Optional[Dict] = None) -> Dict:
        """Interpretación simple con soporte para múltiples ítems"""
        message_lower = user_message.lower()
        
        # Detectar múltiples ítems
        multiple_items = self._detect_multiple_items(user_message)
        
        # Obtener IDs del contexto
        current_project_id = context.get("current_project", {}).get("id") if context else None
        current_sprint_id = context.get("current_sprint", {}).get("id") if context else None
        
        # Patrones para múltiples tareas
        if any(word in message_lower for word in ["crear tareas", "nuevas tareas", "tareas:", "tasks:", "generame", "genera", "inventa"]):
            # Detectar cantidad específica
            import re
            numbers = re.findall(r'\b(\d+)\s*tareas?\b', message_lower)
            num_tasks = int(numbers[0]) if numbers else 1
            
            # Si se especifica cantidad pero no nombres, generar nombres automáticamente
            if num_tasks > 1 and ("genera" in message_lower or "inventa" in message_lower or "generame" in message_lower):
                logger.info(f"[DEBUG] Generando {num_tasks} tareas automáticamente")
                # Extraer el contexto para generar nombres apropiados
                context_words = message_lower.replace("generame", "").replace("genera", "").replace("inventa", "").replace("tareas", "").replace("para", "")
                
                if "tigre" in message_lower and ("recetas" in message_lower or "especiales" in message_lower or "nombres especiales" in message_lower):
                    titles = [
                        "Receta Rugido Salvaje - Carne de venado con especias",
                        "Delicia Felina Supreme - Salmón fresco con hierbas",
                        "Banquete del Rey de la Selva - Búfalo marinado",
                        "Festín Tigre Siberiano - Carne de res premium",
                        "Manjar Rayado Especial - Pollo orgánico gourmet",
                        "Cena del Depredador - Mix de carnes exóticas"
                    ][:num_tasks]
                    logger.info(f"[DEBUG] Generadas recetas para tigre: {titles}")
                elif "tigre" in message_lower and ("comer" in message_lower or "alimentar" in message_lower):
                    titles = [
                        "Preparar la carne del tigre",
                        "Verificar la dieta nutricional",
                        "Limpiar el área de alimentación", 
                        "Supervisar el horario de comida",
                        "Revisar peso del tigre",
                        "Preparar suplementos vitamínicos"
                    ][:num_tasks]
                    logger.info(f"[DEBUG] Generadas tareas de alimentación: {titles}")
                elif "testing" in message_lower or "test" in message_lower:
                    titles = [
                        "Pruebas unitarias",
                        "Pruebas de integración", 
                        "Pruebas de sistema",
                        "Pruebas de usuario"
                    ][:num_tasks]
                    logger.info(f"[DEBUG] Generadas tareas de testing: {titles}")
                else:
                    # Títulos genéricos
                    titles = [f"Tarea {i+1}" for i in range(num_tasks)]
                    logger.info(f"[DEBUG] Generadas tareas genéricas: {titles}")
            else:
                titles = multiple_items if len(multiple_items) > 1 else [user_message.split(":")[-1].strip() if ":" in user_message else "Nueva Tarea"]
                logger.info(f"[DEBUG] Usando títulos detectados: {titles}")
            
            # Detectar sprint específico mencionado
            sprint_name = None
            if "sprint" in message_lower or "en el" in message_lower:
                import re
                # Buscar patrones como "en el sprint X" o "sprint de X"
                sprint_patterns = [
                    r'en el sprint (?:de )?([^,\.]+)',
                    r'sprint (?:de )?([^,\.]+)',
                    r'en (?:el )?([^,\.]+ sprint)',
                    r'para (?:el )?sprint ([^,\.]+)'
                ]
                
                for pattern in sprint_patterns:
                    match = re.search(pattern, message_lower)
                    if match:
                        sprint_name = match.group(1).strip()
                        break
            
            return {
                "accion": "CREAR_MULTIPLES_TAREAS",
                "parametros": {
                    "titles": titles,
                    "project_id": current_project_id,
                    "sprint_id": current_sprint_id,
                    "sprint_name": sprint_name
                },
                "respuesta_usuario": f"Creando {len(titles)} tarea(s)"
            }
        
        # Patrones para múltiples sprints  
        elif any(word in message_lower for word in ["crear sprints", "nuevos sprints", "sprints:"]):
            names = multiple_items if len(multiple_items) > 1 else [user_message.split(":")[-1].strip() if ":" in user_message else "Nuevo Sprint"]
            
            return {
                "accion": "CREAR_MULTIPLES_SPRINTS", 
                "parametros": {
                    "names": names,
                    "project_id": current_project_id
                },
                "respuesta_usuario": f"Creando {len(names)} sprint(s)"
            }
        
        # Comandos individuales (resto del código anterior)
        elif any(word in message_lower for word in ["crear proyecto", "nuevo proyecto", "proyecto llamado"]):
            name = "Nuevo Proyecto"
            if "llamado" in message_lower:
                name = user_message.split("llamado")[-1].strip()
            elif "proyecto" in message_lower:
                parts = user_message.split("proyecto")
                if len(parts) > 1:
                    name = parts[-1].strip()
            
            return {
                "accion": "CREAR_PROYECTO",
                "parametros": {
                    "name": name,
                    "description": f"Proyecto {name} creado desde el bot de Telegram"
                },
                "respuesta_usuario": f"Creando proyecto: {name}"
            }
        
        elif any(word in message_lower for word in ["crear tarea", "nueva tarea", "tarea para"]):
            title = "Nueva Tarea"
            if "para" in message_lower:
                title = user_message.split("para")[-1].strip()
            elif "tarea" in message_lower:
                parts = user_message.split("tarea")
                if len(parts) > 1:
                    title = parts[-1].strip()
            
            return {
                "accion": "CREAR_TAREA",
                "parametros": {
                    "title": title,
                    "project_id": current_project_id,
                    "sprint_id": current_sprint_id
                },
                "respuesta_usuario": f"Creando tarea: {title}"
            }
        
        elif any(word in message_lower for word in ["usar proyecto", "cambiar proyecto", "proyecto activo"]):
            project_name = user_message.split("proyecto")[-1].strip()
            return {
                "accion": "CAMBIAR_PROYECTO",
                "parametros": {"project_name": project_name},
                "respuesta_usuario": f"Cambiando a proyecto: {project_name}"
            }
        
        # Resto de patrones existentes...
        elif any(word in message_lower for word in ["crear usuario", "nuevo usuario", "usuario llamado"]):
            name = "Nuevo Usuario"
            if "llamado" in message_lower:
                name = user_message.split("llamado")[-1].strip()
            elif "usuario" in message_lower:
                parts = user_message.split("usuario")
                if len(parts) > 1:
                    name = parts[-1].strip()
            
            return {
                "accion": "CREAR_USUARIO",
                "parametros": {"full_name": name, "username": name.lower().replace(" ", "")},
                "respuesta_usuario": f"Creando usuario: {name}"
            }
        
        elif any(word in message_lower for word in ["proyecto completo", "proyecto con sprints"]):
            name = "Proyecto Completo"
            if "para" in message_lower:
                name = user_message.split("para")[-1].strip()
            
            return {
                "accion": "CREAR_PROYECTO_COMPLETO",
                "parametros": {"name": name, "num_sprints": 3, "tasks_per_sprint": 5},
                "respuesta_usuario": f"Creando proyecto completo: {name}"
            }
        
        elif any(word in message_lower for word in ["mostrar proyectos", "ver proyectos", "proyectos"]):
            return {
                "accion": "LISTAR_PROYECTOS",
                "parametros": {},
                "respuesta_usuario": "Mostrando todos los proyectos"
            }
        
        elif any(word in message_lower for word in ["mostrar usuarios", "ver usuarios", "usuarios"]):
            return {
                "accion": "LISTAR_USUARIOS",
                "parametros": {},
                "respuesta_usuario": "Mostrando todos los usuarios"
            }
        
        elif any(word in message_lower for word in ["mostrar tareas", "ver tareas", "tareas"]):
            return {
                "accion": "LISTAR_TAREAS",
                "parametros": {},
                "respuesta_usuario": "Mostrando todas las tareas"
            }
        
        elif any(word in message_lower for word in ["estadísticas", "estadisticas", "stats"]):
            return {
                "accion": "OBTENER_ESTADISTICAS",
                "parametros": {},
                "respuesta_usuario": "Mostrando estadísticas del sistema"
            }
        
        else:
            return self._error_response("No pude entender tu comando. Intenta con: 'crear proyecto', 'nueva tarea', 'mostrar proyectos', etc.")
    
    def _detect_multiple_items(self, text: str) -> List[str]:
        """Detectar múltiples ítems en el texto"""
        items = []
        
        # Separadores comunes
        separators = [',', ';', '\n', '•', '-', '*', '1.', '2.', '3.']
        
        for sep in separators:
            if sep in text:
                if sep.endswith('.'):  # Para numeración
                    import re
                    parts = re.split(r'\d+\.', text)[1:]  # Omitir primera parte vacía
                else:
                    parts = text.split(sep)
                
                items = [part.strip() for part in parts if part.strip()]
                if len(items) > 1:
                    break
        
        # Buscar patrones con "y"
        if not items and any(word in text.lower() for word in [' y ', ', y ', 'también', 'además']):
            parts = text.replace(' y ', '|').replace(', y ', '|').split('|')
            items = [part.strip() for part in parts if part.strip()]
        
        # Si solo hay un ítem
        if not items:
            items = [text.strip()]
        
        return items[:10]  # Máximo 10 ítems
        """Interpretación simple sin IA como fallback"""
        message_lower = user_message.lower()
        
        # Patrones simples para comandos comunes
        if any(word in message_lower for word in ["crear proyecto", "nuevo proyecto", "proyecto llamado"]):
            # Extraer nombre del proyecto
            name = "Nuevo Proyecto"
            if "llamado" in message_lower:
                name = user_message.split("llamado")[-1].strip()
            elif "proyecto" in message_lower:
                parts = user_message.split("proyecto")
                if len(parts) > 1:
                    name = parts[-1].strip()
            
            return {
                "accion": "CREAR_PROYECTO",
                "parametros": {"name": name},
                "respuesta_usuario": f"Creando proyecto: {name}"
            }
        
        elif any(word in message_lower for word in ["crear tarea", "nueva tarea", "tarea para"]):
            # Extraer título de la tarea
            title = "Nueva Tarea"
            if "para" in message_lower:
                title = user_message.split("para")[-1].strip()
            elif "tarea" in message_lower:
                parts = user_message.split("tarea")
                if len(parts) > 1:
                    title = parts[-1].strip()
            
            return {
                "accion": "CREAR_TAREA",
                "parametros": {"title": title},
                "respuesta_usuario": f"Creando tarea: {title}"
            }
        
        elif any(word in message_lower for word in ["crear usuario", "nuevo usuario", "usuario llamado"]):
            # Extraer nombre del usuario
            name = "Nuevo Usuario"
            if "llamado" in message_lower:
                name = user_message.split("llamado")[-1].strip()
            elif "usuario" in message_lower:
                parts = user_message.split("usuario")
                if len(parts) > 1:
                    name = parts[-1].strip()
            
            return {
                "accion": "CREAR_USUARIO",
                "parametros": {"full_name": name, "username": name.lower().replace(" ", "")},
                "respuesta_usuario": f"Creando usuario: {name}"
            }
        
        elif any(word in message_lower for word in ["proyecto completo", "proyecto con sprints"]):
            # Proyecto completo
            name = "Proyecto Completo"
            if "para" in message_lower:
                name = user_message.split("para")[-1].strip()
            
            return {
                "accion": "CREAR_PROYECTO_COMPLETO",
                "parametros": {"name": name, "num_sprints": 3, "tasks_per_sprint": 5},
                "respuesta_usuario": f"Creando proyecto completo: {name}"
            }
        
        elif any(word in message_lower for word in ["mostrar proyectos", "ver proyectos", "proyectos"]):
            return {
                "accion": "LISTAR_PROYECTOS",
                "parametros": {},
                "respuesta_usuario": "Mostrando todos los proyectos"
            }
        
        elif any(word in message_lower for word in ["mostrar usuarios", "ver usuarios", "usuarios"]):
            return {
                "accion": "LISTAR_USUARIOS",
                "parametros": {},
                "respuesta_usuario": "Mostrando todos los usuarios"
            }
        
        elif any(word in message_lower for word in ["mostrar tareas", "ver tareas", "tareas"]):
            return {
                "accion": "LISTAR_TAREAS",
                "parametros": {},
                "respuesta_usuario": "Mostrando todas las tareas"
            }
        
        elif any(word in message_lower for word in ["estadísticas", "estadisticas", "stats"]):
            return {
                "accion": "OBTENER_ESTADISTICAS",
                "parametros": {},
                "respuesta_usuario": "Mostrando estadísticas del sistema"
            }
        
        else:
            return self._error_response("No pude entender tu comando. Intenta con: 'crear proyecto', 'nueva tarea', 'mostrar proyectos', etc.")
    
    def _post_process_response(self, response: Dict, context: Optional[Dict] = None) -> Dict:
        """Post-procesar la respuesta para ajustar parámetros"""
        accion = response.get("accion")
        parametros = response.get("parametros", {})
        
        # Procesar según el tipo de acción
        if accion == "ASIGNAR_TAREA":
            parametros = self._process_task_assignment(parametros, context)
        elif accion == "CREAR_TAREA":
            parametros = self._process_task_creation(parametros, context)
        elif accion == "CREAR_SPRINT":
            parametros = self._process_sprint_creation(parametros, context)
        elif accion == "CREAR_PROYECTO_COMPLETO":
            parametros = self._process_complete_project(parametros)
        
        response["parametros"] = parametros
        return response
    
    def _process_task_assignment(self, parametros: Dict, context: Optional[Dict]) -> Dict:
        """Procesar asignación de tareas"""
        if context and "last_users" in context:
            user_name = parametros.get("user_name")
            if user_name and not parametros.get("user_id"):
                # Buscar usuario por nombre
                users = context["last_users"]
                for user in users:
                    if (user_name.lower() in user.get("full_name", "").lower() or 
                        user_name.lower() in user.get("username", "").lower()):
                        parametros["user_id"] = user.get("id")
                        break
        
        return parametros
    
    def _process_task_creation(self, parametros: Dict, context: Optional[Dict]) -> Dict:
        """Procesar creación de tareas"""
        if context and "last_projects" in context:
            project_name = parametros.get("project_name")
            if project_name and not parametros.get("project_id"):
                # Buscar proyecto por nombre
                projects = context["last_projects"]
                for project in projects:
                    if project_name.lower() in project.get("name", "").lower():
                        parametros["project_id"] = project.get("id")
                        break
        
        return parametros
    
    def _process_sprint_creation(self, parametros: Dict, context: Optional[Dict]) -> Dict:
        """Procesar creación de sprints"""
        if context and "last_projects" in context:
            project_name = parametros.get("project_name")
            if project_name and not parametros.get("project_id"):
                # Buscar proyecto por nombre
                projects = context["last_projects"]
                for project in projects:
                    if project_name.lower() in project.get("name", "").lower():
                        parametros["project_id"] = project.get("id")
                        break
        
        return parametros
    
    def _process_complete_project(self, parametros: Dict) -> Dict:
        """Procesar creación de proyecto completo"""
        # Establecer valores por defecto
        parametros.setdefault("num_sprints", 3)
        parametros.setdefault("tasks_per_sprint", 5)
        
        return parametros
    
    def _error_response(self, message: str) -> Dict:
        """Crear respuesta de error estándar"""
        return {
            "accion": "ERROR",
            "parametros": {},
            "respuesta_usuario": message
        }

class CommandProcessor:
    """Procesador de comandos que utiliza el asistente de IA"""
    
    def __init__(self, ai_assistant: AIAssistant):
        self.ai_assistant = ai_assistant
    
    async def process_command(self, user_message: str, context: Optional[Dict] = None) -> Dict:
        """Procesar comando del usuario"""
        # Comandos directos que no requieren IA
        direct_commands = {
            "proyectos": {"accion": "LISTAR_PROYECTOS", "parametros": {}, "respuesta_usuario": "Mostrando todos los proyectos"},
            "usuarios": {"accion": "LISTAR_USUARIOS", "parametros": {}, "respuesta_usuario": "Mostrando todos los usuarios"},
            "tareas": {"accion": "LISTAR_TAREAS", "parametros": {}, "respuesta_usuario": "Mostrando todas las tareas"},
            "estadísticas": {"accion": "OBTENER_ESTADISTICAS", "parametros": {}, "respuesta_usuario": "Mostrando estadísticas del sistema"},
            "stats": {"accion": "OBTENER_ESTADISTICAS", "parametros": {}, "respuesta_usuario": "Mostrando estadísticas del sistema"},
        }
        
        # Verificar comandos directos
        user_message_lower = user_message.lower().strip()
        if user_message_lower in direct_commands:
            return direct_commands[user_message_lower]
        
        # Usar fallback simple directamente para comandos complejos para evitar colgarse
        logger.info(f"Procesando comando complejo: {user_message}")
        return await self.ai_assistant.interpret_command(user_message, context)
    
    def _build_system_prompt(self) -> str:
        """Construir el prompt del sistema"""
        return f"""
        Eres un asistente para el sistema de gestión de proyectos Jaivier (similar a Jira).
        Tu trabajo es interpretar comandos en lenguaje natural y extraer información estructurada.
        
        Tipos de operaciones disponibles:
        1. CREAR_PROYECTO - Crear un nuevo proyecto
        2. CREAR_SPRINT - Crear un nuevo sprint
        3. CREAR_TAREA - Crear una nueva tarea
        4. CREAR_USUARIO - Crear un nuevo usuario
        5. ASIGNAR_TAREA - Asignar una tarea a un usuario
        6. LISTAR_PROYECTOS - Mostrar proyectos existentes
        7. LISTAR_USUARIOS - Mostrar usuarios existentes
        8. LISTAR_TAREAS - Mostrar tareas
        9. CREAR_PROYECTO_COMPLETO - Crear un proyecto con sprints y tareas
        10. OBTENER_ESTADISTICAS - Mostrar estadísticas del sistema
        
        Estados de tareas: {TaskStatus.TODO}=TODO, {TaskStatus.IN_PROGRESS}=IN_PROGRESS, {TaskStatus.COMPLETED}=COMPLETED
        Prioridades: {TaskPriority.LOW}=BAJA, {TaskPriority.MEDIUM}=MEDIA, {TaskPriority.HIGH}=ALTA, {TaskPriority.CRITICAL}=CRÍTICA
        Estados de proyectos: {ProjectStatus.ACTIVE}=ACTIVO, {ProjectStatus.COMPLETED}=COMPLETADO, {ProjectStatus.PAUSED}=PAUSADO
        
        Para CREAR_PROYECTO_COMPLETO, incluye:
        - num_sprints: número de sprints (default: 3)
        - tasks_per_sprint: tareas por sprint (default: 5)
        
        Responde SIEMPRE en formato JSON con esta estructura:
        {{
            "accion": "TIPO_DE_ACCION",
            "parametros": {{
                // parámetros específicos según la acción
            }},
            "respuesta_usuario": "Respuesta amigable para el usuario"
        }}
        
        Ejemplos de interpretación:
        - "Crea un proyecto llamado Mi App" → CREAR_PROYECTO con name="Mi App"
        - "Nueva tarea para revisar código" → CREAR_TAREA con title="Revisar código"
        - "Asigna la tarea 5 a Juan" → ASIGNAR_TAREA con task_id=5, buscar user por nombre "Juan"
        - "Muestra todos los proyectos" → LISTAR_PROYECTOS
        - "Crea un proyecto completo para app móvil con 4 sprints" → CREAR_PROYECTO_COMPLETO
        """
    
    async def interpret_command(self, user_message: str, context: Optional[Dict] = None) -> Dict:
        """Interpretar comando del usuario"""
        try:
            prompt = f"""
            {self.system_prompt}
            
            Comando del usuario: "{user_message}"
            
            Contexto actual: {json.dumps(context or {}, indent=2)}
            
            Interpreta el comando y responde en JSON válido.
            """
            
            response = self.model.generate_content(prompt)
            
            # Extraer JSON de la respuesta
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                try:
                    parsed_response = json.loads(json_match.group())
                    
                    # Validar estructura básica
                    if not all(key in parsed_response for key in ["accion", "parametros", "respuesta_usuario"]):
                        raise ValueError("Estructura JSON incompleta")
                    
                    # Post-procesar parámetros según la acción
                    parsed_response = self._post_process_response(parsed_response, context)
                    
                    return parsed_response
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Error parseando JSON de IA: {e}")
                    return self._error_response("Error procesando la respuesta de IA")
                    
            else:
                logger.warning("No se encontró JSON válido en respuesta de IA")
                return self._error_response("No pude entender tu comando. ¿Podrías ser más específico?")
                
        except Exception as e:
            logger.error(f"Error en interpretación de IA: {e}")
            return self._error_response("Hubo un error procesando tu comando.")
    
    def _post_process_response(self, response: Dict, context: Optional[Dict] = None) -> Dict:
        """Post-procesar la respuesta para ajustar parámetros"""
        accion = response.get("accion")
        parametros = response.get("parametros", {})
        
        # Procesar según el tipo de acción
        if accion == "ASIGNAR_TAREA":
            parametros = self._process_task_assignment(parametros, context)
        elif accion == "CREAR_TAREA":
            parametros = self._process_task_creation(parametros, context)
        elif accion == "CREAR_SPRINT":
            parametros = self._process_sprint_creation(parametros, context)
        elif accion == "CREAR_PROYECTO_COMPLETO":
            parametros = self._process_complete_project(parametros)
        
        response["parametros"] = parametros
        return response
    
    def _process_task_assignment(self, parametros: Dict, context: Optional[Dict]) -> Dict:
        """Procesar asignación de tareas"""
        if context and "last_users" in context:
            user_name = parametros.get("user_name")
            if user_name and not parametros.get("user_id"):
                # Buscar usuario por nombre
                users = context["last_users"]
                for user in users:
                    if (user_name.lower() in user.get("full_name", "").lower() or 
                        user_name.lower() in user.get("username", "").lower()):
                        parametros["user_id"] = user.get("id")
                        break
        
        return parametros
    
    def _process_task_creation(self, parametros: Dict, context: Optional[Dict]) -> Dict:
        """Procesar creación de tareas"""
        if context and "last_projects" in context:
            project_name = parametros.get("project_name")
            if project_name and not parametros.get("project_id"):
                # Buscar proyecto por nombre
                projects = context["last_projects"]
                for project in projects:
                    if project_name.lower() in project.get("name", "").lower():
                        parametros["project_id"] = project.get("id")
                        break
        
        return parametros
    
    def _process_sprint_creation(self, parametros: Dict, context: Optional[Dict]) -> Dict:
        """Procesar creación de sprints"""
        if context and "last_projects" in context:
            project_name = parametros.get("project_name")
            if project_name and not parametros.get("project_id"):
                # Buscar proyecto por nombre
                projects = context["last_projects"]
                for project in projects:
                    if project_name.lower() in project.get("name", "").lower():
                        parametros["project_id"] = project.get("id")
                        break
        
        return parametros
    
    def _process_complete_project(self, parametros: Dict) -> Dict:
        """Procesar creación de proyecto completo"""
        # Establecer valores por defecto
        parametros.setdefault("num_sprints", 3)
        parametros.setdefault("tasks_per_sprint", 5)
        
        return parametros
    
    def _error_response(self, message: str) -> Dict:
        """Crear respuesta de error estándar"""
        return {
            "accion": "ERROR",
            "parametros": {},
            "respuesta_usuario": message
        }

class CommandProcessor:
    """Procesador de comandos que utiliza el asistente de IA"""
    
    def __init__(self, ai_assistant: AIAssistant):
        self.ai_assistant = ai_assistant
    
    async def process_command(self, user_message: str, context: Optional[Dict] = None) -> Dict:
        """Procesar comando del usuario"""
        # Comandos directos que no requieren IA
        direct_commands = {
            "proyectos": {"accion": "LISTAR_PROYECTOS", "parametros": {}, "respuesta_usuario": "Mostrando todos los proyectos"},
            "usuarios": {"accion": "LISTAR_USUARIOS", "parametros": {}, "respuesta_usuario": "Mostrando todos los usuarios"},
            "tareas": {"accion": "LISTAR_TAREAS", "parametros": {}, "respuesta_usuario": "Mostrando todas las tareas"},
            "estadísticas": {"accion": "OBTENER_ESTADISTICAS", "parametros": {}, "respuesta_usuario": "Mostrando estadísticas del sistema"},
            "stats": {"accion": "OBTENER_ESTADISTICAS", "parametros": {}, "respuesta_usuario": "Mostrando estadísticas del sistema"},
        }
        
        # Verificar comandos directos
        user_message_lower = user_message.lower().strip()
        if user_message_lower in direct_commands:
            return direct_commands[user_message_lower]
        
        # Usar IA para interpretar comandos complejos
        return await self.ai_assistant.interpret_command(user_message, context)