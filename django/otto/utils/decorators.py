import threading
from functools import wraps

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _

from structlog import get_logger

from otto.models import App, Notification
from otto.rules import ADMINISTRATIVE_PERMISSIONS

logger = get_logger(__name__)
_thread_locals = threading.local()


def app_access_required(app_handle):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                logger.info("User is not authenticated", category="security")
                return redirect(reverse("index"))

            app = App.objects.get(handle=app_handle)
            if not request.user.has_perm("otto.access_app", app):
                logger.info(
                    "User does not have permission to access app",
                    category="security",
                    app=app.name,
                )
                Notification.objects.create(
                    user=request.user,
                    heading=_("Access controls"),
                    text=_("You are not authorized to access") + f" {app.name}",
                    category="error",
                )
                return redirect(reverse("index"))

            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def permission_required(
    perm,
    fn=None,
    login_url=None,
    raise_exception=False,
    redirect_field_name=REDIRECT_FIELD_NAME,
):
    # Modification of rules.contrib.views.permission_required
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Normalize to a list of permissions
            if isinstance(perm, str):
                perms = (perm,)
            else:
                perms = perm

            # Get the object to check permissions against
            if callable(fn):
                obj = fn(request, *args, **kwargs)
            else:  # pragma: no cover
                obj = fn

            # Get the user
            user = request.user

            # Check for permissions and return a response
            if not user.has_perms(perms, obj):
                logger.info(
                    "User does not have permission",
                    admin=bool(ADMINISTRATIVE_PERMISSIONS.intersection(perms)),
                    category="security",
                    path=request.path,
                    perms=perms,
                )
                # User does not have a required permission
                if raise_exception:
                    raise PermissionDenied()
                else:
                    Notification.objects.create(
                        user=request.user,
                        heading="Access controls",
                        text=_(f"Unauthorized access of URL:") + f" {request.path}",
                        category="error",
                    )
                    return redirect(reverse("index"))
            else:
                # User has all required permissions -- allow the view to execute
                if bool(ADMINISTRATIVE_PERMISSIONS.intersection(perms)):
                    logger.info(
                        "Administrative access granted",
                        admin=True,
                        category="security",
                        path=request.path,
                        perms=perms,
                    )
                return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


# Request Info - for sharing request-specific information across the application
class RequestInfo:
    """
    Track request-specific information, such as the user and feature being accessed.
    Persisted in a thread-local variable.
    Useful for costing and logging.
    """

    def __init__(self, user=None, feature=None):
        self.user = user
        self.feature = feature


def get_request_info():
    return getattr(_thread_locals, "request_info", RequestInfo())


def track_request_info(feature: str = None):
    """
    Adds a RequestInfo object to the thread-local storage for the duration of the request.
    It contains the properties "user" and "feature" (optional argument to decorator).
    Retrieve the RequestInfo object with get_request_info().
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            _thread_locals.request_info = RequestInfo(
                user=request.user, feature=feature
            )
            response = view_func(request, *args, **kwargs)
            return response

        return _wrapped_view

    return decorator
