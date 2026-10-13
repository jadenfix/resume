"""Local resume builder. Stores supplied facts only; exports safely escaped HTML."""
import argparse, json, sqlite3, html
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlsplit
from pathlib import Path
ROOT=Path(__file__).parent
FIELDS={'name':120,'headline':200,'email':200,'experience':10000,'skills':2000}
def validate(data):
 if not isinstance(data,dict):raise ValueError('Expected an object')
 result={}
 for key,limit in FIELDS.items():
  value=data.get(key,'')
  if not isinstance(value,str) or len(value)>limit:raise ValueError(f'{key}: text of at most {limit} characters')
  result[key]=value.strip()
 if not result['name']:raise ValueError('Enter your name')
 return result
def document(data):
 e={k:html.escape(v) for k,v in data.items()}
 return ('<!doctype html><html><head><meta charset="utf-8"><title>Resume</title><style>body{font:16px Georgia;max-width:750px;margin:60px auto;padding:20px;color:#222}h1{font-size:42px}pre{font:inherit;white-space:pre-wrap;line-height:1.65}h2{margin-top:35px;border-bottom:1px solid #ccc;padding-bottom:10px}@media print{body{margin:0;max-width:none}}</style></head><body>'+f'<h1>{e["name"]}</h1><p>{e["headline"]}</p><p>{e["email"]}</p><h2>Experience</h2><pre>{e["experience"]}</pre><h2>Skills</h2><pre>{e["skills"]}</pre></body></html>').encode()
def handler(db):
 def connect():
  c=sqlite3.connect(db);c.execute('CREATE TABLE IF NOT EXISTS profile(id INTEGER PRIMARY KEY, data TEXT)');return c
 class Handler(BaseHTTPRequestHandler):
  def send(self,status,data,mime='application/json',download=False):
   body=json.dumps(data).encode() if mime=='application/json' else data
   self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)));self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'")
   if download:self.send_header('Content-Disposition','attachment; filename="resume.html"')
   self.end_headers();self.wfile.write(body)
  def do_GET(self):
   self.path=urlsplit(self.path).path
   if self.path=='/':return self.send(200,(ROOT/'index.html').read_bytes(),'text/html; charset=utf-8')
   if self.path=='/app.js':return self.send(200,(ROOT/'app.js').read_bytes(),'text/javascript')
   if self.path in ['/api/profile','/export.html','/preview.html']:
    with connect() as c:row=c.execute('SELECT data FROM profile WHERE id=1').fetchone()
    data=json.loads(row[0]) if row else {k:'' for k in FIELDS}
    if self.path=='/api/profile':return self.send(200,data)
    return self.send(200,document(data),'text/html; charset=utf-8',download=self.path=='/export.html')
   self.send(404,{'error':'Not found'})
  def do_POST(self):
   if self.path!='/api/profile':return self.send(404,{'error':'Not found'})
   origin=self.headers.get('Origin')
   if origin and origin!='http://'+self.headers.get('Host',''):return self.send(403,{'error':'Cross-origin writes disabled'})
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 1<=size<=65536:return self.send(413,{'error':'Request size limit: 64KB'})
    data=validate(json.loads(self.rfile.read(size)))
   except (ValueError,TypeError) as e:return self.send(400,{'error':str(e)})
   with connect() as c:c.execute('INSERT INTO profile(id,data) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(json.dumps(data),))
   self.send(200,data)
 return Handler
def main():
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8083);p.add_argument('--db',default=str(ROOT/'resume.sqlite3'));a=p.parse_args();s=ThreadingHTTPServer(('127.0.0.1',a.port),handler(a.db));print(f'http://127.0.0.1:{s.server_port}',flush=True);s.serve_forever()
if __name__=='__main__':main()
