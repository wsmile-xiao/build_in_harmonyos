#!/usr/bin/env python3
"""Relink Apache Arrow upstream test artifacts for HarmonyOS.

Arrow's upstream CTest build tree may record relative NEEDED entries such as
../../release/libarrow_gtest.so.  On the current HarmonyOS device this can load
multiple copies of GTest/GMock from different relative directories and make
otherwise-passing tests exit with SIGTRAP.  This helper rebuilds selected test
executables and helper shared libraries into a single runtime directory so every
NEEDED entry uses the library basename.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
from pathlib import Path


SUPPORT_TARGETS = {
    "gtest": "libarrow_gtest.so",
    "gmock": "libarrow_gmock.so",
    "gmock_main": "libarrow_gmock_main.so",
    "arrow_shared": "libarrow.so",
    "arrow_testing_shared": "libarrow_testing.so",
    "arrow_compute_shared": "libarrow_compute.so",
    "arrow_acero_shared": "libarrow_acero.so",
    "arrow_dataset_shared": "libarrow_dataset.so",
    "parquet_shared": "libparquet.so",
    "arrow_orc_shared": "libarrow_orc.so",
    "arrow_flight_shared": "libarrow_flight.so",
    "arrow_flight_testing_shared": "libarrow_flight_testing.so",
}


def find_link_txt(build_dir: Path, target: str) -> Path | None:
    matches = sorted(build_dir.glob(f"**/CMakeFiles/{target}.dir/link.txt"))
    return matches[0] if matches else None


def transform_command(command: list[str], output: Path, run_dir: Path, known_libs: set[str], soname: str | None) -> list[str]:
    transformed: list[str] = []
    skip_next = False
    replaced_soname = False

    for index, part in enumerate(command):
        if skip_next:
            skip_next = False
            continue

        if part == "-o" and index + 1 < len(command):
            if soname and not replaced_soname:
                transformed.append(f"-Wl,-soname,{soname}")
                replaced_soname = True
            transformed.extend(["-o", str(output)])
            skip_next = True
            continue

        if soname and part.startswith("-Wl,-soname,"):
            if not replaced_soname:
                transformed.append(f"-Wl,-soname,{soname}")
                replaced_soname = True
            continue

        base_name = os.path.basename(part)
        if base_name in known_libs and (run_dir / base_name).exists():
            transformed.append(str(run_dir / base_name))
        else:
            transformed.append(part)

    return transformed


def relink_target(build_dir: Path, run_dir: Path, target: str, output_name: str, known_libs: set[str], optional: bool) -> bool:
    link_txt = find_link_txt(build_dir, target)
    if link_txt is None:
        if optional:
            return False
        raise FileNotFoundError(f"missing CMake link.txt for target: {target}")

    raw_command = link_txt.read_text(encoding="utf-8").strip()
    command = shlex.split(raw_command)
    output = run_dir / output_name
    soname = output_name if output_name.endswith(".so") else None
    transformed = transform_command(command, output, run_dir, known_libs, soname)

    print(f"[relink] {target} -> {output}")
    subprocess.run(transformed, cwd=link_txt.parent.parent.parent, check=True, timeout=900)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", required=True, help="Arrow CMake build directory")
    parser.add_argument("--run-dir", required=True, help="Directory for relinked artifacts")
    parser.add_argument("--target", action="append", default=[], help="CTest executable target to relink; may be repeated")
    parser.add_argument(
        "--support-target",
        action="append",
        default=[],
        help="Extra support shared-library target in target=output.so form",
    )
    parser.add_argument("--skip-default-support", action="store_true", help="Do not relink built-in Arrow support libs")
    args = parser.parse_args()

    build_dir = Path(args.build_dir).resolve()
    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    support_targets = dict(SUPPORT_TARGETS)
    for value in args.support_target:
        if "=" not in value:
            raise ValueError(f"--support-target must use target=output.so: {value}")
        target, output_name = value.split("=", 1)
        support_targets[target] = output_name

    known_libs = set(support_targets.values())
    known_libs.update(["libarrow.so", "libarrow_compute.so", "libarrow_testing.so"])

    if not args.skip_default_support:
        for target, output_name in support_targets.items():
            relink_target(build_dir, run_dir, target, output_name, known_libs, optional=True)

    for target in args.target:
        relink_target(build_dir, run_dir, target, target, known_libs, optional=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
