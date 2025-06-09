#!/usr/bin/env python3
"""
serve_quiz.py

A simple Python HTTP server for serving quiz files,
with optional auto-open and graceful fallback,
suppressing browser-launch errors.
"""
import http.server
import socketserver
import os
import argparse
import webbrowser
import sys

def serve_quiz(directory: str = None, port: int = 8000, no_open: bool = False):
    """
    Serve the given directory over HTTP on localhost:<port>.
    Optionally open index.html in the default browser.

    Args:
      directory: Path to the folder to serve. If None, uses CWD.
      port:      Port number to bind the HTTP server to.
      no_open:   If True, skip attempting to open the browser.
    """
    # Default to current working directory if not provided
    directory = directory or os.getcwd()
    os.chdir(directory)

    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        url = f"http://localhost:{port}/index.html"
        print(f"Serving HTTP at {url}")

        # Try to open the browser unless disabled
        if not no_open:
            try:
                # Suppress underlying browser open errors
                devnull = open(os.devnull, 'w')
                stderr_save = sys.stderr
                sys.stderr = devnull
                webbrowser.open(url)
                sys.stderr = stderr_save
                devnull.close()
            except Exception:
                print(f"Could not open a browser automatically.\nPlease open {url} manually.")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Serve quiz files over HTTP and open index.html in browser"
    )
    parser.add_argument(
        "-p", "--port", type=int, default=8000,
        help="Port number to serve on (default: 8000)"
    )
    parser.add_argument(
        "-d", "--directory", default=None,
        help="Directory to serve (default: current working directory)"
    )
    parser.add_argument(
        "--no-open", action="store_true",
        help="Do not attempt to open the browser automatically"
    )
    args = parser.parse_args()
    serve_quiz(args.directory, args.port, args.no_open)
