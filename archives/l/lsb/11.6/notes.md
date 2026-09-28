# lsb 11.6 适配笔记

## 编译环境

- 构建系统: custom（Python 3 与 POSIX shell 工具）
- 适配日期: 2026-09-24
- 平台: OpenHarmony / aarch64
- 上游源码: Debian `lsb 11.6` 源码包

## 上游测试

- `test/test_lsb_release.py` 包含 11 个有效 unittest 用例。
- `test/test_initdutils.py` 包含 7 个上游显式 skip 的测试占位。
- `test/lsb-test.sh` 是 init-functions 的上游 shell 冒烟测试。
- recipe 在 `build()` 中完整执行上述测试，并使用上游提供的 `test/apt-cache` 与 `test/dpkg-query` 替身程序。

## 消费者测试

- `conan test` 从安装后的 `bin/` 执行 `lsb_release -h`、`lsb_release -i -s`。
- 校验 Python 模块 `lsb_release`、`initdutils` 可从安装目录导入。
- source 安装后的 `lib/lsb/init-functions` 并调用日志函数。
- 校验 `install_initd` 无参数时按上游约定返回用法错误。

## 源码修改

### `0001-ohos-lsb-release-portability.patch`

- 修改文件: `lsb_release.py`
- 改动一（发行版数据回退）：上游默认只读取 `/usr/share/distro-info/*.csv`；OpenHarmony 标准镜像通常不提供该 Debian 数据包，导致模块导入阶段直接失败。补丁保持系统路径优先，同时支持 `LSB_DISTRO_INFO` 和包内 `share/lsb/distro-info/debian.csv` 回退。数据来源为 Debian `distro-info-data` 的 `usr/share/distro-info/debian.csv`，随包安装。
- 改动二（命令解析）：鸿蒙 Python 3.12.9 的子进程走 `posix_spawn`，不做 `PATH` 查找，`subprocess.run(["apt-cache", ...])` 会直接抛 `ENOENT`。补丁新增 `_resolve_command()`，先用 `shutil.which` 把命令解析成绝对路径再执行，解析失败时保留原有容错路径。
- 该补丁未修改任何上游测试文件，也不改变 `lsb_release` 的输出契约。

## 注意事项

- 打包阶段会把 `bin/` 下四个上游命令的 `#!/usr/bin/python3` 首行改写为 `#!/usr/bin/env python3`，因为鸿蒙镜像没有 `/usr/bin/python3`；只改首行，命令正文保持上游原样。
- `install_initd`、`remove_initd` 的系统级写操作仍遵循上游路径，需要使用方具备相应权限。
- 本包不启用 Debian 的 systemd 或 init 服务，只提供 LSB 命令和 shell helper。
