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
            
            lines = ["👥 **Users:**\n"]
            for u in users:
                if isinstance(u, dict):
                    name = u.get("full_name", u.get("username", "Unknown"))
                    uid = u.get("id", "N/A")
                    email = u.get("email", "No email")
                    active = "✅" if u.get("active", True) else "❌"
                    lines.append(f"• **{name}** (ID: {uid}) {active}")
                    lines.append(f"  📧 {email}")
                else:
                    lines.append(f"• {str(u)}")
            
            await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def handle_natural_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle natural language commands"""
        message = update.message.text.lower()
        processing_msg = None
        
        try:
            # Check if it's a creation command first, before listing
            create_keywords = ["crear", "agregar", "añadir", "nueva", "nuevo", "create", "add", "creame", "hazme", "genera", "generar"]
            is_create_command = any(create_word in message for create_word in create_keywords)
            
            # Quick routing for simple list commands (only if NOT creating)
            if not is_create_command:
                if any(word in message for word in ["mostrar proyecto", "list project", "ver proyecto", "proyectos"]):
                    await self.list_projects_command(update, context)
                    return
                
                if any(word in message for word in ["mostrar sprint", "list sprint", "ver sprint", "sprints"]):
                    await self.list_sprints_command(update, context)
                    return
            
            # Only trigger task list if it's explicitly asking to list/show, not create
            if not is_create_command:
                list_keywords = ["mostrar tarea", "list task", "ver tarea", "listar tarea"]
                
                if any(keyword in message for keyword in list_keywords):
                    await self.list_tasks_command(update, context)
                    return
                elif "tareas" in message:
                    await self.list_tasks_command(update, context)
                    return
            
            if any(word in message for word in ["mostrar usuario", "list user", "ver usuario", "usuarios"]):
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