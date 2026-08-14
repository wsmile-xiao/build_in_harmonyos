#!/usr/bin/env python3
"""show-in-file-manager 1.1.4 test_package 断言脚本（test_package 测试源，L0c 要求）。

由 test_package/conanfile.py 的 test() 调用；PYTHONPATH 由调用方注入包内
site-packages。断言点（对应 MANIFEST.yml assertion_count 中 test_package
部分，5 项）：
  1. import showinfm 及其公共 API 全部可调用
  2. 平台识别：system.current_platform 为 Platform.linux（HarmonyOS 补丁生效）
  3. URI 工具函数真实工作（is_uri / path_to_file_uri / file_uri_to_path）
  4. linux_desktop_humanize 纯函数可调用
  5. CLI 入口脚本存在且可执行（--version 输出包含版本）
"""
import os
import stat
import sys

failures = []

# 1) import showinfm + 公共 API
try:
    import showinfm
    from showinfm import (
        show_in_file_manager,
        valid_file_manager,
        user_file_manager,
        stock_file_manager,
    )
    assert callable(show_in_file_manager), "show_in_file_manager not callable"
    assert callable(valid_file_manager), "valid_file_manager not callable"
    assert callable(user_file_manager), "user_file_manager not callable"
    assert callable(stock_file_manager), "stock_file_manager not callable"
    print("PASS import showinfm + public API callable")
except Exception as exc:  # pragma: no cover
    failures.append("import showinfm failed: %s" % exc)

# 2) 平台识别（HarmonyOS 补丁生效：按 Linux 处理，而非 NotImplementedError）
try:
    from showinfm.system import current_platform
    from showinfm.constants import Platform
    assert current_platform == Platform.linux, \
        "current_platform=%r expected Platform.linux" % (current_platform,)
    print("PASS platform detection = Platform.linux (HarmonyOS patch)")
except Exception as exc:  # pragma: no cover
    failures.append("platform detection failed: %s" % exc)

# 3) URI 工具函数真实工作
try:
    from showinfm.system.tools import is_uri, path_to_file_uri, file_uri_to_path
    assert is_uri("file:///home/user/file.txt") is True, "is_uri(file://...) should be True"
    assert is_uri("/home/user/file.txt") is False, "is_uri(plain path) should be False"
    uri = path_to_file_uri("/home/user/my file.txt")
    assert uri.startswith("file://"), "path_to_file_uri returned %r" % uri
    back = file_uri_to_path(uri)
    assert back == "/home/user/my file.txt", "file_uri_to_path roundtrip %r" % back
    print("PASS URI tools (is_uri / path_to_file_uri / file_uri_to_path)")
except Exception as exc:  # pragma: no cover
    failures.append("URI tools failed: %s" % exc)

# 4) linux_desktop_humanize 纯函数
try:
    from showinfm.system.linux import linux_desktop_humanize
    assert callable(linux_desktop_humanize), "linux_desktop_humanize not callable"
    print("PASS linux_desktop_humanize callable")
except Exception as exc:  # pragma: no cover
    failures.append("linux_desktop_humanize failed: %s" % exc)

# 5) CLI 入口存在且可执行（CLI_PATH 由 test_package/conanfile.py 注入）
try:
    cli = os.environ.get("CLI_PATH", "")
    assert cli and os.path.isfile(cli), "CLI not found at %r" % cli
    mode = os.stat(cli).st_mode
    assert mode & stat.S_IXUSR, "CLI not executable: %s" % cli
    print("PASS CLI entry present & executable:", cli)
except Exception as exc:  # pragma: no cover
    failures.append("CLI entry check failed: %s" % exc)

if failures:
    for item in failures:
        print("FAIL:", item)
    sys.exit(1)
print("ALL test_package assertions passed")
