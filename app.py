#!/usr/bin/env python3
import http.server
import json
import urllib.request
import urllib.error
import urllib.parse
import ssl
import time
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress default logging

    def send_json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,PATCH,HEAD,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._serve_file("index.html", "text/html")
        elif self.path.startswith("/static/"):
            fname = self.path[len("/static/"):]
            self._serve_file(fname, self._mime(fname))
        elif self.path == "/api/history":
            self.send_json(200, load_history())
        elif self.path == "/api/collections":
            self.send_json(200, load_collections())
        elif self.path == "/api/environments":
            self.send_json(200, load_environments())
        else:
            self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""

        if self.path == "/api/request":
            self._handle_proxy(body)
        elif self.path == "/api/collections/save":
            self._handle_save_collection(body)
        elif self.path == "/api/environments/save":
            self._handle_save_env(body)
        elif self.path == "/api/history/clear":
            save_history([])
            self.send_json(200, {"ok": True})
        else:
            self.send_json(404, {"error": "Not found"})

    def do_DELETE(self):
        if self.path.startswith("/api/collections/"):
            name = urllib.parse.unquote(self.path[len("/api/collections/"):])
            cols = load_collections()
            cols = [c for c in cols if c.get("name") != name]
            save_collections(cols)
            self.send_json(200, {"ok": True})
        elif self.path.startswith("/api/environments/"):
            name = urllib.parse.unquote(self.path[len("/api/environments/"):])
            envs = load_environments()
            envs = [e for e in envs if e.get("name") != name]
            save_environments(envs)
            self.send_json(200, {"ok": True})
        else:
            self.send_json(404, {"error": "Not found"})

    def _handle_proxy(self, raw):
        try:
            req_data = json.loads(raw)
        except Exception:
            self.send_json(400, {"error": "Invalid JSON"})
            return

        method  = req_data.get("method", "GET").upper()
        url     = req_data.get("url", "")
        headers = req_data.get("headers", {})
        body    = req_data.get("body", None)
        timeout = req_data.get("timeout", 30)

        if not url:
            self.send_json(400, {"error": "URL is required"})
            return

        # encode body
        body_bytes = None
        if body and method not in ("GET", "HEAD"):
            if isinstance(body, str):
                body_bytes = body.encode()
            elif isinstance(body, dict):
                content_type = headers.get("Content-Type", "")
                if "form" in content_type and "json" not in content_type:
                    body_bytes = urllib.parse.urlencode(body).encode()
                else:
                    body_bytes = json.dumps(body).encode()

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        request = urllib.request.Request(url, data=body_bytes, method=method)
        for k, v in headers.items():
            if v:
                request.add_header(k, v)

        t0 = time.time()
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=ctx) as resp:
                elapsed = round((time.time() - t0) * 1000)
                resp_body = resp.read()
                resp_headers = dict(resp.headers)
                status = resp.status

        except urllib.error.HTTPError as e:
            elapsed = round((time.time() - t0) * 1000)
            resp_body = e.read()
            resp_headers = dict(e.headers)
            status = e.code

        except Exception as e:
            self.send_json(200, {
                "error": str(e),
                "status": 0,
                "statusText": "Network Error",
                "time": round((time.time() - t0) * 1000),
                "size": 0,
                "headers": {},
                "body": ""
            })
            return

        # decode body
        content_type = resp_headers.get("Content-Type", "")
        charset = "utf-8"
        if "charset=" in content_type:
            charset = content_type.split("charset=")[-1].split(";")[0].strip()
        try:
            body_str = resp_body.decode(charset)
        except Exception:
            body_str = resp_body.decode("utf-8", errors="replace")

        result = {
            "status": status,
            "statusText": _status_text(status),
            "time": elapsed,
            "size": len(resp_body),
            "headers": resp_headers,
            "body": body_str,
            "contentType": content_type
        }

        # save to history
        hist = load_history()
        hist.insert(0, {
            "method": method,
            "url": url,
            "status": status,
            "time": elapsed,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "request": req_data
        })
        save_history(hist[:100])

        self.send_json(200, result)

    def _handle_save_collection(self, raw):
        try:
            data = json.loads(raw)
        except Exception:
            self.send_json(400, {"error": "Invalid JSON"})
            return
        cols = load_collections()
        # update existing or append
        for i, c in enumerate(cols):
            if c.get("name") == data.get("name"):
                cols[i] = data
                break
        else:
            cols.append(data)
        save_collections(cols)
        self.send_json(200, {"ok": True})

    def _handle_save_env(self, raw):
        try:
            data = json.loads(raw)
        except Exception:
            self.send_json(400, {"error": "Invalid JSON"})
            return
        envs = load_environments()
        for i, e in enumerate(envs):
            if e.get("name") == data.get("name"):
                envs[i] = data
                break
        else:
            envs.append(data)
        save_environments(envs)
        self.send_json(200, {"ok": True})

    def _serve_file(self, fname, mime):
        path = os.path.join(STATIC_DIR, fname)
        if not os.path.exists(path):
            self.send_response(404)
            self.end_headers()
            return
        with open(path, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", len(content))
        self.end_headers()
        self.wfile.write(content)

    def _mime(self, fname):
        ext = fname.rsplit(".", 1)[-1].lower()
        return {"js": "application/javascript", "css": "text/css",
                "html": "text/html", "png": "image/png",
                "svg": "image/svg+xml"}.get(ext, "application/octet-stream")


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

def _load(name):
    p = os.path.join(DATA_DIR, name)
    if not os.path.exists(p):
        return []
    with open(p) as f:
        return json.load(f)

def _save(name, data):
    with open(os.path.join(DATA_DIR, name), "w") as f:
        json.dump(data, f, indent=2)

def load_history():      return _load("history.json")
def save_history(d):     _save("history.json", d)
def load_collections():  return _load("collections.json")
def save_collections(d): _save("collections.json", d)
def load_environments(): return _load("environments.json")
def save_environments(d):_save("environments.json", d)

def _status_text(code):
    texts = {200:"OK",201:"Created",204:"No Content",301:"Moved Permanently",
             302:"Found",304:"Not Modified",400:"Bad Request",401:"Unauthorized",
             403:"Forbidden",404:"Not Found",405:"Method Not Allowed",
             408:"Request Timeout",409:"Conflict",422:"Unprocessable Entity",
             429:"Too Many Requests",500:"Internal Server Error",
             502:"Bad Gateway",503:"Service Unavailable",504:"Gateway Timeout"}
    return texts.get(code, "Unknown")


if __name__ == "__main__":
    port = 5000
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"  WebService Tester running at http://localhost:{port}")
    print("  Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
