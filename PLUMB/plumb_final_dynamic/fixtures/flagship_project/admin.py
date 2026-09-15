import pickle
import subprocess
ADMIN_API_TOKEN = 'sk_live_9f8a7b6c5d4e3f2a1b0c'
def run_admin_command(user_command):
    subprocess.run(user_command, shell=True)
def load_uploaded_session(raw_bytes):
    return pickle.loads(raw_bytes)
