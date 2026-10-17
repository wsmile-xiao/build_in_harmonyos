# Test Report — librouteros 4.2.2

> R03 上游单元测试真实执行轮。本报告基于本轮真实命令、实际统计与日志，
> 全部日志位于执行端 `$HOME/tmp/librouteros-r03-logs/`（绝对路径与 SHA-256 见下）。

## 1. 上游单元测试（官方仓库 tag 4.2.2）

- **获取途径**：`curl -sSL -o librouteros-4.2.2-tag.tar.gz https://codeload.github.com/luqasz/librouteros/tar.gz/refs/tags/4.2.2`
  → HTTP 200 / 130,708 B / SHA-256 `03832d651deba880ea327f10494530805ac1f020a282a02bc1c7822e634f3777`
- **tag 身份核验**：解包后 `pyproject.toml` `name = "librouteros"`、`version = "4.2.2"` 与 tag 一致；
  解包位置 `$HOME/ohpc_tmp/r03_upstream/tag_extract/`（交付树之外，未 vendored 进 archives/）
- **被测对象**：Conan 打包产物 `package_folder/lib/python3.12/site-packages`（经 PYTHONPATH 导入 librouteros 4.2.2）
- **运行命令**：`PYTHONPATH=<conan site-packages> python -m pytest tests/unit -v`
- **结果**：**230 collected / 230 passed / 0 failed / 0 skipped / 0 errors，退出码 0，通过率 100%**
  - 计数口径说明：上游 `tests/unit` 共有 **143 个测试函数定义**（12 个文件），pytest 对参数化用例展开后
    collected = 230；两种口径均可复算（函数定义数 = 逐文件 `grep -cE 'def test_'` 求和）。
  - 日志：`upstream_unit_suite_execution.log` SHA-256 `984e0d9e62c3231d741326e9cee29a1e2982055df09fd7015730bfa80f486ba9`
  - 收集：`upstream_unit_suite_collect.log` SHA-256 `6acd194394f9f13c66a3df70af5bcb7fbc69d42f1f5de3b278c12c8f95e4a4b5`

### 逐文件台账

| 文件 | 函数定义数 | pytest collected | passed |
|---|---|---|---|
| tests/unit/test_api.py | 10 | 30 | 30 |
| tests/unit/test_config.py | 56 | 72 | 72 |
| tests/unit/test_connections.py | 13 | 15 | 15 |
| tests/unit/test_exceptions.py | 1 | 1 | 1 |
| tests/unit/test_librouteros.py | 18 | 32 | 32 |
| tests/unit/test_path.py | 15 | 15 | 15 |
| tests/unit/test_protocol.py | 17 | 43 | 43 |
| tests/unit/test_query.py | 13 | 22 | 22 |
| **合计** | **143** | **230** | **230** |

台账日志：`upstream_unit_suite_per_file_ledger.log` SHA-256 `0c14aa2d76f33a45fc53398df24510c80c3def14506970d1863572cf9bc88c9b`

## 2. 上游集成测试（tests/integration）

- **计数**：22 个测试函数（test_config=10, test_general=6, test_generator=2, test_path=4）；
  pytest collect-only = 52（含参数化展开）
- **真实运行尝试**：`timeout 60 env PYTHONPATH=... python -m pytest tests/integration -q`
  → 2 skipped, 50 errors, 退出码 1
- **失败根因**：`FileNotFoundError: [Errno 2] No such file or directory: 'qemu-img'`
  （`tests/integration/conftest.py` 的 `routeros_vm` fixture 需启动 QEMU 虚拟机）
- **官方前置依据**：`.github/workflows/test.yml` integration job（docker 拉取
  `lukaszkostka/librouteros_images:latest` 提供 `routeros_*.qcow2`）+ `images/README.md`
  （qemu-img 创建磁盘镜像、qemu-system 安装 RouterOS）；`.qcow2` 镜像不随源码归档发布
  （tag 源码树 `images/` 仅含 README.md）
- **阻塞归属**：全部 22 个集成函数依赖 qemu-img/qemu-system 与 RouterOS 磁盘镜像，
  本机无 docker/qemu-system-i386/qemu-img → **不可运行**（环境前置缺失，非本库缺陷）
- **恢复条件**：安装 qemu-utils/qemu-system-i386 并从官方镜像源获取
  `routeros_6.33.3.qcow2` / `routeros_7.18.2.qcow2` 后可运行
- **统计处理**：集成测试未运行项**不计入**适配后合计与通过/跳过统计
- 日志：`upstream_integration_suite_census_and_blocking_evidence.log` SHA-256 `0002d4a72ddfb6f38c25f7659dcd413c2d6bdd145202838ce729135276c3b3c0`

## 3. 鸿蒙特有测试（harmonyos_test/test_harmonyos.py）

- **运行命令**：`PYTHONPATH=<conan site-packages> python3 archives/l/librouteros/4.2.2/harmonyos_test/test_harmonyos.py`
- **结果**：**7/7 passed，退出码 0**（24 条 assert，全部可失败；负向注入 HARMONYOS_TEST_INJECT_FAIL=1 → 退出码 1）
- 日志：`harmonyos_specific_test_rerun.log` SHA-256 `48b891bf1669ee13f2de7774606111ee6c9e76df67bc3f7d37abd5d6f6e3614a`

## 4. test_package（消费者测试）

- **运行命令**：`conan create archives/l/librouteros/4.2.2`（test_package test() 阶段）
- **结果**：**12/12 passed，退出码 0**（32 条 assert；可失败双向证明：
  注入 `port.default==9999` → AssertionError: default port: 8728 退出码 1；恢复后 12/12 退出码 0）
- 日志：`test_package_execution_revalidation.log` SHA-256 `0575b85b97e9f01ddc74755d037781db4cec7f028d191d569874fd5ddf963c73`、
  `r34_test_package_substance_recheck.log` SHA-256 `496e162283f0cc4e573bdaa588e75f9601978fa43e7e64334cabbd5001a81a17`

## 5. 统计汇总（固定口径：实际执行数）

### 上游测试用例统计（官方 tag 4.2.2 源码树）

| 类型 | 用例数 | 来源 |
|---|---|---|
| 单元测试（tests/unit） | 143（函数定义）/ 230（参数化展开后实际执行） | 官方 tag 归档 SHA-256 03832d65…，逐文件 grep 计数 |
| 集成测试（tests/integration） | 22（函数）/ 52（参数化） | 同上；未运行（qemu 前置缺失） |
| **合计** | **143 函数 / 230 实际执行用例** | |

### 适配后测试用例统计（本轮实际执行）

| 类型 | 用例数 | 与上游对比 | 说明 |
|---|---|---|---|
| 上游单元测试（真实执行） | 230 | 不变（按官方套件原样执行） | 230/230 passed |
| 鸿蒙特有测试（真实执行） | 7 | +7 | 7/7 passed |
| 集成测试 | 0 | 不可运行不计 | qemu 前置缺失 |
| **合计（去重后实际执行）** | **237** | **+7** | 237/237 passed |

### 少报核验

- `上游实测 N = 230`（tests/unit 参数化展开后实际执行数；函数定义口径 143）
- `上游声明 N = 230`（本轮 PR 声明）
- 结论：**实测 N ≤ 声明 N 成立（相等），不构成少报**（R01/R02 曾声明 N=0 属少报，本轮已修正）
