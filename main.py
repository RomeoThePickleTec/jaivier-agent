# main.py - FIXED VERSION
"""Bot principal de Telegram para Jaivier"""

import asyncio
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config.settings import TELEGRAM_BOT_TOKEN, LOG_LEVEL, LOG_FORMAT
from ai.improved_assistant import ImprovedAIAssistant
from ai.json_executor import JSONExecutor
from bot.handlers import BotHandlers

# Configurar logging
logging.basicConfig(
    format=LOG_FORMAT,
    level=getattr(logging, LOG_LEVEL)
)
logger = logging.getLogger(__name__)

class JaivierBot:
    """Bot principal de Jaivier"""
    
    def __init__(self):
        # Inicializar componentes (sin API manager global)
        self.ai_assistant = ImprovedAIAssistant()
        self.json_executor = JSONExecutor(None)  # No context manager needed
        self.handlers = BotHandlers(self.ai_assistant, self.json_executor)
        
        # Estado del bot
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Inicializar el bot y sus componentes"""
        logger.info("🔐 Inicializando Jaivier Bot...")
        
        try:
            # No need for global API initialization anymore
            # Each chat will authenticate individually
            logger.info("✅ Bot components initialized")
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Error durante la inicialización: {e}")
            return False
    
    async def cleanup(self):
        """Limpiar recursos del bot"""
        logger.info("🧹 Limpiando recursos del bot...")
        try:
            # Cleanup will be handled by individual chat sessions
            from bot.auth_manager import chat_auth_manager
            
            # Logout all active sessions
            for chat_id in list(chat_auth_manager.chat_sessions.keys()):
                chat_auth_manager.logout_chat(chat_id)
            
            logger.info("✅ Recursos limpiados correctamente")
        except Exception as e:
            logger.error(f"❌ Error limpiando recursos: {e}")
    
    def setup_handlers(self, app: Application):
        """Configurar manejadores del bot"""
        logger.info("⚙️ Configurando manejadores...")
        
        # Comandos del sistema
        app.add_handler(CommandHandler("start", self.handlers.start_command))
        app.add_handler(CommandHandler("ayuda", self.handlers.help_command))
        app.add_handler(CommandHandler("help", self.handlers.help_command))
        app.add_handler(CommandHandler("status", self.handlers.status_command))
        app.add_handler(CommandHandler("login", self.handlers.login_command))
        app.add_handler(CommandHandler("logout", self.handlers.logout_command))
        
        # Comandos de datos
        app.add_handler(CommandHandler("proyectos", self.handlers.list_projects_command))
        app.add_handler(CommandHandler("sprints", self.handlers.list_sprints_command))
        app.add_handler(CommandHandler("tareas", self.handlers.list_tasks_command))
        app.add_handler(CommandHandler("usuarios", self.handlers.list_users_command))
        
        # IA Generativa
        app.add_handler(CommandHandler("iagenerativa", self.handlers.ia_generativa_command))
        
        # Mensajes naturales
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handlers.handle_natural_message
        ))
        
        logger.info("✅ Manejadores configurados correctamente")
    
    async def run(self):
        """Ejecutar el bot"""
        if not self.initialized:
            logger.error("❌ Bot no inicializado. Llama a initialize() primero.")
            return
        
        try:
            # Crear aplicación con timeouts personalizados
            app = (Application.builder()
                   .token(TELEGRAM_BOT_TOKEN)
                   .read_timeout(30)
                   .write_timeout(30)
                   .connect_timeout(30)
                   .pool_timeout(30)
                   .build())
            
            # Configurar manejadores
            self.setup_handlers(app)
            
            # Configurar cleanup
            async def cleanup_on_shutdown(application):
                await self.cleanup()
            
            app.post_shutdown = cleanup_on_shutdown
            
            # Mostrar información de inicio
            logger.info("🤖 Jaivier Bot iniciado y listo para recibir comandos!")
            logger.info("🔐 Autenticación por chat individual activada")
            logger.info("📱 Busca @Jaivier21Bot en Telegram")
            logger.info("Presiona Ctrl+C para detener el bot")
            
            # Inicializar la aplicación
            await app.initialize()
            
            # Iniciar polling
            await app.start()
            await app.updater.start_polling(
                poll_interval=1.0,
                timeout=20,
                bootstrap_retries=3
            )
            
            # Mantener el bot corriendo
            try:
                # Esperar indefinidamente hasta que se interrumpa
                import signal
                stop_signals = (signal.SIGTERM, signal.SIGINT)
                loop = asyncio.get_running_loop()
                
                # Crear un future que se complete cuando se reciba una señal
                stop_future = loop.create_future()
                
                def signal_handler():
                    if not stop_future.done():
                        stop_future.set_result(None)
                
                for sig in stop_signals:
                    signal.signal(sig, lambda s, f: signal_handler())
                
                # Esperar hasta que se reciba la señal
                await stop_future
                
            except KeyboardInterrupt:
                logger.info("👋 Recibido Ctrl+C, deteniendo bot...")
            
            # Detener el bot
            logger.info("🛑 Deteniendo bot...")
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando el bot: {e}")
            raise

def main():
    """Función principal - versión simplificada"""
    
    # Configurar event loop para Windows
    if hasattr(asyncio, 'WindowsProactorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    async def run_bot():
        """Función async interna"""
        bot = JaivierBot()
        
        try:
            # Inicializar bot
            success = await bot.initialize()
            if not success:
                print("❌ Error: No se pudo inicializar el bot")
                print("   Verifica la configuración del bot")
                return
            
            # Ejecutar bot
            await bot.run()
            
        except KeyboardInterrupt:
            print("\n👋 Bot detenido por el usuario")
        except Exception as e:
            print(f"❌ Error crítico: {e}")
            logger.exception("Error crítico en run_bot")
        finally:
            # Asegurar cleanup
            try:
                await bot.cleanup()
            except Exception as cleanup_error:
                logger.error(f"Error en cleanup: {cleanup_error}")
    
    # Ejecutar directamente con asyncio.run
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n👋 Bot detenido por el usuario")
    except Exception as e:
        print(f"❌ Error crítico en main: {e}")

if __name__ == '__main__':
    main()