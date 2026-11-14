import importlib.util,tempfile,pathlib,unittest,time,json
from unittest.mock import patch
base=pathlib.Path(__file__).resolve().parents[1]
p=base/'ha_bundle/scripts/ania_ha.py'
if not p.exists():p=base.parent/'home_assistant/scripts/ania_ha.py'
spec=importlib.util.spec_from_file_location('helper',p);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
class Tests(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();h.ROOT=pathlib.Path(self.t.name)
 def tearDown(self):self.t.cleanup()
 def test_target_only_one_post(self):
  with patch.object(h,'request',return_value=dict(status='in_progress',request_id='a'*32,target_c=17)) as r:
   self.assertEqual(h.run('target','17')[0],0);r.assert_called_once();self.assertEqual(r.call_args.args[1]['target_c'],17)
 def test_invalid_target_no_request(self):
  with patch.object(h,'request') as r:
   for x in ['3','26','nan','12.5','17; reboot']:self.assertEqual(h.run('target',x)[0],2)
   r.assert_not_called()
 def test_last_value_preserved_as_stale(self):
  old=dict(status='confirmed',setpoint_c=13,observed_epoch=time.time()-12,observed_at='old')
  (h.ROOT/'.ania_last_confirmed.json').write_text(json.dumps(old))
  with patch.object(h,'request',side_effect=TimeoutError()):
   _,result=h.run('read');self.assertEqual(result['status'],'stale');self.assertEqual(result['observed_at'],'old');self.assertEqual(result['setpoint_c'],13)
 def test_status_never_posts(self):
  with patch.object(h,'request',return_value=dict(status='in_progress',request_id='a'*32)) as r:
   h.run('status','a'*32);r.assert_called_once_with('/v1/command/'+'a'*32)
if __name__=='__main__':unittest.main()
