""""
Configuramos aquí las llamadas al backend, las cuales obtienen toda la información del usuario
"""
##
# Hay que reemplazar las llamadas con la librería correcta 
##

BASE_URL = "http://back-api:8080"

tasks = "/tasklist"
sprints = "/sprintlist"
users = "/userlist"
projects = "/projectlist"
login = "/auth/login"
assignees = "/assignee"

def login(url=BASE_URL):
    request(url+login).json()

def getUsers(url=BASE_URL):
    request(url).json()

def getProjects(url=BASE_URL):
    request(url).json()

def getTasks(url=BASE_URL):
    request(url).json()

def getAssignees(url=BASE_URL):
    request(url).json()

def getSprints(url=BASE_URL):
    request(url).json()

def sendRequest(url=BASE_URL):