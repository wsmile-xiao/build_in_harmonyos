# labgrid

**labgrid** 是 Pengutronix 面向嵌入式开发的板卡控制框架：既是可导入的 Python 库（resource / driver / strategy 三层对象模型，附带 pytest 插件 `labgrid.pytestplugin`），也是六个命令行工具。上游采用 Python 3 + setuptools 分发，许可证 LGPL-2.1-or-later。

## 功能概述

安装后提供 6 个命令行工具：

| 工具 | 功能 |
|------|------|
| `labgrid-client` | 向 coordinator 申请/释放 place、增删 match 与 alias、执行 `ssh`/`rsync`/`forward` 等子命令（分布式测试机调度客户端） |
| `labgrid-coordinator` | 协调器服务端：管理 exporter 注册、place 状态与资源匹配 |
| `labgrid-exporter` | 资源导出器：把本机串口/USB/网络等资源注册到 coordinator |
| `labgrid-suggest` | 按 target 的 match 需求给出建议 |
| `labgrid-autoinstall` | 自动安装流程（USB 启动介质等） |
| `labgrid-tap-fwd` | TAP 网络转发辅助工具 |

另含 Python 包 `labgrid`（`resource` / `driver` / `strategy` / `remote` / `util` 与 pytest 插件），可作为库被下游测试工程直接 `import`。

## OHOS 适配（HarmonyOS PC / aarch64）

### 构建与交付方式

- `package_type = "python-require"`，纯 Python 无本地编译；`build()` 中先 `pip install` 运行期依赖闭包到私有目录，再以 PEP 517（`--no-build-isolation` + 私有 setuptools）构建并安装 labgrid 本体到 `staging`。
- 交付布局：`lib/python3.12/site-packages/labgrid` + `labgrid-26.0.dist-info`（entry point `pytest11 = labgrid.pytestplugin`）、`bin/` 六个控制台脚本、`deps/` 运行期依赖闭包。
- `bin/` 脚本 shebang 由构建期解释器的绝对路径改写为 `#!/usr/bin/env python3`（仓内 Python CLI 包统一做法），`runenv_info` 暴露 `bin/` 到 PATH、`site-packages` 与 `deps` 到 PYTHONPATH。
- `package()` 只从构建目录拷贝产物，**不需要联网**。

### 关键攻坚点

1. **R36 依赖闸：14 条运行期依赖只有 3 条在 ohpcd 可消费**
   `attrs`、`pyyaml`、`xmodem` 已发布；`exceptiongroup`、`grpcio`、`grpcio-reflection`、`protobuf`、`jinja2`、`pexpect`、`pyserial-labgrid`、`pytest`、`pyudev`、`pyusb`、`requests` 未发布（连带传递缺口 `iniconfig`、`markupsafe>=2.0`、`psutil`）。声明进 `requirements()` 会硬阻塞构建，故按仓内 vendor 路线：`requirements()` 留空，运行期闭包定版后 pip 装进包内 `deps/`，由 `package_info()` 经 PYTHONPATH 暴露。先例：`advocate/1.0.0`、`awscli/2.34.56`、`python3-rdflib/7.1.4`、`gym/0.26.2`。
2. **同名异构不可替代**
   `grpcio`（PyPI）≠ ohpcd `grpc/1.70.0`（C++）；`protobuf`（PyPI 发行版）≠ ohpcd `protobuf/33.6.1`（C++）；`pyserial-labgrid` ≠ ohpcd `pyserial/3.5`（labgrid 自带 fork）。
3. **C 扩展只提供 ohos_aarch64 标签的 wheel**
   `grpcio`、`protobuf`、`PyYAML` 必须用 `--platform ohos_aarch64 --only-binary=:all:` 安装，否则 pip 回退去编译 sdist，在 HarmonyOS 上必然失败（无 `Python.h`、`platform ohos is not supported`）。
4. **上游测试在 worker 上真实执行的三项环境适配**（均已落进 `conanfile.py`，未改动上游任何源码）
   - `TMPDIR` 指向**本进程 uid 所有的**临时根：pytest 的 `tmpdir` 夹具会校验 basetemp 属主与解释器 uid 是否一致，而 worker 上构建目录内新建文件的属主是 buildbot uid，该检查永远不可能通过；进程自身临时根（OHOS 上为应用 cache 目录）下的目录会继承本进程 uid，检查才能通过。若确无此根，则额外传 `--basetemp`（唯一跳过该检查的途径）。
   - `<testdeps>/bin` 加入 PATH：套件会以裸名 `pytest` 再次拉起运行器（`tests/test_fixtures.py`、`tests/test_flags.py`、`tests/test_steplogger.py`）。
   - `testshim/` 提供 (a) 一行 `python` 执行包装（上游多处硬编码裸名 `python`，而本平台只有 `python3`）与 (b) `sitecustomize.py`（OHOS exec-PATH 仿真，见下）。
5. **沙箱 exec-PATH 缺失**
   本 worker 的 HAP 解释器无法按 POSIX 语义解析**裸程序名**：`subprocess.run(["/bin/true"])` 成功、`subprocess.run(["true"])` 抛 `FileNotFoundError`，而 `/bin/sh -c 'true'` 正常（PATH 解析发生在 shell 内而非解释器 spawn 路径）。labgrid 自身就是 POSIX 写法（`labgrid/util/ssh.py` 起裸名 `ssh`/`rsync`、`cat`），上游测试也故意起裸名 `true`/`false`/`cat`。`tools/ohos_exec_path_shim.py` 在测试运行期用 `shutil.which` 先把名字解析成绝对路径，等效恢复 POSIX 行为；它只在测试进程与子进程生效，**不会进入交付包**。

### 与 Linux 的差异

- **无 `libudev.so`**：HarmonyOS 不提供 udev（`/system/lib64`、`/system/lib`、`/usr/lib`、`/vendor` 均无）。labgrid 基于 udev 的 resource（`UdevManager`）依赖 pyudev 动态加载 `libudev.so`，因此相关 4 个上游用例在真机上必然失败（详见「测试结果」）；不使用 udev 的能力（remote/coordinator/driver/strategy/YAML/CLI）正常。
- **`/tmp` 只读**：`TMPDIR` 已被指向可写的应用 cache 目录，构建与测试均不依赖 `/tmp`。
- **裸名命令解析**：见上，仅在测试运行期由 shim 补偿；下游用户在自己的 OHOS 环境中同样应使用绝对路径或 shell 解析。

## 测试结果（OHOS aarch64 真机实测）

### 上游测试（在 `build()` 中真实执行，`test_package` 不替代该统计）

```bash
# cwd = conan 构建目录；测试树 = sdist 解包后的原始 tests/，上游源码零改动
python3 -m pytest tests -v --tb=short --no-header -p no:cacheprovider \
    --continue-on-collection-errors --timeout 300 --timeout-method=signal
```

| 指标 | 数值 |
|------|------|
| 发现（discovered） | 478 |
| 收集（collected） | 474 |
| 通过（passed） | 414 |
| 失败（failed） | 4 |
| 跳过（skipped） | 60 |
| 错误（errors） | 0 |
| 耗时 | 639.55s |

- **4 个失败**（均在 `tests/test_environment.py`，同一平台根因，已在配方 `PLATFORM_LIMITED_TESTS` 逐条登记，**不 skip、不 xfail，如实计为 failed**）：
  `TestEnvironment::test_create_named_resources`、`TestEnvironment::test_create_named_drivers`、`TestEnvironment::test_usbserialport_warning`、`TestEnvironment::test_usbserialport_no_warning` —— 全部为 `ImportError: No library named udev`。
- **60 个跳过**全部为上游自带条件（56 个用例级 + 4 个模块级收集期跳过），非本适配引入：
  22 个上游 `localsshmanager` opt-in 标记、11 个 `sshusername` opt-in 标记、10 个缺 user+mount+network namespace 能力、
  其余为可选工具/后端缺失（`openocd` 3、`sigrok-cli` 4、`graphviz` 1、`minimalmodbus` 1、`pysnmp`/`kasa`/`vxi11` 4）；
  另有 4 个测试模块在收集期由上游 `pytest.importorskip` 跳过：`test_docker`(docker)、`test_onewire`(onewire)、`test_pyvisa`(pyvisa)、`test_tasmota`(paho.mqtt.client)。58 个 `.py` 全部就位，`tests/` 零改动。

### test_package（消费者视角，7/7 通过）

1. 元数据版本 `26.0`（`importlib.metadata` 与 `labgrid.__version__` 一致）
2. vendored 运行期闭包导入（含 `grpcio`/`protobuf`/`PyYAML` 的 C 扩展）
3. labgrid 子系统导入（remote client/coordinator/exporter、driver、strategy、util.yaml）
4. labgrid 自有 YAML loader/dumper 往返一致
5. `Environment(config).get_target()` 构造出 `Target`
6. **新增鸿蒙消费者用例**：以 `--lg-env` 驱动包自带 pytest，经交付的 `pytest11 -> labgrid.pytestplugin` 入口点使用 `env` 夹具（`2 passed`）
7. 6 个控制台脚本交付完整、shebang 为 `#!/usr/bin/env python3`、`--help` 退出码 0

## 依赖关系

- 编译期：无 C/C++ 依赖（纯 Python）；构建工具 `setuptools`/`wheel`/`setuptools_scm` 仅构建期安装。
- 运行期（已随包 vendor 到 `deps/`）：`attrs` 26.1.0、`exceptiongroup` 1.3.1、`grpcio` 1.84.0、`grpcio-reflection` 1.84.0、`protobuf` 7.35.1、`jinja2` 3.1.6、`pexpect` 4.9.0、`pyserial-labgrid` 3.5.0.2、`pytest` 9.1.1、`pyudev` 0.24.4、`pyusb` 1.3.1、`PyYAML` 6.0.3、`requests` 2.34.2、`xmodem` 0.5.0（含传递依赖）。
- 上游测试：`psutil`、`pytest-mock`、`pytest-benchmark`、`py-netgear-plus`、`pytest-timeout`（仅构建期，不随包交付）。

## 使用示例

```python
# 消费者（CMakeLists / conanfile 中 require labgrid/26.0 后）
import labgrid
from labgrid import Environment
```

```bash
# 交付的命令行工具（bin/ 已由 runenv 加入 PATH）
labgrid-client --help
labgrid-coordinator --version
```

## 参考资料

- 上游仓库：https://github.com/labgrid-project/labgrid
- 文档：https://labgrid.readthedocs.io/
- PyPI：https://pypi.org/project/labgrid/26.0/
