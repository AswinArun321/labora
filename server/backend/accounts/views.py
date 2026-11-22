import csv
import io

from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from labs.secure_browser import is_secure_browser_request

from .models import CollegeSettings, Department, Subject, User
from .permissions import IsAdminRole, ReadOnlyOrAdmin
from .serializers import (CollegeSettingsSerializer, DepartmentSerializer, MeSerializer, SubjectSerializer,
                          UserSerializer)


from rest_framework_simplejwt.views import TokenRefreshView


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class RefreshThrottle(AnonRateThrottle):
    scope = "refresh"


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [RefreshThrottle]


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def login(request):
    user = authenticate(username=request.data.get("username", ""), password=request.data.get("password", ""))
    if user is None or not user.is_active:
        return Response({"detail": "Invalid username or password."}, status=status.HTTP_401_UNAUTHORIZED)
    if user.is_student and CollegeSettings.load().students_secure_browser_only and not is_secure_browser_request(request):
        return Response({"detail": "Students must sign in from the LABORA Secure Browser.",
                         "code": "secure_browser_required"}, status=status.HTTP_403_FORBIDDEN)
    refresh = RefreshToken.for_user(user)
    return Response({"access": str(refresh.access_token), "refresh": str(refresh),
                     "user": MeSerializer(user).data})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    refresh_token = request.data.get("refresh")
    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass
    return Response({"detail": "Successfully logged out."})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(MeSerializer(request.user).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def client_status(request):
    """Lets the UI show whether the server recognised the secure browser."""
    return Response({"secure_browser": is_secure_browser_request(request),
                     "college_name": CollegeSettings.load().college_name})


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [ReadOnlyOrAdmin]


class SubjectViewSet(viewsets.ModelViewSet):
    serializer_class = SubjectSerializer
    permission_classes = [ReadOnlyOrAdmin]

    def get_queryset(self):
        u = self.request.user
        qs = Subject.objects.select_related("department").prefetch_related("teachers", "students")
        if u.is_admin_role:
            return qs
        if u.is_teacher:
            return qs.filter(teachers=u)
        return qs.filter(students=u)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminRole])
    def enroll(self, request, pk=None):
        """Enroll students by username or roll number: {"students": ["21MCA01", ...]}"""
        subject = self.get_object()
        ids = [s.strip() for s in request.data.get("students", []) if str(s).strip()]
        found = list(User.objects.filter(role=User.Role.STUDENT).filter(username__in=ids)) + \
            list(User.objects.filter(role=User.Role.STUDENT, roll_no__in=ids))
        subject.students.add(*found)
        matched = {u.username for u in found} | {u.roll_no for u in found}
        return Response({"enrolled": len(set(found)), "not_found": [i for i in ids if i not in matched]})


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        qs = User.objects.select_related("department").order_by("role", "roll_no", "username")
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        return qs

    @action(detail=True, methods=["post"], url_path="set-password")
    def set_password(self, request, pk=None):
        user = self.get_object()
        new_password = (request.data.get("password") or "").strip()
        if len(new_password) < 6:
            return Response({"detail": "Password must be at least 6 characters."}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save()
        return Response({"detail": f"Password updated for {user.username}."})

    @action(detail=False, methods=["post"], url_path="import")
    def import_csv(self, request):
        """CSV columns: username,password,first_name,last_name,role,roll_no,batch,semester,department_code"""
        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "Upload a CSV file as 'file'."}, status=400)
        if f.size > 5 * 1024 * 1024:
            return Response({"detail": "File too large (max 5 MB)."}, status=status.HTTP_400_BAD_REQUEST)
        reader = csv.DictReader(io.StringIO(f.read().decode("utf-8-sig")))
        depts = {d.code: d for d in Department.objects.all()}
        created, errors = 0, []
        with transaction.atomic():
            for i, row in enumerate(reader, start=2):
                uname = (row.get("username") or "").strip()
                if not uname:
                    errors.append(f"Row {i}: missing username")
                    continue
                if User.objects.filter(username=uname).exists():
                    errors.append(f"Row {i}: {uname} already exists")
                    continue
                u = User(username=uname, first_name=row.get("first_name", "").strip(),
                         last_name=row.get("last_name", "").strip(),
                         role=(row.get("role") or "student").strip().lower(),
                         roll_no=row.get("roll_no", "").strip(), batch=row.get("batch", "").strip(),
                         department=depts.get((row.get("department_code") or "").strip()))
                sem = (row.get("semester") or "").strip()
                u.semester = int(sem) if sem.isdigit() else None
                u.set_password((row.get("password") or "").strip() or uname)
                u.save()
                created += 1
        return Response({"created": created, "errors": errors})


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def college_settings(request):
    cs = CollegeSettings.load()
    if request.method == "GET":
        return Response(CollegeSettingsSerializer(cs).data)
    if not request.user.is_admin_role:
        return Response({"detail": "Admin only."}, status=403)
    logo = request.FILES.get("logo")
    if logo and logo.size > 2 * 1024 * 1024:
        return Response({"detail": "Logo file too large (max 2 MB)."}, status=status.HTTP_400_BAD_REQUEST)
    ser = CollegeSettingsSerializer(cs, data=request.data, partial=True)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)
