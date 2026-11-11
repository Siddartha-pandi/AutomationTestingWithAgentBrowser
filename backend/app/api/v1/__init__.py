"""API v1 master router module."""

from fastapi import APIRouter

from backend.app.api.v1.artifacts import router as artifacts_router
from backend.app.api.v1.audit import router as audit_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.browser import router as browser_router
from backend.app.api.v1.recorder import router as recorder_router
from backend.app.api.v1.credentials import router as credentials_router
from backend.app.api.v1.dom import router as dom_router
from backend.app.api.v1.elements import router as elements_router
from backend.app.api.v1.environments import router as environments_router
from backend.app.api.v1.executions import router as executions_router
from backend.app.api.v1.flows import router as flows_router
from backend.app.api.v1.healing import router as healing_router
from backend.app.api.v1.projects import router as projects_router
from backend.app.api.v1.reports import router as reports_router
from backend.app.api.v1.roles import router as roles_router
from backend.app.api.v1.schedules import router as schedules_router
from backend.app.api.v1.test_suites import router as test_suites_router
from backend.app.api.v1.tests import router as tests_router
from backend.app.api.v1.users import router as users_router
from backend.app.api.v1.ws_monitor import router as ws_monitor_router

api_v1_router = APIRouter(prefix="/api/v1")

# Authentication, Users & Roles
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(roles_router)

# Projects, Environments & Credentials
api_v1_router.include_router(projects_router)
api_v1_router.include_router(environments_router)
api_v1_router.include_router(credentials_router)

# Automation Flows & Testing
api_v1_router.include_router(flows_router)
api_v1_router.include_router(tests_router)
api_v1_router.include_router(test_suites_router)
api_v1_router.include_router(schedules_router)

# Browser Intelligence, Recorder & Self-Healing
api_v1_router.include_router(browser_router)
api_v1_router.include_router(recorder_router)
api_v1_router.include_router(dom_router)
api_v1_router.include_router(elements_router)
api_v1_router.include_router(healing_router)

# Executions, Artifacts, Reports, WebSocket & Audit
api_v1_router.include_router(executions_router)
api_v1_router.include_router(ws_monitor_router)
api_v1_router.include_router(artifacts_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(audit_router)
