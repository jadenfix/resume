import unittest,subprocess,tempfile,sys,json,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).parent
class E2E(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.start()
 def start(self):
  self.proc=subprocess.Popen([sys.executable,str(ROOT/'app.py'),'--port','0','--db',self.tmp.name+'/db.sqlite3'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True);self.url=self.proc.stdout.readline().strip()
 def tearDown(self):self.proc.terminate();self.proc.wait(timeout=5);self.proc.stdout.close();self.tmp.cleanup()
 def request(self,path,data=None):
  req=urllib.request.Request(self.url+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read())
 def restart(self):self.proc.terminate();self.proc.wait(timeout=5);self.proc.stdout.close();self.start()
 def test_save_restart_and_sanitized_export(self):
  data={'name':'<script>bad()</script>','headline':'Example role','experience':'User supplied experience','skills':'Python'}
  self.request('/api/profile',data);self.restart();self.assertEqual(self.request('/api/profile')['name'],data['name'])
  with urllib.request.urlopen(self.url+'/export.html') as r:
   text=r.read().decode();self.assertNotIn('<script>',text);self.assertIn('&lt;script&gt;',text);self.assertIn('attachment',r.headers['Content-Disposition'])
 def test_validation(self):
  for data in [[],{}, {'name':7},{'name':'x','skills':'y'*2001}]:
   with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/profile',data)
   self.assertEqual(e.exception.code,400)
if __name__=='__main__':unittest.main()
