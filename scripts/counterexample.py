"""Extract and explain the actual solver witness, preserving pre-reset meaning."""
from pathlib import Path
import csv,json,hashlib,re
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'build/broken/engine_0/trace.vcd'
names={};values={};rows=[];time=None
fields=['rst','wr_en','rd_en','wr_data','level','f_count','take_write','take_read']
smtc=(path.parent/'trace.smtc').read_text()
state_ids=set(map(int,re.findall(r'(?m)^state (\d+)$',smtc)))
def capture():
    if time is not None and time%10==0 and 'smt_step' in values and all(name in values for name in fields):
        step=values['smt_step']
        if step in state_ids and (not rows or rows[-1]['step']!=step):
            rows.append(dict(step=step,**{name:values[name] for name in fields}))
for line in path.read_text().splitlines():
    if line.startswith('$var'):
        parts=line.split();names[parts[3]]=parts[4]
    elif line.startswith('#'):
        capture();time=int(line[1:])
    elif line.startswith('b'):
        bits,ident=line[1:].split()
        if ident in names and set(bits)<=set('01'):values[names[ident]]=int(bits,2)
capture()
assert rows and rows[0]['rst']==1
assert [row['step'] for row in rows]==sorted(state_ids)
for number,body in re.findall(r'(?ms)^state (\d+)\n(.*?)(?=^state |\Z)',smtc):
    row=rows[int(number)]
    for field in ('rst','wr_en','rd_en','wr_data'):
        token=re.search(r'assume \(= \['+field+r'\] (true|false|#b[01]+)\)',body)[1]
        expected=(1 if token=='true' else 0) if token in ('true','false') else int(token[2:],2)
        assert row[field]==expected,(number,field)
mismatch=next(i for i,row in enumerate(rows) if i>0 and row['level']!=row['f_count'])
before,after=rows[mismatch-1],rows[mismatch]
assert before['rst']==0 and before['take_write']==before['take_read']==1
assert after['level']==before['level']+1 and after['f_count']==before['f_count']
assert before['level']==before['f_count']
with (ROOT/'reports/counterexample.csv').open('w',newline='') as out:
    writer=csv.DictWriter(out,fieldnames=['step']+fields);writer.writeheader();writer.writerows(rows)
# Replay all concrete input cycles through an independent simulation scoreboard.
words=[(row['rst']<<10)|(row['wr_en']<<9)|(row['rd_en']<<8)|row['wr_data'] for row in rows]
(ROOT/'build/replay.mem').write_text('\n'.join(f'{value:03x}' for value in words)+'\n')
record={'witness_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'source_sha256':hashlib.sha256((ROOT/'tests/fifo_broken.v').read_bytes()).hexdigest(),
        'first_mismatch_step':after['step'],'preceding_inputs':before,'mismatched_state':after,
        'replay_steps':len(rows),
        'scope':'Step zero is unconstrained pre-reset state. Compare occupancy only after the required initial reset edge.'}
(ROOT/'reports/counterexample.json').write_text(json.dumps(record,indent=2)+'\n')
print('FIFO_CAUSAL_SIMULTANEOUS_TRANSFER_COUNTEREXAMPLE_EXTRACTED',before['level'],'->',after['level'],'expected',after['f_count'])
