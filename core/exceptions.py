from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_429_TOO_MANY_REQUESTS,
)


class AppException(Exception):
    def __init__(self, status_code: int, error_code: str, message: str):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(message)


# Auth
class InvalidCredentialsError(AppException):
    def __init__(self):
        super().__init__(HTTP_401_UNAUTHORIZED, "AUTH_001", "Invalid username or password")


class AccountDisabledError(AppException):
    def __init__(self):
        super().__init__(HTTP_403_FORBIDDEN, "AUTH_002", "Account is disabled")


class TokenInvalidError(AppException):
    def __init__(self, msg: str = "Token is invalid or expired"):
        super().__init__(HTTP_401_UNAUTHORIZED, "AUTH_003", msg)


class TokenRevokedError(AppException):
    def __init__(self):
        super().__init__(HTTP_401_UNAUTHORIZED, "AUTH_004", "Token has been revoked")


class RateLimitError(AppException):
    def __init__(self):
        super().__init__(HTTP_429_TOO_MANY_REQUESTS, "AUTH_005", "Too many requests")


class WeakPasswordError(AppException):
    def __init__(self):
        super().__init__(HTTP_400_BAD_REQUEST, "AUTH_006",
                         "Password must be at least 6 characters")


class WrongPasswordError(AppException):
    def __init__(self):
        super().__init__(HTTP_400_BAD_REQUEST, "AUTH_007", "Current password is incorrect")


class ResetTokenInvalidError(AppException):
    def __init__(self):
        super().__init__(HTTP_400_BAD_REQUEST, "AUTH_008", "Reset token is invalid or expired")


class SessionNotFoundError(AppException):
    def __init__(self):
        super().__init__(HTTP_404_NOT_FOUND, "AUTH_009", "Session not found")


class SessionAccessDeniedError(AppException):
    def __init__(self):
        super().__init__(HTTP_403_FORBIDDEN, "AUTH_010", "Cannot access this session")


# Users
class UserNotFoundError(AppException):
    def __init__(self):
        super().__init__(HTTP_404_NOT_FOUND, "USER_001", "User not found")


class UsernameExistsError(AppException):
    def __init__(self):
        super().__init__(HTTP_409_CONFLICT, "USER_002", "Username already exists")


class EmailExistsError(AppException):
    def __init__(self):
        super().__init__(HTTP_409_CONFLICT, "USER_003", "Email already exists")


class UserAccessDeniedError(AppException):
    def __init__(self):
        super().__init__(HTTP_403_FORBIDDEN, "USER_004", "Access denied to this user")


class UserModifyDeniedError(AppException):
    def __init__(self):
        super().__init__(HTTP_403_FORBIDDEN, "USER_005", "Cannot modify this user")


class UserDeleteDeniedError(AppException):
    def __init__(self):
        super().__init__(HTTP_403_FORBIDDEN, "USER_006", "Cannot delete this user")


# Organizations
class DepartmentNotFoundError(AppException):
    def __init__(self):
        super().__init__(HTTP_404_NOT_FOUND, "ORG_001", "Department not found")


class DepartmentCodeExistsError(AppException):
    def __init__(self):
        super().__init__(HTTP_409_CONFLICT, "ORG_002", "Department code already exists")


class DepartmentHasChildrenError(AppException):
    def __init__(self):
        super().__init__(HTTP_400_BAD_REQUEST, "ORG_003",
                         "Cannot delete department with sub-departments")


class DepartmentHasMembersError(AppException):
    def __init__(self):
        super().__init__(HTTP_400_BAD_REQUEST, "ORG_004",
                         "Cannot delete department with members")


class DepartmentParentInvalidError(AppException):
    def __init__(self):
        super().__init__(HTTP_400_BAD_REQUEST, "ORG_008",
                         "Cannot set department parent to itself or its descendant")


class PositionNotFoundError(AppException):
    def __init__(self):
        super().__init__(HTTP_404_NOT_FOUND, "ORG_005", "Position not found")


class PositionCodeExistsError(AppException):
    def __init__(self):
        super().__init__(HTTP_409_CONFLICT, "ORG_006", "Position code already exists")


class PositionHasMembersError(AppException):
    def __init__(self):
        super().__init__(HTTP_400_BAD_REQUEST, "ORG_007",
                         "Cannot delete position with members")


class PermissionDeniedError(AppException):
    def __init__(self, msg: str = "Permission denied"):
        super().__init__(HTTP_403_FORBIDDEN, "FORBIDDEN", msg)


# Periods
class PeriodNotFoundError(AppException):
    def __init__(self):
        super().__init__(HTTP_404_NOT_FOUND, "PERIOD_001", "Period not found")


class PeriodDateConflictError(AppException):
    def __init__(self, msg: str = "Period date conflict"):
        super().__init__(HTTP_409_CONFLICT, "PERIOD_002", msg)


class PeriodStatusTransitionError(AppException):
    def __init__(self, msg: str = "Invalid status transition"):
        super().__init__(HTTP_400_BAD_REQUEST, "PERIOD_003", msg)


class PeriodDeleteDeniedError(AppException):
    def __init__(self, msg: str = "Cannot delete this period"):
        super().__init__(HTTP_403_FORBIDDEN, "PERIOD_004", msg)


# Plan Phase
class JobAnalysisFailedError(AppException):
    def __init__(self, msg: str = "Job analysis failed"):
        super().__init__(HTTP_400_BAD_REQUEST, "PLAN_001", msg)


class ContractGenerationFailedError(AppException):
    def __init__(self, msg: str = "Contract generation failed"):
        super().__init__(HTTP_400_BAD_REQUEST, "PLAN_002", msg)


class ContractConfirmedError(AppException):
    def __init__(self):
        super().__init__(HTTP_400_BAD_REQUEST, "PLAN_003", "Cannot modify confirmed contract")


class GoalAlreadyExistsError(AppException):
    def __init__(self):
        super().__init__(HTTP_400_BAD_REQUEST, "PLAN_007", "A goal already exists for this user and period")


class IndicatorWeightError(AppException):
    def __init__(self, msg: str = "Indicator weight validation failed"):
        super().__init__(HTTP_400_BAD_REQUEST, "PLAN_004", msg)


class PrototypeNotFoundError(AppException):
    def __init__(self):
        super().__init__(HTTP_404_NOT_FOUND, "PLAN_005", "Job prototype not found")


class ContractNotFoundError(AppException):
    def __init__(self):
        super().__init__(HTTP_404_NOT_FOUND, "PLAN_006", "Contract not found")


# Do Phase


class PeriodNotOpenError(AppException):
    def __init__(self):
        super().__init__(HTTP_400_BAD_REQUEST, "DO_002", "Period is not open, cannot submit data")


class DiagnosticReportGenerationError(AppException):
    def __init__(self, msg: str = "Diagnostic report generation failed"):
        super().__init__(HTTP_400_BAD_REQUEST, "DO_003", msg)


class CoachingRequestNotFoundError(AppException):
    def __init__(self):
        super().__init__(HTTP_404_NOT_FOUND, "DO_004", "Coaching request not found")


# Check Phase
class SelfAssessmentNotFoundError(AppException):
    def __init__(self):
        super().__init__(HTTP_404_NOT_FOUND, "CHECK_001", "Self assessment not found")


class EvaluationTaskNotFoundError(AppException):
    def __init__(self):
        super().__init__(HTTP_404_NOT_FOUND, "CHECK_002", "Evaluation task not found")


class SelfAssessmentRequiredError(AppException):
    def __init__(self):
        super().__init__(HTTP_400_BAD_REQUEST, "CHECK_003", "Self assessment must be submitted before evaluation")


class SelfAssessmentAlreadySubmittedError(AppException):
    def __init__(self):
        super().__init__(HTTP_400_BAD_REQUEST, "CHECK_004", "Self assessment already submitted, cannot modify")


class WeightValidationError(AppException):
    def __init__(self, msg: str = "Indicator weight validation failed"):
        super().__init__(HTTP_400_BAD_REQUEST, "CHECK_005", msg)


class ScoreAggregateNotFoundError(AppException):
    def __init__(self):
        super().__init__(HTTP_404_NOT_FOUND, "CHECK_006", "Score aggregate not found")


class FinalResultNotFoundError(AppException):
    def __init__(self):
        super().__init__(HTTP_404_NOT_FOUND, "CHECK_007", "Final result not found")


# Action Phase
class ReviewReportNotFoundError(AppException):
    def __init__(self):
        super().__init__(HTTP_404_NOT_FOUND, "ACTION_001", "Review report not found")


class DevelopmentPlanNotFoundError(AppException):
    def __init__(self):
        super().__init__(HTTP_404_NOT_FOUND, "ACTION_002", "Development plan not found")


class PlanAlreadySubmittedError(AppException):
    def __init__(self):
        super().__init__(HTTP_400_BAD_REQUEST, "ACTION_003", "Plan already submitted, cannot modify")


class InheritanceSuggestionNotFoundError(AppException):
    def __init__(self):
        super().__init__(HTTP_404_NOT_FOUND, "ACTION_004", "Inheritance suggestion not found")


class FinalResultNotFoundError(AppException):
    def __init__(self):
        super().__init__(HTTP_404_NOT_FOUND, "CHECK_007", "Final result not found")


def add_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error_code": exc.error_code, "message": exc.message},
        )
