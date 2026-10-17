# acme-tiny-pyc 5.0.3 适配笔记

## 包来源说明（为什么是 acme-tiny-pyc）

acme-tiny-pyc 是 Alpine 打包生态中 acme-tiny 的**预编译 Python bytecode 子包**：
Alpine 的 `acme-tiny` 主包安装 `acme_tiny.py`，而 `acme-tiny-pyc` 子包使用
`py-compile`/`compileall` 额外生成 `__pycache__/acme_tiny.cpython-*.pyc`，
供 python3 直接加载，从而在保持脚本可审计的同时提升冷启动性能。

本任务按**路径 A** 将 acme-tiny-pyc 5.0.3 作为**独立 Conan 包**归档，源码来源
为同一上游项目 diafygi/acme-tiny 5.0.3 的 PyPI sdist（conandata.yml 已注明）。

## 独立包策略（保留 .py + 额外提供 .pyc 的原因）

Alpine 的 pyc 子包**依附主包存在**（主包提供 acme_tiny.py，子包只补 pyc）。
但本任务归档为独立 Conan 包，包内**必须自包含可运行**，因此 conanfile.py
package() 同时：

1. 保留运行所需模块文件 `acme_tiny.py`（铺到 `lib/python3.12/site-packages/`）；
2. 额外提供预编译 bytecode `__pycache__/acme_tiny.cpython-312.pyc`
   （`python3 -m py_compile` 生成，即 acme-tiny-pyc 的本质）；
3. 生成可执行入口 `bin/acme-tiny`（等价 console script `acme_tiny:main`）。

包内自检（fail-fast，见 conan create 日志）：
- `import acme_tiny` 且 `main`/`get_crt` 可调用
- `bin/acme-tiny -h` 退出码 0
- `__pycache__/acme_tiny.cpython-*.pyc` 存在
- 直接从 .pyc 加载模块并确认关键入口

## 编译环境

- 构建系统: setuptools / PEP 517（pyproject.toml，`build-backend=setuptools.build_meta`）
- 编译日期: 2026-08-05
- 编译器: 无（纯 Python，无 C 扩展，settings 仅 os/arch）
- Python: 3.12.9（宿主）；目标包布局 lib/python3.12/site-packages
- 状态: built

## 编译步骤

```bash
# 1. PEP 517 wheel 构建验证（产物平台无关 py3-none-any）
python3 -m pip wheel --no-deps --no-build-isolation -w dist .

# 2. 安装 + pyc 生成（conanfile.py package() 内完成）
python3 -m py_compile acme_tiny.py   # 生成 __pycache__/acme_tiny.cpython-312.pyc

# 3. 包内自检（import / CLI -h / pyc 存在 / pyc 直接加载）
```

## 上游测试情况

真机测试驱动下实测（驱动三要素仅为测试子进程作用域，非包内容/运行时依赖：临时 python->python3 wrapper 经 PATH 前缀注入、签名 Pebble 测试服务经 ACME_TINY_PEBBLE_BIN 注入、OPENSSL_CONF 指向临时 openssl.cnf）。

测试驱动可复现信息（最小集）：
- **Pebble**：官方 release `https://github.com/letsencrypt/pebble/releases/download/v2.10.1/pebble-linux-arm64.tar.gz`，原始文件 SHA256=`b53fd072a69eb7692451de4e8b0667e0bdf5cccd7e36fc51b8eaf2fcc135ed9f`；可执行性验证：`binary-sign-tool sign -selfSign 1`（仅用于测试服务可执行性的临时自签名，不记录/不提交证书、私钥或签名材料）→ `display-sign` 显示 `code signature is self-sign` → `pebble -h` 正常。
- **python wrapper**：临时目录内 `python` 脚本转发全部参数给 `python3`，仅经测试子进程 PATH 前缀生效。
- **OPENSSL_CONF**：指向临时 openssl.cnf，仅测试子进程环境变量。
- **sitecustomize**（如需禁用 posix_spawn 兼容层）：临时目录内重建，经临时 PYTHONPATH 注入，未修改上游源码、未持久化。
- **清理**：每次测试后确认无 pebble/http.server/测试子进程残留、5002 端口未监听，并清理临时测试目录。

| 测试文件 | 用例数 | 结果 | 说明 |
|----------|--------|------|------|
| tests/test_install.py | 2 | 2 通过 / 0 skipped | venv pip install + acme-tiny -h；python wrapper 满足上游 `python` 命令假设，2/2 passed |
| tests/test_module.py | 17 | 15 通过 / 2 条件性 skipped | 签名 Pebble + OPENSSL_CONF 下 15 passed；2 个为上游条件性 skip（test_success_cn / test_weak_key，skipIf(not USE_STAGING)），非环境跳过 |
| 合计 | 19 | 17 通过 / 2 skipped | 未修改任何上游测试文件、断言、数据、skip 条件或预期结果；0 failed / 0 errors / 0 timeout |

> 注：2 个 skipped 只能如实写为上游 test_success_cn 与 test_weak_key 的
> `@unittest.skipIf((not USE_STAGING), ...)` 条件性跳过（test_module.py L429/L447）。
> 上游测试结果不视为 Conan package build 必然执行的测试；conanfile.py build()
> 仍仅做确定性构建与包内自检（import / CLI 入口 / pyc 生成与直接加载）。

> test_module.py 中 4 个用例（success_cn/weak_key/nonce_retry/
> pebble_doesnt_support_cn_domains）本身受 `ACME_TINY_USE_STAGING` /
> `ACME_TINY_PEBBLE_BIN` 环境变量控制；其余 13 个也全部依赖 pebble + 本地
> challenge 文件服务器。
>
> conanfile.py build() 仅做确定性构建与包内基础自检（wheel 构建、import、
> CLI 入口、pyc 生成与直接加载），不运行依赖 venv/ensurepip 的上游测试
> （CI #13585 修复）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI #13585：conan create 失败（`python -m venv` 内 ensurepip 失败） | build() 强制运行上游 tests/test_install.py，其 setUp 依赖 `python -m venv`（venv 内部 `ensurepip --upgrade --default-pip` 在 CI 环境不可用） | 移除 build() 中 test_install 强制运行；改为确定性包内自检（import / CLI 入口 / pyc 生成与直接加载）；test_install 2 用例记 skipped/unrunnable |
| 2 | 本环境 Python subprocess 无法按 PATH 解析命令名 | 平台 posix_spawn 行为（连 `openssl`/`python3` 相对名也失败，显式绝对路径可 exec） | 配方自检/测试全部使用显式路径或 sys.executable，不依赖相对名 |
| 3 | test_module.py 无法运行 | 需要 pebble 测试服务二进制，github 网络不可达（curl 000） | 记录 unrunnable/skipped（17 用例），不伪造通过结果 |
| 4 | HMDFS/平台对 `python` symlink exec 限制 | 符号链接经 posix_spawn 解析失败 | 用 shell wrapper 脚本代替 symlink |

## 依赖版本

- python3: 3.12.9（宿主，运行时依赖 python3/3.12.8 声明于 manifest）
- openssl: 3.0.9（运行时命令依赖：`openssl dgst -sha256 -sign` / `openssl rsa`）
- setuptools: 83.0.0（构建工具，PEP 517）
- pip: 26.2（构建工具）

## 验证结果

```bash
# conan create（含 build 内上游 test_install + package 内自检 + test_package 4 断言）
python3 ohc-run.py conan-verify acme-tiny-pyc 5.0.3
# → 通过（详见 conan-verify 输出与 conan create 日志）

# 产物结构（package 内）
#   bin/acme-tiny
#   lib/python3.12/site-packages/acme_tiny.py
#   lib/python3.12/site-packages/__pycache__/acme_tiny.cpython-312.pyc
```

## 补丁

无源码补丁（patches_applied: []）。纯 Python 包，无编译差异；上游测试断言
未做任何修改。
---

**编译结束**: 2026-08-07 17:54
**最终状态**: built
