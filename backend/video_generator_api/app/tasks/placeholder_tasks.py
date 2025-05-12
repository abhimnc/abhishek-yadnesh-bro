import time
from app.core.celery_app import celery_app

@celery_app.task(acks_late=True) # Example: acknowledge after task completion
def example_task(x: int, y: int) -> int:
    print(f"Received task: example_task with args {x}, {y}")
    time.sleep(5) # Simulate some work
    result = x + y
    print(f"Task example_task completed with result: {result}")
    return result

@celery_app.task
def another_example_task(message: str) -> str:
    print(f"Received task: another_example_task with message '{message}'")
    time.sleep(2)
    response = f"Processed message: {message}"
    print(f"Task another_example_task completed with response: {response}")
    return response

# You can add more placeholder tasks here for testing different scenarios
# e.g., tasks that raise exceptions, tasks with retries, etc. 