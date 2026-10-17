# wsdd 0.8 适配笔记

## 编译环境
- 构建系统: custom（纯 Python，无 C/C++ 编译）
- 编译器: Python 3.12 syntax check
- 状态: built after OpenDesk verification

## 构建步骤

1. `conan source` 下载并校验 Debian 上游源码包。
2. `build()` 对 `src/wsdd.py` 执行 `python3 -m py_compile`。
3. `package()` 将 `wsdd.py` 安装为 `bin/wsdd`，设置可执行位。
4. `test_package` 以消费者身份运行 `wsdd --version` 和 `wsdd --help`。

## 上游测试说明

上游 `test/regressions/run-regressions.sh` 会发现 3 个 shell 回归入口。
`02_non_existing_interface/run.sh` 在设备 Python 3.12 上执行并验证 issue #201
回归；两个 Python 版本矩阵脚本要求 Python 3.7-3.11 和 netcat，本设备不提供
这些运行时，因此明确记录为环境跳过，不计入通过。`test/netlink_monitor.py`
和 `test/routesocket_monitor.py` 是环境探针，不是自动化测试入口。

真机探测确认 HarmonyOS Python 未导出 `AF_NETLINK`，手工传入 Linux
常量后 `bind()` 仍返回 `bad family`。因此补丁使用 libc `getifaddrs()`
轮询地址变化，并将 IPv4/IPv6 组播设置视为 Linux 兼容路径，避免启动时
抛出 `NotImplementedError: unsupported OS: HarmonyOS`。

## 验证结果

由 OpenDesk 设备运行 `ci/conan/build_and_test.sh archives/w/wsdd/0.8`，
结果记录在本 PR 的 CI 日志中。
