import os

def get_abs_path(path: str):
    try:
        return os.path.abspath(path)
    except:
        return "(no fle path)"