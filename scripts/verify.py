"""Verify actual proof/cover/witness/replay/simulation evidence, not exit codes alone."""
from pathlib import Path
import csv,hashlib,json,re

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports'
for mode in ('broken','prove','cover'):
    status=(ROOT/f'build/{mode}/status').read_text().split()[0]
    text=(R/f'{mode}.log').read_text()
    expected='FAIL' if mode=='broken' else 'PASS'
    assert status==expected and f'DONE ({expected}, rc=' in text,mode
    assert 'DONE (ERROR' not in text and 'DONE (TIMEOUT' not in text
    source='tests/fifo_broken.v' if mode=='broken' else 'rtl/fifo.v'
    assert (ROOT/source).read_bytes()==(ROOT/f'build/{mode}/src'/Path(source).name).read_bytes(),mode+' RTL changed after proof'
    assert (ROOT/'formal/contract.vh').read_bytes()==(ROOT/f'build/{mode}/src/contract.vh').read_bytes(),mode+' properties changed'
    config=ROOT/f'formal/fifo_{mode}.sby'
    assert config.read_bytes()==(ROOT/f'build/{mode}/config.sby').read_bytes(),mode+' task changed after proof'
assert int((R/'broken_exit.txt').read_text())==2
assert int((R/'prove_exit.txt').read_text())==int((R/'cover_exit.txt').read_text())==0
broken=(R/'broken.log').read_text()
assert re.search(r'failed assertion fifo\.a_level .* step 4',broken)
prove=(R/'prove.log').read_text()
assert 'successful proof by k-induction' in prove
assert 'returned pass for basecase' in prove and 'returned pass for induction' in prove
contract=(ROOT/'formal/contract.vh').read_text()
assert re.findall(r'\bassume\((.*?)\)',contract)==['rst']
assert 'if(!f_past_valid) assume(rst);' in contract and 'reg f_past_valid=0;' in contract
assert 'f_push=wr_en && (f_count<4)' in contract and 'f_pop=rd_en && (f_count>0)' in contract
expected_covers=set(re.findall(r'\b(c_\w+):\s*cover\(',contract))
cover=(ROOT/'build/cover/PASS').read_text()
reached=dict((name,int(step)) for name,step in re.findall(r'reached cover statement fifo\.(c_\w+) .* step (\d+)',cover))
assert len(expected_covers)==12 and expected_covers==set(reached)
for trace in re.findall(r'cover trace: (engine_0/\S+\.vcd)',cover):assert (ROOT/'build/cover'/trace).stat().st_size>100
cex=json.loads((R/'counterexample.json').read_text())
witness=ROOT/'build/broken/engine_0/trace.vcd'
assert hashlib.sha256(witness.read_bytes()).hexdigest()==cex['witness_sha256']
assert hashlib.sha256((ROOT/'tests/fifo_broken.v').read_bytes()).hexdigest()==cex['source_sha256']
rows=list(csv.DictReader((R/'counterexample.csv').open()))
assert len(rows)==cex['replay_steps']==5
assert cex['preceding_inputs']['take_read']==cex['preceding_inputs']['take_write']==1
assert cex['mismatched_state']['level']==2 and cex['mismatched_state']['f_count']==1
simulation=(R/'simulation.log').read_text()
match=re.search(r'FIFO_SIM_PASS cycles=(\d+) checks=(\d+) pushes=(\d+) pops=(\d+) simultaneous=(\d+) rejected_writes=(\d+) rejected_reads=(\d+) resets=(\d+)',simulation)
assert match and tuple(map(int,match.groups()))==(2195,13170,983,967,394,95,168,11)
assert not re.search(r'(?i)fatal|error|mismatch',simulation)
replay=(R/'replay_fixed.log').read_text()
assert 'FIFO_REPLAY_PASS cycles=5 checks=30' in replay and not re.search(r'(?i)fatal|error|mismatch',replay)
for mode,cycle in (('simulation',3),('replay',2)):
    negative=(R/f'{mode}_broken.log').read_text()
    assert f'FIFO_SIM_MISMATCH occupancy cycle={cycle} level=2 expected=1 rst=0 wr=1 rd=1' in negative
    assert int((R/f'{mode}_broken_exit.txt').read_text())==1
    assert '_PASS' not in negative
versions=(R/'tool_versions.txt').read_text()
assert 'SBY v0.63-11-g6424d15' in versions and 'Icarus Verilog version 14.0' in versions
yosys=re.search(r'^ Yosys (.+)$',(ROOT/'build/prove/model/design.log').read_text(),re.M)[1]
lock=json.loads((ROOT/'crucible.lock').read_text())
assert {tool['name'] for env in lock['environments'] for tool in env['tools']}=={'symbiyosys','iverilog'}
summary={'measurement_date':'2026-11-01','configuration':{'entries':4,'data_bits':8,'reset':'synchronous active high; first proof edge must reset; later resets unconstrained'},
 'proof':'PASS: basecase and temporal induction; unbounded safety under stated single-clock/reset model',
 'engine':'SymbiYosys smtbmc yices','sby_version':'v0.63-11-g6424d15','yosys_version':yosys,
 'covers':reached,'cover_count':len(reached),'broken_assertion':'a_level fails at formal step 4',
 'counterexample':cex,'simulation':dict(zip(('cycles','checks','pushes','pops','simultaneous','rejected_writes','rejected_reads','resets'),map(int,match.groups()))),
 'replay':{'cycles':5,'checks':30,'corrected':'PASS','broken':'occupancy mismatch, 2 versus expected 1; exit 1'},
 'scope':'Exact fixed four-entry eight-bit untimed RTL safety. No CDC, liveness/fairness, timing, physical implementation or hardware claim.'}
files=['rtl/fifo.v','tests/fifo_broken.v','tests/tb.v','formal/contract.vh','formal/fifo_prove.sby','formal/fifo_cover.sby','formal/fifo_broken.sby']
summary['files_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files}
(R/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('files_sha256','counterexample')},indent=2))
print('FIFO_UNBOUNDED_PROOF_COVERS_CAUSAL_COUNTEREXAMPLE_AND_SIMULATION_VERIFIED')
