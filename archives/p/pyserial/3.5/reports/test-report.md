# pyserial 3.5 test report

- Upstream command: `python3 test/run_all_tests.py`
- Result: 61 tests collected; 53 passed, 5 skipped, 3 failed (53 + 5 + 3 = 61).
- Failures: `test_pty.py` two PTY tests and one PTY-related test failed because TIOCMBIS returned PermissionError 13 on the current device.
- Consumer command: `python3 test_package/test_pyserial_consumer.py <package-folder>`
- Consumer result: 1/1 passed.
