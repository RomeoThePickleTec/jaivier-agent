# bot/auth_manager.py
"""Gestor de autenticación por chat/usuario"""

import logging
import asyncio
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from api.services import APIManager
from config.settings import API_BASE_URL

logger = logging.getLogger(__name__)

class ChatAuthManager:
    """Gestor de autenticación por chat individual"""
    
    def __init__(self):
        # Almacenar sesiones por chat_id
        self.chat_sessions: Dict[int, Dict] = {}
        # Estados de autenticación en progreso
        self.pending_auth: Dict[int, Dict] = {}
        
    def is_authenticated(self, chat_id: int) -> bool:
        """Verificar si un chat está autenticado"""
        session = self.chat_sessions.get(chat_id)
        if not session:
            return False
        
        # Verificar si el token no ha expirado
        expires_at = session.get('expires_at')
        if expires_at and datetime.now() > expires_at:
            logger.info(f"Token expired for chat {chat_id}")
            self.logout_chat(chat_id)
            return False
        
        return session.get('authenticated', False)
    
    def start_auth_flow(self, chat_id: int):
        """Iniciar flujo de autenticación para un chat"""
        self.pending_auth[chat_id] = {
            'step': 'username',
            'username': None,
            'password': None,
            'started_at': datetime.now()
        }
        logger.info(f"Started auth flow for chat {chat_id}")
    
    def is_in_auth_flow(self, chat_id: int) -> bool:
        """Verificar si un chat está en proceso de autenticación"""
        return chat_id in self.pending_auth
    
    def get_auth_step(self, chat_id: int) -> Optional[str]:
        """Obtener el paso actual de autenticación"""
        auth_data = self.pending_auth.get(chat_id)
        return auth_data.get('step') if auth_data else None
    
    def process_auth_input(self, chat_id: int, input_text: str) -> Tuple[str, bool]:
        """
        Procesar entrada durante autenticación
        Returns: (message, is_complete)
        """
        if chat_id not in self.pending_auth:
            return "No hay proceso de autenticación activo.", False
        
        auth_data = self.pending_auth[chat_id]
        current_step = auth_data['step']
        
        if current_step == 'username':
            auth_data['username'] = input_text.strip()
            auth_data['step'] = 'password'
            return f"👤 Usuario: {input_text}\n🔐 Ahora envía tu contraseña:", False
        
        elif current_step == 'password':
            auth_data['password'] = input_text.strip()
            # Autenticación completa, ready to authenticate
            return "🔄 Verificando credenciales...", True
        
        return "Error en el flujo de autenticación.", False
    
    async def complete_authentication(self, chat_id: int) -> Tuple[bool, str]:
        """
        Completar proceso de autenticación
        Returns: (success, message)
        """
        if chat_id not in self.pending_auth:
            return False, "No hay proceso de autenticación activo."
        
        auth_data = self.pending_auth[chat_id]
        username = auth_data.get('username')
        password = auth_data.get('password')
        
        if not username or not password:
            return False, "Faltan credenciales."
        
        try:
            # Crear APIManager para este chat
            api_manager = APIManager(API_BASE_URL)
            success = await api_manager.initialize(username, password)
            
            if success:
                # Guardar sesión
                self.chat_sessions[chat_id] = {
                    'username': username,
                    'authenticated': True,
                    'api_manager': api_manager,
                    'expires_at': datetime.now() + timedelta(hours=24),  # Token válido por 24h
                    'login_time': datetime.now()
                }
                
                # Limpiar proceso de auth
                del self.pending_auth[chat_id]
                
                logger.info(f"Authentication successful for chat {chat_id}, user {username}")
                return True, f"✅ Autenticación exitosa!\n👤 Conectado como: {username}\n🔗 API: {API_BASE_URL}"
            else:
                logger.warning(f"Authentication failed for chat {chat_id}, user {username}")
                return False, "❌ Credenciales incorrectas. Intenta de nuevo con /login"
                
        except Exception as e:
            logger.error(f"Error during authentication for chat {chat_id}: {e}")
            return False, f"❌ Error de conexión: {str(e)}"
        finally:
            # Limpiar proceso de auth en caso de error
            if chat_id in self.pending_auth:
                del self.pending_auth[chat_id]
    
    def get_api_manager(self, chat_id: int) -> Optional[APIManager]:
        """Obtener APIManager para un chat autenticado"""
        session = self.chat_sessions.get(chat_id)
        if session and session.get('authenticated'):
            return session.get('api_manager')
        return None
    
    def get_username(self, chat_id: int) -> Optional[str]:
        """Obtener username para un chat autenticado"""
        session = self.chat_sessions.get(chat_id)
        if session and session.get('authenticated'):
            return session.get('username')
        return None
    
    def logout_chat(self, chat_id: int) -> bool:
        """Cerrar sesión de un chat"""
        if chat_id in self.chat_sessions:
            session = self.chat_sessions[chat_id]
            api_manager = session.get('api_manager')
            
            # Cerrar conexiones del APIManager
            if api_manager:
                try:
                    # Si hay loop corriendo, usar create_task
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(api_manager.close())
                    else:
                        asyncio.run(api_manager.close())
                except Exception as e:
                    logger.warning(f"Error closing API manager for chat {chat_id}: {e}")
            
            del self.chat_sessions[chat_id]
            logger.info(f"Logged out chat {chat_id}")
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Limpiar sesiones expiradas"""
        current_time = datetime.now()
        expired_chats = []
        
        for chat_id, session in self.chat_sessions.items():
            expires_at = session.get('expires_at')
            if expires_at and current_time > expires_at:
                expired_chats.append(chat_id)
        
        for chat_id in expired_chats:
            logger.info(f"Cleaning up expired session for chat {chat_id}")
            self.logout_chat(chat_id)
    
    async def check_and_refresh_token(self, chat_id: int) -> bool:
        """
        Verificar si el token sigue válido y refrescarlo si es necesario
        Returns True si el token es válido o se refrescó exitosamente
        """
        if not self.is_authenticated(chat_id):
            return False
        
        api_manager = self.get_api_manager(chat_id)
        if not api_manager:
            return False
        
        try:
            # Hacer una llamada simple para verificar si el token funciona
            health = await api_manager.health_check()
            if health:
                return True
            else:
                # Token probablemente expirado, cerrar sesión
                logger.warning(f"Health check failed for chat {chat_id}, token may be expired")
                self.logout_chat(chat_id)
                return False
        except Exception as e:
            logger.error(f"Error checking token for chat {chat_id}: {e}")
            # En caso de error 403 o similar, cerrar sesión
            if "403" in str(e) or "401" in str(e):
                logger.warning(f"Authentication error for chat {chat_id}, logging out")
                self.logout_chat(chat_id)
            return False
    
    def get_session_info(self, chat_id: int) -> Optional[Dict]:
        """Obtener información de la sesión de un chat"""
        session = self.chat_sessions.get(chat_id)
        if session:
            return {
                'username': session.get('username'),
                'login_time': session.get('login_time'),
                'expires_at': session.get('expires_at'),
                'authenticated': session.get('authenticated', False)
            }
        return None

# Instancia global del gestor de autenticación
chat_auth_manager = ChatAuthManager()