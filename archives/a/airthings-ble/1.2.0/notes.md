# airthings-ble 1.2.0 适配笔记

## 编译环境
- 构建系统: custom（纯 Python，poetry-core，pip install . 安装到 site-packages）
- 编译日期: 2026-08-20
- 编译器: clang/clang++（Python 运行时由设备提供，无需 C 编译）
- 状态: built（等待真机预检通过后由 HMBS 统一发布）

## 编译步骤

```bash
# conan create 由真机预检执行；配方内 build() 完成：
python3 -m pip install . --prefix=<stage>          # poetry-core 从 pypi.cnb.cool 镜像解析
# 上游测试由 test_package 的 test() 执行（test_package/tests/ 内复制的上游套件）：
python3 -m pytest test_package/tests/ -q --no-header -o addopts=  # 输出 HMBS_UPSTREAM_TEST_RESULT
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | PyPI sdist 不含 tests/ 目录 | 官方 sdist 打包仅含 LICENSE/PKG-INFO/README/airthings_ble/pyproject，无测试 | 源码改用 GitHub 官方 tag archive（sha256 已实测核验），使上游 pytest 套件可随源码接入 |
| 2 | 运行时依赖 bleak/bleak-retry-connector/async-interrupt/cbor2 未发布为 conan 配方 | 这些 Python 包暂无 conan 配方 | 遵循 aiven-client 先例：`pip install .` 时由 pip 从配置的 pypi.cnb.cool 镜像自动解析依赖，装进同一 site-packages |
| 3 | 上游 pytest addopts 带 `--cov`（需 pytest-cov） | pyproject.toml 配置了 coverage 报告 | 运行测试时以 `-o addopts=` 覆盖，避免依赖未安装的 pytest-cov |
| 4 | 上游测试模块级 import bleak（解析器顶层 `from bleak import ...`） | 包设计如此 | 依赖与包同装进 site-packages，PYTHONPATH 指向同一目录即可导入 |
| 5 | AI Review 声称 test_wave_plus.py/test_wave_mini.py 的 payload 无法满足 8 项断言 | 审查者误索引 `<4B8H` struct 字节（把 4 个 B 之后的 8 个 H 从 index 1 起算） | 已核对上游 sensor_decoders.py：`_decode_wave_plus` 用 val[1]/2、val[2]、val[4..9]；实测 payload 解码得 humidity=28.0/radon_1day=11/radon_longterm=34/temp=24.93/voc=108/co2=797/illuminance=5/pressure=999.92 全部命中；两文件与上游 tag 1.2.0 官方 tests/ 逐字节一致（sha256 核验）。判 false_positive，不改动 |

## 依赖版本

- 运行时 Python 依赖（由 pip 从 pypi.cnb.cool 镜像解析，未发布 conan 配方）：
  - bleak >= 1.0.1（python < 3.14）
  - bleak-retry-connector >= 4.4.3
  - async-interrupt >= 1.2.2
  - cbor2 >= 5.6.5
- 测试依赖：pytest（build() 内若缺失则由 pip 安装）

## 验证结果

- 上游测试：12 个测试文件（tests/），30 个 TEST 函数，纯 hex 数据解码逻辑、无需真实 BLE 硬件；上游 tests/ 原样复制进 test_package/tests/，由 test_package 的 test() 在 conan create 时真实执行并输出 HMBS_UPSTREAM_TEST_RESULT 标记
- test_package：test_airthings_ble.py 真实调用库 API（设备类型枚举 / Wave Plus hex 解码 / 氡气分级 / ATOM 请求序列化），本地 Python 3.13 实测 15/15 断言通过
- 最终数字以真机预检日志为准（本笔记不填写测试数字）

## 注意事项

- 测试全部使用上游测试套件同款 hex 数据（test_wave_mini.py / test_atom_request.py / test_radon_level.py），无需 BLE 硬件，可在无蓝牙环境完整执行
- 包类型 python-require；`package_info()` 通过 runenv_info.append_path 暴露 site-packages 到 PYTHONPATH
