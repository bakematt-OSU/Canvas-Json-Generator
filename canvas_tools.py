#!/usr/bin/env python3
"""
canvas_extractor.py

Provides a menu-driven CLI to:
  1) Process files (HTML, ZIP, folders)
  2) Toggle quiz webserver (start/stop)
  3) JSON control (backup and clear outputs)
  4) Analyze questions (duplicates, filtering)
  5) Exit
"""
import sys
import os
import argparse
import zipfile
import shutil
import subprocess
import shlex
import json
from datetime import datetime
from collections import defaultdict

from extractor import (
    extract_main,
    ZIP_FILE,
    EXTRACT_FOLDER,
    OUTPUT_JSON,
    IMAGES_FOLDER,
    extract_questions_from_taken_quiz,
    write_json,
)

# Paths and defaults
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVE_SCRIPT = os.path.join(SCRIPT_DIR, "web_serve.py")
INPUT_DIR = "_INPUT"
BACKUP_DIR = "_BACKUP"
SERVER_HOST = "localhost"
SERVER_PORT = 8000
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/index.html"
server_proc = None


# --- Menu prompts ---
def prompt_main_menu():
    running = server_proc and server_proc.poll() is None
    status = f"RUNNING at {SERVER_URL}" if running else "STOPPED"
    print("=== Canvas Study Tools Utility ===")
    print(f"Webserver status: {status}")
    print("1) Process files")
    print("2) Toggle quiz webserver (start/stop)")
    print("3) Question Backup/Clear")
    print("4) Analyze Questions")
    print("5) Exit")
    return input("Select an option: ").strip()

def prompt_process_menu():
    print("\n-- Process Files in the Input Folder --")
    print("1) Select individual HTML files")
    print("2) ZIP archives")
    print("3) Folders of HTML files")
    print("4) Back to main menu")
    return input("Select an option: ").strip()

def prompt_json_menu():
    print("\n-- Question Backup/Clear --")
    print("1) Backup current JSON, extracted quizzes, and images")
    print("2) Erase Question Library and Start Fresh")
    print("3) Return to Main Menu")
    return input("Select an option: ").strip()


# --- Listing utilities ---
def list_input_html():
    try:
        files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".html")]
    except FileNotFoundError:
        print(f"Directory '{INPUT_DIR}' not found.")
        return []
    if files:
        print(f"\nAvailable HTML files in '{INPUT_DIR}':")
        for idx, f in enumerate(files, 1):
            print(f"  {idx}) {f}")
    else:
        print(f"No HTML files found in '{INPUT_DIR}'.")
    return files

def list_input_zips():
    try:
        zips = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".zip")]
    except FileNotFoundError:
        print(f"Directory '{INPUT_DIR}' not found.")
        return []
    if zips:
        print(f"\nAvailable ZIP files in '{INPUT_DIR}':")
        for idx, f in enumerate(zips, 1):
            print(f"  {idx}) {f}")
    else:
        print(f"No ZIP files found in '{INPUT_DIR}'.")
    return zips

def list_input_folders():
    try:
        folders = [
            d
            for d in os.listdir(INPUT_DIR)
            if os.path.isdir(os.path.join(INPUT_DIR, d))
        ]
    except FileNotFoundError:
        print(f"Directory '{INPUT_DIR}' not found.")
        return []
    if folders:
        print(f"\nAvailable folders in '{INPUT_DIR}':")
        for idx, d in enumerate(folders, 1):
            print(f"  {idx}) {d}")
    else:
        print(f"No folders found in '{INPUT_DIR}'.")
    return folders


# --- Processing routines ---
def handle_process_html_selection(html_files):
    if not html_files:
        print("No HTML files selected.\n")
        return
    os.makedirs(IMAGES_FOLDER, exist_ok=True)
    all_questions = []
    for html in html_files:
        print(f"Parsing {html}…")
        all_questions.extend(extract_questions_from_taken_quiz(html, IMAGES_FOLDER))
    write_json(all_questions, OUTPUT_JSON)
    print(f"\u2713 Processed {len(all_questions)} questions to {OUTPUT_JSON}")
    print(f"\u2713 Images saved in {IMAGES_FOLDER}\n")

def handle_process_html():
    files = list_input_html()
    if not files:
        return
    sel = input("Enter file numbers to process (comma-separated): ").strip()
    indices = [int(x) - 1 for x in sel.split(",") if x.strip().isdigit()]
    html_files = [
        os.path.join(INPUT_DIR, files[i]) for i in indices if 0 <= i < len(files)
    ]
    handle_process_html_selection(html_files)

def handle_process_zips():
    zips = list_input_zips()
    if not zips:
        return
    sel = input("Enter ZIP numbers to process (comma-separated): ").strip()
    indices = [int(x) - 1 for x in sel.split(",") if x.strip().isdigit()]
    for i in indices:
        if 0 <= i < len(zips):
            zip_path = os.path.join(INPUT_DIR, zips[i])
            print(f"\nExtracting from {zip_path}…")
            extract_main(zip_path, EXTRACT_FOLDER, OUTPUT_JSON, IMAGES_FOLDER)
    print()

def handle_process_folders():
    folders = list_input_folders()
    if not folders:
        return
    sel = input("Enter folder numbers to process (comma-separated): ").strip()
    indices = [int(x) - 1 for x in sel.split(",") if x.strip().isdigit()]
    html_files = []
    for i in indices:
        if 0 <= i < len(folders):
            folder_path = os.path.join(INPUT_DIR, folders[i])
            files = [f for f in os.listdir(folder_path) if f.lower().endswith(".html")]
            html_files.extend(os.path.join(folder_path, f) for f in files)
    handle_process_html_selection(html_files)

def handle_process_menu():
    choice = prompt_process_menu()
    if choice == "1":
        handle_process_html()
    elif choice == "2":
        handle_process_zips()
    elif choice == "3":
        handle_process_folders()
    elif choice == "4":
        return
    else:
        print("Invalid choice. Please select 1-4.\n")


# --- Server toggle ---
def handle_toggle_server():
    global server_proc
    if server_proc and server_proc.poll() is None:
        print("Stopping webserver…")
        server_proc.terminate()
        server_proc.wait()
        server_proc = None
        print("Webserver stopped.\n")
    else:
        cmd = (
            f"{shlex.quote(sys.executable)} "
            f"{shlex.quote(SERVE_SCRIPT)} --directory {shlex.quote(SCRIPT_DIR)}"
            f" --port {SERVER_PORT}"
        )
        print(f"Starting webserver on port {SERVER_PORT} serving '{SCRIPT_DIR}'…")
        server_proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print(f"Webserver running (PID {server_proc.pid}). Access it at {SERVER_URL}\n")


# --- JSON control routines ---
def backup_json_and_images():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"backup_{timestamp}.zip"
    backup_path = os.path.join(BACKUP_DIR, zip_name)
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(OUTPUT_JSON):
            zf.write(OUTPUT_JSON, arcname=os.path.basename(OUTPUT_JSON))
        if os.path.isdir(EXTRACT_FOLDER):
            for root, _, files in os.walk(EXTRACT_FOLDER):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.join(
                        os.path.basename(EXTRACT_FOLDER),
                        os.path.relpath(full_path, EXTRACT_FOLDER),
                    )
                    zf.write(full_path, arcname=rel_path)
        if os.path.isdir(IMAGES_FOLDER):
            for root, _, files in os.walk(IMAGES_FOLDER):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.join(
                        os.path.basename(IMAGES_FOLDER),
                        os.path.relpath(full_path, IMAGES_FOLDER),
                    )
                    zf.write(full_path, arcname=rel_path)
    print(f"\u2713 Backup created at {backup_path}\n")

def clear_output_folder():
    confirm = input(
        f"Are you sure you want to delete all files in '{os.path.abspath(os.path.dirname(OUTPUT_JSON))}'? Type 'YES' to confirm: "
    ).strip()
    if confirm != "YES":
        print("Clear cancelled. No files were deleted.\n")
    else:
        if os.path.isdir(EXTRACT_FOLDER):
            shutil.rmtree(EXTRACT_FOLDER)
        if os.path.isdir(IMAGES_FOLDER):
            shutil.rmtree(IMAGES_FOLDER)
        if os.path.exists(OUTPUT_JSON):
            os.remove(OUTPUT_JSON)
        os.makedirs(EXTRACT_FOLDER, exist_ok=True)
        os.makedirs(IMAGES_FOLDER, exist_ok=True)
        print("\u2713 Output folder cleared and ready for new data.\n")

def handle_json_control():
    choice = prompt_json_menu()
    if choice == "1":
        backup_json_and_images()
    elif choice == "2":
        clear_output_folder()
    elif choice == "3":
        return
    else:
        print("Invalid choice. Please select 1-3.\n")


# --- Question Analysis ---
def handle_question_analysis():
    if not os.path.exists(OUTPUT_JSON):
        print("No JSON data found. Please process quizzes first.\n")
        return

    # Load data
    with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Deduplicate based on question text
    seen = set()
    unique_questions = []
    for entry in data:
        question_texts = [block['text'] for block in entry.get('question_body', []) if block.get('type') == 'text']
        question_key = " ".join(question_texts).strip().lower()
        if question_key not in seen:
            seen.add(question_key)
            unique_questions.append(entry)

    # --- Auto-backup (not user-triggered) ---
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"auto_backup_dedup_{timestamp}.zip"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(OUTPUT_JSON):
            zf.write(OUTPUT_JSON, arcname=os.path.basename(OUTPUT_JSON))
        if os.path.isdir(EXTRACT_FOLDER):
            for root, _, files in os.walk(EXTRACT_FOLDER):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.join(os.path.basename(EXTRACT_FOLDER), os.path.relpath(full_path, EXTRACT_FOLDER))
                    zf.write(full_path, arcname=rel_path)
        if os.path.isdir(IMAGES_FOLDER):
            for root, _, files in os.walk(IMAGES_FOLDER):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.join(os.path.basename(IMAGES_FOLDER), os.path.relpath(full_path, IMAGES_FOLDER))
                    zf.write(full_path, arcname=rel_path)

    # Save deduplicated JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(unique_questions, f, indent=2)

    print(f"\u2713 Duplicate removal complete. {len(unique_questions)} unique questions saved to {OUTPUT_JSON}")
    print(f"\u2713 Auto-backup of original data saved to {backup_path}\n")



# --- Main menu and dispatch ---
def main_menu():
    while True:
        choice = prompt_main_menu()
        if choice == "1":
            handle_process_menu()
        elif choice == "2":
            handle_toggle_server()
        elif choice == "3":
            handle_json_control()
        elif choice == "4":
            handle_question_analysis()
        elif choice == "5":
            if server_proc and server_proc.poll() is None:
                print("Shutting down webserver before exit…")
                server_proc.terminate()
                server_proc.wait()
            print("Exiting. Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Please select 1-5.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Canvas quiz extractor and server menu")
    parser.add_argument("--extract", action="store_true", help="Process HTML files immediately")
    parser.add_argument("--serve", action="store_true", help="Start quiz webserver immediately")
    args = parser.parse_args()

    if args.extract:
        handle_process_html()
        main_menu()
    elif args.serve:
        handle_toggle_server()
        main_menu()
    else:
        main_menu()
