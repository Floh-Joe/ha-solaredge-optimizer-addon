from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import solaredge_optimizers


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = solaredge_optimizers.get_optimizers_data()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        self.wfile.write(json.dumps(data).encode())


def run():
    server = HTTPServer(("", 8126), Handler)
    server.serve_forever()


if __name__ == "__main__":
    run()
