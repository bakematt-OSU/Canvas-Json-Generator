#!/usr/bin/env python3
import http.server
import socketserver
import os
import webbrowser
import argparse

def serve_quiz(directory: str = None, port: int = 8000):
    """
    Serve the given directory over HTTP on localhost:<port> and open index.html in the default browser.
    
    Args:
      directory: Path to the folder to serve. If None, uses CWD.
      port:      Port number to bind the HTTP server to.
    """
    # Default to current working directory if not provided
    directory = directory or os.getcwd()
    os.chdir(directory)

    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        url = f"http://localhost:{port}/index.html"
        print(f"Serving HTTP at {url}")
        webbrowser.open(url)
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
    args = parser.parse_args()
    serve_quiz(args.directory, args.port)
