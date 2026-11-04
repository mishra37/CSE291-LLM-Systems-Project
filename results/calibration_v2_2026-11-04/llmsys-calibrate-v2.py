import json
from pathlib import Path
import subprocess

root=Path.home()/'CSE291-LLM-Systems-Project'
source=root/'workloads/tasks/v2'
def read(name):
    return [json.loads(x) for x in (source/name).read_text().splitlines()]
multi=read('multistep.jsonl')
tasks=[read('short_qa.jsonl')[0],read('long_context.jsonl')[0],*read('long_generation.jsonl'),*[multi[i] for i in (0,10,20,30)]]
out=root/'workloads/generated/calibration_v2.jsonl'
out.parent.mkdir(exist_ok=True)
out.write_text(''.join(json.dumps(t)+'\n' for t in tasks))
py=str(Path.home()/'llmsys/venv/bin/python')
subprocess.run([py,'-m','workloads.validate_collection','--tasks-dir','workloads/tasks/v2'],cwd=root,check=True)
for policy in ('fifo_request','fifo_task'):
    import os
    subprocess.run(['bash','setup/launch_server.sh','--cache-ram','0'],cwd=root,env=dict(os.environ,CTX='16384',NP='4'),check=True)
    subprocess.run([py,'-m','runner.run','--workload',str(out),'--sched',policy,'-k','1','--tool-delay','0.1','--name','calibration_v2_'+policy,'--server-args','-c 16384 -np 4 --cache-ram 0'],cwd=root,check=True)
    result=root/'results/raw'/('calibration_v2_'+policy)
    (result/'deployment.json').write_text(json.dumps({'base_commit':'555d9b4f2e6b02e0133ee02fe4f706f7d1b35120','includes_uncommitted_runner_changes':True,'source_archive_sha256':'bd183b9dec319c8855146bb07f92d81b8c3755a000b3514f4a046da0400d7e88','purpose':'v2 task calibration: two QA controls, ten writing tasks, four multistep subtypes; not a policy comparison'},indent=2))
    print('QUALITY',policy,(result/'quality.jsonl').read_text(),flush=True)
