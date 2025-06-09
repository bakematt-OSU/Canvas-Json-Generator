#!/usr/bin/env python3
import zipfile
import os
import re
import json
from bs4 import BeautifulSoup, Tag

# —— CONFIG —————————————————————————————————————————————————————————————
ZIP_FILE        = '_INPUT/Quizes.zip'
EXTRACT_FOLDER  = '_OUTPUT/extracted_quizzes'
OUTPUT_JSON     = '_OUTPUT/extracted_questions_full.json'


# —— UNZIP UTILITY —————————————————————————————————————————————————————
def extract_zip(zip_path: str, extract_to: str):
    os.makedirs(extract_to, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_to)


# —— FILENAME PARSER — extract quiz# and attempt# from filename —————————————————
def parse_filename(fname: str):
    base = os.path.splitext(fname)[0]
    m_quiz    = re.search(r'quiz[_\s-]?(\d+)', base, re.IGNORECASE)
    m_attempt = re.search(r'attempt[_\s-]?(\d+)', base, re.IGNORECASE)
    return (m_quiz.group(1) if m_quiz else None,
            m_attempt.group(1) if m_attempt else None)


# —— CORE PARSER ————————————————————————————————————————————————————————
def extract_questions_from_taken_quiz(html_path: str, quiz_num, attempt) -> list:
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    out = []
    for q in soup.find_all("div", class_="display_question"):
        # — question text
        qt_div = q.find("div", class_="question_text")
        question_text = qt_div.get_text(" ", strip=True) if qt_div else ""

        # — points awarded / possible
        pa, pp = None, None
        up = q.find("div", class_="user_points")
        pp_span = q.find("span", class_="points question_points")
        if up:
            m = re.search(r'([\d.]+)', up.get_text())
            pa = float(m.group(1)) if m else None
        if pp_span:
            m = re.search(r'([\d.]+)', pp_span.get_text())
            pp = float(m.group(1)) if m else None

        # — options + which were selected
        opts, sel = [], []
        for ans in q.find_all("div", class_="answer"):
            # text
            at = ans.find("div", class_="answer_text") or ans.find("div", class_="answer_label")
            text = at.get_text(" ", strip=True) if at else ""
            opts.append(text)
            # selected?
            if "selected_answer" in ans.get("class", []):
                sel.append(text)

        # — image extraction logic from HTML_Extract.py
        imgs = []
        if qt_div:
            for child in qt_div.descendants:
                if isinstance(child, Tag) and child.name == "img":
                    src = child.get("src") or child.get("data-src") or ""
                    if src:
                        imgs.append(src)

        out.append({
            "source_file":      os.path.basename(html_path),
            "quiz_number":      quiz_num,
            "attempt":          attempt,
            "question":         question_text,
            "options":          opts,
            "selected_options": sel,
            "points_awarded":   pa,
            "points_possible":  pp,
            "question_pictures":imgs
        })

    return out


# —— WRITE JSON ————————————————————————————————————————————————————————
def write_json(data: list, out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# —— MAIN WORKFLOW ——————————————————————————————————————————————————————
def main():
    extract_zip(ZIP_FILE, EXTRACT_FOLDER)
    all_qs = []

    for fname in os.listdir(EXTRACT_FOLDER):
        if not fname.lower().endswith('.html'):
            continue
        quiz_num, attempt = parse_filename(fname)
        path = os.path.join(EXTRACT_FOLDER, fname)
        all_qs.extend(extract_questions_from_taken_quiz(path, quiz_num, attempt))

    write_json(all_qs, OUTPUT_JSON)
    print(f"✔ Extracted {len(all_qs)} questions into {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
