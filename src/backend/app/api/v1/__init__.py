"""API v1 routes."""

from litestar import Router

from app.api.v1.users import UserController
from app.api.v1.exams import ExamController
from app.api.v1.conversations import ConversationController


api_v1_router = Router(
    path="/api/v1",
    route_handlers=[
        UserController,
        ExamController,
        ConversationController,
    ],
    tags=["API v1"],
)
