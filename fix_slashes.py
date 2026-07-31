import os
import glob

endpoints_dir = r"c:\Users\DELL\Documents\deluzex-backend\app\api\endpoints\*.py"

for filepath in glob.glob(endpoints_dir):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace root slash routes with empty string routes
    content = content.replace('@router.get("/")', '@router.get("")')
    content = content.replace('@router.post("/")', '@router.post("")')
    content = content.replace('@router.put("/")', '@router.put("")')
    content = content.replace('@router.delete("/")', '@router.delete("")')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
print("Fixed trailing slashes!")
