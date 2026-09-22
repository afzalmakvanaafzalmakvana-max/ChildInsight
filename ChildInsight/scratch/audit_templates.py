import os
import re
import glob

workspace = r'c:\Users\User\Downloads\ChildInsight\ChildInsight'
template_dir = os.path.join(workspace, 'app', 'templates')

print("--- Template Static Analysis ---")
dead_links = []
forms_without_csrf = []
buttons_without_handlers = []

for filepath in glob.glob(os.path.join(template_dir, '**', '*.html'), recursive=True):
    rel_path = os.path.relpath(filepath, template_dir)
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    in_form = False
    form_has_csrf = False
    form_start_line = 0
    form_method = 'GET'

    for idx, line in enumerate(lines, 1):
        # Check href="#"
        match = re.search(r'<a\s+[^>]*href=["\']#["\'][^>]*>', line)
        if match:
            tag = match.group(0)
            if not any(k in tag.lower() for k in ['dropdown', 'collapse', 'tab', 'toggle', 'btn', 'javascript', 'modal']):
                dead_links.append((rel_path, idx, tag.strip()))

        # Check forms for CSRF
        if '<form' in line:
            in_form = True
            form_start_line = idx
            form_method = 'POST' if 'post' in line.lower() else 'GET'
            form_has_csrf = ('csrf_token' in line or 'csrf' in line)
        if in_form:
            if 'csrf_token' in line or 'csrf' in line:
                form_has_csrf = True
            if '</form>' in line:
                if form_method == 'POST' and not form_has_csrf:
                    forms_without_csrf.append((rel_path, form_start_line))
                in_form = False
                form_has_csrf = False

print(f"Total dead href='#' found: {len(dead_links)}")
for r, ln, tag in dead_links[:20]:
    print(f"  {r}:{ln} -> {tag}")

print(f"\nTotal POST forms without CSRF found: {len(forms_without_csrf)}")
for r, ln in forms_without_csrf:
    print(f"  {r}:{ln}")
