from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from accounts import views as acc
from labs import views as labs

router = DefaultRouter()
router.register("departments", acc.DepartmentViewSet, basename="department")
router.register("subjects", acc.SubjectViewSet, basename="subject")
router.register("users", acc.UserViewSet, basename="user")
router.register("practicals", labs.PracticalViewSet, basename="practical")

api = [
    path("auth/login/", acc.login),
    path("auth/refresh/", TokenRefreshView.as_view()),
    path("auth/me/", acc.me),
    path("client-status/", acc.client_status),
    path("college-settings/", acc.college_settings),
    path("workspace/<int:practical_id>/", labs.workspace),
    path("workspace/<int:practical_id>/save/", labs.workspace_save),
    path("workspace/<int:practical_id>/run/", labs.workspace_run),
    path("workspace/<int:practical_id>/run-async/", labs.workspace_run_async),
    path("workspace/<int:practical_id>/events/", labs.workspace_events),
    path("workspace/<int:practical_id>/submit/", labs.workspace_submit),
    path("executions/<int:pk>/", labs.execution_detail),
    path("submissions/<int:pk>/", labs.submission_detail),
    path("submissions/<int:pk>/approve/", labs.submission_approve),
    path("submissions/<int:pk>/request-correction/", labs.submission_request_correction),
    path("submissions/<int:pk>/ai-summary/", labs.submission_ai_summary),
    path("records/", labs.record_overview),
    path("records/subject/<int:subject_id>/", labs.record_subject),
    path("records/submission/<int:pk>/", labs.record_single),
    path("reports/subject/<int:subject_id>/", labs.subject_report),
    path("", include(router.urls)),
]

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/", include(api)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Optional: serve the built React app from Django (single-server test / small installs).
# Production should serve frontend/dist with Nginx instead (deploy/nginx.conf).
if settings.FRONTEND_DIST and (settings.FRONTEND_DIST / "index.html").exists():
    urlpatterns += [
        re_path(r"^assets/(?P<path>.*)$", serve, {"document_root": settings.FRONTEND_DIST / "assets"}),
        re_path(r"^(?!api/|django-admin/|media/).*$", serve, {"document_root": settings.FRONTEND_DIST, "path": "index.html"}),
    ]
