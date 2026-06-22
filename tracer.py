import sys
import contextvars
import os
import time
import uuid
import json
import shutil

m = sys.monitoring
TOOL = m.PROFILER_ID
previous_time = time.perf_counter_ns()

_current = contextvars.ContextVar("trace_buffer", default=None)
PROJECT_ROOT = os.path.abspath(os.getcwd())

INTERNAL_PATH_PARTS = {
    "tracer.py",
    "_yaml",
    "annotated_doc",
    "annotated_types",
    "anyio",
    "certifi",
    "click",
    "detect_installer",
    "dns",
    "dotenv",
    "email_validator",
    "fastapi",
    "fastapi_cli",
    "fastapi_cloud_cli",
    "fastar",
    "h11",
    "httpcore",
    "httptools",
    "httpx",
    "idna",
    "jinja2",
    "markdown_it",
    "markupsafe",
    "mdurl",
    "multipart",
    "pip",
    "pydantic",
    "pydantic_core",
    "pydantic_extra_types",
    "pydantic_settings",
    "pygments",
    "python_multipart",
    "rich",
    "rich_toolkit",
    "rignore",
    "sentry_sdk",
    "shellingham",
    "starlette",
    "typer",
    "typing_extensions.py",
    "typing_inspection",
    "urllib3",
    "uvicorn",
    "uvloop",
    "watchfiles",
    "websockets",
    "yaml",
}

class TracerMiddleware():
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        with TraceRequest(f"{scope['method']} {scope['path']}"):
            await self.app(scope, receive, send)

class TraceRequest():
    def __init__(self, name, out_dir=".traces"):
        self.name = name
        self.out_dir = out_dir

    def __enter__(self):
        self.buf = []
        self.token = _current.set(self.buf)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        _current.reset(self.token)
        self._flush()

    def _flush(self):
        files = os.listdir(self.out_dir)
        if files is not None:
            shutil.rmtree(self.out_dir)
        
        os.makedirs(self.out_dir, exist_ok=True)
        path = os.path.join(self.out_dir, f"trace_{uuid.uuid4().hex}.ndjson")
        with open(path, "w") as f:
            f.write(json.dumps({"v": 1, "request": self.name}) + "\n")
            for event in self.buf:
                f.write(json.dumps(event) + "\n")



def on_line(code, line_number):
    global previous_time
    buf = _validate(code)
    if buf is m.DISABLE:
        return m.DISABLE
    now = time.perf_counter_ns()
    elapsed_ns = now - previous_time
    previous_time = now
    frame = sys._getframe(1)
    variables = {k: repr(v)[:100] for k, v in frame.f_locals.items()}
    buf.append(("line", line_number, code.co_filename, elapsed_ns, variables))

def on_start(code, instruction_offset):
    global previous_time
    buf = _validate(code)
    if buf is m.DISABLE:
        return m.DISABLE
    now = time.perf_counter_ns()
    elapsed_ns = now - previous_time
    previous_time = now
    buf.append(("call", code.co_qualname, elapsed_ns))

def on_return(code, instruction_offset, return_val):
    buf = _validate(code)
    if buf is m.DISABLE:
        return m.DISABLE
    buf.append(("ret", code.co_qualname, repr(return_val)[:100]))
    
def _validate(code):
    buf = _current.get()
    f = code.co_filename
    if buf is None or not f.startswith(PROJECT_ROOT):
        return m.DISABLE
    if any(part in INTERNAL_PATH_PARTS for part in f.replace("\\", "/").split("/")):
        return m.DISABLE
    return buf
    
def install():
    m.use_tool_id(TOOL, "tracer")
    m.set_events(TOOL, m.events.PY_START | m.events.PY_RETURN | m.events.LINE)
    m.register_callback(TOOL, m.events.LINE, on_line)
    m.register_callback(TOOL, m.events.PY_START, on_start)
    m.register_callback(TOOL, m.events.PY_RETURN, on_return)

install()