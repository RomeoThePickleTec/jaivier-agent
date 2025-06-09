# api/ia_generativa.py
"""Endpoint de IA Generativa para crear proyectos completos automáticamente"""

import json
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import google.generativeai as genai
from config.settings import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# Configure Gemini
if GEMINI_API_KEY and GEMINI_API_KEY != "TU_GEMINI_API_KEY":
    genai.configure(api_key=GEMINI_API_KEY)

class IAGenerativaProjects:
    """Generador de proyectos completos usando IA"""
    
    def __init__(self):
        self.model = None
        self._initialize_model()
        
    def _initialize_model(self):
        """Initialize Gemini model"""
        if not GEMINI_API_KEY or GEMINI_API_KEY == "TU_GEMINI_API_KEY":
            logger.warning("⚠️ Gemini API Key not configured")
            return
        
        try:
            model_names = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.0-pro']
            for model_name in model_names:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    logger.info(f"✅ Model {model_name} initialized")
                    break
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"❌ Error configuring Gemini: {e}")
            self.model = None
    
    async def generate_complete_project(self, project_description: str, api_manager) -> Dict:
        """
        Generate a complete project with sprints and tasks based on description
        
        Args:
            project_description: Natural language description of the project
            api_manager: API manager for creating the project
            
        Returns:
            Dict with success status and created project details
        """
        try:
            logger.info(f"Generating complete project from description: {project_description[:100]}...")
            
            # Generate project structure using AI
            project_structure = await self._generate_project_structure(project_description)
            
            if not project_structure:
                return {"success": False, "error": "Failed to generate project structure"}
            
            # Create the actual project, sprints, and tasks
            result = await self._create_project_from_structure(project_structure, api_manager)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in generate_complete_project: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_project_structure(self, description: str) -> Optional[Dict]:
        """Generate project structure using AI"""
        
        if not self.model:
            # Fallback structure without AI
            return self._generate_fallback_structure(description)
        
        try:
            prompt = f"""
            You are a project management AI expert. Based on the following project description, generate a complete project structure with sprints and tasks.

            Project Description: "{description}"

            Generate a JSON response with the following structure:
            {{
                "project": {{
                    "name": "Project Name",
                    "description": "Brief project description",
                    "technologies": ["tech1", "tech2"],
                    "duration_weeks": 8,
                    "team_size": 3
                }},
                "sprints": [
                    {{
                        "name": "Sprint 1 - Setup",
                        "description": "Initial setup and configuration",
                        "duration_weeks": 2,
                        "objectives": ["obj1", "obj2"]
                    }}
                ],
                "tasks": [
                    {{
                        "title": "Setup development environment",
                        "description": "Configure development tools and environment",
                        "sprint_index": 0,
                        "priority": "high",
                        "estimated_hours": 8,
                        "dependencies": []
                    }}
                ]
            }}

            IMPORTANT GUIDELINES:
            1. Create 3-5 sprints depending on project complexity
            2. Each sprint should have 4-8 tasks
            3. Tasks should be specific and actionable
            4. Use appropriate priorities: low, medium, high, critical
            5. Estimate realistic hours for each task
            6. Consider dependencies between tasks
            7. Progressive complexity from basic setup to advanced features
            8. Include testing, documentation, and deployment tasks

            Generate a realistic and well-structured project plan.
            """
            
            response = self.model.generate_content(prompt)
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\\{.*\\}', response.text, re.DOTALL)
            if json_match:
                try:
                    structure = json.loads(json_match.group())
                    logger.info(f"Generated project structure with {len(structure.get('sprints', []))} sprints and {len(structure.get('tasks', []))} tasks")
                    return structure
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing AI JSON response: {e}")
                    return self._generate_fallback_structure(description)
            else:
                logger.warning("No JSON found in AI response")
                return self._generate_fallback_structure(description)
                
        except Exception as e:
            logger.error(f"Error generating project structure with AI: {e}")
            return self._generate_fallback_structure(description)
    
    def _generate_fallback_structure(self, description: str) -> Dict:
        """Generate fallback structure without AI"""
        
        # Extract project name from description
        lines = description.split('\n')
        project_name = "Generated Project"
        
        for line in lines:
            if "proyecto:" in line.lower() or "project:" in line.lower():
                project_name = line.split(':')[-1].strip()
                break
        
        # Detect if it's a specific type of project
        desc_lower = description.lower()
        
        if any(word in desc_lower for word in ["esp32", "arduino", "sensor", "iot", "hardware"]):
            return self._generate_iot_project_structure(project_name, description)
        elif any(word in desc_lower for word in ["web", "frontend", "backend", "api", "dashboard"]):
            return self._generate_web_project_structure(project_name, description)
        elif any(word in desc_lower for word in ["mobile", "app", "android", "ios", "react native"]):
            return self._generate_mobile_project_structure(project_name, description)
        else:
            return self._generate_generic_project_structure(project_name, description)
    
    def _generate_iot_project_structure(self, name: str, description: str) -> Dict:
        """Generate IoT/Hardware project structure"""
        return {
            "project": {
                "name": name,
                "description": "IoT project with hardware components and data monitoring",
                "technologies": ["ESP32", "Sensors", "MicroPython", "Firebase", "React"],
                "duration_weeks": 6,
                "team_size": 2
            },
            "sprints": [
                {
                    "name": "Sprint 1 - Hardware Setup",
                    "description": "Hardware configuration and basic sensor testing",
                    "duration_weeks": 1,
                    "objectives": ["Hardware assembly", "Basic sensor readings", "Serial communication"]
                },
                {
                    "name": "Sprint 2 - Logic Implementation", 
                    "description": "Implement automation logic and control systems",
                    "duration_weeks": 2,
                    "objectives": ["Automation logic", "Control systems", "Configuration"]
                },
                {
                    "name": "Sprint 3 - Communication & Dashboard",
                    "description": "Data transmission and web dashboard",
                    "duration_weeks": 2,
                    "objectives": ["Data transmission", "Web dashboard", "Real-time monitoring"]
                },
                {
                    "name": "Sprint 4 - Testing & Deployment",
                    "description": "Integration testing and final deployment",
                    "duration_weeks": 1,
                    "objectives": ["Integration testing", "Performance optimization", "Documentation"]
                }
            ],
            "tasks": [
                # Sprint 1 tasks
                {"title": "Configure ESP32 development environment", "description": "Setup IDE and drivers", "sprint_index": 0, "priority": "high", "estimated_hours": 4, "dependencies": []},
                {"title": "Connect and test sensors", "description": "Wire sensors and verify readings", "sprint_index": 0, "priority": "high", "estimated_hours": 6, "dependencies": []},
                {"title": "Implement serial communication", "description": "Setup serial debugging and monitoring", "sprint_index": 0, "priority": "medium", "estimated_hours": 3, "dependencies": []},
                {"title": "Create electrical diagram", "description": "Document circuit connections", "sprint_index": 0, "priority": "low", "estimated_hours": 2, "dependencies": []},
                
                # Sprint 2 tasks
                {"title": "Implement threshold logic", "description": "Define sensor thresholds and triggers", "sprint_index": 1, "priority": "high", "estimated_hours": 5, "dependencies": []},
                {"title": "Add automatic control", "description": "Implement automated responses", "sprint_index": 1, "priority": "high", "estimated_hours": 8, "dependencies": []},
                {"title": "Create configuration system", "description": "Allow runtime configuration", "sprint_index": 1, "priority": "medium", "estimated_hours": 6, "dependencies": []},
                {"title": "Test offline operation", "description": "Verify system works without PC", "sprint_index": 1, "priority": "medium", "estimated_hours": 4, "dependencies": []},
                
                # Sprint 3 tasks
                {"title": "Implement data transmission", "description": "Send data via HTTP/MQTT", "sprint_index": 2, "priority": "high", "estimated_hours": 8, "dependencies": []},
                {"title": "Create web dashboard", "description": "Build React dashboard with Firebase", "sprint_index": 2, "priority": "high", "estimated_hours": 12, "dependencies": []},
                {"title": "Add real-time monitoring", "description": "Display live sensor data", "sprint_index": 2, "priority": "medium", "estimated_hours": 6, "dependencies": []},
                {"title": "Implement data history", "description": "Store and display historical data", "sprint_index": 2, "priority": "medium", "estimated_hours": 8, "dependencies": []},
                
                # Sprint 4 tasks
                {"title": "Integration testing", "description": "Test complete system integration", "sprint_index": 3, "priority": "high", "estimated_hours": 8, "dependencies": []},
                {"title": "Performance optimization", "description": "Optimize code and performance", "sprint_index": 3, "priority": "medium", "estimated_hours": 6, "dependencies": []},
                {"title": "Create documentation", "description": "Write user and technical documentation", "sprint_index": 3, "priority": "medium", "estimated_hours": 4, "dependencies": []},
                {"title": "Final deployment", "description": "Deploy and configure final system", "sprint_index": 3, "priority": "high", "estimated_hours": 4, "dependencies": []}
            ]
        }
    
    def _generate_web_project_structure(self, name: str, description: str) -> Dict:
        """Generate Web project structure"""
        return {
            "project": {
                "name": name,
                "description": "Web application with frontend and backend components",
                "technologies": ["React", "Node.js", "Express", "MongoDB", "TailwindCSS"],
                "duration_weeks": 8,
                "team_size": 3
            },
            "sprints": [
                {
                    "name": "Sprint 1 - Foundation",
                    "description": "Project setup and basic architecture",
                    "duration_weeks": 2,
                    "objectives": ["Project setup", "Basic authentication", "Database design"]
                },
                {
                    "name": "Sprint 2 - Core Features",
                    "description": "Main application functionality",
                    "duration_weeks": 3,
                    "objectives": ["Core features", "API development", "UI components"]
                },
                {
                    "name": "Sprint 3 - Advanced Features",
                    "description": "Advanced functionality and integrations",
                    "duration_weeks": 2,
                    "objectives": ["Advanced features", "Integrations", "Performance optimization"]
                },
                {
                    "name": "Sprint 4 - Testing & Deployment",
                    "description": "Testing, optimization, and deployment",
                    "duration_weeks": 1,
                    "objectives": ["Testing", "Bug fixes", "Production deployment"]
                }
            ],
            "tasks": [
                # Sprint 1
                {"title": "Setup development environment", "description": "Configure dev tools and environment", "sprint_index": 0, "priority": "high", "estimated_hours": 4, "dependencies": []},
                {"title": "Create project structure", "description": "Setup frontend and backend structure", "sprint_index": 0, "priority": "high", "estimated_hours": 6, "dependencies": []},
                {"title": "Implement authentication system", "description": "User login and registration", "sprint_index": 0, "priority": "high", "estimated_hours": 12, "dependencies": []},
                {"title": "Design database schema", "description": "Create database models and relationships", "sprint_index": 0, "priority": "high", "estimated_hours": 8, "dependencies": []},
                
                # Sprint 2
                {"title": "Build API endpoints", "description": "Create REST API endpoints", "sprint_index": 1, "priority": "high", "estimated_hours": 16, "dependencies": []},
                {"title": "Create UI components", "description": "Build reusable React components", "sprint_index": 1, "priority": "high", "estimated_hours": 20, "dependencies": []},
                {"title": "Implement main features", "description": "Core application functionality", "sprint_index": 1, "priority": "high", "estimated_hours": 24, "dependencies": []},
                {"title": "Add form validation", "description": "Client and server-side validation", "sprint_index": 1, "priority": "medium", "estimated_hours": 8, "dependencies": []},
                
                # Sprint 3
                {"title": "Add advanced features", "description": "Complex business logic features", "sprint_index": 2, "priority": "high", "estimated_hours": 20, "dependencies": []},
                {"title": "Implement file upload", "description": "File handling and storage", "sprint_index": 2, "priority": "medium", "estimated_hours": 10, "dependencies": []},
                {"title": "Add search functionality", "description": "Search and filtering capabilities", "sprint_index": 2, "priority": "medium", "estimated_hours": 12, "dependencies": []},
                {"title": "Performance optimization", "description": "Optimize loading and performance", "sprint_index": 2, "priority": "medium", "estimated_hours": 8, "dependencies": []},
                
                # Sprint 4
                {"title": "Write comprehensive tests", "description": "Unit and integration tests", "sprint_index": 3, "priority": "high", "estimated_hours": 16, "dependencies": []},
                {"title": "Fix bugs and issues", "description": "Address testing feedback", "sprint_index": 3, "priority": "high", "estimated_hours": 12, "dependencies": []},
                {"title": "Setup production deployment", "description": "Configure production environment", "sprint_index": 3, "priority": "high", "estimated_hours": 8, "dependencies": []},
                {"title": "Create documentation", "description": "User and developer documentation", "sprint_index": 3, "priority": "medium", "estimated_hours": 6, "dependencies": []}
            ]
        }
    
    def _generate_mobile_project_structure(self, name: str, description: str) -> Dict:
        """Generate Mobile app project structure"""
        return {
            "project": {
                "name": name,
                "description": "Mobile application for iOS and Android",
                "technologies": ["React Native", "Expo", "Firebase", "Redux", "TypeScript"],
                "duration_weeks": 10,
                "team_size": 3
            },
            "sprints": [
                {
                    "name": "Sprint 1 - Setup & Navigation",
                    "description": "Project setup and navigation structure",
                    "duration_weeks": 2,
                    "objectives": ["Development setup", "Navigation", "Basic screens"]
                },
                {
                    "name": "Sprint 2 - Authentication & Core",
                    "description": "User authentication and core features",
                    "duration_weeks": 3,
                    "objectives": ["Authentication", "Core features", "Data management"]
                },
                {
                    "name": "Sprint 3 - Advanced Features",
                    "description": "Advanced functionality and integrations",
                    "duration_weeks": 3,
                    "objectives": ["Advanced features", "Push notifications", "Offline support"]
                },
                {
                    "name": "Sprint 4 - Polish & Release",
                    "description": "UI polish, testing, and app store release",
                    "duration_weeks": 2,
                    "objectives": ["UI polish", "Testing", "App store submission"]
                }
            ],
            "tasks": [
                # Sprint 1
                {"title": "Setup React Native environment", "description": "Configure development environment", "sprint_index": 0, "priority": "high", "estimated_hours": 6, "dependencies": []},
                {"title": "Create navigation structure", "description": "Setup navigation between screens", "sprint_index": 0, "priority": "high", "estimated_hours": 10, "dependencies": []},
                {"title": "Design basic screens", "description": "Create main app screens", "sprint_index": 0, "priority": "high", "estimated_hours": 16, "dependencies": []},
                {"title": "Setup state management", "description": "Configure Redux/Context", "sprint_index": 0, "priority": "medium", "estimated_hours": 8, "dependencies": []},
                
                # Sprint 2
                {"title": "Implement authentication", "description": "User login and registration", "sprint_index": 1, "priority": "high", "estimated_hours": 16, "dependencies": []},
                {"title": "Create core features", "description": "Main app functionality", "sprint_index": 1, "priority": "high", "estimated_hours": 24, "dependencies": []},
                {"title": "Add data persistence", "description": "Local and remote data storage", "sprint_index": 1, "priority": "high", "estimated_hours": 12, "dependencies": []},
                {"title": "Implement user profiles", "description": "User profile management", "sprint_index": 1, "priority": "medium", "estimated_hours": 10, "dependencies": []},
                
                # Sprint 3
                {"title": "Add push notifications", "description": "Firebase push notifications", "sprint_index": 2, "priority": "high", "estimated_hours": 12, "dependencies": []},
                {"title": "Implement offline support", "description": "Offline functionality", "sprint_index": 2, "priority": "medium", "estimated_hours": 16, "dependencies": []},
                {"title": "Add camera integration", "description": "Camera and media features", "sprint_index": 2, "priority": "medium", "estimated_hours": 10, "dependencies": []},
                {"title": "Social features", "description": "Sharing and social integration", "sprint_index": 2, "priority": "low", "estimated_hours": 14, "dependencies": []},
                
                # Sprint 4
                {"title": "UI/UX improvements", "description": "Polish user interface", "sprint_index": 3, "priority": "high", "estimated_hours": 16, "dependencies": []},
                {"title": "Performance optimization", "description": "Optimize app performance", "sprint_index": 3, "priority": "high", "estimated_hours": 10, "dependencies": []},
                {"title": "Test on devices", "description": "Test on real devices", "sprint_index": 3, "priority": "high", "estimated_hours": 12, "dependencies": []},
                {"title": "App store submission", "description": "Prepare and submit to stores", "sprint_index": 3, "priority": "high", "estimated_hours": 8, "dependencies": []}
            ]
        }
    
    def _generate_generic_project_structure(self, name: str, description: str) -> Dict:
        """Generate generic project structure"""
        return {
            "project": {
                "name": name,
                "description": "Software development project",
                "technologies": ["To be defined"],
                "duration_weeks": 6,
                "team_size": 3
            },
            "sprints": [
                {
                    "name": "Sprint 1 - Planning & Setup",
                    "description": "Project planning and initial setup",
                    "duration_weeks": 1,
                    "objectives": ["Requirements analysis", "Architecture design", "Development setup"]
                },
                {
                    "name": "Sprint 2 - Core Development",
                    "description": "Core functionality implementation",
                    "duration_weeks": 3,
                    "objectives": ["Core features", "Basic functionality", "Initial testing"]
                },
                {
                    "name": "Sprint 3 - Testing & Deployment",
                    "description": "Testing, bug fixes, and deployment",
                    "duration_weeks": 2,
                    "objectives": ["Testing", "Bug fixes", "Deployment preparation"]
                }
            ],
            "tasks": [
                {"title": "Requirements analysis", "description": "Analyze and document requirements", "sprint_index": 0, "priority": "high", "estimated_hours": 8, "dependencies": []},
                {"title": "Architecture design", "description": "Design system architecture", "sprint_index": 0, "priority": "high", "estimated_hours": 12, "dependencies": []},
                {"title": "Development environment setup", "description": "Setup development tools", "sprint_index": 0, "priority": "high", "estimated_hours": 6, "dependencies": []},
                {"title": "Core feature implementation", "description": "Implement main features", "sprint_index": 1, "priority": "high", "estimated_hours": 40, "dependencies": []},
                {"title": "Testing implementation", "description": "Write and run tests", "sprint_index": 2, "priority": "high", "estimated_hours": 16, "dependencies": []},
                {"title": "Deployment preparation", "description": "Prepare for production deployment", "sprint_index": 2, "priority": "high", "estimated_hours": 12, "dependencies": []}
            ]
        }
    
    async def _create_project_from_structure(self, structure: Dict, api_manager) -> Dict:
        """Create actual project, sprints, and tasks from structure"""
        try:
            logger.info("Creating project from generated structure...")
            
            project_info = structure.get("project", {})
            sprints_info = structure.get("sprints", [])
            tasks_info = structure.get("tasks", [])
            
            # Create project
            project_data = {
                "name": project_info.get("name", "Generated Project"),
                "description": project_info.get("description", "AI Generated Project"),
                "start_date": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end_date": (datetime.now() + timedelta(weeks=project_info.get("duration_weeks", 6))).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "status": 0  # Active
            }
            
            project_result = await api_manager.projects.create(project_data)
            if not project_result or project_result.get("error"):
                return {"success": False, "error": "Failed to create project"}
            
            # Wait and get the created project
            await asyncio.sleep(0.5)
            projects = await api_manager.projects.get_all()
            project = None
            for p in projects:
                if p.get("name") == project_data["name"]:
                    project = p
                    break
            
            if not project:
                return {"success": False, "error": "Could not find created project"}
            
            project_id = project.get("id")
            created_sprints = []
            
            # Create sprints
            for i, sprint_info in enumerate(sprints_info):
                sprint_data = {
                    "name": sprint_info.get("name", f"Sprint {i+1}"),
                    "description": sprint_info.get("description", ""),
                    "project_id": project_id,
                    "start_date": (datetime.now() + timedelta(weeks=i*2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "end_date": (datetime.now() + timedelta(weeks=(i+1)*2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "status": 0  # Active
                }
                
                sprint_result = await api_manager.sprints.create(sprint_data)
                if sprint_result and not sprint_result.get("error"):
                    await asyncio.sleep(0.3)
                    # Get created sprint
                    sprints = await api_manager.sprints.get_all(project_id)
                    for s in sprints:
                        if s.get("name") == sprint_data["name"] and s not in created_sprints:
                            created_sprints.append(s)
                            break
            
            logger.info(f"Created {len(created_sprints)} sprints")
            
            # Create tasks
            created_tasks = 0
            for task_info in tasks_info:
                sprint_index = task_info.get("sprint_index", 0)
                if sprint_index < len(created_sprints):
                    sprint_id = created_sprints[sprint_index].get("id")
                    
                    # Convert priority to number
                    priority_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
                    priority = priority_map.get(task_info.get("priority", "medium"), 2)
                    
                    task_data = {
                        "title": task_info.get("title", "Task"),
                        "description": task_info.get("description", ""),
                        "project_id": project_id,
                        "sprint_id": sprint_id,
                        "priority": priority,
                        "status": 0,  # TODO
                        "estimated_hours": task_info.get("estimated_hours", 8),
                        "due_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
                    }
                    
                    task_result = await api_manager.tasks.create(task_data)
                    if task_result and not task_result.get("error"):
                        created_tasks += 1
                    
                    await asyncio.sleep(0.1)  # Small delay to avoid overwhelming API
            
            return {
                "success": True,
                "data": {
                    "project": project,
                    "sprints_created": len(created_sprints),
                    "tasks_created": created_tasks,
                    "total_items": 1 + len(created_sprints) + created_tasks
                },
                "summary": f"✅ AI Generated project '{project_data['name']}' created successfully!\n\n📁 Project: {project_data['name']}\n🏃 Sprints: {len(created_sprints)}\n📋 Tasks: {created_tasks}\n🤖 Generated by AI"
            }
            
        except Exception as e:
            logger.error(f"Error creating project from structure: {e}")
            return {"success": False, "error": str(e)}

# Global instance
ia_generativa = IAGenerativaProjects()