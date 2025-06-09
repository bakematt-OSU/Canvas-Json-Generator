#!/usr/bin/env python3
"""
extractor.py

Provides functions to extract quiz questions from Canvas HTML files,
copy images, slugify names, and write output JSON. Now includes
`extract_main` for programmatic integration with canvas_tools.
"""
import zipfile
import os
import re
import json
import shutil
from bs4 import BeautifulSoup, Tag, NavigableString

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

# —— MAIN EXTRACT FUNCTION —————————————————————————————————————————————————
def extract_main(
    zip_path: str,
    extract_to: str,
    output_json: str,
    images_folder: str
):
    """
    Extracts HTML files from a ZIP, processes each for quiz questions,
    and writes the combined JSON. Saves any images to `images_folder`.
    """
    # Unzip HTML files
    extract_zip(zip_path, extract_to)
    os.makedirs(images_folder, exist_ok=True)

    # Process each HTML file
    all_qs = []
    for fname in os.listdir(extract_to):
        if not fname.lower().endswith('.html'):
            continue
        path = os.path.join(extract_to, fname)
        print(f"Parsing {fname}…")
        all_qs.extend(
            extract_questions_from_taken_quiz(path, images_folder)
        )

    # Write out JSON
    write_json(all_qs, output_json)
    print(f"✔ Extracted {len(all_qs)} questions into {output_json}\n"
          f"✔ Images saved in {images_folder}")

# —— SLUGIFY UTILITY ————————————————————————————————————————————————————
def slugify(text: str) -> str:
    s = text.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return re.sub(r'-{2,}', '-', s).strip('-')

# —— COPY & RENAME IMAGE ——————————————————————————————————————————————————
def copy_and_rename_image(
    src_path: str,
    dest_folder: str,
    question_id: str,
    img_idx: int
) -> str:
    ext = os.path.splitext(src_path)[1] or '.png'
    new_filename = f"{question_id}_img{img_idx:02d}{ext}"
    os.makedirs(dest_folder, exist_ok=True)
    try:
        shutil.copy(src_path, os.path.join(dest_folder, new_filename))
        return new_filename
    except Exception:
        return None

# —— FLATTEN CONTENT —————————————————————————————————————————————————————
def iter_qt_content(element):
    """
    Recursively yield ('text', str) and ('img', Tag) for content in document order.
    """
    for child in element.contents:
        if isinstance(child, NavigableString):
            txt = child.strip()
            if txt:
                yield ('text', txt)
        elif isinstance(child, Tag):
            if child.name == 'img':
                yield ('img', child)
            else:
                yield from iter_qt_content(child)

# —— CORE PARSER ————————————————————————————————————————————————————————
def extract_questions_from_taken_quiz(
    html_path: str,
    images_folder: str = IMAGES_FOLDER
) -> list:
    """
    Parse a taken Canvas quiz HTML, extract questions, options, status, and images.
    `images_folder` is where to copy any local images.
    """
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # — CLASS INFO FROM BREADCRUMBS
    class_name = class_code = section = term = year = None
    crumbs_li = soup.select_one(
        'div.ic-app-crumbs nav#breadcrumbs ul li:nth-of-type(2) span.ellipsible'
    )
    if crumbs_li:
        course_label = crumbs_li.get_text(strip=True)
        m_cls = re.match(r'^(.*?)\s*\(([^)]+)\)$', course_label)
        if m_cls:
            class_name = m_cls.group(1).strip()
            parts = m_cls.group(2).split('_')
            if len(parts) == 4:
                class_code = f"{parts[0]}_{parts[1]}"
                section = parts[2]
                ty = parts[3]
                term_map = {'S':'Spring','W':'Winter','F':'Fall','U':'Summer'}
                term = term_map.get(ty[0], 'Unknown')
                year = ty[1:]

    # — HEADER: QUIZ & STUDENT
    quiz_name = ''
    first_name = last_name = None
    hdr = soup.find('header', class_='quiz-header')
    if hdr and hdr.h2:
        full_header = hdr.h2.get_text(' ', strip=True)
        m = re.match(r'(.+?)\s*Results\s+for\s+(.+)', full_header)
        if m:
            quiz_name = m.group(1).strip()
            full_name = m.group(2).strip()
            parts = full_name.split(None, 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts)>1 else None
        else:
            quiz_name = re.sub(r'\s*Results\s+for.*$', '', full_header).strip()
    quiz_slug = slugify(quiz_name) if quiz_name else None

    # — ATTEMPT NUMBER
    attempt = None
    sel = soup.select_one('li.quiz_version.selected a')
    if sel:
        m = re.search(r'Attempt\s*(\d+)', sel.get_text())
        if m:
            attempt = int(m.group(1))

    questions = []
    for idx, q in enumerate(soup.find_all('div', class_='display_question'), start=1):
        opts, sel_opts = [], []
        # for ans in q.find_all('div', class_='answer'):
        #     at = ans.find('div', class_='answer_text') or ans.find('div', class_='answer_label')
        #     text = at.get_text(' ', strip=True) if at else ''
        #     opts.append(text)
        #     if 'selected_answer' in ans.get('class', []):
        #         sel_opts.append(text)
        for ans in q.find_all('div', class_='answer'):
            text = ''
            
            # Handle numerical or text-box inputs (type="text")
            input_field = ans.find('input', class_='question_input')
            if input_field and input_field.has_attr('value'):
                text = input_field['value'].strip()

            # Handle dropdown select (matching questions)
            elif ans.find('select'):
                match_prompt = ans.find('div', class_='answer_match_left')
                selected = ans.find('select').find('option', selected=True)
                left = match_prompt.get_text(strip=True) if match_prompt else ''
                right = selected.get_text(strip=True) if selected else ''
                text = f"{left} → {right}" if left or right else ''

            # Handle normal answer text
            else:
                at = ans.find('div', class_='answer_text') or ans.find('div', class_='answer_label')
                text = at.get_text(' ', strip=True) if at else 'No answer text found.'

            # Clean NBSP just in case
            text = text.replace('\u00a0', ' ')

            # Append to options
            opts.append(text)
            if 'selected_answer' in ans.get('class', []):
                sel_opts.append(text)

        # — POINTS & STATUS
        up = q.find('div', class_='user_points')
        pp_span = q.find('span', class_='points question_points')
        pa = float(re.search(r'[\d.]+', up.get_text()).group()) if up and re.search(r'[\d.]+', up.get_text()) else None
        pp = float(re.search(r'[\d.]+', pp_span.get_text()).group()) if pp_span and re.search(r'[\d.]+', pp_span.get_text()) else None
        if pa is not None and pp is not None:
            if pa == pp:
                status = 'correct'
            elif pa == 0:
                status = 'incorrect'
            else:
                status = 'partial'
        else:
            status = None

        # — QUESTION ID
        question_id = f"{quiz_slug}_att{attempt}_q{idx:02d}" if quiz_slug and attempt is not None else None


        # — QUESTION BODY & IMAGES
        qt_div = q.find('div', class_='question_text')
        question_body = []
        img_counter = 1
        text_buf = ''
        if qt_div:
            for node_type, node in iter_qt_content(qt_div):
                if node_type == 'text':
                    text_buf += (' ' if text_buf else '') + node
                else:
                    if text_buf.strip():
                        question_body.append({'type':'text','text':text_buf.strip()})
                        text_buf = ''
                    src = node.get('src') or node.get('data-src') or ''
                    if src:
                        if src.startswith(('http://','https://')):
                            img_ref = src
                        else:
                            orig = os.path.normpath(os.path.join(os.path.dirname(html_path), src))
                            img_ref = copy_and_rename_image(orig, images_folder, question_id or quiz_slug or 'img', img_counter)
                        if img_ref:
                            question_body.append({'type':'image','src':img_ref})
                            img_counter += 1
            if text_buf.strip():
                question_body.append({'type':'text','text':text_buf.strip()})

        questions.append({
            'first_name':       first_name,
            'last_name':        last_name,
            'class_name':       class_name,
            'class':            class_code,
            'section':          section,
            'term':             term,
            'year':             year,
            'quiz_name':        quiz_name,
            'attempt':          attempt,
            'question_id':      question_id,
            'question_number':  idx,
            'status':           status,
            'points_awarded':   pa,
            'points_possible':  pp,
            'question_body':    question_body,
            'options':          opts,
            'selected_options': sel_opts,
            'source_file':      os.path.basename(html_path)
        })

    return questions

# —— WRITE JSON ————————————————————————————————————————————————————————
def write_json(data: list, out_path: str):
    """
    Append new entries to an existing JSON array, or create it if missing/invalid.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    # Load existing entries, if any
    try:
        with open(out_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
            if not isinstance(existing, list):
                existing = []
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []
    # Combine and write back
    combined = existing + data
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

def OLD_write_json(data: list, out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# —— CLI ENTRYPOINT —————————————————————————————————————————————————————
def main():
    extract_main(ZIP_FILE, EXTRACT_FOLDER, OUTPUT_JSON, IMAGES_FOLDER)

if __name__ == '__main__':
    main()
