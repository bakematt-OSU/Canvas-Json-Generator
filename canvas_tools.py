#!/usr/bin/env python3
"""
canvas_extractor.py

Provides a menu-driven CLI to:
  1) Process HTML files (extract questions)
  2) Serve quizzes (webserver)
"""
import sys
import os
import argparse
from extractor import (
    main as extract_main,
    ZIP_FILE,
    EXTRACT_FOLDER,
    OUTPUT_JSON,
    IMAGES_FOLDER,
    extract_questions_from_taken_quiz,
    write_json
)
from serve_quiz import serve_quiz

# Default input directory for HTML files
INPUT_DIR = '_INPUT'

def prompt_menu():
    print("=== Canvas Study Tools Utility ===")
    print("1) Process HTML files")
    print("2) Serve quizzes (webserver)")
    print("3) Exit")
    return input("Select an option: ").strip()


def handle_process_html():
    print("\n-- Process HTML Files --")
    print("Select input method:")
    print("1) Individual HTML files")
    print("2) ZIP file")
    print("3) Folder")
    print(f"4) All .html files in '{INPUT_DIR}'")
    choice = input("Select an option [1-4]: ").strip()
    html_files = []

    if choice == '1':
        files_str = input("Enter paths to HTML files (separated by commas): ").strip()
        html_files = [f.strip() for f in files_str.split(',') if f.strip()]
    elif choice == '2':
        print(f"Using ZIP file: {ZIP_FILE}")
        extract_main(ZIP_FILE, EXTRACT_FOLDER, OUTPUT_JSON, IMAGES_FOLDER)
        print()
        return
    elif choice == '3':
        folder = input("Enter folder containing HTML files: ").strip()
        html_files = [
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith('.html')
        ]
    elif choice == '4':
        html_files = [
            os.path.join(INPUT_DIR, f)
            for f in os.listdir(INPUT_DIR)
            if f.lower().endswith('.html')
        ]
    else:
        print("Invalid choice. Returning to menu.\n")
        return

    # Process selected HTML files
    os.makedirs(IMAGES_FOLDER, exist_ok=True)
    all_questions = []
    for html in html_files:
        print(f"Parsing {html}…")
        all_questions.extend(extract_questions_from_taken_quiz(html, IMAGES_FOLDER))
    write_json(all_questions, OUTPUT_JSON)
    print(f"✔ Processed {len(all_questions)} questions to {OUTPUT_JSON}")
    print(f"✔ Images saved in {IMAGES_FOLDER}\n")


def handle_serve_quizzes():
    print("\n-- Serve Quizzes --")
    default_dir = os.path.abspath(os.path.dirname(OUTPUT_JSON))
    directory = input(f"Directory to serve [{default_dir}]: ").strip() or default_dir
    port_input = input("Port number [8000]: ").strip()
    port = int(port_input) if port_input.isdigit() else 8000
    no_open_input = input("Open browser automatically? (Y/n): ").strip().lower()
    no_open = (no_open_input == 'n')
    serve_quiz(directory, port, no_open)


def main_menu():
    while True:
        choice = prompt_menu()
        if choice == '1':
            handle_process_html()
        elif choice == '2':
            try:
                handle_serve_quizzes()
            except KeyboardInterrupt:
                print("\nWeb server stopped by user.\n")
        elif choice == '3':
            print("Exiting. Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Please select 1, 2, or 3.\n")


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
