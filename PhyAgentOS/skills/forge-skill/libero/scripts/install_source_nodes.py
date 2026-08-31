#!/usr/bin/env python3
"""Install reproducible environment-driven source launchers for local development."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceNode:
    node_id: str
    artifact_id: str
    version: str
    entrypoint: str
    expected_digest: str
    script: str


NODES = (
    SourceNode(
        node_id="gateway",
        artifact_id="gateway-1.1.0-source-session-v1",
        version="1.1.0",
        entrypoint="gateway",
        expected_digest="91c7cc832b57255b273208117429b4febe1ba4fd0e7224e7879d94aca736d17e",
        script='''#!/usr/bin/env sh
set -eu
: "${FORGE_GATEWAY_ROOT:?set FORGE_GATEWAY_ROOT to the forge_gateway checkout}"
: "${FORGE_GATEWAY_PYTHON:?set FORGE_GATEWAY_PYTHON to its Python interpreter}"
export PYTHONPATH="${FORGE_GATEWAY_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
exec "${FORGE_GATEWAY_PYTHON}" -m forge_gateway "$@"
''',
    ),
    SourceNode(
        node_id="libero_benchmark",
        artifact_id="libero-benchmark-1.0.0-source-session-v1",
        version="1.0.0",
        entrypoint="libero_benchmark",
        expected_digest="451f6e42d63ea1f4b4259b7fa8a89bc3b8ac95f44b43f26c03ec4192d6544779",
        script='''#!/usr/bin/env sh
set -eu
: "${LIBERO_BENCHMARK_ROOT:?set LIBERO_BENCHMARK_ROOT to the benchmark checkout}"
: "${LIBERO_BENCHMARK_PYTHON:?set LIBERO_BENCHMARK_PYTHON to the LIBERO Python interpreter}"
export PYTHONPATH="${LIBERO_BENCHMARK_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
exec "${LIBERO_BENCHMARK_PYTHON}" -u "${LIBERO_BENCHMARK_ROOT}/main.py" "$@"
''',
    ),
    SourceNode(
        node_id="lerobot_runner",
        artifact_id="lerobot-runner-1.0.2-source-session-v1",
        version="1.0.2-session.1",
        entrypoint="lerobot_runner",
        expected_digest="7d1f42d56e428a239c3d045a99a56468d2d656bcc9736e76005d79362d0d418a",
        script='''#!/usr/bin/env sh
set -eu
: "${LEROBOT_RUNNER_PYTHON:?set LEROBOT_RUNNER_PYTHON to an environment with lerobot-inference installed}"
exec "${LEROBOT_RUNNER_PYTHON}" -m lerobot_inference "$@"
''',
    ),
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_value(node: SourceNode, entrypoint: Path) -> dict:
    value = {
        "manifest_version": 1,
        "node_id": node.node_id,
        "artifact_id": node.artifact_id,
        "version": node.version,
        "platform": "linux",
        "arch": "x86_64",
        "entrypoints": {node.entrypoint: node.entrypoint},
        "files": [
            {
                "path": node.entrypoint,
                "sha256": file_sha256(entrypoint),
                "size": entrypoint.stat().st_size,
            }
        ],
    }
    canonical = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    value["digest"] = hashlib.sha256(canonical).hexdigest()
    return value


def install(runtime_root: Path, node: SourceNode) -> None:
    target = runtime_root / "nodes" / node.node_id / "versions" / node.artifact_id
    manifest_path = target / "node-manifest.json"
    if target.exists():
        if not manifest_path.is_file():
            raise RuntimeError(f"refusing to replace incomplete artifact: {target}")
        current = json.loads(manifest_path.read_text(encoding="utf-8"))
        if current.get("digest") != node.expected_digest:
            raise RuntimeError(f"existing artifact has a different digest: {target}")
        print(f"CACHE_HIT {node.node_id} {node.expected_digest}")
        return

    target.mkdir(parents=True)
    entrypoint = target / node.entrypoint
    entrypoint.write_text(node.script, encoding="utf-8", newline="\n")
    entrypoint.chmod(entrypoint.stat().st_mode | 0o111)
    value = manifest_value(node, entrypoint)
    if value["digest"] != node.expected_digest:
        raise RuntimeError(
            f"launcher digest drift for {node.node_id}: {value['digest']} != {node.expected_digest}"
        )
    manifest_path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"INSTALLED {node.node_id} {node.expected_digest}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=Path.home() / ".PhyAgentOS" / "forge_runtime",
    )
    args = parser.parse_args()
    if os.name != "posix":
        raise RuntimeError("source Node launchers require a POSIX host")
    root = args.runtime_root.expanduser().resolve()
    for node in NODES:
        install(root, node)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
