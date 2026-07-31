import os

files_to_fix_models = [
    r"c:\Users\DELL\Documents\deluzex-backend\app\api\deps.py",
    r"c:\Users\DELL\Documents\deluzex-backend\app\api\endpoints\auth.py",
    r"c:\Users\DELL\Documents\deluzex-backend\app\api\endpoints\cart.py",
    r"c:\Users\DELL\Documents\deluzex-backend\app\api\endpoints\categories.py",
    r"c:\Users\DELL\Documents\deluzex-backend\app\api\endpoints\newsletter.py",
    r"c:\Users\DELL\Documents\deluzex-backend\app\api\endpoints\projects.py",
    r"c:\Users\DELL\Documents\deluzex-backend\app\api\endpoints\testimonials.py",
    r"c:\Users\DELL\Documents\deluzex-backend\app\core\database.py"
]

for file in files_to_fix_models:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace("import models\n", "from app import models\n")
    content = content.replace("import models, schemas", "from app import models, schemas")
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)

main_file = r"c:\Users\DELL\Documents\deluzex-backend\app\main.py"
with open(main_file, 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace("from api import api_router", "from app.api import api_router")
content = content.replace("from core.config import settings", "from app.core.config import settings")
content = content.replace("from core.database import init_db", "from app.core.database import init_db")
with open(main_file, 'w', encoding='utf-8') as f:
    f.write(content)

deps_file = r"c:\Users\DELL\Documents\deluzex-backend\app\api\deps.py"
with open(deps_file, 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace("from core.security", "from app.core.security")
with open(deps_file, 'w', encoding='utf-8') as f:
    f.write(content)

auth_file = r"c:\Users\DELL\Documents\deluzex-backend\app\api\endpoints\auth.py"
with open(auth_file, 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace("from core.security", "from app.core.security")
with open(auth_file, 'w', encoding='utf-8') as f:
    f.write(content)

models_file = r"c:\Users\DELL\Documents\deluzex-backend\app\models\__init__.py"
with open(models_file, 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace("from models.", "from app.models.")
with open(models_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Imports restored!")
