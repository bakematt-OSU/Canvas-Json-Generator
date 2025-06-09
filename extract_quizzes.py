#!/usr/bin/env python3
import zipfile, os, re, json, shutil
from bs4 import BeautifulSoup, Tag, NavigableString

# ——— PATHS —————————————————————————————————————————————————————————————
ZIP_FILE       = '_INPUT/Quizes.zip'
EXTRACT_FOLDER = '_OUTPUT/extracted_quizzes'
IMAGES_FOLDER  = '_OUTPUT/_images'
OUTPUT_JSON    = '_OUTPUT/extracted_questions_full.json'

# ——— ENSURE OUTPUT FOLDERS EXIST ————————————————————————————————————————
os.makedirs(EXTRACT_FOLDER, exist_ok=True)
os.makedirs(IMAGES_FOLDER, exist_ok=True)


def extract_zip():
    with zipfile.ZipFile(ZIP_FILE, 'r') as zf:
        zf.extractall(EXTRACT_FOLDER)


def slugify(text):
    s = text.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return re.sub(r'-{2,}', '-', s).strip('-')


def extract_questions_from_html(path):
    soup = BeautifulSoup(open(path, encoding='utf-8'), 'html.parser')

    # Get quiz_name & attempt as you already have…
    hdr = soup.find('header', class_='quiz-header')
    raw = hdr.h2.get_text(" ", strip=True) if hdr else ""
    m = re.match(r'(.+?)\s*Results\s+for\s+(.+)$', raw)
    quiz_name = m.group(1) if m else raw
    quiz_slug = slugify(quiz_name)

    sel = soup.select_one('li.quiz_version.selected a')
    attempt = int(re.search(r'Attempt\s*(\d+)', sel.get_text()).group(1)) if sel else None

    # Optionally get student name from that same header fallback…
    student = m.group(2) if m else ""
    first_name, last_name = student.split(" ",1) if " " in student else (student, "")

    questions = []
    for idx, q in enumerate(soup.find_all("div", class_="display_question"), start=1):
        # 1) QUESTION TEXT DIV
        qt_div = q.find("div", class_="question_text")

        # 2) Build question_body: interleaved text & images
        body = []
        img_counter = 1
        if qt_div:
            for node in qt_div.contents:
                # a) TEXT NODE
                if isinstance(node, NavigableString):
                    txt = node.strip()
                    if txt:
                        body.append({"type":"text", "text": txt})

                # b) IMG TAG
                elif isinstance(node, Tag) and node.name == "img":
                    # original src
                    orig = node.get("src") or node.get("data-src") or ""
                    ext  = os.path.splitext(orig)[1] or ".png"

                    new_name = f"{quiz_slug}_att{attempt}_q{idx:02d}_img{img_counter:02d}{ext}"
                    shutil.copy(
                        os.path.join(EXTRACT_FOLDER, orig),
                        os.path.join(IMAGES_FOLDER, new_name)
                    )
                    body.append({"type":"image", "src": new_name})
                    img_counter += 1

                # c) ANY OTHER TAG (e.g. <p>, <strong>, etc.)
                elif isinstance(node, Tag):
                    txt = node.get_text(" ", strip=True)
                    if txt:
                        body.append({"type":"text", "text": txt})
                    # and still catch nested images:
                    for img in node.find_all("img", recursive=False):
                        orig = img.get("src") or img.get("data-src") or ""
                        ext  = os.path.splitext(orig)[1] or ".png"
                        new_name = f"{quiz_slug}_att{attempt}_q{idx:02d}_img{img_counter:02d}{ext}"
                        shutil.copy(
                            os.path.join(EXTRACT_FOLDER, orig),
                            os.path.join(IMAGES_FOLDER, new_name)
                        )
                        body.append({"type":"image","src":new_name})
                        img_counter += 1

        # 3) POINTS
        up = q.find("div", class_="user_points")
        pp = q.find("span", class_="points question_points")
        pa = float(re.search(r'[\d.]+', up.get_text()).group()) if up else None
        pt = float(re.search(r'[\d.]+', pp.get_text()).group()) if pp else None

        # 4) OPTIONS + SELECTED
        opts, sel_opts = [], []
        for ans in q.find_all("div", class_="answer"):
            txt = (ans.find("div", class_="answer_text") or
                   ans.find("div", class_="answer_label")).get_text(" ",strip=True)
            opts.append(txt)
            if "selected_answer" in ans.get("class", []):
                sel_opts.append(txt)

        # 5) status
        if pa is None or pt is None:
            status = None
        elif pa == pt:
            status = "correct"
        elif pa == 0:
            status = "incorrect"
        else:
            status = "partial"

        # 6) BUILD ID
        question_id = f"{quiz_slug}_att{attempt}_q{idx:02d}"

        questions.append({
            "status":            status,
            "question_id":       question_id,
            "first_name":        first_name,
            "last_name":         last_name,
            "quiz_name":         quiz_name,
            "attempt":           attempt,
            "question_body":     body,
            "options":           opts,
            "selected_options":  sel_opts,
            "points_awarded":    pa,
            "points_possible":   pt,
            "source_file":       os.path.basename(path)
        })

    return questions


def main():
    extract_zip()
    all_q = []
    for fn in os.listdir(EXTRACT_FOLDER):
        if fn.lower().endswith('.html'):
            all_q += extract_questions_from_html(os.path.join(EXTRACT_FOLDER, fn))

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(all_q, f, indent=2, ensure_ascii=False)

    print(f"✔ Wrote {len(all_q)} questions to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
