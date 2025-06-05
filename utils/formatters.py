# utils/formatters.py
"""Utilidades para formatear mensajes del bot"""

from typing import List, Dict
from config.settings import TaskStatus, TaskPriority, ProjectStatus

def format_projects_list(projects: List[Dict]) -> str:
    """Formatear lista de proyectos"""
    if not projects:
        return "📂 No hay proyectos disponibles."
    
    message = "📁 **Proyectos disponibles:**\n\n"
    for project in projects:
        status = project.get('status', 0)
        status_emoji = "🟢" if status == ProjectStatus.ACTIVE else "🔴" if status == ProjectStatus.COMPLETED else "⏸️"
        
        message += f"{status_emoji} **{project.get('name', 'Sin nombre')}** (ID: {project.get('id')})\n"
        message += f"   📝 {project.get('description', 'Sin descripción')}\n"
        
        # Agregar fechas si están disponibles
        if project.get('start_date'):
            message += f"   📅 Inicio: {project.get('start_date')[:10]}\n"
        if project.get('end_date'):
            message += f"   🏁 Fin: {project.get('end_date')[:10]}\n"
        
        message += "\n"
    
    return message

def format_users_list(users: List[Dict]) -> str:
    """Formatear lista de usuarios"""
    if not users:
        return "👥 No hay usuarios disponibles."
    
    message = "👥 **Usuarios disponibles:**\n\n"
    for user in users:
        active_emoji = "✅" if user.get('active', True) else "❌"
        role = user.get('role', 1)
        role_emoji = "👑" if role == 0 else "💻" if role == 1 else "🧪" if role == 2 else "📊"
        
        message += f"{active_emoji} {role_emoji} **{user.get('full_name', user.get('username', 'Sin nombre'))}** (ID: {user.get('id')})\n"
        message += f"   📧 {user.get('email', 'Sin email')}\n"
        message += f"   👤 {user.get('username', 'Sin username')}\n"
        message += f"   🏠 {user.get('work_mode', 'REMOTE')}\n\n"
    
    return message

def format_tasks_list(tasks: List[Dict]) -> str:
    """Formatear lista de tareas"""
    if not tasks:
        return "📋 No hay tareas disponibles."
    
    message = "📋 **Tareas disponibles:**\n\n"
    for task in tasks:
        priority = task.get('priority', 2)
        priority_emoji = "🔴" if priority == TaskPriority.CRITICAL else "🟡" if priority == TaskPriority.HIGH else "🟢" if priority == TaskPriority.LOW else "🔵"
        
        status = task.get('status', 0)
        status_emoji = "⏳" if status == TaskStatus.IN_PROGRESS else "✅" if status == TaskStatus.COMPLETED else "📝"
        
        message += f"{status_emoji} {priority_emoji} **{task.get('title', 'Sin título')}** (ID: {task.get('id')})\n"
        
        description = task.get('description', 'Sin descripción')
        if len(description) > 50:
            description = description[:50] + "..."
        message += f"   📝 {description}\n"
        
        if task.get('estimated_hours'):
            message += f"   ⏱️ {task.get('estimated_hours')}h estimadas\n"
        
        if task.get('due_date'):
            message += f"   📅 Vence: {task.get('due_date')[:10]}\n"
        
        message += "\n"
    
    return message

def format_statistics(users: List[Dict], projects: List[Dict], tasks: List[Dict]) -> str:
    """Formatear estadísticas del sistema"""
    # Contadores básicos
    total_users = len(users) if isinstance(users, list) else 0
    total_projects = len(projects) if isinstance(projects, list) else 0
    total_tasks = len(tasks) if isinstance(tasks, list) else 0
    
    # Estadísticas de usuarios
    active_users = 0
    roles_count = {"admin": 0, "developer": 0, "tester": 0, "manager": 0}
    
    if isinstance(users, list):
        for user in users:
            if user.get('active', True):
                active_users += 1
            
            role = user.get('role', 1)
            if role == 0:
                roles_count["admin"] += 1
            elif role == 1:
                roles_count["developer"] += 1
            elif role == 2:
                roles_count["tester"] += 1
            elif role == 3:
                roles_count["manager"] += 1
    
    # Estadísticas de proyectos
    project_status_count = {"active": 0, "completed": 0, "paused": 0}
    
    if isinstance(projects, list):
        for project in projects:
            status = project.get('status', 0)
            if status == ProjectStatus.ACTIVE:
                project_status_count["active"] += 1
            elif status == ProjectStatus.COMPLETED:
                project_status_count["completed"] += 1
            elif status == ProjectStatus.PAUSED:
                project_status_count["paused"] += 1
    
    # Estadísticas de tareas
    task_status_count = {"todo": 0, "in_progress": 0, "completed": 0}
    task_priority_count = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    
    if isinstance(tasks, list):
        for task in tasks:
            status = task.get('status', 0)
            if status == TaskStatus.TODO:
                task_status_count["todo"] += 1
            elif status == TaskStatus.IN_PROGRESS:
                task_status_count["in_progress"] += 1
            elif status == TaskStatus.COMPLETED:
                task_status_count["completed"] += 1
            
            priority = task.get('priority', 2)
            if priority == TaskPriority.LOW:
                task_priority_count["low"] += 1
            elif priority == TaskPriority.MEDIUM:
                task_priority_count["medium"] += 1
            elif priority == TaskPriority.HIGH:
                task_priority_count["high"] += 1
            elif priority == TaskPriority.CRITICAL:
                task_priority_count["critical"] += 1
    
    # Calcular porcentajes
    completed_tasks_percent = round((task_status_count["completed"] / total_tasks * 100) if total_tasks > 0 else 0, 1)
    active_projects_percent = round((project_status_count["active"] / total_projects * 100) if total_projects > 0 else 0, 1)
    
    message = f"""
📊 **Estadísticas del Sistema Jaivier**

👥 **Usuarios ({total_users} total):**
• ✅ Activos: {active_users}
• 👑 Admins: {roles_count["admin"]}
• 💻 Desarrolladores: {roles_count["developer"]}
• 🧪 Testers: {roles_count["tester"]}
• 📊 Managers: {roles_count["manager"]}

📁 **Proyectos ({total_projects} total):**
• 🟢 Activos: {project_status_count["active"]} ({active_projects_percent}%)
• 🔴 Completados: {project_status_count["completed"]}
• ⏸️ Pausados: {project_status_count["paused"]}

📋 **Tareas ({total_tasks} total):**
• 📝 Por hacer: {task_status_count["todo"]}
• ⏳ En progreso: {task_status_count["in_progress"]}
• ✅ Completadas: {task_status_count["completed"]} ({completed_tasks_percent}%)

🎯 **Prioridades de Tareas:**
• 🟢 Baja: {task_priority_count["low"]}
• 🔵 Media: {task_priority_count["medium"]}
• 🟡 Alta: {task_priority_count["high"]}
• 🔴 Crítica: {task_priority_count["critical"]}

📈 **Métricas Clave:**
• Progreso general: {completed_tasks_percent}% tareas completadas
• Proyectos activos: {active_projects_percent}%
• Productividad: {round(total_tasks/total_users if total_users > 0 else 0, 1)} tareas por usuario
    """
    
    return message

def format_sprint_info(sprint: Dict) -> str:
    """Formatear información de un sprint"""
    message = f"🏃 **Sprint: {sprint.get('name', 'Sin nombre')}**\n\n"
    message += f"📝 {sprint.get('description', 'Sin descripción')}\n"
    
    if sprint.get('start_date'):
        message += f"📅 Inicio: {sprint.get('start_date')[:10]}\n"
    if sprint.get('end_date'):
        message += f"🏁 Fin: {sprint.get('end_date')[:10]}\n"
    
    status = sprint.get('status', 0)
    status_text = "Activo" if status == 0 else "Completado" if status == 1 else "Pausado"
    message += f"🔄 Estado: {status_text}\n"
    
    return message

def format_project_summary(project: Dict, sprints: List[Dict] = None, tasks: List[Dict] = None) -> str:
    """Formatear resumen detallado de un proyecto"""
    message = f"📁 **Proyecto: {project.get('name', 'Sin nombre')}**\n\n"
    message += f"📝 {project.get('description', 'Sin descripción')}\n\n"
    
    if project.get('start_date'):
        message += f"📅 Inicio: {project.get('start_date')[:10]}\n"
    if project.get('end_date'):
        message += f"🏁 Fin: {project.get('end_date')[:10]}\n"
    
    if sprints:
        message += f"\n🏃 **Sprints ({len(sprints)}):**\n"
        for sprint in sprints[:3]:  # Mostrar solo los primeros 3
            message += f"• {sprint.get('name', 'Sin nombre')}\n"
        if len(sprints) > 3:
            message += f"• ... y {len(sprints) - 3} más\n"
    
    if tasks:
        completed_tasks = sum(1 for task in tasks if task.get('status') == TaskStatus.COMPLETED)
        message += f"\n📋 **Tareas:** {len(tasks)} total, {completed_tasks} completadas\n"
    
    return message