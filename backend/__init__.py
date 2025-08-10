# re-export FastAPI app for convenience
from importlib import import_module

app = import_module("backend.app").app
