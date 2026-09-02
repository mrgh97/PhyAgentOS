#!/usr/bin/env python3
"""Download or verify the two external LingBot-VA model repositories."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelSpec:
    repo_id: str
    revision: str
    directory: str
    required: tuple[str, ...]


POLICY = ModelSpec(
    repo_id="lerobot/lingbot_va_libero_long",
    revision="73e0be23b134a7c4dfc2d82f6ff27ba0bfdc0932",
    directory="lingbot_va_libero_long",
    required=("config.json", "model.safetensors"),
)
BASE = ModelSpec(
    repo_id="robbyant/lingbot-va-base",
    revision="68b7bc1b35da6ddc67ea94c4ceb58d768fbb3f9c",
    directory="lingbot_va_base_frozen",
    required=("vae/config.json", "text_encoder/config.json", "tokenizer/tokenizer.json"),
)


def verify(path: Path, spec: ModelSpec) -> Path:
    missing = [relative for relative in spec.required if not (path / relative).is_file()]
    if missing:
        raise RuntimeError(
            f"{spec.repo_id} is incomplete at {path}: missing {', '.join(missing)}"
        )
    return path.resolve()


def resolve(
    root: Path,
    spec: ModelSpec,
    *,
    local_files_only: bool,
    verify_only: bool,
) -> Path:
    destination = root / spec.directory
    try:
        # A complete inference payload is already a cache hit. Do not ask the Hub
        # for unrelated README/demo assets or re-copy multi-GB weight files.
        return verify(destination, spec)
    except RuntimeError:
        if verify_only:
            raise
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise RuntimeError("install huggingface-hub before downloading models") from exc
    snapshot_download(
        repo_id=spec.repo_id,
        revision=spec.revision,
        local_dir=destination,
        local_files_only=local_files_only,
    )
    return verify(destination, spec)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--model-root",
        type=Path,
        default=Path.home() / ".cache" / "phyagentos" / "models" / "lingbot-va",
    )
    result.add_argument(
        "--local-files-only",
        action="store_true",
        help="disable network and require a complete Hugging Face cache/local directory",
    )
    result.add_argument(
        "--verify-only",
        action="store_true",
        help="verify the two local directories without calling Hugging Face",
    )
    return result


def main() -> int:
    args = parser().parse_args()
    root = args.model_root.expanduser().resolve()
    policy = resolve(
        root,
        POLICY,
        local_files_only=args.local_files_only,
        verify_only=args.verify_only,
    )
    base = resolve(
        root,
        BASE,
        local_files_only=args.local_files_only,
        verify_only=args.verify_only,
    )
    print(f"LINGBOT_VA_MODEL_DIR={policy}")
    print(f"LINGBOT_VA_BASE_DIR={base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
