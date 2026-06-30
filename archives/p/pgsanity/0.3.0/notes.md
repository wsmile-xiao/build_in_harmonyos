# pgsanity 0.3.0 适配笔记

## 编译环境
- 构建系统: python (pip wheel install)
- 编译日期: 2026-06-12
- 编译器: none (pure Python)
- 状态: published

## 编译步骤

1. Downloaded pgsanity-0.3.0-py3-none-any.whl from PyPI
2. Installed to staging directory using pip --target:
   `pip install pgsanity-0.3.0-py3-none-any.whl --target=$TEST_PREFIX/$DEFAULT_PREFIX/lib/python3.12/site-packages --no-deps`
3. Manually created entry point script bin/pgsanity with shebang `/usr/bin/env python3`
4. Removed __pycache__ from staging directory
5. Installed to local prefix for verification:
   `pip install pgsanity-0.3.0-py3-none-any.whl --target=$DEFAULT_PREFIX/lib/python3.12/site-packages --no-deps`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pip install from source (pyproject.toml) failed | uv_build build backend requires maturin/Rust which has SSL issues on HarmonyOS | Used pre-built wheel (pgsanity-0.3.0-py3-none-any.whl) directly |
| 2 | Entry point script shebang `/data/service/hnp/python.org/python_3.12/bin/python3.12` fails on HarmonyOS | Direct ELF binary can't load shared libs (libpython3.12.so.1.0, libintl.so.8) | Changed shebang to `/usr/bin/env python3` which uses the working bash wrapper script |
| 3 | pip --target doesn't create console_scripts in bin/ | pip --target mode skips creating entry point scripts | Manually created bin/pgsanity script with correct shebang |
| 4 | pip config has target=/storage/Users/currentUser/.opendesk/interpreters/pip-global which is not in sys.path | pip-global directory not in Python sys.path | Used --target option to install to correct site-packages directory |

## 源码修改

No source code patches needed. pgsanity is a pure Python package - the only modification is the entry point script shebang, which is a pip-generated file (not source code). The shebang is changed from `/data/service/hnp/python.org/python_3.12/bin/python3.12` to `/usr/bin/env python3` during packaging.

## 依赖版本

- python/3.12.8 (system Python, provided by HarmonyOS)

## 验证结果

```bash
$ pgsanity --help
usage: pgsanity [-h] [--add-semicolon] [files ...]

Check syntax of SQL for PostgreSQL

$ python3 -m pgsanity.pgsanity --help
usage: pgsanity.py [-h] [--add-semicolon] [files ...]

# SQL syntax check test:
$ pgsanity test_sql.sql
# (valid SQL passes, invalid SQL reports errors)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pgsanity-0.3.0-ohos-aarch64.tar.gz | ~10KB | Release package (bin + lib) |
| pgsanity-0.3.0-ohos-aarch64-debug.tar.gz | 0KB | Debug symbols (no ELF binaries, empty) |

## 注意事项

- pgsanity is a pure Python package - no ELF binaries, no strip/sign/RPATH needed
- The entry point script must use `/usr/bin/env python3` shebang, not the direct python3.12 path
- Requires Python 3.9+ on target system
---

**编译结束**: 2026-06-12 18:29
**最终状态**: published
