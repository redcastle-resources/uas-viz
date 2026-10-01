"""Static file server with HTTP Range support for previewing the whole site locally.

Mounts landing-page/ at /, potree-static-site/ at /potree/, and
dtm-static-site/ at /dtm/, matching the deployed layout the landing page
links to. Range support is required by Potree's octree/hierarchy loaders and
geotiff.js/COG reads.
"""
import http.server
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

MOUNTS = {
    '/potree': os.path.join(ROOT, 'potree-static-site'),
    '/dtm': os.path.join(ROOT, 'dtm-static-site'),
    '': os.path.join(ROOT, 'landing-page'),
}


class RangeRequestHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = path.split('?', 1)[0].split('#', 1)[0]
        for prefix, directory in MOUNTS.items():
            if prefix and (path == prefix or path.startswith(prefix + '/')):
                rel = path[len(prefix):].lstrip('/')
                return os.path.join(directory, rel) if rel else directory
        rel = path.lstrip('/')
        return os.path.join(MOUNTS[''], rel) if rel else MOUNTS['']

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            for index in ('index.html', 'index.htm'):
                index_path = os.path.join(path, index)
                if os.path.exists(index_path):
                    path = index_path
                    break
            else:
                return super().send_head()

        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404, "File not found")
            return None

        fs = os.fstat(f.fileno())
        file_len = fs.st_size
        range_header = self.headers.get('Range')

        if range_header:
            match = re.match(r'bytes=(\d*)-(\d*)', range_header)
            if not match or not (match.group(1) or match.group(2)):
                f.close()
                self.send_error(416, "Requested Range Not Satisfiable")
                self.send_header('Content-Range', f'bytes */{file_len}')
                return None

            start_str, end_str = match.groups()
            if start_str:
                start = int(start_str)
                end = int(end_str) if end_str else file_len - 1
            else:
                length = int(end_str)
                start = max(file_len - length, 0)
                end = file_len - 1

            if start >= file_len or start > end:
                f.close()
                self.send_error(416, "Requested Range Not Satisfiable")
                self.send_header('Content-Range', f'bytes */{file_len}')
                return None

            end = min(end, file_len - 1)
            length = end - start + 1

            self.send_response(206)
            self.send_header('Content-type', self.guess_type(path))
            self.send_header('Content-Range', f'bytes {start}-{end}/{file_len}')
            self.send_header('Content-Length', str(length))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Last-Modified', self.date_time_string(fs.st_mtime))
            self.end_headers()

            f.seek(start)
            self._range_length = length
            return f

        self.send_response(200)
        self.send_header('Content-type', self.guess_type(path))
        self.send_header('Content-Length', str(file_len))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Last-Modified', self.date_time_string(fs.st_mtime))
        self.end_headers()
        self._range_length = file_len
        return f

    def copyfile(self, source, outputfile):
        if hasattr(self, '_range_length'):
            remaining = self._range_length
            while remaining > 0:
                chunk = source.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                outputfile.write(chunk)
                remaining -= len(chunk)
        else:
            super().copyfile(source, outputfile)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    server = http.server.ThreadingHTTPServer(('', port), RangeRequestHandler)
    print(f'Serving full site on http://localhost:{port} (Range requests supported)')
    print(f'  /        -> landing-page/')
    print(f'  /potree/ -> potree-static-site/')
    print(f'  /dtm/    -> dtm-static-site/')
    server.serve_forever()


if __name__ == '__main__':
    main()
