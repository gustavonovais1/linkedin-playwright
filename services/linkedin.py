import os

def start_linkedin_bot(segments: str | None = None):
    import subprocess, sys
    args = [sys.executable, "-m", "bot.linkedin.src.main"]
    storage = "linkedin_storage.json"
    args += ["--storage", storage]
    env = os.environ.copy()
    env["DEFAULT_SEGMENTS"] = segments or "updates,visitors,followers,competitors"
    env["DB_HOST"] = env.get("POSTGRES_HOST")
    env["DB_NAME"] = env.get("POSTGRES_DB") 
    env["DB_USER"] = env.get("POSTGRES_USER")
    env["DB_PASSWORD"] = env.get("POSTGRES_PASSWORD") 
    p = subprocess.Popen(args, env=env)
    return {"pid": p.pid, "started": True}
