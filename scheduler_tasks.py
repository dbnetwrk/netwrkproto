# scheduler_tasks.py
from tasks import generate_post_core

if __name__ == "__main__":
    message, error = generate_post_core()
    if error:
        print(error)
    else:
        print(message)
