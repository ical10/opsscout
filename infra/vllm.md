# vLLM on AMD MI300X — provisioning runbook

> Slice 0.5 deliverable. Run these steps once before any cs worker that needs `AMD_VLLM_BASE_URL` reachable.

## 1. Provision the MI300X instance

1. Log in to the AMD Developer Cloud → request a single MI300X instance (the 192GB-VRAM SKU is fine; we don't need the 8-GPU node for a 30B-A3B model).
2. SSH in.
3. Confirm the GPU is visible:

```bash
rocm-smi
# Expect: 1× MI300X, ~192 GB HBM, idle utilisation
```

4. Note the public hostname / IP — fill it in here once chosen:

```
AMD instance hostname: <FILL ME IN>
```

## 2. Install + serve Qwen3-30B-A3B

ROCm-flavoured vLLM is preinstalled in the standard MI300X image. If not, install in a fresh venv:

```bash
python3 -m venv ~/vllm-venv && source ~/vllm-venv/bin/activate
pip install --upgrade pip
pip install vllm
```

Serve the model exactly per spec §4 — DO NOT alter the flags:

```bash
vllm serve Qwen/Qwen3-30B-A3B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --max-model-len 32768
```

Initial weight download takes ~10–15 minutes. Successful start prints `Application startup complete` and an OpenAI-compatible router on port 8000.

## 3. Verify the endpoint

From the AMD instance shell:

```bash
curl -s http://localhost:8000/v1/models | jq
# Expect: {"object":"list","data":[{"id":"Qwen/Qwen3-30B-A3B-Instruct", ... }]}
```

## 4. Expose the endpoint to your laptop

Pick whichever access pattern fits your AMD account; document the chosen one here:

- **SSH port-forward (simplest)**: from your laptop, run
  ```bash
  ssh -N -L 8000:localhost:8000 <user>@<amd-host>
  ```
  Local URL becomes `http://localhost:8000/v1`.
- **Public IP + firewall rule**: AMD console → security group → allow TCP 8000 from your laptop's IP. URL becomes `http://<amd-host>:8000/v1`.
- **Reverse proxy (HTTPS)**: nginx/Caddy in front of port 8000 with a real cert. URL becomes `https://<your-domain>/v1`.

## 5. Configure your local `.env`

Edit `/Users/rizal/GDrive/opsscout/.env` and set:

```bash
AMD_VLLM_BASE_URL=http://localhost:8000/v1   # or whatever URL you chose above
```

`.env` is gitignored — don't commit the URL.

## 6. Smoke test from your laptop

Save the snippet below as `infra/smoke_test.py` (the path is gitignored — it never ends up in a commit). Then run:

```bash
AMD_VLLM_BASE_URL=http://localhost:8000/v1 \
  .venv/bin/python infra/smoke_test.py
```

Expected output: a parsed `DemandForecast` printed as JSON, with `demand_multiplier` ∈ [0, 5] and a non-empty `reasoning` string.

```python
# infra/smoke_test.py — gitignored. One-off vLLM endpoint check.
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from openai import OpenAI

from models import DemandForecast


SAMPLE = """
Saturday's coastal weather is heavy rain (52mm, 45kph wind), unsafe for surf
and rafting. Highland forecast is partly cloudy 18°C — fine for trekking.
Bali International Surf Championships brings ~4,200 stuck tourists. Airbnb:
5/32 listings available, avg $285 vs baseline $145 — very_high pressure.
Estimated demand_multiplier ~1.8 above_normal, confidence 0.88.
"""


def main() -> None:
    base_url = os.environ["AMD_VLLM_BASE_URL"]
    print(f"→ {base_url}")
    client = OpenAI(base_url=base_url, api_key="not-needed")

    models = [m.id for m in client.models.list().data]
    print(f"   models: {models}")
    qwen = next(m for m in models if "Qwen3-30B" in m)

    completion = client.beta.chat.completions.parse(
        model=qwen,
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract the data into the JSON schema. Use null when "
                    "unknown. Do not invent fields."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Business: nusa_adventures. Date: 2026-05-10.\n\n"
                    f"Forecaster analysis:\n{SAMPLE}"
                ),
            },
        ],
        response_format=DemandForecast,
        temperature=0.0,
        max_tokens=2048,
    )

    parsed = completion.choices[0].message.parsed
    assert parsed is not None, "parse returned None"
    print(parsed.model_dump_json(indent=2))

    assert 0.0 <= parsed.demand_multiplier <= 5.0
    assert 0.0 <= parsed.confidence <= 1.0
    assert parsed.reasoning.strip() != ""
    assert parsed.demand_trend in {
        "spike", "above_normal", "normal", "below_normal", "drop"
    }

    print("\n✅ vLLM smoke test PASSED")


if __name__ == "__main__":
    main()
```

If the smoke test passes, tag the repo state:

```bash
git tag v0-foundation
```

cs workers branch from this tag for parallel slice work.

## Troubleshooting

- **`vllm serve` OOM** — the MoE 30B-A3B model needs ~80 GB VRAM with 32k context. If you see OOM, drop `--max-model-len` to 16384.
- **`curl /v1/models` returns 404** — vLLM is still loading weights; wait for `Application startup complete`.
- **Smoke test returns empty `reasoning`** — increase `temperature` in `infra/smoke_test.py` from 0.0 to 0.3 only for the smoke.
- **SSH tunnel keeps dying** — add `ServerAliveInterval 60` to your `~/.ssh/config`.
