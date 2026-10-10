# python-msgpack 1.1.1 — 适配笔记

## 概述
- 上游: https://github.com/msgpack/msgpack-python（PyPI sdist 1.1.1）
- 类型: 纯 Python 包（sdist 自带可选 C 扩展 _cmsgpack，本移植不编）
- License: Apache-2.0
- SHA-256 (PyPI sdist): 77b79ce34a2bdab2594f490c8e80dd62a02d650b91a75159a63ec413b8d104cd

## 适配要点
1. copytree 剔除 _cmsgpack.c/*.pyx → 只装纯 Python 实现；__init__.py 对
   _cmsgpack ImportError 自动回退 msgpack.fallback，公共 API 一致。
2. conan 包名 python-msgpack：ohpcd 的 msgpack/7.0.1 是 msgpack-c C 库，不提供
   Python 模块；cachecontrol 的 msgpack<2.0.0,>=0.5.2 由本包满足。
3. R38: 纯库无 commands.json。

## 上游测试（设备实测 2026-09-26）
- 入口: `python3 -m pytest test/`；pytest 9.1.1 实测：120 passed / 0 failed
  （0.5 秒）——纯 Python fallback 实现下上游选项矩阵与边界用例全过。
- 日志见 run 证据 dep-upstream/upstream-msgpack.log。
- 等效验证: test_package 消费者测试（序列化往返 + cachecontrol Serializer 选项）。

## 环境
- Python 3.12.9, Conan 2.x, profile ohos-aarch64
