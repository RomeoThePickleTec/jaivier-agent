# bot/handlers.py - COMPLETE VERSION
"""Complete bot handlers with full CRUD support"""

import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from config.settings import API_BASE_URL, DEFAULT_USERNAME

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self, api_manager, ai_assistant, json_executor):
        self.api_manager = api_manager
        self.ai_assistant = ai_assistant  
        self.json_executor = json_executor
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome = f"""🚀 **Jaivier Bot - Ready!**

✅ **Connected to:** {API_BASE_URL}
👤 **User:** {DEFAULT_USERNAME}

**Commands:**
• /proyectos - List projects
• /sprints - List sprints  
• /tareas - List tasks
• /usuarios - List team members
• /status - Check connection

**Natural Language:**
• "crear proyecto MyApp"
• "new sprint Development"
• "create task Login system"
• "mostrar proyectos"
• "proyecto completo WebShop"

Try: "crear proyecto MiApp" 🚀"""
        await update.message.reply_text(welcome, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """📚 **Available Commands:**

**CREATE:**
• "crear proyecto [name]" - Create project
• "new sprint [name]" - Create sprint
• "create task [title]" - Create task
• "proyecto completo [name]" - Full project setup

**LIST:**
• /proyectos or "mostrar proyectos"
• /sprints or "list sprints"
• /tareas or "ver tareas"
• /usuarios or "mostrar equipo"

**EXAMPLES:**
• "crear proyecto E-commerce"
• "new sprint for project 5"
• "create 3 tasks: login, dashboard, profile"
• "mostrar sprints del proyecto 2"

**COMPLEX:**
• "proyecto completo llamado WebApp" (creates project + sprint + tasks)
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🔍 Checking connection...")
        
        try:
            health = await self.api_manager.health_check()
            logger.info(f"Health check result: {health}")
            
            if health:
                # Get counts with detailed logging
                logger.info("Getting projects...")
                projects = await self.api_manager.projects.get_all()
                logger.info(f"Projects result: {projects}")
                
                logger.info("Getting sprints...")
                sprints = await self.api_manager.sprints.get_all()
                logger.info(f"Sprints result: {sprints}")
                
                logger.info("Getting tasks...")
                tasks = await self.api_manager.tasks.get_all()
                logger.info(f"Tasks result: {tasks}")
                
                status_msg = f"""✅ **CONNECTED**

🔗 **API:** {API_BASE_URL}
👤 **User:** {DEFAULT_USERNAME}
🔐 **Auth:** {self.api_manager.authenticated}

📊 **Data:**
• 📁 Projects: {len(projects) if projects else 0}
• 🏃 Sprints: {len(sprints) if sprints else 0}
• 📋 Tasks: {len(tasks) if tasks else 0}

**Debug Info:**
• Projects type: {type(projects)}
• Sprints type: {type(sprints)}
• Tasks type: {type(tasks)}"""
            else:
                status_msg = f"""❌ **DISCONNECTED**

🔗 **API:** {API_BASE_URL}
⚠️ Cannot reach server"""
            
            await update.message.reply_text(status_msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Status check error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def list_projects_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            projects = await self.api_manager.projects.get_all()
            
            if not projects:
                await update.message.reply_text("📁 No projects found")
                return
            
            lines = ["📁 Projects:\n"]
            for p in projects:
                if isinstance(p, dict):
                    name = p.get("name", "Unknown")
                    pid = p.get("id", "N/A")
                    status = p.get("status", 0)
                    status_text = ["Active", "Completed", "Paused"][min(status, 2)]
                    lines.append(f"• {name} (ID: {pid}) - {status_text}")
                else:
                    lines.append(f"• {str(p)}")
            
            message_text = "\n".join(lines)
            
            # Try with markdown first, fallback to plain text
            try:
                await update.message.reply_text(message_text, parse_mode='Markdown')
            except Exception as parse_error:
                logger.warning(f"Markdown parsing failed, sending plain text: {parse_error}")
                # Remove markdown formatting and send as plain text
                plain_text = message_text.replace("**", "").replace("*", "")
                await update.message.reply_text(plain_text)
            
        except Exception as e:
            logger.error(f"Error listing projects: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def list_sprints_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            sprints = await self.api_manager.sprints.get_all()
            
            if not sprints:
                await update.message.reply_text("🏃 No sprints found")
                return
            
            lines = ["🏃 Sprints:\n"]
            for s in sprints:
                if isinstance(s, dict):
                    name = s.get("name", "Unknown")
                    sid = s.get("id", "N/A")
                    project_id = s.get("project_id", "N/A")
                    status = s.get("status", 0)
                    status_text = ["Active", "Completed"][min(status, 1)]
                    lines.append(f"• {name} (ID: {sid}, Project: {project_id}) - {status_text}")
                else:
                    lines.append(f"• {str(s)}")
            
            message_text = "\n".join(lines)
            
            # Try with markdown first, fallback to plain text
            try:
                await update.message.reply_text(message_text, parse_mode='Markdown')
            except Exception as parse_error:
                logger.warning(f"Markdown parsing failed, sending plain text: {parse_error}")
                # Remove markdown formatting and send as plain text
                plain_text = message_text.replace("**", "").replace("*", "")
                await update.message.reply_text(plain_text)
            
        except Exception as e:
            logger.error(f"Error listing sprints: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def list_tasks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            logger.info("Starting task retrieval...")
            tasks = await self.api_manager.tasks.get_all()
            logger.info(f"Retrieved {len(tasks) if tasks else 0} tasks: {tasks}")
            
            if not tasks:
                await update.message.reply_text("📋 No tasks found")
                return
            
            # Paginate tasks to avoid message length limits
            MAX_TASKS_PER_MESSAGE = 10
            task_chunks = [tasks[i:i + MAX_TASKS_PER_MESSAGE] for i in range(0, len(tasks), MAX_TASKS_PER_MESSAGE)]
            
            for chunk_idx, chunk in enumerate(task_chunks):
                lines = []
                if len(task_chunks) > 1:
                    lines.append(f"📋 Tasks (Page {chunk_idx + 1}/{len(task_chunks)}):\n")
                else:
                    lines.append("📋 Tasks:\n")
                
                for t in chunk:
                    if isinstance(t, dict):
                        title = t.get("title", "Unknown")
                        tid = t.get("id", "N/A")
                        priority = t.get("priority", 2)
                        status = t.get("status", 0)
                        
                        priority_text = ["", "🟢Low", "🔵Medium", "🟡High", "🔴Critical"][min(priority, 4)]
                        status_text = ["📝TODO", "⏳Progress", "✅Done"][min(status, 2)]
                        
                        # Simplified formatting to avoid entity parsing issues
                        lines.append(f"• {title} (ID: {tid})")
                        lines.append(f"  {priority_text} | {status_text}")
                    else:
                        lines.append(f"• {str(t)}")
                
                message_text = "\n".join(lines)
                
                # Try with markdown first, fallback to plain text
                try:
                    await update.message.reply_text(message_text, parse_mode='Markdown')
                except Exception as parse_error:
                    logger.warning(f"Markdown parsing failed, sending plain text: {parse_error}")
                    # Remove markdown formatting and send as plain text
                    plain_text = message_text.replace("**", "").replace("*", "")
                    await update.message.reply_text(plain_text)
            
        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def list_users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            users = await self.api_manager.users.get_all()
            
            if not users:
                await update.message.reply_text("👥 No users found")
                return
            
            lines = ["👥 **Team Members:**\n"]
            for u in users:
                if isinstance(u, dict):
                    name = u.get("full_name", u.get("username", "Unknown"))
                    uid = u.get("id", "N/A")
                    email = u.get("email", "No email")
                    role = u.get("role", "Developer")
                    work_mode = u.get("work_mode", "Remote")
                    active = "🟢" if u.get("active", True) else "🔴"
                    
                    # Format role nicely
                    role_display = role.replace("_", " ").title() if role else "Developer"
                    
                    # Main line with name, ID and status
                    lines.append(f"• {active} {name} (ID: {uid})")
                    
                    # Secondary line with role, work mode and email
                    lines.append(f"  📧 {email}")
                    lines.append(f"  💼 {role_display} | 🏠 {work_mode}")
                    lines.append("")  # Empty line for spacing
                else:
                    lines.append(f"• {str(u)}")
            
            # Remove last empty line
            if lines and lines[-1] == "":
                lines.pop()
            
            message_text = "\n".join(lines)
            
            # Try with markdown first, fallback to plain text
            try:
                await update.message.reply_text(message_text, parse_mode='Markdown')
            except Exception as parse_error:
                logger.warning(f"Markdown parsing failed, sending plain text: {parse_error}")
                # Remove markdown formatting and send as plain text
                plain_text = message_text.replace("**", "").replace("*", "")
                await update.message.reply_text(plain_text)
            
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def handle_natural_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle natural language commands"""
        message = update.message.text.lower()
        original_message = update.message.text
        processing_msg = None
        
        try:
            # Check if message is too long
            if len(original_message) > 2000:
                help_msg = f"""📝 **Mensaje muy largo** ({len(original_message)} caracteres)

Para proyectos complejos, te recomiendo:

🔹 **Resumir la información esencial:**
   • Nombre del proyecto
   • Tecnologías principales  
   • Número de sprints
   • Objetivo general

📋 **Ejemplo:**
   "crear proyecto Bookwise para app de reseñas de libros con TypeScript NextJS, 3 sprints: fundaciones, funcionalidad principal, deploy y mejoras"

🤖 **Luego puedes pedir más detalles:**
   • "agregar más tareas al sprint 1"
   • "crear tareas específicas de autenticación"

¿Quieres intentarlo con un mensaje más corto?"""
                
                await update.message.reply_text(help_msg, parse_mode='Markdown')
                return
            # Check if it's a creation, deletion, or assignment command first, before listing
            create_keywords = ["crear", "agregar", "añadir", "nueva", "nuevo", "create", "add", "creame", "hazme", "genera", "generar"]
            delete_keywords = ["eliminar", "elminame", "delete", "borrar", "remove"]
            assignment_keywords = ["asignar", "assign", "añadele", "añadir al proyecto", "add to project"]
            removal_keywords = ["quita", "quitar", "remover", "sacar", "eliminar usuario", "remove user"]
            is_create_command = any(create_word in message for create_word in create_keywords)
            is_delete_command = any(delete_word in message for delete_word in delete_keywords)
            is_assignment_command = any(assign_word in message for assign_word in assignment_keywords)
            is_removal_command = any(removal_word in message for removal_word in removal_keywords)
            
            # Quick routing for simple list commands (only if NOT creating, deleting, assigning, or removing)
            if not is_create_command and not is_delete_command and not is_assignment_command and not is_removal_command:
                if any(word in message for word in ["mostrar proyecto", "list project", "ver proyecto", "proyectos"]):
                    await self.list_projects_command(update, context)
                    return
                
                if any(word in message for word in ["mostrar sprint", "list sprint", "ver sprint", "sprints"]):
                    await self.list_sprints_command(update, context)
                    return
            
            # Only trigger task list if it's explicitly asking to list/show, not create, delete, assign, or remove
            if not is_create_command and not is_delete_command and not is_assignment_command and not is_removal_command:
                list_keywords = ["mostrar tarea", "list task", "ver tarea", "listar tarea"]
                
                if any(keyword in message for keyword in list_keywords):
                    await self.list_tasks_command(update, context)
                    return
                elif "tareas" in message:
                    await self.list_tasks_command(update, context)
                    return
            
            # Only show users if it's not an assignment or removal command
            if not is_assignment_command and not is_removal_command and any(word in message for word in ["mostrar usuario", "list user", "ver usuario", "usuarios", "users", "equipo", "team", "mostrar equipo", "ver equipo"]):
                await self.list_users_command(update, context)
                return
            
            # For complex operations, use AI + JSON executor
            processing_msg = await update.message.reply_text("🤔 Processing your request...")
            
            # Build context with available projects and sprints
            try:
                projects = await self.api_manager.projects.get_all()
                sprints = await self.api_manager.sprints.get_all()
                
                context = {
                    "available_projects": projects[:5],  # Limit to avoid too much context
                    "available_sprints": sprints[:10]   # Show recent sprints
                }
            except:
                context = {}
            
            # Generate operations with AI
            operations_json = await asyncio.wait_for(
                self.ai_assistant.generate_operations(message, context),
                timeout=30.0
            )
            
            logger.info(f"[BOT] Generated operations: {operations_json}")
            
            # Execute operations
            response_text = await asyncio.wait_for(
                self.json_executor.execute_operations(operations_json, update.effective_user.id, update),
                timeout=60.0
            )
            
            if processing_msg:
                try:
                    await processing_msg.delete()
                except:
                    pass  # Ignore delete errors
            
            # Try with markdown first, fallback to plain text
            try:
                await update.message.reply_text(response_text, parse_mode='Markdown')
            except Exception as parse_error:
                logger.warning(f"Markdown parsing failed, sending plain text: {parse_error}")
                # Check if message is too long for Telegram
                if len(response_text) > 4000:
                    # Split into smaller parts
                    lines = response_text.split('\n')
                    current_chunk = ""
                    
                    for line in lines:
                        if len(current_chunk + line + '\n') > 4000:
                            # Send current chunk
                            plain_chunk = current_chunk.replace("**", "").replace("*", "")
                            await update.message.reply_text(plain_chunk)
                            current_chunk = line + '\n'
                        else:
                            current_chunk += line + '\n'
                    
                    # Send remaining chunk
                    if current_chunk.strip():
                        plain_chunk = current_chunk.replace("**", "").replace("*", "")
                        await update.message.reply_text(plain_chunk)
                else:
                    # Remove markdown formatting and send as plain text
                    plain_text = response_text.replace("**", "").replace("*", "")
                    await update.message.reply_text(plain_text)
            
        except asyncio.TimeoutError:
            if processing_msg:
                try:
                    await processing_msg.delete()
                except:
                    pass
            await update.message.reply_text("⏰ Request timeout. Try simpler commands like '/proyectos'")
            
        except Exception as e:
            logger.error(f"Error in natural message handling: {e}")
            if processing_msg:
                try:
                    await processing_msg.delete()
                except:
                    pass
            
            # Provide helpful error response
            error_msg = f"❌ Error processing request.\n\nTry these instead:\n• /proyectos\n• /sprints\n• /tareas\n• \"crear proyecto MyApp\""
            await update.message.reply_text(error_msg)