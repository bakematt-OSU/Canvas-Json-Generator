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


# —— SLUGIFY UTILITY ————————————————————————————————————————————————————
def slugify(text: str) -> str:
    """
    Convert text into a URL-friendly slug:
      - lowercase, non-alphanumerics → hyphens,
      - collapse multiple hyphens,
      - strip leading/trailing hyphens
    """
    s = text.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-{2,}', '-', s).strip('-')
    return s


# —— CORE PARSER ————————————————————————————————————————————————————————
def extract_questions_from_taken_quiz(html_path: str) -> list:
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # — 1) QUIZ NAME
    quiz_name = ""
    hdr = soup.find('header', class_='quiz-header')
    if hdr:
        h2 = hdr.find('h2')
        if h2:
            txt = h2.get_text(" ", strip=True)
            quiz_name = re.sub(r'\s*Results\s+for.*$', '', txt)

    # Precompute slug
    quiz_slug = slugify(quiz_name) if quiz_name else None

    # — 2) CURRENT ATTEMPT
    attempt = None
    sel = soup.select_one('li.quiz_version.selected a')
    if sel:
        m = re.search(r'Attempt\s*(\d+)', sel.get_text())
        if m:
            attempt = int(m.group(1))

    questions = []
    # Enumerate to know question index
    for idx, q in enumerate(soup.find_all("div", class_="display_question"), start=1):
        # — question text
        qt_div = q.find("div", class_="question_text")
        question_text = (
            qt_div.get_text(" ", strip=True).replace("\u00a0", " ")
            if qt_div else ""
        )

        # — points awarded / possible
        pa = pp = None
        up = q.find("div", class_="user_points")
        pp_span = q.find("span", class_="points question_points")
        if up:
            m = re.search(r'([\d.]+)', up.get_text())
            pa = float(m.group(1)) if m else None
        if pp_span:
            m = re.search(r'([\d.]+)', pp_span.get_text())
            pp = float(m.group(1)) if m else None

        # — options + which selected
        opts, sel_opts = [], []
        for ans in q.find_all("div", class_="answer"):
            at = ans.find("div", class_="answer_text") or ans.find("div", class_="answer_label")
            text = at.get_text(" ", strip=True) if at else ""
            opts.append(text)
            if "selected_answer" in ans.get("class", []):
                sel_opts.append(text)

        # — question images (inside question_text)
        pics = []
        if qt_div:
            for child in qt_div.descendants:
                if isinstance(child, Tag) and child.name == "img":
                    src = child.get("src") or child.get("data-src") or ""
                    if src:
                        pics.append(src)

        # — build unique question_id
        if quiz_slug and attempt is not None:
            question_id = f"{quiz_slug}_att{attempt}_q{idx:02d}"
        else:
            question_id = None

        questions.append({
            "question_id":       question_id,
            "source_file":       os.path.basename(html_path),
            "quiz_name":         quiz_name,
            "attempt":           attempt,
            "question":          question_text,
            "options":           opts,
            "selected_options":  sel_opts,
            "points_awarded":    pa,
            "points_possible":   pp,
            "question_pictures": pics
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

    all_qs = []
    for fname in os.listdir(EXTRACT_FOLDER):
        if not fname.lower().endswith('.html'):
            continue
        path = os.path.join(EXTRACT_FOLDER, fname)
        print(f"Parsing {fname}…")
        all_qs.extend(extract_questions_from_taken_quiz(path))

    write_json(all_qs, OUTPUT_JSON)
    print(f"✔ Extracted {len(all_qs)} questions into {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
