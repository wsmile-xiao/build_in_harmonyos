# riscemu 2.2.7 适配笔记

## 编译环境
- 构建系统: custom（纯 Python / poetry-core，`pip install` 完成安装，无 C/C++ 编译单元）
- 编译日期: 2026-09-29
- 编译器: clang/clang++（配方保留 profile 默认值；本包无编译单元）
- 平台: aarch64-linux-ohos（HarmonyOS PC，Conan 2.29.1 OHOS 适配版，profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built

## 编译步骤

riscemu 是**纯 Python RISC-V 模拟器**（0 个 C/C++ 源文件），构建即「安装 + 打包」：

```bash
# 1. 取源码：GitHub 官方 tag archive（含上游 test/ 两套测试套件）
#    https://github.com/AntonLydike/riscemu/archive/refs/tags/v2.2.7.tar.gz
#    sha256 d9d4da9bb4449c3de3c691e01dba5d0e8e9048cd9f32db3eab6476ea326fbd0c
# 2. build(): python3 -m pip install . --prefix=<stage> --ignore-installed
# 3. package(): 将 <stage> 全量拷入 package_folder
#    -> bin/{riscemu, readelf.py} + lib/python3.12/site-packages/{riscemu, elftools, importlib_resources}
# 4. package_info(): runenv_info 暴露 PYTHONPATH=<site-packages>，PATH 追加 <pkg>/bin
conan create archives/r/riscemu/2.2.7 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

- 配方：`package_type = "python-require"`，`settings = os, arch, compiler, build_type`，
  不声明 `requires`（运行时依赖由 pip 解析并打入包内），`validate()` 仅允许 OHOS / Linux。
- 与已合并先例 `airthings-ble 1.2.0`、`aiven-client`、`rapt-ble 0.1.2` 同构。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 把 `sphinx-docs/` 当源码根提升，生成的 `.work` 少了仓库根文件 | 归档根含带构建脚本的文档目录，工具的嵌套源码探测误判 | 手工 `tar xzf ... --strip-components=1` 重建 `.orig` / `.work`（真实仓库根 133 个文件），再跑 `lang-preflight`（否则语言探测失真） |
| 2 | PyPI sdist 不含 `test/`，无法接入上游测试 | poetry 只按 `pyproject.toml` 收文件，测试不在 sdist 内 | 改用 GitHub 官方 tag archive（含 `test/*.py` 与 `test/filecheck/`），sha256 已核验；不上 gitcode 搬运源 |
| 3 | `lit` 下 `fibs.asm` 假失败（期望的 `[CPU] Program exited with code 1265227608` 不出现） | lit 为每个用例重建最小环境，**不转发 HOME**；riscemu 调试路径执行 `readline.write_history_file(expanduser("~/.riscemu_history"))` 抛 `FileNotFoundError` 中断 ebreak 处理 | 新增平台 shim `test/filecheck/lit.local.cfg` 转发 `HOME`（无则 `tempfile.mkdtemp` 兜底）；上游 `.asm` 文件零改动 |
| 4 | `lit` 下 `snitch/*.asm` 与 `python3 -m riscemu` 找不到被测包 | lit 的 `pass_vars` 白名单**不含 PYTHONPATH**，被测包只通过 `PYTHONPATH` 暴露 | 同上 `lit.local.cfg` 转发 `PYTHONPATH`；`test_package` 的 `_child_env()` 把它设为 `site-packages:test_package:原值`（`snitch` 不在 wheel 内，随 test_package 提供副本） |
| 5 | `lit --timeout=5` 直接 `fatal: Setting a timeout per test not supported` | lit 的 per-test timeout 依赖 `psutil`，镜像/宿主未预装 | test_package 侧按需安装 `psutil==5.9.5`（**必须精确固定**：本平台只有 5.9.5 提供 `ohos_aarch64` abi3 wheel，更新的 5.9.x 无 wheel 且 setup.py 直接 `platform ohos is not supported`）；装不上时不 raise，而是自动去掉 `--timeout` 并把实际命令记入标记的 `timeout_guard` 字段 |
| 6 | `lit` 中 `p2align.asm` 报 `'riscemu': command not found`（exit 127） | 该用例用裸 `riscemu` 命令（console script），而 lit 环境里 PATH 没有包自己的 `bin/` | `_child_env()` 把 `<pkg>/bin` 与 `dirname(sys.executable)` 置于 PATH 之前 |
| 7 | 「`filecheck` 已安装」的探针恒真，pip 安装被静默跳过，直到 lit 报 127 | `test_package/filecheck/` 目录满足 `import filecheck`（PEP 420 隐式命名空间包），而真正缺的是同名 CLI | CLI 依赖改用 PATH 探针 `shutil.which(name, path=env["PATH"])`，安装后复检并 raise |
| 8 | 上游 `riscemu.priv` 整块不可导入 | `priv/__main__.py` 的 `from riscemu import RunConfig` 在 `riscemu/__init__.py` 中不存在；`PrivCPU.py`/`ElfLoader.py` 用顶层绝对导入 `from core.*`（应为 `from ..core.*`）；2.2.7 与 master 同样如此 | **不打补丁**（保持与上游 tag 逐字节一致），在 `notes.md`/`manifest.yaml`/DRAFT E431 记录为不可用面；消费者测试回避 `riscemu.priv` |
| 9 | `pip install . --prefix=<stage>` 可能判定 `Requirement already satisfied` 而跳过，产物不自包含 | 构建机 `~/usr/local/lib/python3.12/site-packages` 已装部分同名依赖 | 一律加 `--ignore-installed`，强制整棵闭包解析进 staging 前缀；`build()` 内断言 riscemu / elftools / importlib_resources 三者均在 stage 中 |
| 10 | PR CI 构建超时（`TimeoutExpired ... riscemu ... fibs.asm -o libc` 卡满 300 s） | `fibs.asm` 以 `ebreak` 结尾，riscemu 会进入 `code.InteractiveConsole` 调试器**读 stdin 等输入**；测试脚本的 `subprocess.run` 继承了 worker 上「只开不放」的 stdin 管道（无数据、不 EOF）→ 挂起。lit 子套件不受影响，因为 lit 会把子进程 stdin 立即关闭（`lit/TestRunner.py`） | 消费者测试的 `run()` 统一 `stdin=subprocess.DEVNULL`（与 lit 同语义，确定性 EOF），超时上限 300 s → 120 s；用 `stdin=<(sleep 60)` 与 `sleep 240 \| ...` 两种「敌对 stdin」复现验证，52/52 断言 1.6 s 内完成 |
| 11 | worker 上 `pip install <tool>` 可能无写权限 | CI 的 python3 位于只读系统目录（`ci/conan/setup.sh` 自身也退化为 `pip install --user`） | 测试工具（pytest / lit / psutil / filecheck）改为安装到 `tempfile.mkdtemp()` 的临时 **prefix**（`pip install --prefix`），再把 `<prefix>/bin` 与 `<prefix>/lib/pythonX.Y/site-packages` 追加到子进程 PATH/PYTHONPATH；解释器目录零写入 |

## 源码修改

无补丁（`patches: {}` / `patches_applied: []`）。上游源码原样使用，
`build()` 只做 `pip install .`，不触碰源码文件。

`test_package/` 内为上游资产的**逐字节副本**（可 `cmp` 复核）：

- `test_package/tests/` ← 上游 `test/*.py`（9 个 `test_*.py` + `__init__.py`；
  顶层文件集合 sha256 `4cb5a6b7640a7ba84c0705b8a0af291c1f652c003151f14d8a33200f2ffb8325`，与上游相同）
- `test_package/filecheck/` ← 上游 `test/filecheck/`（`lit.cfg`、11 个用例、`libc/`、`snitch/`、`.gitignore`
  逐文件 `cmp` 相同）
- `test_package/snitch/` ← 上游 `snitch/`（sha256 `55e3da88…f4950c`，与上游相同；**不在 wheel 内**）
- `test_package/programs/` ← 上游 `examples/` 的 3 个样例汇编（`hello-world.asm`、
  `static-data.asm`、`fibs.asm`，逐字节相同），供消费者 CLI 端到端测试使用

唯一新增文件：`test_package/filecheck/lit.local.cfg`（平台 shim，见问题 3/4；上游 lit 用例零改动）。

## 依赖版本

配方不声明 `requires`（依赖未发布为 conan 配方），构建时由 pip 从
`https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple` 解析并打入包内 site-packages：

| 包 | 版本 | 说明 |
|----|------|------|
| riscemu | 2.2.7 | 本包（poetry-core 构建 wheel） |
| pyelftools | 0.30 | 上游运行时直接依赖（`^0.30`）；仅被不可导入的 `priv/ElfLoader` 使用 |
| importlib_resources | 6.5.2 | 上游运行时直接依赖（`^6.1.0`）；`riscemu_main.py:6` 顶层导入 |

test_package 侧额外需要（**不进产物**，仅测试期，缺失时装入临时 prefix）：
pytest（宿主已有 9.1.1；缺失时按 `pytest>=7.4,<8` 安装）/ lit 16.0.6 /
psutil 5.9.5（精确固定，见问题 5）/ filecheck 0.0.23。

## 验证结果

源码归档差异（决策依据）：PyPI sdist `riscemu-2.2.7.tar.gz` sha256
`9f206b195371cef4246a0d04cef6a439dc026396860c19a8850a761fd700c499` **不含 `test/`**；
GitHub 官方 tag archive（`v2.2.7`）sha256
`d9d4da9bb4449c3de3c691e01dba5d0e8e9048cd9f32db3eab6476ea326fbd0c` 含 `test/`，配方采用后者。

```bash
# 本地 conan create（profile ci/conan/profiles/ohos-aarch64，--build=missing）
$ conan create archives/r/riscemu/2.2.7 \
      -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
#   -> 见 reports/conan-create.log，test_package 全部通过

# 消费者断言（真实 API + CLI 端到端）
$ python3 test_package/test_riscemu.py <site-packages>
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "discovered": 52, "passedCount": 52}

# 上游 pytest 套件（逐字节副本，与上游 CI 同参 -W error）
$ python3 -m pytest test_package/tests -q --no-header -o addopts= -p no:cacheprovider -W error
49 passed in 0.10s
$ HMBS_UPSTREAM_SUITE_PYTEST={"status": "passed", "framework": "pytest", "discovered": 49, "executed": 49, "passed": 49, "failed": 0, "skipped": 0}

# 上游 lit/filecheck 套件（逐字节副本，与上游 CI 同参 --timeout=5 -v）
# （psutil 装不上时自动降级为无 --timeout，标记的 timeout_guard 记录实际情况）
$ lit --timeout=5 -v test_package/filecheck
-- Testing: 11 tests, 11 workers --
  Passed: 11
$ HMBS_UPSTREAM_SUITE_LIT={"status": "passed", "framework": "lit", "discovered": 11, "executed": 11, "passed": 11, "failed": 0, "skipped": 0}

# 聚合
$ HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "pytest+lit", "discovered": 60, "executed": 60, "passed": 60, "failed": 0, "skipped": 0, "suites": [...]}
```

上游测试 60/60（pytest 49 + lit 11）通过，消费者断言 52/52 通过，合计 **112/112（100%）**。

产物布局（`conan cache path riscemu/2.2.7:6b129b068851896169fae42d399fa922d239ce8a`）：

```
bin/{riscemu, readelf.py}
lib/python3.12/site-packages/{riscemu, elftools, importlib_resources,
                             riscemu-2.2.7.dist-info, pyelftools-0.30.dist-info,
                             importlib_resources-6.5.2.dist-info}   # 4.6 MB
```

### G0 等价的手工干净构建验证（无 `./configure`，纯 Python 包不适用 autotools G0）

本包无 `configure` 脚本，`ohc-run.py clean-verify`（G0）按 autotools 流程跑 `./configure`
会以 exit 127 结束，属**不适用**而非构建缺陷；此处用等价的手工干净验证替代，并放置
`.g0-manually-verified` 标记（同 `archives/g/gping/1.20.1-r0` 先例）：

```bash
# 从固定 sha256 的原始 tarball 解压到干净目录（无 patch、无缓存），新建空 venv
$ tar xzf riscemu-2.2.7.tar.gz --strip-components=1 -C g0-riscemu   # 132 个文件
$ python3 -m venv venv && ./venv/bin/python -m pip install --no-cache-dir .
$ ./venv/bin/python -c "import riscemu, riscemu.core, elftools; print(riscemu.__version__, elftools.__version__)"
2.2.7 0.30
$ ./venv/bin/riscemu ./examples/hello-world.asm
Hello world                     # RC=0
$ ./venv/bin/python -m pytest test -q -W error
49 passed

# 干净树直跑上游 lit（未加平台 shim）复现上游缺陷，反证 fibs.asm 的失败与平台无关：
$ PATH=venv/bin:$PATH ./venv/bin/lit --timeout=5 -v test/filecheck
  Passed: 10
  Failed:  1            # fibs.asm：lit 不转发 HOME -> 调试器写 history 抛 FileNotFoundError
```

对照：同一套 lit 用例在 `test_package/filecheck/`（含 `lit.local.cfg` shim）下 11/11 通过。

### 远端 CI 首次失败（PR #13868 / worker PR-check #64986）与修复

首次远端 CI 的 `conan-build-test` 在「消费者测试」阶段失败：

```
[FAIL] unexpected_exception:TimeoutExpired:Command
  ['...python3', '-m', 'riscemu', '-v', '.../test_package/filecheck/fibs.asm', '-o', 'libc']
  timed out after 300 seconds
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": false, "discovered": 43, "passedCount": 42}
```

根因：`fibs.asm` 末尾的 `ebreak` 会让 riscemu 进入交互式调试器（`riscemu/debug.py`
`launch_debug_session` → `code.InteractiveConsole(...).interact()`）并**从 stdin 读命令**。
本地复现与 CI 的差别只在 stdin：本地（终端/已关闭的 stdin）读到 EOF 立即返回，CI worker
上的 stdin 是一条「打开但不送数据、也不 EOF」的管道，于是 `subprocess.run` 继承 stdin 后
一直等到自身的 300 s 超时。上游 lit 套件不会踩到这一点，因为 lit 会在 spawn 后立刻
关闭子进程 stdin（`lit/TestRunner.py`：`if stdin == subprocess.PIPE: procs[-1].stdin.close()`），
子进程看到的就是即时 EOF。

修复（不改任何上游测试文件）：

1. `test_riscemu.py` 的 `run()` 统一 `stdin=subprocess.DEVNULL`（等价 lit 的关闭语义），
   单次超时 300 s → 120 s；
2. 顺带把测试工具安装从解释器目录改为临时 prefix（见问题 11），并把 psutil 精确固定为
   5.9.5、缺失时 lit 自动降级（见问题 5）——worker 的 python3 与本地一样是 `ohos` 平台，
   `psutil>=5.9,<6` 会解析到无 ohos wheel 的版本并在源码构建阶段失败。

验证方式（在**只缺工具**的干净 venv + 受限 PATH 下跑真实 `conan create`，触发全部回退分支）：

```
[test_package] test tool prefix: /storage/Users/currentUser/tmp/riscemu-testtools-rgbwc0vp
[test_package] installing test tool(s) into ...: pytest>=7.4,<8      -> 49 passed
[test_package] installing test tool(s) into ...: lit>=16,<17
[test_package] installing test tool(s) into ...: psutil==5.9.5
HMBS_UPSTREAM_SUITE_LIT={"status": "passed", ... "passed": 11, "timeout_guard": 5}
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "discovered": 52, "passedCount": 52}
```

（修复前的同一条命令会在 `psutil>=5.9,<6` 上复现 worker 同类失败：`platform ohos is not
supported`。）

## 注意事项

- 包不产出 `.so`，产物即 site-packages 目录树 + console script；消费方通过
  `runenv_info` 的 `PYTHONPATH`（及 `bin/` 的 PATH）引用。
- 已知不可用面：`riscemu.priv`（特权模式 + ELF 加载）不可导入，属上游缺陷，未打补丁；
  详见 DRAFT E431 与 `reports/test-report.md` 的「已知限制」。
- `test_package/filecheck/lit.local.cfg` 是唯一的平台新增文件，其余测试资产逐字节等于上游。
- `test_package/{conanbuild.sh, conanrun.sh, deactivate_*.sh, *env-*.sh}` 与
  `test_package/metadata/` 由 conan 就地生成，**不提交**（已随构建清理）。
---

**编译结束**: 2026-09-29 22:12
**最终状态**: built
