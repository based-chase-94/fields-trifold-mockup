#!/usr/bin/env python3
"""Serve the repo root on http://localhost:8124/ — same as GitHub Pages will.

The page works straight off disk too; this is only for checking it over HTTP.
"""

import functools
import http.server
import pathlib
import socketserver

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = 8124

handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                            directory=str(ROOT))
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("127.0.0.1", PORT), handler) as httpd:
    print(f"serving {ROOT} at http://localhost:{PORT}/  (ctrl-c to stop)")
    httpd.serve_forever()
