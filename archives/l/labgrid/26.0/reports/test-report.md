# labgrid/26.0 — 测试报告（OHOS aarch64 真机）

> 本文件位于 `reports/`，被 `.gitignore:96` 整目录忽略，**不进 PR**，仅作本地证据留档。

## 1. 上游测试（在 `conanfile.py build()` 中真实执行）

**测试入口核验**：上游无 `make check` / `ctest` / `meson test`；测试入口即 sdist 内 `tests/`
（58 个 `.py`：52 个含用例 + 4 个模块级 `importorskip` + `conftest.py` + `test_protocol.py` 辅助模块；
783 处 `assert`；454 个 `def test_`，参数化后收集 474 项）。

**执行的命令**（`cwd` = conan 构建目录 = sdist 解包后的原始上游源码树，`tests/` 零改动）：

```bash
python3 -m pytest tests -v --tb=short --no-header -p no:cacheprovider \
    --continue-on-collection-errors --timeout 300 --timeout-method=signal
```

**汇总**

| 指标 | 数值 |
|------|------|
| discovered | 478 |
| collected | 474（另有 4 模块收集期 skip） |
| **passed** | **414** |
| **failed** | **4** |
| **skipped** | **60** |
| errors | 0 |
| 耗时 | 639.55s |

## 2. 逐用例名称与日志路径

- 完整逐用例名单（`-v` 输出，含状态与进度百分比）：
  `.workbuddy/tmp/labgrid-26.0/conan-create4.log`（构建日志中前缀 `labgrid/26.0: [labgrid upstream] `）；
  独立复现基线：`.workbuddy/tmp/labgrid-26.0/standalone/pytest-shim4.log`
- 逐文件统计（基线解析）：

| 测试文件 | PASS | FAIL | SKIP | 合计 |
|---|---:|---:|---:|---:|
| tests/test_agent.py | 14 | 0 | 0 | 14 |
| tests/test_autoinstall.py | 5 | 0 | 0 | 5 |
| tests/test_bareboxdriver.py | 4 | 0 | 0 | 4 |
| tests/test_client.py | 23 | 0 | 0 | 23 |
| tests/test_config.py | 7 | 0 | 0 | 7 |
| tests/test_coordinator.py | 15 | 0 | 0 | 15 |
| tests/test_dediprogflasher.py | 4 | 0 | 0 | 4 |
| **tests/test_environment.py** | **6** | **4** | 0 | 10 |
| tests/test_eth008digitaloutput.py | 9 | 0 | 0 | 9 |
| tests/test_ethernetport.py | 1 | 0 | 0 | 1 |
| tests/test_export.py | 6 | 0 | 0 | 6 |
| tests/test_externalconsoledriver.py | 3 | 0 | 0 | 3 |
| tests/test_factory.py | 14 | 0 | 0 | 14 |
| tests/test_filedigitaloutput.py | 3 | 0 | 0 | 3 |
| tests/test_fixtures.py | 8 | 0 | 0 | 8 |
| tests/test_flags.py | 8 | 0 | 0 | 8 |
| tests/test_flashrom.py | 2 | 0 | 0 | 2 |
| tests/test_flashscript.py | 4 | 0 | 0 | 4 |
| tests/test_graphstrategy.py | 13 | 0 | 1 | 14 |
| tests/test_httpdigitalout.py | 8 | 0 | 0 | 8 |
| tests/test_httpvideo.py | 3 | 0 | 0 | 3 |
| tests/test_laa.py | 54 | 0 | 0 | 54 |
| tests/test_lxaiobus.py | 5 | 0 | 0 | 5 |
| tests/test_manualswitchdriver.py | 4 | 0 | 0 | 4 |
| tests/test_modbusrtudriver.py | 2 | 0 | 1 | 3 |
| tests/test_netns.py | 0 | 0 | 10 | 10 |
| tests/test_openocd.py | 0 | 0 | 3 | 3 |
| tests/test_pb2.py | 12 | 0 | 0 | 12 |
| tests/test_powerdriver.py | 32 | 0 | 4 | 36 |
| tests/test_processwrapper.py | 5 | 0 | 0 | 5 |
| tests/test_qemudriver.py | 6 | 0 | 0 | 6 |
| tests/test_remote.py | 4 | 0 | 0 | 4 |
| tests/test_reporter.py | 3 | 0 | 0 | 3 |
| tests/test_resource.py | 4 | 0 | 0 | 4 |
| tests/test_sched.py | 4 | 0 | 0 | 4 |
| tests/test_serialdriver.py | 12 | 0 | 0 | 12 |
| tests/test_serialport.py | 2 | 0 | 0 | 2 |
| tests/test_shelldriver.py | 8 | 0 | 0 | 8 |
| tests/test_sigrok.py | 0 | 0 | 4 | 4 |
| tests/test_sispm.py | 1 | 0 | 0 | 1 |
| tests/test_sshdriver.py | 6 | 0 | 11 | 17 |
| tests/test_step.py | 12 | 0 | 0 | 12 |
| tests/test_steplogger.py | 1 | 0 | 0 | 1 |
| tests/test_strategy.py | 2 | 0 | 0 | 2 |
| tests/test_sysfsgpioagent.py | 2 | 0 | 0 | 2 |
| tests/test_target.py | 39 | 0 | 0 | 39 |
| tests/test_timeout.py | 2 | 0 | 0 | 2 |
| tests/test_ubootdriver.py | 4 | 0 | 0 | 4 |
| tests/test_usbtmc.py | 2 | 0 | 0 | 2 |
| tests/test_usbvideo.py | 1 | 0 | 0 | 1 |
| tests/test_util.py | 14 | 0 | 22 | 36 |
| tests/test_yaml.py | 4 | 0 | 0 | 4 |
| **合计** | **414** | **4** | **60** | **478** |

## 3. 4 个失败的逐项归因（同一根因，平台限制）

```
FAILED tests/test_environment.py::TestEnvironment::test_create_named_resources
FAILED tests/test_environment.py::TestEnvironment::test_create_named_drivers
FAILED tests/test_environment.py::TestEnvironment::test_usbserialport_warning
FAILED tests/test_environment.py::TestEnvironment::test_usbserialport_no_warning
```

- **首错**：`ImportError: No library named udev`
- **根因**：HarmonyOS 不提供 `libudev.so`（实测 `/system/lib64`、`/system/lib`、`/usr/lib`、`/vendor` 均无）；
  `pyudev` 通过 `ctypes.util.find_library("udev")` 加载失败，`Environment.get_target()` 构造
  `UdevManager` 系 resource 时抛异常。
- **处理**：逐条登记进 `conanfile.py` 的 `PLATFORM_LIMITED_TESTS`；**真实执行、如实计为 failed，
  不 skip、不 xfail**。`build()` 仅当出现 `errors`、或出现该集合之外的 failed、或无任何 passed 时才抛错。
- **影响面**：不使用 udev 的能力（remote/coordinator/exporter、driver、strategy、YAML、6 个 CLI）全部正常。

## 4. 60 个 skip 的归因（全部为上游自带条件，非本适配引入）

**60 = 56 个用例级 skip + 4 个模块级收集期 skip**（`collected 474 items / 4 skipped`；
474 = 4 failed + 414 passed + 56 skipped）。

| 来源 | 数量 | 上游条件（源码原文） |
|---|---:|---|
| `tests/test_util.py`（`@pytest.mark.localsshmanager`） | 22 | 上游 opt-in 标记，默认跳过（需真实本机 ssh 环境 + 显式开关） |
| `tests/test_sshdriver.py`（`@pytest.mark.sshusername`） | 11 | 上游 opt-in 标记，默认跳过（需 `--ssh-username`） |
| `tests/test_netns.py`（`pytestmark`） | 10 | `not netns_allowed()` → `missing user+mount+network namespace privileges` |
| `tests/test_powerdriver.py` | 4 | `pytest.importorskip("pysnmp"/"kasa"/"vxi11")` 可选后端未安装 |
| `tests/test_sigrok.py`（`pytestmark`） | 4 | `not which("sigrok-cli")` → `sigrok not available` |
| `tests/test_openocd.py`（`pytestmark`） | 3 | `not which("openocd")` → `openocd not available` |
| `tests/test_graphstrategy.py` | 1 | `pytest.importorskip("graphviz")` |
| `tests/test_modbusrtudriver.py` | 1 | `pytest.importorskip("minimalmodbus")` |
| **小计（用例级）** | **56** | |
| 模块级收集期（计入 60 但无逐用例行） | 4 | `pytest.importorskip`：`test_docker`(docker)、`test_onewire`(onewire)、`test_pyvisa`(pyvisa)、`test_tasmota`(paho.mqtt.client) |
| **合计** | **60** | |

## 5. `test_package`（消费者视角）

命令：`python3 test_labgrid_consumer.py <package_folder>`（`conanfile.py` 以 `env="conanrun"` 调用）

| # | 检查 | 结果 |
|---|------|------|
| 1 | 元数据版本 26.0（`importlib.metadata` 与 `labgrid.__version__` 一致） | PASS |
| 2 | vendored 运行期闭包导入（grpcio/protobuf/PyYAML 的 C 扩展等 12 个） | PASS |
| 3 | labgrid 子系统导入（remote client/coordinator/exporter、driver、strategy、util.yaml） | PASS |
| 4 | labgrid 自有 YAML loader/dumper 往返一致 | PASS |
| 5 | `Environment(<真实 config.yaml>).get_target("main")` 构造出 `Target` | PASS |
| 6 | **新增 HarmonyOS 消费者用例**（`--lg-env` + 交付的 `pytest11` 入口点 + `env` 夹具） | PASS（`2 passed`） |
| 7 | 6 个控制台脚本存在、shebang `#!/usr/bin/env python3`、`--help` 退出 0 | PASS |

**合计 7/7 通过。**

## 6. 环境适配记录（均为 recipe 侧，上游 `tests/` 零改动）

| 轮次 | 配置 | 结果 |
|---|---|---|
| 1 | 早期补丁版（`--basetemp` + exec shim） | 19 failed / 301 passed / 60 skipped / **98 errors** |
| 2 | + exec-PATH shim 覆盖子解释器 | 41 failed / 360 passed / 60 skipped / 17 errors |
| 3 | + `testshim/python` 包装 + 应用 cache TMPDIR（属主） | 28 failed / 390 passed / 60 skipped / **0 errors** |
| 4 | + `<testdeps>/bin` 入 PATH（套件二次拉起裸名 `pytest`） | **4 failed / 414 passed / 60 skipped / 0 errors** |

首错 → 根因 → 对策：

1. `OSError: The temporary directory .../pytest-of-102 is not owned by the current user`（98 例）
   → `_pytest/tmpdir.py:198` 校验 basetemp 属主 == 解释器 uid；构建目录内新建目录属主为 buildbot uid（20401006），
   进程 uid 为 20420178，永不匹配 → `TMPDIR/TMP/TEMP` 指向**本进程 uid 所有**的临时根
   （`/data/storage/el2/base/cache/labgrid-26.0-tmp`，属主按父目录继承）；无此根时追加 `--basetemp`。
2. `ExceptionPexpect: ... python`（pexpect `which()` 预检失败）+ 套件二次拉起裸名 `pytest` 找不到
   → 本平台只有 `python3` → `testshim/python` 一行 `#!/bin/sh` exec 包装置于 PATH 首位 + `PATH` 前置 `<testdeps>/bin`。
3. `FileNotFoundError: 'true' / 'cat' / 'ssh'`（spawn 路径不解析裸名）
   → `tools/ohos_exec_path_shim.py` 以 `sitecustomize.py` 名注入，`shutil.which` 预解析 `Popen`/`os.exec*` 的 `argv[0]`。

## 7. 消费者用例可行性（新增鸿蒙测试用例）

- 位置：`test_package/test_labgrid_consumer.py` 的 CHECK 6（运行期生成 `test_harmonyos_consumer.py`）
- 形式：**下游消费者视角** —— 用 `--lg-env` 指定 labgrid 配置，由交付包自带的 pytest 插件
  （`pytest11 -> labgrid.pytestplugin` 入口点）提供 `env` 夹具并执行两个用例：
  `test_env_fixture_exposes_target(env)`、`test_labgrid_yaml_loader_is_the_packaged_one()`
- 覆盖的上游盲区：上游单元测试全部针对**源码树**运行，从不验证“安装后的包 + 插件入口点”这条消费者路径
- 可行性结论：**通过**（`2 passed`）；子进程显式传 `PYTHONPATH=<site-packages>:<deps>`，
  确保解析的是交付产物而非宿主环境
- 实测命令（由 CHECK 6 组装）：
  `python3 -m pytest <tmp>/test_harmonyos_consumer.py -v --no-header -p no:cacheprovider -p no:randomly --lg-env <tmp>/lg_env.yaml --basetemp <tmp>/basetemp`
