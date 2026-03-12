"""API v1 routes."""

from app.api.v1.admin import AdminController
from app.api.v1.conversations import ConversationController
from app.api.v1.exams import ExamController
from app.api.v1.ielts import IELTSController
from app.api.v1.practice import PracticeController
from app.api.v1.speech import SpeechController
from app.api.v1.users import UserController
from litestar import Router

api_v1_router = Router(
    path="/api/v1",
    route_handlers=[
        UserController,
        ExamController,
        ConversationController,
        PracticeController,
        IELTSController,
        SpeechController,
        AdminController,
    ],
    tags=["API v1"],
)
