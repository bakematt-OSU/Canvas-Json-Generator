#!/usr/bin/env python3

# IMPORTS
import zipfile
import os
import json
import re
from bs4 import BeautifulSoup

# CONSTANTS — paths for your input ZIP, working folder, and final JSON
ZIP_FILE        = '_INPUT/Quizes.zip'
EXTRACT_FOLDER  = '_OUTPUT/extracted_quizzes'
OUTPUT_JSON     = '_OUTPUT/extracted_questions_full.json'


# -----------------------------------------------------------------------------
# EXTRACT THE ZIP INTO A DIRECTORY
# -----------------------------------------------------------------------------
def extract_zip(zip_path: str, extract_to: str):
    """
    UNZIP THE ARCHIVE TO A FOLDER FOR PROCESSING.
    """
    os.makedirs(extract_to, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_to)


# -----------------------------------------------------------------------------
# PARSE ONE “TAKEN” QUIZ HTML INTO A LIST OF QUESTION DICTS
# -----------------------------------------------------------------------------
def extract_questions_from_taken_quiz(html_path: str) -> list:
    """
    FOR EACH <div class="display_question"> IN THE HTML, PULL OUT:
      - question text
      - all option texts
      - which options were selected
      - points awarded & possible
      - any <img> URLs

    RETURNS A LIST OF DICTS.
    """
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    questions = soup.find_all("div", class_="display_question")
    result = []

    for q in questions:
        # QUESTION TEXT
        qt_div = q.find("div", class_="question_text")
        question_text = (
            qt_div.get_text(separator=" ", strip=True).replace("\u00a0", " ")
            if qt_div else ""
        )

        # POINTS
        pa, pp = None, None
        pa_div = q.find("div", class_="user_points")
        pp_span = q.find("span", class_="points question_points")
        if pa_div:
            m = re.search(r"[\d.]+", pa_div.get_text())
            pa = float(m.group()) if m else None
        if pp_span:
            m = re.search(r"[\d.]+", pp_span.get_text())
            pp = float(m.group()) if m else None

        # OPTIONS + SELECTED OPTIONS
        opts = []
        selected = []
        answers = q.find_all("div", class_="answer")
        for ans in answers:
            # TEXT OF THE OPTION
            at = ans.find("div", class_="answer_text") or ans.find("div", class_="answer_label")
            text = at.get_text(strip=True).replace("\u00a0", " ") if at else ""
            opts.append(text)

            # LOOK FOR 'selected_answer' CLASS
            if "selected_answer" in ans.get("class", []):
                selected.append(text)

        # QUESTION PICTURES
        pics = []
        for img in q.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            pics.append(src)

        # COLLECT INTO DICT
        result.append({
            "question":           question_text,
            "options":            opts,
            "selected_options":   selected,
            "points_awarded":     pa,
            "points_possible":    pp,
            "question_pictures":  pics
        })

    return result


# -----------------------------------------------------------------------------
# WRITE JSON TO DISK
# -----------------------------------------------------------------------------
def write_json(data: list, out_path: str):
    """
    DUMP THE LIST OF QUESTION DICTS TO A JSON FILE.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# -----------------------------------------------------------------------------
# MAIN WORKFLOW
# -----------------------------------------------------------------------------
def main():
    # 1) UNZIP QUIZ FILES
    extract_zip(ZIP_FILE, EXTRACT_FOLDER)

    all_qs = []

    # 2) FIND & PARSE EACH HTML
    for fname in os.listdir(EXTRACT_FOLDER):
        if not fname.lower().endswith(".html"):
            continue
        path = os.path.join(EXTRACT_FOLDER, fname)
        print(f"Parsing {fname}…")
        qs = extract_questions_from_taken_quiz(path)
        all_qs.extend(qs)

    # 3) WRITE OUT JSON
    write_json(all_qs, OUTPUT_JSON)
    print(f"Done — {len(all_qs)} questions written to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
