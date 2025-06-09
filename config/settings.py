# config/settings.py
"""Configuración global del bot"""

import os
from datetime import timedelta

# Configuración de Telegram
#PRODUCTION
#TELEGRAM_BOT_TOKEN = "8054295560:AAGGaiqV7Un5TM_2yemt1XrFnvTrbzDnYKE"
#development
TELEGRAM_BOT_TOKEN = "7612443849:AAEOOFxQ6UI0mjOhMiIz7vJjUFx6Sp79WtA"  # Reemplaza con tu token de bot

# Configuración de API
API_BASE_URL = "http://220.158.78.114:8081"
# DEFAULT_USERNAME = "djeison"
# DEFAULT_PASSWORD = "Hello123"

# Configuración de IA
GEMINI_API_KEY = "AIzaSyDdfbfnH3P-Z3JR12WN5ysRmnXMR-wY6jc"  # Reemplaza con tu API key

# Configuración de logging
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Configuración de timeouts
REQUEST_TIMEOUT = 30
HEALTH_CHECK_TIMEOUT = 5

# Configuración de proyectos por defecto
DEFAULT_PROJECT_DURATION = timedelta(days=30)
DEFAULT_SPRINT_DURATION = timedelta(days=14)
DEFAULT_TASK_ESTIMATION = 8  # horas

# Estados y prioridades
class TaskStatus:
    TODO = 0
    IN_PROGRESS = 1
    COMPLETED = 2

class TaskPriority:
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class ProjectStatus:
    ACTIVE = 0
    COMPLETED = 1
    PAUSED = 2

class UserRole:
    ADMIN = 0
    DEVELOPER = 1
    TESTER = 2
    MANAGER = 3