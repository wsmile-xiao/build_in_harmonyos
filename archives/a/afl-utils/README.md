# afl-utils

**afl-utils** 是一组围绕 afl-fuzz（American Fuzzy Lop）的自动化辅助工具集，用于崩溃样本的采集与验证、并行 fuzz 作业管理、语料精简以及统计/同步。它由 rc0r（@_rc0r）开发，采用 Python 3 编写，通过 setuptools 分发。

## 功能概述

安装后提供 8 个命令行工具：

| 工具 | 功能 |
|------|------|
| `afl-collect` | 采集崩溃样本 → gdb + exploitable 分析 → 建立样本索引 / SQLite 落库 |
| `afl-cron` | 周期性调度其它 afl-utils 工具（守护进程） |
| `afl-minimize` | 语料精简（afl-cmin / afl-tmin 封装） |
| `afl-multicore` | 在多核机器上并行拉起 afl-fuzz 作业（screen 会话管理） |
| `afl-multikill` | 终止 afl-multicore 启动的作业会话 |
| `afl-stats` | 汇总 fuzzer_stats、历史落库（SQLite）、可选 Twitter 发布 |
| `afl-sync` | 通过 rsync 在多台机器间同步 fuzz 目录 |
| `afl-vcrash` | 崩溃样本验证（可复现性） |

另含 Python 包 `afl_utils`（工具实现）与 `db_connectors`（SQLite 连接器）。

## OHOS 适配（HarmonyOS PC / aarch64）

- **纯 Python 3 包**：无本地编译步骤，`pip install` 即可产出 8 个入口脚本与两个 Python 包。
- **私有前缀安装**：所有依赖与本体均通过 `pip --prefix/--target` 安装到 Conan 构建目录内的私有前缀，**不注入共享 `/usr/local`**。
- **运行期依赖打包**：上游声明的运行期依赖 `simplejson`、`twitter`、`exploitable`（以及 twitter 的 `certifi`）被一并打入包的 `site-packages`，工具开箱即用。
- **exploitable 来源**：`exploitable==1.32-rcor` 不在 PyPI，按上游 `setup.py` 的 `dependency_links` 从官方 GitLab 归档获取。
- **simplejson 平台 wheel**：社区镜像只提供 `ohos_aarch64` 标签的 wheel，需显式 `--platform ohos_aarch64 --only-binary=:all:` 安装。
- **运行时工具依赖**：`afl-multicore`/`afl-multikill` 包装 `afl-fuzz`，`afl-sync` 驱动 `rsync`，分别由制品仓 `afl/1.35b`、`rsync/3.3.0` 提供（`requires`）。
- **构建期工具依赖**：上游测试会 shell out 到 `make`（每个用例 `setUp` 构建 `testdata/crash_process`）与 `ls`（afl-vcrash 的 trivial 目标），而 CI worker 的 PATH 两者皆无 → 由制品仓 `bmake/20200710`、`coreutils/9.10` 提供（`tool_requires`），配方在构建期解析并注入测试 PATH。
- **上游测试修改（3 个补丁，均未削弱断言）**：`0003` 同步 PGID 文件 `/tmp` 路径口径为 `tempfile.gettempdir()`；`0004` 把 `setsid` 外部命令 spawn 改为 Python 原生 `start_new_session=True`；`0005` 使套件容忍平台缺失的宿主工具（`make` 调用加 `shutil.which` 守卫、`ls` 目标回退到解释器）。详见 `1.35a/notes.md`。
- **多平台可移植性修复**：`afl-multicore`/`afl-multikill` 的 PGID 文件原硬编码 `/tmp`（本平台 `/tmp` 只读，工具不可用），补丁改为经 `tempfile.gettempdir()`（遵循 `$TMPDIR`）解析；上游对应测试用例同步修改（见 `1.35a/notes.md` 声明）。

## 依赖关系

- 编译/构建：无 C/C++ 依赖（纯 Python）。
- 运行期：`afl/1.35b`（afl-fuzz）、`rsync/3.3.0`；Python 侧 `simplejson`、`twitter`、`exploitable`、`certifi`（已随包打包）。
- 上游测试：Python `pytest` + `pytest-timeout`（仅构建期）。

## 测试结果

- 上游 pytest 套件（`tests/` 9 文件 92 用例）：**92 passed / 0 failed / 0 skipped（100%）**，在构建期真实运行（`conan create` 实测 rc=0）。
- test_package 消费者测试：**11/11 PASS**（打印 `ASSERTIONS: passed=11 failed=0 total=11`）。
- 详情（含上游测试用例修改声明与逐项实验证据）见 `1.35a/notes.md` 与 `1.35a/reports/test-report.md`。

## 参考资料

- 上游仓库：https://gitlab.com/rc0r/afl-utils
- 许可证：Apache-2.0
