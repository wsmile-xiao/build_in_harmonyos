# Adaptation Notes - librouteros 4.2.2

## Overview
librouteros 是 MikroTik RouterOS 的 Python API 客户端实现（同步 + asyncio），
提供 `connect()`/`async_connect()` 入口、`Api`/`AsyncApi` 类、协议字编码解码
（`protocol.py` 纯函数）、MD5 token 登录（`login.py`）、查询构建器
（`query.py` 的 Key/And/Or）、配置管理工具（`config.py` 的 export/compare/rollback）。

## Build System
- uv_build（`pyproject.toml` build-backend = uv_build，PEP 517 纯 Python 后端）
- 纯 Python wheel（py3-none-any）— 无 C/C++ 编译
- Runtime deps: `dependencies = []`（pyproject 声明为空）
- requires-python: >=3.10.0

## Build Process
1. 下载 PyPI sdist `librouteros-4.2.2.tar.gz`（GitHub 上游直连在本环境不可达，PyPI 官方发布物为权威来源）
2. `pip install "uv_build==0.12.*"`（构建后端，社区 PyPI 源已有 0.12.19）
3. `pip install --no-deps --prefix=$staging .` 然后归一化到 `lib/pythonX.Y/site-packages`
4. 复制 LICENSE 到 licenses/
5. test_package: import + 协议字编解码 + 长度编解码 + MD5 登录编码 + config 工具函数 + 查询构建

## Upstream Tests
- 上游 sdist **无测试文件**（无 test/ 目录，纯 Python API 客户端包）。
- test_package 补全 12 个消费者测试（test_package/test_librouteros.py），全部不需要
  真实 RouterOS 设备，可在 OHOS 受限环境运行：
  1. test_import_api — import librouteros 及核心符号（connect/async_connect/Api/AsyncApi）
  2. test_connect_kwargs_defaults — ConnectKwargs 默认值（host/port/encoding/login_method）
  3. test_parse_word — 协议字 `=key=value` 解析（str/int/bool 三型）
  4. test_compose_word — 协议字 `=key=value` 组装（str/int/bool 三型）
  5. test_encode_length — 长度编码边界（<0x80 / 两字节 / 四字节）
  6. test_decode_length — 长度解码回环
  7. test_encode_password — MD5 token 登录编码（RouterOS 6.43 前认证，已知向量）
  8. test_parse_version — RouterOS 版本串 `7.16rc1 (testing)` → (7, 16)
  9. test_strip_header — /export 头部时间戳归一化
  10. test_compare_empty — 相同配置无差异 diff
  11. test_compare_diff — 不同配置产生 unified diff 且含 running/candidate 标记
  12. test_query_key — Key 运算符构建查询生成器（==/!=/</>）

## OHOS-specific handling
- 纯 Python noarch：settings 仅 ("os", "arch")，无需编译器（R32 平台判断用 in ("Linux", "OHOS")）。
- build() 中 pip 安装 uv_build 使用 --break-system-packages + 超时重试，
  规避 CI 干净环境无预装问题。
- 无 .so 产物，不涉及 HMDFS umask 077 的共享库权限问题。

## 验证
- conan create: PASS（12/12 test_package 通过）
- 版本号：4.2.2（上游正式 PyPI 版本，R37）

## 已知限制
- 与真实 RouterOS 设备的连接/命令执行不在本包测试范围（需要硬件设备），
  L1 验证覆盖 import/协议编解码/登录编码/配置工具纯函数。
- RouterOS 7.x 的 rollback（/system/scheduler 死手开关）逻辑依赖真实设备，仅静态可导入验证。
---

**编译结束**: 2026-09-28 14:03
**最终状态**: built
