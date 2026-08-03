# Adaptation Notes — dovi_convert 8.2.0.1

## Software
- **Name**: dovi_convert
- **Version**: 8.2.0.1 (upstream tag v8.2.0)
- **Description**: Dolby Vision Profile 7 -> 8.1 converter (single-file Python CLI)
- **License**: GPL-3.0-or-later
- **Source**: https://github.com/cryptochrome/dovi_convert/archive/refs/tags/v8.2.0.tar.gz
- **SHA256** (tarball): bf6d9a634d66415b96faa4ee90c0e60149b91b5ab0c53dfb4111cdb2f593ed40
- **Upstream repo**: https://github.com/cryptochrome/dovi_convert

## Build System
- **Type**: None (single-file Python script, no build system)
- **conanfile.py build()**: no-op除了确保可执行位
- **package()**: copy dovi_convert.py -> bin/dovi_convert, chmod +x, copy LICENSE

## Dependencies
- **构建依赖**: 无（纯 Python 单文件脚本）
- **运行时依赖**（通过 subprocess 调用，非 Conan 依赖）:
  - python3 (>= 3.8)
  - ffmpeg
  - dovi_tool (https://github.com/quietvoid/dovi_tool)
  - mkvtoolnix (mkvmerge, mkvextract)
  - mediainfo
- **测试依赖**: bash（运行 test_package 烟雾测试）

## Issues Encountered
1. **上游无测试套件**: 审计 v8.2.0 tag 源码，仓库根只有 dovi_convert.py 等文件，无 test/、tests/、spec/ 目录，无 pytest/unittest/cram 配置，.github/workflows/ 只有 docker-publish.yml（构建 Docker 镜像，非测试）。确认上游测试用例数为 0。
2. **shebang**: 脚本使用 `#!/usr/bin/env python3`，OHOS 上 python3 在 PATH 中可用，无需 patch。
3. **无 --version**: dovi_convert 没有 `--version` 标志，但有 `help` 子命令（输出用法）和无参调用（输出 usage）。test_package 使用 `help` 子命令做烟雾测试，该路径不调用外部媒体工具，也不执行 update-check，安全可测。
4. **可执行位**: tarball 中的 dovi_convert.py 可能没有可执行位，conanfile.py build() 中显式 `os.chmod` 添加 S_IXUSR|S_IXGRP|S_IXOTH。package() 中 shutil.move 后再次确保可执行位。
5. **文件重命名**: 上游脚本名是 `dovi_convert.py`，但安装后命令名应为 `dovi_convert`（无 .py 后缀，与上游 README 安装说明一致：`sudo mv dovi_convert.py /usr/local/bin/dovi_convert`）。package() 中 rename 实现。

## Test
- **上游测试**: 0 个。审计 v8.2.0 tag 源码确认无测试套件。
- **test_package**: bash 烟雾测试 (test_dovi_convert.sh)，4 个断言:
  - Test 1: `command -v dovi_convert` — 验证二进制在 PATH 中
  - Test 2: `dovi_convert help` — 验证 help 子命令输出包含工具名
  - Test 3: `dovi_convert` (无参) — 验证 usage 输出
  - Test 4: `dovi_convert cleanup` — 验证 cleanup 子命令可运行（无备份时为 no-op）

## Installed Files
- bin/dovi_convert — 主可执行脚本（从 dovi_convert.py 重命名）
- licenses/LICENSE — GPL-3.0 许可证

## Notes
- dovi_convert 是 CLI 应用程序 (application)，非库。package_info 中 libs=[]，bindirs=["bin"]。
- 运行时外部工具 (ffmpeg/dovi_tool/mkvtoolnix/mediainfo) 不是 Conan 依赖，由用户在目标系统单独安装。
- 上游 v8.2.0 changelog: 引入 Backup & Restore 功能 (backup/restore 子命令、--backup/--delete 标志)。
