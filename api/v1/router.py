from fastapi import APIRouter

from api.v1.auth.router import router as auth_router
from api.v1.users.router import router as users_router
from api.v1.organizations.router import router as organizations_router
from api.v1.periods.router import router as periods_router
from api.v1.plan.router import router as plan_router
from api.v1.do.router import router as do_router
from api.v1.check.router import router as check_router
from api.v1.action.router import router as action_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(organizations_router)
api_router.include_router(periods_router)
api_router.include_router(plan_router)
api_router.include_router(do_router)
api_router.include_router(check_router)
api_router.include_router(action_router)
