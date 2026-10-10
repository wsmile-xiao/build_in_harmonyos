#!/usr/bin/env python3
"""Consumer test for packaged filelock 3.32.7 — real API (R34).

Lock acquisition/release/re-entrancy/timeout semantics against the packaged
module on the OHOS device filesystem (temp dir, not a network resource).
"""
import os
import sys
import tempfile

site = sys.argv[1]
if site not in sys.path:
    sys.path.insert(0, site)

import filelock  # noqa: E402


def main():
    assert os.path.isdir(site), f"site-packages missing: {site}"
    assert filelock.__version__ == "3.32.7", filelock.__version__

    tmpdir = tempfile.mkdtemp(prefix="filelock_tp_")
    lock_path = os.path.join(tmpdir, "test.lock")

    # 1. acquire / release roundtrip
    lock = filelock.FileLock(lock_path)
    with lock.acquire(timeout=5):
        assert lock.is_locked
    assert not lock.is_locked

    # 2. re-entrant (same instance) acquire on the same file
    with lock:
        assert lock.is_locked
    assert not lock.is_locked

    # 3. second independent lock on the same file must time out
    other = filelock.FileLock(lock_path)
    with lock:
        try:
            other.acquire(timeout=1)
            raise AssertionError("second lock unexpectedly acquired")
        except filelock.Timeout:
            pass
    assert not lock.is_locked

    # 4. after release the other lock can acquire
    with other.acquire(timeout=5):
        assert other.is_locked
    assert not other.is_locked

    print("test_filelock: OK (version, acquire/release, re-entrancy, "
          "timeout, post-release acquire)")


if __name__ == "__main__":
    main()
