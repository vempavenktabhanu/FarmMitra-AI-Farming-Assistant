import sys
from pathlib import Path
from urllib.parse import parse_qs, urlencode

# Add project root directory to sys.path so app can be imported
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app import app as flask_app


class VercelPathFix:
    """
    WSGI Middleware to fix URL paths on Vercel.
    Vercel CLI 66+ passes rewritten destination paths (like /api/index)
    to backend frameworks. This middleware restores the user's actual requested path.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        qs_str = environ.get("QUERY_STRING", "")
        if "__vercel_path=" in qs_str:
            qs = parse_qs(qs_str)
            if "__vercel_path" in qs and qs["__vercel_path"]:
                target = qs.pop("__vercel_path", ["/"])[0]
                environ["PATH_INFO"] = target or "/"
                environ["QUERY_STRING"] = urlencode(qs, doseq=True)
        else:
            # Check headers where Vercel preserves the original incoming request path
            for header in (
                "HTTP_X_FORWARDED_URI",
                "HTTP_X_MATCHED_PATH",
                "HTTP_X_ORIGINAL_URI",
                "HTTP_X_VERCEL_FORWARDED_PATH",
            ):
                original_path = environ.get(header)
                if original_path and not original_path.startswith("/api/index"):
                    environ["PATH_INFO"] = original_path.split("?")[0]
                    break
            else:
                path = environ.get("PATH_INFO", "")
                if path in ("/api/index", "/api/index.py", "/api/index/"):
                    environ["PATH_INFO"] = "/"
                elif path.startswith("/api/index/"):
                    environ["PATH_INFO"] = path[len("/api/index"):]

        environ["SCRIPT_NAME"] = ""
        return self.wsgi_app(environ, start_response)


app = VercelPathFix(flask_app)
application = app
