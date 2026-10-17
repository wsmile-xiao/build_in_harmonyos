# udiskie 2.6.2 适配笔记

## 概览

- 上游：https://github.com/coldfix/udiskie （MIT），tag `v2.6.2`（codeload HTTP 200，143991 B）
- 语言：**100% Python 3**（源码树 0 个 C/C++ 文件；`pyproject.toml` PEP 517/setuptools）
- 构建系统：python（conan `conan create`，`package_type=application`）
- 编译日期：2026-10-12
- 状态：built

## 适配内容

### 1. 打包层（OHOS 相关改动）

| # | 上游形态 | OHOS 适配 |
|---|---------|-----------|
| 1 | setuptools entry point 把 4 个启动器装进解释器 system site-packages，shebang 写死构建解释器绝对路径 | 重新生成 4 个启动器：`#!/usr/bin/env python3` + 包相对 `site-packages` 引导，可脱离 conan runenv 独立运行 |
| 2 | 运行时依赖 PyGObject/PyYAML/docopt 走 pip | **PyGObject（`gi` 原生绑定）为 conan 依赖 `pygobject/3.58.0`**；纯 Python 依赖 docopt/PyYAML 以 **vendor** 方式随包发布（由 `tool_requires docopt/0.6.2`、`pyyaml/6.0.2` 提供来源），使启动器自包含 |

### 2. 源码补丁（2 个，均可移植性补丁）

**0001-defer-gi-runtime-ohos.patch**（`udiskie/cli.py` + `udiskie/__init__.py`）
- 将 gi(PyGObject) 运行时导入改为**惰性**（PEP 562 module `__getattr__`）。
- 根因：`cli.py` 顶层 `from gi.repository import GLib`、`from .async_ import …`、
  `import udiskie.mount/udisks2` 会在导入期要求可加载的 gi C 扩展与 GLib/Gio typelib；
  OHOS 上 `_gi.cpython-312-aarch64-linux-ohos.so` 重定位失败
  （`ImportError: Error relocating … PyType_Ready: symbol not found`），且系统/conan cache
  内**无任何 `.typelib`** → 连 `udiskie --version`/`--help` 都无法运行。
- 效果：`--version`/`--help`（经 docopt 即退出，不触碰 gi）可运行；实际设备操作路径
  仍在首次使用时导入 gi，行为不变。

**0002-cache-optional-keyutils-ohos.patch**（`udiskie/cache.py`）
- `python-keyutils` 变为**可选**：缺失时以内置 `_FallbackKeyring` 进程内缓存按相同语义
  （带超时的临时缓存、访问即续期、可 revoke）回退。
- 根因：`cache.py` 顶层 `import keyutils`；python-keyutils 为绑定 libkeyutils/内核 keyring 的
  C 扩展 —— OHOS 制品仓与社区 PyPI 镜像仅有 sdist（缺 `keyutils.h`、系统无 libkeyutils），
  且内核 keyring 系统调用被沙箱阻止（ctypes 直调 arm64 `add_key`(248) → 进程被 kill）。
- 效果：`import udiskie.cache` 可导入，`--password-cache` 特性在 OHOS 上以进程内缓存工作
  （安全性权衡：不再由内核 keyring 托管，仅存活于当前进程，已在补丁注释与 README 写明）。

## 依赖

| 依赖 | 类型 | 版本 | ohpcd | 说明 |
|------|------|------|-------|------|
| PyGObject（`gi`） | 运行时·强制（原生） | 3.58.0 | ✅ EXIT=0 | 唯一"需独立适配仓"的原生绑定；传递依赖 glib2/2.88.0、gobject-introspection/1.78.1、libffi/3.4.4 自动拉取 |
| docopt | 构建期来源（随包 vendor） | 0.6.2 | ✅ EXIT=0 | CLI 参数解析（纯 Python，内嵌） |
| PyYAML | 构建期来源（随包 vendor） | 6.0.2 | ✅ EXIT=0 | YAML 配置解析（内嵌纯 Python `yaml`，跳过 `_yaml` C 加速器） |

## 上游测试（R51，build() 内真实执行）

上游 CI（`.github/workflows/python-package.yml`）实际只跑 `python test/test_match.py`；
仓库内另有 `test/test_cache.py`（标准库 unittest），上游 CI 刻意不跑（`CHANGES.rst`
2.5.7："remove keyutils from CI workflow"）。两者均为上游样例，本适配两者都真实执行。

| 用例文件 | 总数 | 通过 | 失败 | 跳过 | 结果 |
|----------|------|------|------|------|------|
| `test/test_match.py` | 2 | 2 | 0 | 0 | ✅ 全通过 |
| `test/test_cache.py` | 4 | 4 | 0 | 0 | ✅ 全通过（经 0002 补丁的 keyutils 回退） |

## 遇到问题与解决

| # | 问题 | 根因 | 解决 |
|---|------|------|------|
| 1 | 本地 `init-build` 下载源码超时 | 本机无法直连 `github.com`（仅 `codeload.github.com`） | conandata 使用官方 `github.com/.../v2.6.2.tar.gz`（与 codeload 同一 tarball，sha256 已核验）；CI/W3 自动镜像重写 |
| 2 | `udiskie --version` 无法运行（L2 skip） | `cli.py` 顶层导入 gi，沙箱无法 dlopen `_gi.*.so` 且无 typelib | 补丁 0001：惰性化 gi 运行时导入 |
| 3 | 启动器在裸环境缺 `docopt` | 启动器仅注入包自身 site-packages，依赖经 conan runenv 提供 | 内嵌 docopt + PyYAML（vendor），启动器自包含 |
| 4 | 上游 `test_cache` 4 例 ImportError | `cache.py` 顶层 `import keyutils`，OHOS 无该能力 | 补丁 0002：keyutils 可选 + 进程内回退 |
| 5 | G1 门禁要求 `export_sources()`/`apply_conandata_patches` | 门禁强制骨架 | 补齐标准骨架 |
| 6 | L0g 硬编码 remote 拦截 | 注释含 `-r=ohpcd` | 移除注释中的 remote 串 |
| 7 | G2 干净构建找不到源码 | github.com 不可达 | conan-verify 自动注入 ghfast.top 镜像（结束恢复） |
---

**编译结束**: 2026-10-12 17:31
**最终状态**: built
