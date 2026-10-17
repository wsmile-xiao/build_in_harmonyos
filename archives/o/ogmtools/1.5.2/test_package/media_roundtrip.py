"""Real PCM -> OGM -> PCM flow through the installed ogmtools package."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import uuid
import wave

TOOLS = ("ogmmerge", "ogmdemux", "ogminfo", "ogmsplit", "ogmcat", "dvdxchap")


def command(bindir, tool, args, root):
    binary = (bindir / tool).resolve(strict=True)
    if binary.parent != bindir.resolve(strict=True):
        raise RuntimeError("tested executable escaped its package bin directory")
    result = subprocess.run([str(binary), *map(str, args)], cwd=root,
                            capture_output=True, timeout=60)
    sys.stdout.buffer.write(result.stdout)
    sys.stderr.buffer.write(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"{tool} returned {result.returncode}")
    return result


def roundtrip(bindir, root, prefix, seed):
    # Two full seconds avoid upstream progress's integer zero-duration case.
    pcm = b"".join(struct.pack("<h", ((i * seed) % 65536) - 32768)
                   for i in range(16000))
    source = root / (prefix + "-input.wav")
    ogm = root / (prefix + "-container.ogm")
    output = prefix + "-output"
    with wave.open(str(source), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(8000)
        stream.writeframes(pcm)
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    command(bindir, "ogmmerge", ["-o", ogm, source], root)
    if ogm.read_bytes()[:4] != b"OggS":
        raise RuntimeError("ogmmerge did not produce an Ogg container")
    command(bindir, "ogminfo", [ogm], root)
    command(bindir, "ogmdemux", ["-o", output, ogm], root)
    decoded = root / (output + "-a1.wav")
    with wave.open(str(decoded), "rb") as stream:
        observed = (stream.getnchannels(), stream.getsampwidth(), stream.getframerate(),
                    stream.getnframes(), stream.getcomptype())
        recovered = stream.readframes(stream.getnframes())
    if observed != (1, 2, 8000, 16000, "NONE") or recovered != pcm:
        raise RuntimeError(f"PCM roundtrip differs: {observed}; {len(recovered)}/{len(pcm)} bytes")
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_sha:
        raise RuntimeError("consumer changed its source fixture")
    return {"pcm_bytes": len(pcm), "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
            "source_uid": source.stat().st_uid, "parent_uid": root.stat().st_uid,
            "process_uid": os.getuid(), "container_bytes": ogm.stat().st_size,
            "tool_sha256": {tool: hashlib.sha256((bindir / tool).read_bytes()).hexdigest()
                            for tool in ("ogmmerge", "ogminfo", "ogmdemux")}}


def main():
    mode, bindir_text, parent_text = sys.argv[1:]
    if mode not in ("consumer", "harmony"):
        raise RuntimeError("unknown test mode")
    bindir = Path(bindir_text).resolve(strict=True)
    parent = Path(parent_text).resolve(strict=True)
    if mode == "harmony":
        if os.uname().sysname != "HarmonyOS" or os.uname().machine != "aarch64":
            raise RuntimeError("HarmonyOS PC target identity required")
        if not parent.is_relative_to(Path("/storage/Users/currentUser")):
            raise RuntimeError("HMDFS task-private build folder required")
    root = parent / ("ogmtools-" + mode + "-" + uuid.uuid4().hex)
    os.mkdir(root, 0o775)
    try:
        if mode == "consumer":
            for tool in TOOLS:
                result = command(bindir, tool, ["--version"], root)
                if b"1.5" not in result.stdout + result.stderr:
                    raise RuntimeError("unexpected upstream version for " + tool)
            detail = roundtrip(bindir, root, "ascii", 29)
        else:
            detail = roundtrip(bindir, root, "鸿蒙文件投影 空格", 47)
            if detail["source_uid"] != detail["parent_uid"]:
                raise RuntimeError("fixture owner differs from the observed HMDFS parent")
            detail["platform"] = list(os.uname())
            detail["ownership_projected"] = detail["source_uid"] != detail["process_uid"]
            if not detail["ownership_projected"]:
                raise RuntimeError("fixture did not exercise HMDFS ownership projection")
        print("OGMTOOLS_TEST_DETAIL=" + json.dumps(detail, sort_keys=True), flush=True)
    finally:
        if root.is_symlink() or root.resolve().parent != parent:
            raise RuntimeError("cleanup root identity drift")
        shutil.rmtree(root)
    if root.exists():
        raise RuntimeError("test-private root was not cleaned")
    print("CONSUMER_TEST_PASS=7/7" if mode == "consumer" else "HARMONY_TEST_PASS=1/1", flush=True)


if __name__ == "__main__":
    main()
