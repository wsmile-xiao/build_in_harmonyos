# libvhdi 20251119 适配笔记

## 当前状态

- 状态：built（`conan create` 干净轮通过；制品尚未上传）
- 分支：`feat/libvhdi-20251119`
- worktree：`/storage/Users/currentUser/ws/worktrees/libvhdi-20251119`
- 主检出未切换分支；未推 fork `main`
- 真机：OHOS aarch64（HarmonyOS，HongMeng Kernel 1.12.0），设备单端完成构建与测试

## 编译环境

- 构建系统：Autotools（发布包自带 `configure`/`aclocal.m4`/`config.guess`/`config.sub`/`Makefile.in`，**不需要** autoreconf）
- 编译器：`clang` / `clang++`（OHOS SDK，`/data/service/hnp/bin/clang`）
- 目标：`os=OHOS`、`arch=armv8`、`compiler=clang 15`、`build_type=Release`（`ci/conan/profiles/ohos-aarch64`）
- 环境变量：`CONFIG_SHELL=/data/service/hnp/bin/bash`、`SHELL=/data/service/hnp/bin/bash`
- 上游测试的 `HOME` 指向构建目录内的一次性目录，不触碰操作者真实 `HOME`

## W0 依赖检查

上游 `configure.ac` 把 13 个同族 libyal 组件作为**本地**组件参与构建：

`libcerror libcthreads libcdata libclocale libcnotify libcsplit libuna libcfile
libcpath libbfio libfcache libfdata libfguid`

这 13 个目录随发布包一起提供，以 libtool `noinst_LTLIBRARIES` 形式静态并入
`libvhdi`，**不需要**独立的 Conan 包。制品仓中也无对应 recipe，按「一库一分支」
约束不在本 PR 混入依赖适配。

可选能力：

- `libfuse`：仅 `vhdimount` 挂载用，显式关闭（`--with-libfuse=no`），因此不构成依赖；
- Python 绑定（pyvhdi）：显式关闭（`--disable-python`）。

外部编译依赖：无（`requires` 为空）。

## W1 源码与构建系统

- 上游项目：`https://github.com/libyal/libvhdi`
- 目标版本：`20251119`
- 上游 tag：`20251119` → commit `2c1ce1a8fd2fd62049579d0bfaf5ac1a3eff1429`（2025-11-19T14:50:55Z）
- 上游 release 资产：`libvhdi-alpha-20251119.tar.gz`（注意同族 libfsntfs 是
  `-experimental-` 前缀，资产名不能从版本号或同族包推断）
- 实际使用的源码：Debian orig 镜像
  `https://deb.debian.org/debian/pool/main/libv/libvhdi/libvhdi_20251119.orig.tar.gz`
  - SHA256：`026cc41e506bef433999090a777519a3cb471510dc352fa44d6867cf6a0e7990`
  - 设备网络无法连接 github.com:443（release 资产下载超时），GitHub API 可达

### 发布包身份核验（镜像 ↔ 上游提交）

通过 GitHub contents API（`Accept: application/vnd.github.raw`，`ref=<commit>`）
逐字节比对 11 个关键源文件与上游 tag 提交，结果全部 **IDENTICAL**：

| 文件 | 结果 |
|---|---|
| `configure.ac` | IDENTICAL |
| `Makefile.am` | IDENTICAL |
| `libvhdi/Makefile.am` | IDENTICAL |
| `include/libvhdi.h.in` | IDENTICAL |
| `tests/Makefile.am` | IDENTICAL |
| `libvhdi/libvhdi_file.c` | IDENTICAL |
| `libvhdi/libvhdi_support.c` | IDENTICAL |
| `libvhdi/libvhdi_file_footer.c` | IDENTICAL |
| `vhditools/Makefile.am` | IDENTICAL |
| `README` | IDENTICAL |
| `include/libvhdi/definitions.h.in` | IDENTICAL |

未做「上游 release 资产 ↔ Debian orig 整包」逐字节比对：设备网络不可达
`github.com:443`（release 资产下载超时）。已比对的是发布包中承担构建与 API 契约的
关键文件（含两个最核心的库实现文件）。

证据副本：`$TASK_DIR/upstream-check/`（含原始抓取文件与说明）。

### 闭包审计（配方在 build() 早期强制）

tarball 内同时具备：

1. 13 个本地 libyal 组件目录（见 W0）；
2. 生成好的 Autotools 文件：`configure`、`aclocal.m4`、`config.guess`、
   `config.sub`、`Makefile.in`。

配方在 `build()` 开头逐项 `isdir`/`isfile` 检查，任一缺失立即以
`ConanInvalidConfiguration` 报「源包非自包含」，不调用未锁定的 `synclibs.sh`，
也不静默 bootstrap。

## 配方设计

`archives/l/libvhdi/20251119/conanfile.py`：

- `source()`：`get(..., filename="libvhdi_20251119.orig.tar.gz", strip_root=True, **conandata["sources"])`
  —— 显式文件名，避免 Conan 从 URL 推断格式失败（BadZipFile 类问题）；
- `generate()`：`AutotoolsToolchain` + `--disable-python`/`--with-libfuse=no`/
  `--enable-static-executables=no`；OHOS 下显式加
  `--build/--host=aarch64-unknown-linux-ohos`（`shared`/`fPIC` 的
  `--enable-shared/--disable-static` 由 `AutotoolsToolchain` 依据 `shared` 选项自动生成，
  配方不重复添加）；
- `build()`（OHOS）：
  1. 闭包检查；
  2. `umask 022`，把 `configure` 中 `umask 077` 改为 `umask 022` 并 `chmod 755`；
  3. 用 `CONFIG_SHELL` 显式执行 `configure`（HMDFS 禁止直接执行源码树脚本）；
  4. `make -j4`；
  5. 给 `tests/test_runner.sh` 打运行期适配（libtool 包装脚本 → `.libs/<name>`），
     注入 `libvhdi/.libs` 的 `LD_LIBRARY_PATH`；
  6. `make -j1 check LOG_COMPILER="$CONFIG_SHELL"`（让 automake 用 bash 启动 runner）；
  7. 上游测试的 `HOME` 指向 `build_folder/upstream-test-home`。

  Linux 分支走 `autotools.configure()` + `make -j1 check`（非 OHOS 路径不引入
  HMDFS 适配）。
- `package()`：`make install DESTDIR=<package_folder>`，并安装 `COPYING`、
  `COPYING.LESSER`。
- `package_info()`：`libs = ["vhdi"]`，并设置 `cmake_file_name`/`cmake_target_name`/
  `pkg_config_name`。

> **测试运行适配 vs 上游测试用例修改**：对 `tests/test_runner.sh` 的改动只是让
> libtool 包装脚本解析到真实 ELF、并让 automake 用 bash 跑 runner；**没有任何**
> 上游测试用例（`tests/vhdi_test_*.c`、`tests/*.sh` 的断言与逻辑）被修改。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 报 `cannot guess build type` / 识别不出主机 | 发布包自带 `config.guess`（2024-07-27）不识别 `uname -s = HarmonyOS` | 显式传 `--build/--host=aarch64-unknown-linux-ohos`（自带 `config.sub` 接受该三元组） |
| 2 | Autoconf 临时目录 `Permission denied` | HMDFS 不保存 other 位，`umask 077` 落盘目录不可写 | 构建期把 `configure` 的 `umask 077` 改成 `022`，全程 `umask 022` |
| 3 | 直接执行源码树脚本失败 | HMDFS 禁止直接 exec 源码树脚本 | `CONFIG_SHELL` 显式解释 `configure`；`make check` 传 `LOG_COMPILER` |
| 4 | runner 报 `Invalid test executable`（libtool 包装脚本） | `check_PROGRAMS` 产物是 libtool 包装脚本，真实 ELF 在 `.libs/` | 构建期给 `test_runner.sh` 加 `.libs/<name>` 解析并注入 `LD_LIBRARY_PATH` |
| 5 | `test_vhdiinfo.sh` SKIP | 发布包不含 `input/` 测试夹具，runner 按上游规则退出 77 | 如实记录为 SKIP（上游能力边界），不伪造成 PASS |
| 6 | 消费者正向签名断言初次失败 | `libvhdi_check_file_signature` 仅在 `file_size > 512` 时探测；512 字节夹具被跳过 | 夹具改为 1024 字节、`conectix` 写在 offset 512（末段 512 字节块首） |

## 上游测试三步法（R51）

**清点**：`tests/Makefile.am` 的 `check_PROGRAMS` 注册 26 个 C 测试程序；
automake `TESTS` 注册 3 个 shell runner（`test_library.sh`、`test_tools.sh`、
`test_vhdiinfo.sh`）。

**实跑**（干净轮 `conan create` 的 `build()` 内 `make check`）：

| runner | 程序数 | PASS | FAIL | SKIP | 逐字证据 |
|---|---|---|---|---|---|
| `test_library.sh` | 23 | 23 | 0 | 0 | 21 个 library 程序 + `file`/`support`（无 `input/` 时按 runner 规则无参数真实执行） |
| `test_tools.sh` | 3 | 3 | 0 | 0 | `info_handle`/`output`/`signal` |
| `test_vhdiinfo.sh` | 1（runner 级） | 0 | 0 | 1 | `Test input directory not found.` → exit 77 |

automake 汇总：`# TOTAL: 3 / # PASS: 2 / # SKIP: 1 / # FAIL: 0 / # ERROR: 0`。

**口径**：N 取候选最大值 = **26**（程序级，全部真实执行且通过）；runner 级 3 个
单列；`test_vhdiinfo.sh` 的 SKIP 是发布包不含 `input/` 夹具的能力边界，
**不计入** 26 的分子分母，单列为 NOT_RUN。

- 上游程序级：N = 26，N′ = 26，PASS 26 / FAIL 0 / SKIP 0
- 上游 runner 级：TOTAL 3，PASS 2，SKIP 1，FAIL 0

**消费者测试**（`test_package`，`conan create` 自动执行）：

- 通用消费者断言 11/11 PASS；
- 鸿蒙专项断言 6/6 PASS（`__OHOS__` 编译目标、可写 `TMPDIR`、临时文件
  创建/写入/读回/清理、1024 字节合成 VHD footer 的正向签名识别）。
  `TMPDIR` 一项按宿主条件判定：设备 `/tmp` 只读时必须提供可写的非 `/tmp` `TMPDIR`
  （计 1 条断言）；宿主 `/tmp` 可写时该条件不存在，按 `SKIP` 记录、**不计为通过**
  （与已合入的 `archives/c/cronic/3/test_package/test_cronic_ohos.sh` OHOS-6 同口径）。

## 知识增量评估（路径 B 未申报）

| 本轮可迁移做法 | 知识库既有条目 | 结论 |
|---|---|---|
| 运行时合成最小合法夹具替代缺失/不可用夹具 | `E554`（madplay 无声卡：程序化生成确定性音频 fixture + 文件 sink 校验） | 高度重叠 |
| libyal 多组件发布包闭包审计、镜像回退、测试能力分层 | `DRAFT-libfsntfs-release-archive-closure`（17 组件同名方法） | 重复 |
| autotools 交叉三元组 / HMDFS umask / libtool `.libs` | `E007` / `E011` / `E087` / `E330` | 已收录 |
| release 资产名（alpha vs experimental）不可推断 | 与 `DRAFT-opencsg-1.8.2-upstream-tag-name-vs-version-archive-selection` 主题相邻 | 不足以独立成条 |

因此本 PR **不携带 `knowledge/drafts/**` 草稿**，标题按任务来源取 `【积分赛】`
（不写 `【知识库扩展】`）。若维护方认为「把上游因缺夹具而 SKIP 的格式探测正向路径，
在消费者测试中用运行时合成的最小合法夹具补上」值得独立成条，可在后续任务中提升。

## 遗留风险与未运行项

- `vhdimount` 构建但不具备挂载能力（`--with-libfuse=no`），未做挂载验证；
- `test_vhdiinfo.sh` 端到端 runner 未运行（无 `input/` 夹具）；vhdiinfo 的真实镜像解析
  改由 `reports/conan-verify-supplement.md` 的合成 VHD 固定盘人工补测覆盖；
- pyvhdi Python 绑定未构建、未测试（显式关闭）；
- `vhdimount`/`vhdiinfo` 未做 ELF 签名（sign）验证之外的运行验证由 CI L2 smoke 承担。
