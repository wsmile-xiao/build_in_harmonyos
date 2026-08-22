#!/usr/bin/env python3
"""mock consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually call the tested API — mock.patch + Mock.assert_called
(pure user-space).

Usage: test_mock.py <site-packages>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "mock")):
        raise AssertionError(f"mock package missing in {site}")
    sys.path.insert(0, site)
    # R34: 真实调用被测库 API
    import mock

    m = mock.Mock()
    m.some_method(1, 2)
    m.some_method.assert_called_once_with(1, 2)
    with mock.patch("os.getcwd", return_value="/mock"):
        if os.getcwd() != "/mock":
            raise AssertionError("mock.patch did not apply")
    print(f"OK: mock 5.2.0 (Mock.assert_called + patch ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
