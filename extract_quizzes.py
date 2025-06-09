#!/usr/bin/env python3
import zipfile
import os
import re
import json
import shutil
from bs4 import BeautifulSoup, Tag

# —— CONFIG —————————————————————————————————————————————————————————————
ZIP_FILE        = '_INPUT/Quizes.zip'
EXTRACT_FOLDER  = '_OUTPUT/extracted_quizzes'
OUTPUT_JSON     = '_OUTPUT/extracted_questions_full.json'
IMAGES_FOLDER   = '_OUTPUT/_images'

# —— UNZIP UTILITY —————————————————————————————————————————————————————
def extract_zip(zip_path: str, extract_to: str):
    os.makedirs(extract_to, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_to)

# —— SLUGIFY UTIL ———————————————————————————————————————————————————————
def slugify(text: str) -> str:
    s = text.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-{2,}', '-', s).strip('-')
    return s

# —— COPY & RENAME IMAGE ——————————————————————————————————————————————————
def copy_and_rename_image(src_path: str, dest_folder: str, question_id: str, img_idx: int) -> str:
    ext = os.path.splitext(src_path)[1] or '.png'
    new_filename = f"{question_id}_img{img_idx:02d}{ext}"
    os.makedirs(dest_folder, exist_ok=True)
    try:
        shutil.copy(src_path, os.path.join(dest_folder, new_filename))
        return new_filename
    except Exception:
        return None

# —— CORE PARSER ————————————————————————————————————————————————————————
def extract_questions_from_taken_quiz(html_path: str) -> list:
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # — HEADER: QUIZ & STUDENT
    quiz_name = ""
    first_name = last_name = None
    hdr = soup.find('header', class_='quiz-header')
    if hdr:
        h2 = hdr.find('h2')
        if h2:
            full_header = h2.get_text(" ", strip=True)
            m = re.match(r"(.+?)\s*Results\s+for\s+(.+)", full_header)
            if m:
                quiz_name = m.group(1).strip()
                full_name = m.group(2).strip()
                parts = full_name.split(None, 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else None
            else:
                quiz_name = re.sub(r"\s*Results\s+for.*$", "", full_header).strip()

    quiz_slug = slugify(quiz_name) if quiz_name else None

    # — ATTEMPT
    attempt = None
    sel = soup.select_one('li.quiz_version.selected a')
    if sel:
        m = re.search(r'Attempt\s*(\d+)', sel.get_text())
        if m:
            attempt = int(m.group(1))

    questions = []
    for idx, q in enumerate(soup.find_all("div", class_="display_question"), start=1):
        # — OPTIONS & STATUS
        opts, sel_opts = [], []
        for ans in q.find_all("div", class_="answer"):
            at = ans.find("div", class_="answer_text") or ans.find("div", class_="answer_label")
            text = at.get_text(" ", strip=True) if at else ""
            opts.append(text)
            if "selected_answer" in ans.get("class", []):
                sel_opts.append(text)

        up = q.find("div", class_="user_points")
        pp_span = q.find("span", class_="points question_points")
        pa = float(re.search(r'([\d.]+)', up.get_text()).group(1)) if up and re.search(r'([\d.]+)', up.get_text()) else None
        pp = float(re.search(r'([\d.]+)', pp_span.get_text()).group(1)) if pp_span and re.search(r'([\d.]+)', pp_span.get_text()) else None

        if pa is not None and pp is not None:
            if pa == pp:
                status = 'correct'
            elif pa == 0:
                status = 'incorrect'
            else:
                status = 'partial'
        else:
            status = None

        question_id = f"{quiz_slug}_att{attempt}_q{idx:02d}" if quiz_slug and attempt is not None else None

        # — QUESTION BODY & IMAGES
        qt_div = q.find("div", class_="question_text")
        question_body = []
        pics = []
        if qt_div:
            img_counter = 1
            for node in qt_div.children:
                if isinstance(node, Tag) and node.name == 'img':
                    src = node.get('src') or node.get('data-src') or ''
                    if src:
                        if src.startswith('http'):
                            img_ref = src
                        else:
                            orig_path = os.path.normpath(os.path.join(os.path.dirname(html_path), src))
                            img_ref = copy_and_rename_image(orig_path, IMAGES_FOLDER, question_id or quiz_slug or 'img', img_counter)
                        if img_ref:
                            question_body.append({'type': 'image', 'src': img_ref})
                            pics.append(img_ref)
                    img_counter += 1
                else:
                    text = ''
                    if isinstance(node, Tag):
                        text = node.get_text(" ", strip=True)
                    else:
                        text = str(node).strip()
                    if text:
                        question_body.append({'type': 'text', 'text': text})
        
        questions.append({
            "status":            status,
            "question_id":       question_id,
            "first_name":        first_name,
            "last_name":         last_name,
            "quiz_name":         quiz_name,
            "attempt":           attempt,
            "question_body":     question_body,
            "options":           opts,
            "selected_options":  sel_opts,
            "points_awarded":    pa,
            "points_possible":   pp,
            "question_pictures": pics,
            "source_file":       os.path.basename(html_path)
        })

    return questions

# —— WRITE JSON ————————————————————————————————————————————————————————
def write_json(data: list, out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# —— MAIN WORKFLOW ——————————————————————————————————————————————————————
def main():
    extract_zip(ZIP_FILE, EXTRACT_FOLDER)
    os.makedirs(IMAGES_FOLDER, exist_ok=True)

    all_qs = []
    for fname in os.listdir(EXTRACT_FOLDER):
        if not fname.lower().endswith('.html'):
            continue
        path = os.path.join(EXTRACT_FOLDER, fname)
        print(f"Parsing {fname}…")
        all_qs.extend(extract_questions_from_taken_quiz(path))

    write_json(all_qs, OUTPUT_JSON)
    print(f"✔ Extracted {len(all_qs)} questions into {OUTPUT_JSON}\n✔ Images saved in {IMAGES_FOLDER}")

if __name__ == "__main__":
    main()
