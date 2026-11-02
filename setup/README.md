# Node setup

Both environments use the same scripts. Heavy files (llama.cpp build, model, venv) go to `~/llmsys`, outside the repo.

```bash
bash setup/setup_node.sh                 # ~10-20 min the first time
CTX=16384 NP=4 bash setup/launch_server.sh
~/llmsys/venv/bin/python setup/smoke_test.py
```

The smoke test passes if:
- call 1 and call 2 both return text
- call 2 shows `cache_n` around 2000+ and a much smaller `prompt_ms` (the prefix cache works)
- `nvidia-smi` shows about 5–7 GB in use

## DataHub (free, use for development)
1. https://datahub.ucsd.edu → profile **CSE291A_FA26_003 - Yiying Zhang [FA26]**.
2. Open a Terminal and run `nvidia-smi`. You should see a 24 GB slice of an RTX PRO 6000 (Blackwell, compute 12.0).
3. Get the code: `git clone <your private repo>`, or upload the `setup/` folder plus `requirements.txt`.
4. Run the three commands above. DataHub has no CUDA toolkit, so the script installs CUDA 12.8 with conda (several GB, one time).
5. Save the TritonAI key for later workload generation: `echo $OPENAI_BASE_URL; echo $OPENAI_API_KEY`. Put the values in a `.env` file. Never commit it.

Caveats:
- The server is up only while the notebook session is.
- GPU memory figures on a MIG/vGPU slice can look odd. Note them in `results/env_*.txt`.

## AWS (final measurements)
Budget: $200 total, $20/day.

1. **Region.** Use whichever region the course account is set up in. Check Service Quotas → EC2 → "Running On-Demand G and VT instances". It needs to be ≥ 4 vCPUs (≥ 8 for g6.2xlarge).
2. **Key pair.** EC2 → Key Pairs → *Import key pair* → paste `~/.ssh/id_ed25519.pub` from your Mac.
3. **Launch instance:**
   - AMI: **Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04)**. It already has the driver and CUDA.
   - Type: **g6.xlarge** (1× L4 24 GB, 4 vCPU, 16 GB RAM, ~$0.80/hr). Use g6.2xlarge (8 vCPU) if the client or tool simulation becomes CPU-bound.
   - Storage: 80 GB gp3. This costs about $6.40/month even while the instance is stopped.
   - Security group: SSH (22) from **My IP** only.
4. Connect and set up:
   ```bash
   ssh ubuntu@<public-ip>
   git clone <your private repo> && cd <repo> && bash setup/setup_node.sh
   ```
5. To use the server from your laptop: `ssh -L 8080:127.0.0.1:8080 ubuntu@<ip>`.
6. **Stop the instance when you're done.** Optional: set a CloudWatch alarm or a scheduled stop.

Cost guide: one 4-hour sweep on g6.xlarge is about $3.20. Keep sessions under ~20 hours/day to stay below the daily cap. Use `nohup`/`tmux` for long runs so an SSH drop doesn't kill them.

Measure the baseline on **one** platform (AWS L4). Use DataHub only for development, so the numbers stay comparable.
