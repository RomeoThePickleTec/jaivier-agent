# bot/context.py
"""Manejo de contexto de conversación"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ConversationContext:
    """Maneja el contexto de conversación por usuario"""
    
    def __init__(self):
        self.user_contexts = {}
        self.max_history = 20  # Máximo de mensajes en historial
        
    def get_context(self, user_id: int) -> Dict:
        """Obtener contexto del usuario"""
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {
                "conversation_history": [],
                "current_project": None,
                "current_sprint": None,
                "pending_actions": [],
                "last_created_items": {
                    "projects": [],
                    "sprints": [],
                    "tasks": [],
                    "users": []
                },
                "user_preferences": {
                    "default_sprint_duration": 14,
                    "default_task_estimation": 8,
                    "preferred_priority": 2
                }
            }
        return self.user_contexts[user_id]
    
    def add_message(self, user_id: int, message: str, response: str, action_taken: str = None):
        """Agregar mensaje al historial"""
        context = self.get_context(user_id)
        
        conversation_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_message": message,
            "bot_response": response,
            "action_taken": action_taken
        }
        
        context["conversation_history"].append(conversation_entry)
        
        # Mantener solo los últimos N mensajes
        if len(context["conversation_history"]) > self.max_history:
            context["conversation_history"] = context["conversation_history"][-self.max_history:]
    
    def set_current_project(self, user_id: int, project_id: int, project_name: str):
        """Establecer proyecto actual"""
        context = self.get_context(user_id)
        context["current_project"] = {
            "id": project_id,
            "name": project_name,
            "set_at": datetime.now().isoformat()
        }
    
    def set_current_sprint(self, user_id: int, sprint_id: int, sprint_name: str):
        """Establecer sprint actual"""
        context = self.get_context(user_id)
        context["current_sprint"] = {
            "id": sprint_id,
            "name": sprint_name,
            "set_at": datetime.now().isoformat()
        }
    
    def add_created_item(self, user_id: int, item_type: str, item_data: Dict):
        """Agregar ítem creado al contexto"""
        context = self.get_context(user_id)
        
        if item_type in context["last_created_items"]:
            context["last_created_items"][item_type].append({
                **item_data,
                "created_at": datetime.now().isoformat()
            })
            
            # Mantener solo los últimos 10 ítems
            if len(context["last_created_items"][item_type]) > 10:
                context["last_created_items"][item_type] = context["last_created_items"][item_type][-10:]
    
    def get_conversation_summary(self, user_id: int) -> str:
        """Obtener resumen de la conversación"""
        context = self.get_context(user_id)
        history = context["conversation_history"][-5:]  # Últimos 5 mensajes
        
        summary = "Contexto reciente:\n"
        for entry in history:
            summary += f"Usuario: {entry['user_message']}\n"
            if entry.get('action_taken'):
                summary += f"Acción: {entry['action_taken']}\n"
        
        if context["current_project"]:
            summary += f"\nProyecto actual: {context['current_project']['name']}\n"
        
        if context["current_sprint"]:
            summary += f"Sprint actual: {context['current_sprint']['name']}\n"
            
        return summary

class MultipleItemGenerator:
    """Generador de múltiples ítems basado en contexto"""
    
    def __init__(self, api_manager, context_manager):
        self.api_manager = api_manager
        self.context_manager = context_manager
    
    async def create_multiple_tasks(self, user_id: int, task_descriptions: List[str], project_id: int = None, sprint_id: int = None, sprint_name: str = None) -> List[Dict]:
        """Crear múltiples tareas"""
        logger.info(f"[DEBUG] create_multiple_tasks iniciado para user {user_id}")
        logger.info(f"[DEBUG] task_descriptions: {task_descriptions}")
        logger.info(f"[DEBUG] project_id: {project_id}, sprint_id: {sprint_id}, sprint_name: {sprint_name}")
        
        context = self.context_manager.get_context(user_id)
        
        # Buscar sprint por nombre si se especifica
        if sprint_name and not sprint_id:
            logger.info(f"[DEBUG] Buscando sprint por nombre: {sprint_name}")
            sprints = await self.api_manager.sprints.get_all(project_id)
            logger.info(f"[DEBUG] Sprints disponibles: {len(sprints)}")
            for sprint in sprints:
                logger.info(f"[DEBUG] Comparando '{sprint_name.lower()}' con '{sprint.get('name', '').lower()}'")
                if sprint_name.lower() in sprint.get("name", "").lower():
                    sprint_id = sprint.get("id")
                    logger.info(f"[DEBUG] Sprint encontrado! ID: {sprint_id}")
                    break
            
            if not sprint_id:
                logger.warning(f"[DEBUG] No se encontró sprint con nombre: {sprint_name}")
        
        # Usar proyecto/sprint del contexto si no se especifica
        if not project_id and context["current_project"]:
            project_id = context["current_project"]["id"]
            logger.info(f"[DEBUG] Usando project_id del contexto: {project_id}")
        
        if not sprint_id and context["current_sprint"]:
            sprint_id = context["current_sprint"]["id"]
            logger.info(f"[DEBUG] Usando sprint_id del contexto: {sprint_id}")
        
        created_tasks = []
        preferences = context["user_preferences"]
        
        logger.info(f"[DEBUG] Creando {len(task_descriptions)} tareas...")
        
        for i, description in enumerate(task_descriptions):
            task_data = {
                "title": description.strip(),
                "description": f"Tarea creada automáticamente: {description}",
                "priority": preferences["preferred_priority"],
                "status": 0,  # TODO
                "estimated_hours": preferences["default_task_estimation"],
                "project_id": project_id,
                "sprint_id": sprint_id,
                "due_date": (datetime.now() + timedelta(days=7 + i)).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            
            logger.info(f"[DEBUG] Creando tarea {i+1}: {task_data['title']}")
            logger.info(f"[DEBUG] Task data completo: {task_data}")
            
            result = await self.api_manager.tasks.create(task_data)
            logger.info(f"[DEBUG] Resultado de API para tarea {i+1}: {result}")
            
            # Manejar respuesta exitosa pero sin JSON
            if result and result.get("success") and not result.get("error"):
                # Crear objeto de tarea simulado para el contexto
                task_obj = {**task_data, "id": f"temp_{i}_{int(datetime.now().timestamp())}"}
                created_tasks.append(task_obj)
                self.context_manager.add_created_item(user_id, "tasks", task_obj)
                logger.info(f"[DEBUG] Tarea {i+1} creada exitosamente (respuesta success)")
            elif result and not result.get("error"):
                created_tasks.append(result)
                self.context_manager.add_created_item(user_id, "tasks", result)
                logger.info(f"[DEBUG] Tarea {i+1} creada exitosamente (respuesta con data)")
            else:
                logger.error(f"[DEBUG] Error creando tarea {i+1}: {result}")
        
        logger.info(f"[DEBUG] Total tareas creadas: {len(created_tasks)}")
        return created_tasks
    
    async def create_multiple_sprints(self, user_id: int, sprint_names: List[str], project_id: int = None) -> List[Dict]:
        """Crear múltiples sprints"""
        context = self.context_manager.get_context(user_id)
        
        # Usar proyecto del contexto si no se especifica
        if not project_id and context["current_project"]:
            project_id = context["current_project"]["id"]
        
        created_sprints = []
        preferences = context["user_preferences"]
        duration = preferences["default_sprint_duration"]
        
        for i, name in enumerate(sprint_names):
            start_date = datetime.now() + timedelta(days=i * duration)
            end_date = start_date + timedelta(days=duration)
            
            sprint_data = {
                "name": name.strip(),
                "description": f"Sprint {name} creado automáticamente",
                "project_id": project_id,
                "status": 0,
                "start_date": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end_date": end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            
            result = await self.api_manager.sprints.create(sprint_data)
            if not (isinstance(result, dict) and result.get("error")):
                created_sprints.append(result)
                self.context_manager.add_created_item(user_id, "sprints", result)
        
        return created_sprints
    
    def parse_multiple_items(self, text: str) -> List[str]:
        """Parsear múltiples ítems de un texto"""
        # Buscar patrones de listas
        items = []
        
        # Separadores comunes
        separators = [',', ';', '\n', '•', '-', '*']
        
        for sep in separators:
            if sep in text:
                parts = text.split(sep)
                items = [part.strip() for part in parts if part.strip()]
                break
        
        # Si no hay separadores, buscar palabras clave
        if not items and any(word in text.lower() for word in ['y ', ' y ', 'también', 'además']):
            # Dividir por "y"
            parts = text.replace(' y ', '|').replace('y ', '|').split('|')
            items = [part.strip() for part in parts if part.strip()]
        
        # Si solo hay un ítem
        if not items:
            items = [text.strip()]
        
        return items[:10]  # Máximo 10 ítems