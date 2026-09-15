from http.server import BaseHTTPRequestHandler, HTTPServer
import json
PORT = 8765
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            body = json.dumps({'status':'ok'}).encode()
            self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(body)
        elif self.path == '/items/count':
            # Deliberate runtime bug: expected count is 3, observed count is 99.
            body = json.dumps({'count':99}).encode()
            self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(body)
        else:
            self.send_response(404); self.end_headers()
    def log_message(self, *args):
        pass
if __name__ == '__main__':
    HTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
