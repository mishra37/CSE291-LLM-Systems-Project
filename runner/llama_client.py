"""Minimal async client for llama-server's native /completion endpoint (streaming)."""
import asyncio
import json
import time

import aiohttp


def chatml(system, messages):
    """Qwen2.5 chat template. messages: list of (role, content). Ends with an open assistant turn."""
    parts = [f"<|im_start|>system\n{system}<|im_end|>\n"]
    parts += [f"<|im_start|>{role}\n{content}<|im_end|>\n" for role, content in messages]
    parts.append("<|im_start|>assistant\n")
    return "".join(parts)


class LlamaClient:
    def __init__(self, base_url, timeout_s=300):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout_s)
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout, connector=aiohttp.TCPConnector(limit=0))
        return self

    async def __aexit__(self, *exc):
        await self.session.close()

    async def props(self):
        async with self.session.get(f"{self.base_url}/props") as r:
            return await r.json()

    async def metrics(self):
        """Prometheus /metrics as {name: value} (llamacpp: prefix stripped)."""
        async with self.session.get(f"{self.base_url}/metrics") as r:
            body = await r.text()
        out = {}
        for line in body.splitlines():
            if line.startswith("llamacpp:"):
                name, _, value = line.partition(" ")
                out[name[len("llamacpp:"):]] = float(value)
        return out

    async def complete(self, prompt, max_tokens, slot=-1, clock=time.monotonic):
        """Stream one completion. Output length is fixed (ignore_eos) so runs are comparable.

        Returns {status, error, text, t_first_token, t_done, final}; `final` is llama.cpp's last
        stream message (timings, id_slot, truncated, ...). status is ok | http_<code> | error |
        timeout | conn_error.
        """
        payload = {"prompt": prompt, "n_predict": max_tokens, "ignore_eos": True,
                   "cache_prompt": True, "temperature": 0.0, "stream": True, "id_slot": slot}
        out = {"status": "ok", "error": "", "text": "", "t_first_token": None, "final": {}}
        pieces, buf = [], b""
        try:
            async with self.session.post(f"{self.base_url}/completion", json=payload) as r:
                if r.status != 200:
                    out.update(status=f"http_{r.status}", error=(await r.text())[:300])
                else:
                    # manual line splitting: the final message can exceed aiohttp's readline limit
                    async for chunk in r.content.iter_any():
                        buf += chunk
                        *lines, buf = buf.split(b"\n")
                        for line in lines:
                            if not line.startswith(b"data:"):
                                continue
                            data = line[5:].strip()
                            if data == b"[DONE]":
                                continue
                            msg = json.loads(data)
                            if "error" in msg:
                                out.update(status="error", error=str(msg["error"])[:300])
                            if msg.get("content"):
                                if out["t_first_token"] is None:
                                    out["t_first_token"] = clock()
                                pieces.append(msg["content"])
                            if msg.get("stop"):
                                out["final"] = msg
        except asyncio.TimeoutError:
            out.update(status="timeout")
        except aiohttp.ClientError as e:
            out.update(status="conn_error", error=str(e)[:300])
        except Exception as e:  # never let one bad response kill a scheduler worker
            out.update(status="error", error=f"{type(e).__name__}: {e}"[:300])
        out["text"] = "".join(pieces)
        out["t_done"] = clock()
        return out
