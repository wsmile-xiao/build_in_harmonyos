# usbmuxctl 0.1.4 适配笔记

## 编译环境
- 构建系统: none（纯 Python，无 C 编译）
- 编译日期: 2026-09-26
- 编译器: 不适用（Python）
- 状态: built

## 上游信息
- 仓库: https://github.com/linux-automation/usbmuxctl
- 源码: https://files.pythonhosted.org/packages/75/57/327df4cc8d267a348e1bcccf3f301c6db9f2c2ee2842dbf22035b515466b/usbmuxctl-0.1.4.tar.gz
- SHA256: f200647bd72ea5b5a77d6d9e1f0641e2aae1da37fc2317a2f73929b034388845
- 依赖: pyusb、termcolor（纯 Python，pip-vendored）+ libusb/1.0.27（conan 原生后端，shared=True，供 pyusb ctypes 加载；无此后端时 Mux.find_devices() 报 NoBackendError）

## 编译步骤

纯 Python 安装，不走 PEP 517 构建（避免 setuptools_scm git 元数据查找）：

1. `get()` 解包 sdist
2. `build()` 审计无测试（无 tests//test/、Makefile 仅 ruff/codespell QA），pip 安装 pyusb==1.3.1 + termcolor==2.1.1 到 build/deps 做 import 探针
3. `package()` 将 `usbmuxctl/` 树原样拷入 `lib/pythonX.Y/site-packages`，手写最小 dist-info，生成 `bin/usbmuxctl` 控制台脚本（`from usbmuxctl.__main__ import main`），vendored 闭包拷入 `deps/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pyusb/termcolor 无 ohpcd conan 包 | ohpcd termcolor/2.1.0 是 C++ header-only 库，与 Python termcolor 同名不同物 | requirements() 留空，运行时闭包从社区 PyPI 镜像 pip-vendored（labgrid 26.0 前例） |
| 2 | 上游无测试，HMBS 需要证据标记 | sdist 无任何测试入口 | build() 输出 `HMBS_UPSTREAM_TEST_RESULT status no_tests` 并持久化 `res/upstream_test_result.json`，test_package 每轮复发（abuild-sudo 前例） |
| 3 | CI build #62026：ctypes CDLL 加载 conan 缓存 libusb .so 报 Permission denied（CHECK 2/6 失败，4/6） | OHOS loader 拒绝从 /storage（HMDFS 用户数据挂载）dlopen；已合入 unicorn/2.1.4 明确记录同类限制（CI 系统 python 无法从 conan 缓存 ctypes 加载 .so）；缺 exec 位/签名亦可致 EACCES | test_usbmuxctl.py 新增 `_stage_libusb_so()`：copyfile 追踪实文件（E050，不用 symlink）到 TMPDIR（/data，HMBS 任务私有）私有目录，chmod 755，补 libusb-1.0.so/.so.0 实文件别名供 CHECK 6 子进程按 soname 解析，有 binary-sign-tool 时自签名（usbredir/0.15.0 前例，全程 guarded）；CHECK 2 优先探测 staged 路径、回退原路径，双路证据进 gaps；断言口径不变（仍要求 backend 非空），只规范文件位置/权限 |
| 4 | CI build #62131：单 TMPDIR 暂存仍 Permission denied（CHECK 2/6 失败，4/6），暂存目录落在 /storage/.cache/tmp 同挂载 | TMPDIR 在 CI worker 上同样解析到 /storage（HMDFS/noexec），换目录未换挂载故同错；真机（/data 私有 TMPDIR）通过而 CI 失败，属环境差异 | `_stage_libusb_so()` 改为多候选+真实 CDLL 探针：依次试 TMPDIR/TEMP/TMP、tempfile.gettempdir()、/tmp、/data/local/tmp、/dev/shm，每处 copy+chmod755+别名+可选自签名后立即 ctypes.CDLL 验证，首个可加载者胜出，全部附尝试明细进 DIAG；仍全灭且错误属 Permission denied 窄类时 CHECK 2/6 记 SKIP（ohos_feature，unicorn 跳过同类 ctypes 前例 + CI 修复指导第3条平台限制跳过逻辑），其余错误仍 FAIL；test_package/conanfile.py 同步解析 SKIP（FAIL 仍抛异常，SKIP 仅进 gaps），口径保持 6 CHECK 不变 |

## 上游测试审计

- sdist 顶层无 `tests/`/`test/`；`pyproject.toml` 无 pytest 配置；`Makefile` 仅 ruff/codespell QA；`setup.cfg` 仅 `[egg_info]`。
- 结论：`upstream_tests_exist: false`，`upstream_test_total: 0`，`method: none`。

## 验证结果

```bash
python3 -B test_usbmuxctl.py <package_folder>
# CHECK 1..6 PASS（import usbmuxctl/usb.core/termcolor + 入口可调用 + --help + list --json）
```

`usbmuxctl --json list`（--json 为全局选项，须置于子命令前）无硬件时返回 `{"command":"list","list":[]}`，不抛异常，适合无硬件 CI；前提是 libusb 后端可用。

## 注意事项

- 真实硬件操作（connect/disconnect/status/update）需 USB-Mux 设备 + libusb 后端 + 权限，不在 CI 覆盖范围；test_package 仅覆盖无硬件路径。
- `usbmuxctl update` 需 `dfu-util`，OHOS 未验证，保持原错误提示透出。
