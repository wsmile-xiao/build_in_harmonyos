"""Real signed native font API access through an HMDFS UTF-8 path."""
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile


def check(probe, configuration, build_root):
    original = pathlib.Path(configuration)
    assert original.is_file() and not original.is_symlink()
    raw = original.read_bytes()
    with tempfile.TemporaryDirectory(prefix="字体配置-", dir=build_root) as temporary:
        root = pathlib.Path(temporary)
        process_uid = os.getuid()
        storage_uid = root.stat().st_uid
        assert storage_uid != process_uid, "HMDFS_PROJECTED_OWNERSHIP_NOT_OBSERVED"
        copied = root / "fonts.conf"
        with open(copied, "xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        assert copied.stat().st_uid == storage_uid
        assert hashlib.sha256(copied.read_bytes()).digest() == hashlib.sha256(raw).digest()
        shutil.copytree(original.parent / "conf.d", root / "conf.d")
        env = os.environ.copy()
        env.update(FONTCONFIG_FILE=str(copied), FONTCONFIG_PATH=str(original.parent))
        result = subprocess.run([probe, str(copied), "match"], env=env,
                                capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr
        for marker in ("CONFIG_LOAD PASS", "FONT_ENUMERATION PASS",
                       "FONT_MATCH PASS file=/system/fonts/"):
            assert marker in result.stdout, (marker, result.stdout)
        print("HARMONY_TEST_PASS=1/1", flush=True)
        print("HARMONY_TEST_COUNT=1; 1/1 PASS", flush=True)


if __name__ == "__main__":
    assert len(sys.argv) == 4
    check(*sys.argv[1:])
