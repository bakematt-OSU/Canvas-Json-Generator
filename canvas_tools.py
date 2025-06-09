#!/usr/bin/env python3
"""
canvas_extractor.py

Provides a menu-driven CLI to:
  1) Manage file processing (HTML, ZIP, folders)
  2) Serve quizzes (webserver)
"""
import sys
import os
import argparse
import zipfile
from extractor import (
    extract_main,
    ZIP_FILE,
    EXTRACT_FOLDER,
    OUTPUT_JSON,
    IMAGES_FOLDER,
    extract_questions_from_taken_quiz,
    write_json
)
from serve_quiz import (
    serve_quiz,
    main as serve_main
)

# Default input directory for files
INPUT_DIR = '_INPUT'


def prompt_main_menu():
    print("=== Canvas Study Tools Utility ===")
    print("1) Process files")
    print("2) Serve quizzes (webserver)")
    print("3) Exit")
    return input("Select an option: ").strip()


def prompt_process_menu():
    print("\n-- Process Files in the Input Folder --")
    print("1) Select Indivdual HTML files")
    print("2) ZIP HTML files")
    print("3) Folder of HTML files")
    print("4) Back to main menu")
    return input("Select an option: ").strip()


def list_input_html():
    try:
        files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.html')]
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
        zips = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.zip')]
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
        folders = [d for d in os.listdir(INPUT_DIR) if os.path.isdir(os.path.join(INPUT_DIR, d))]
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
    print(f"✔ Processed {len(all_questions)} questions to {OUTPUT_JSON}")
    print(f"✔ Images saved in {IMAGES_FOLDER}\n")


def handle_process_html():
    files = list_input_html()
    if not files:
        return
    sel = input("Enter file numbers to process (comma-separated): ").strip()
    indices = [int(x)-1 for x in sel.split(',') if x.strip().isdigit()]
    html_files = [os.path.join(INPUT_DIR, files[i]) for i in indices if 0 <= i < len(files)]
    handle_process_html_selection(html_files)


def handle_process_zips():
    zips = list_input_zips()
    if not zips:
        return
    sel = input("Enter ZIP numbers to process (comma-separated): ").strip()
    indices = [int(x)-1 for x in sel.split(',') if x.strip().isdigit()]
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
    indices = [int(x)-1 for x in sel.split(',') if x.strip().isdigit()]
    html_files = []
    for i in indices:
        if 0 <= i < len(folders):
            folder_path = os.path.join(INPUT_DIR, folders[i])
            files = [f for f in os.listdir(folder_path) if f.lower().endswith('.html')]
            html_files.extend(os.path.join(folder_path, f) for f in files)
    handle_process_html_selection(html_files)


def handle_process_menu():
    while True:
        choice = prompt_process_menu()
        if choice == '1':
            handle_process_html()
        elif choice == '2':
            handle_process_zips()
        elif choice == '3':
            handle_process_folders()
        elif choice == '4':
            return
        else:
            print("Invalid choice. Please select 1-4.\n")


def handle_serve_quizzes():
    print("\n-- Serve Quizzes --")
    # Default to the folder where OUTPUT_JSON lives
    default_dir = os.path.abspath(os.path.dirname(OUTPUT_JSON))
    directory =  default_dir
    port_input = input("Port number [8000]: ").strip()
    port = int(port_input) if port_input.isdigit() else 8000
    no_open_input = input("Open browser automatically? (Y/n): ").strip().lower()
    no_open = (no_open_input == 'n')
    serve_quiz(directory, port, no_open)


def main_menu():
    while True:
        choice = prompt_main_menu()
        if choice == '1':
            handle_process_menu()
        elif choice == '2':
            handle_serve_quizzes()
        elif choice == '3':
            print("Exiting. Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Please select 1-3.\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Canvas quiz extractor and server menu")
    parser.add_argument('--extract', action='store_true', help='Process HTML files immediately')
    parser.add_argument('--serve', action='store_true', help='Serve quizzes immediately')
    args = parser.parse_args()

    if args.extract:
        handle_process_html()
    elif args.serve:
        handle_serve_quizzes()
    else:
        main_menu()
