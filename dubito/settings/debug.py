import os
from pathlib import Path

print("project dir")
PROJECT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print(os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

print("static root")
print(os.path.join(PROJECT_DIR, 'staticfiles'))

print("base dir")
BASE_DIR = os.path.dirname(os.path.dirname((os.path.abspath(__file__))))
print(os.path.dirname(os.path.dirname((os.path.abspath(__file__)))))

print("static root")
print(os.path.join(BASE_DIR, 'staticfiles'))
