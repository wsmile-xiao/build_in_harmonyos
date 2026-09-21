# libvslvm 20240504 — HarmonyOS PC 适配笔记

> 任务：`feat/libvslvm-20240504`（积分赛，新增包）｜分支基线 `7a34c9f8e`（upstream/main）
> 编译器：clang 15.0.4（OHOS SDK，`/data/service/hnp/bin/clang`），目标 `aarch64-unknown-linux-gnu`
> Conan 2.29.1（OHOS 适配版）｜profile `ci/conan/profiles/ohos-aarch64`

## 1. 源码溯源

- 上游 GitHub：https://github.com/libyal/libvslvm
- 实测（2026-09-20）`git ls-remote --tags` 有 `refs/tags/20240504`（dc7f647）与
  `refs/tags/20260901`（80bbcdd）。
- 本任务版本取 **上游 release 资产** `libvslvm-experimental-20240504.tar.gz`
  （libyal 近年版本以 experimental 命名发行；release 资产为 autotools `make dist`
  产物，自带生成的 configure，无需 bootstrap）：
  `https://github.com/libyal/libvslvm/releases/download/20240504/libvslvm-experimental-20240504.tar.gz`
  sha256 `7217676f74ba145f9c2ba6b1c6296d7fa041c2ab2673d34dc06b53511aa65833`（本机下载实测）。
- 交叉参照：Debian 同版本源包 `libvslvm_20240504.orig.tar.gz` 存在于
  `https://deb.debian.org/debian/pool/main/libv/libvslvm/`（20240504-1 系二进制包亦在）。
- 对照排除：GitHub tag 自动归档 `archive/refs/tags/20240504.tar.gz` 也可达，但那是 git
  tree 快照（无生成的 configure），非上游发布物，不取。

## 2. 语言判定（R47）处置留痕

`lang-preflight` 对本包判 `detected_language=mixed` → 终态 `env_unsupported`，**判据不成立**：

- 命中 `manifest=python` 的 `pyproject.toml`/`setup.py` 是**可选 Python 绑定模块
  （`pyvslvm`）的打包元数据**（`pyproject.toml` 全文只有 3 行 `[build-system]`
  setuptools 后端声明；`setup.py` 首行注释即 "Script to build and install
  Python-bindings"；源码树内 `.py` 仅 3 个：`setup.py` 与 `tests/pyvslvm_test_*.py` 两个
  绑定测试脚本）。
- 工具自报源码统计 232 个文件中 `c:227`（98%），另有 351 个 `.h`；真实构建入口是发行包
  自带的 `configure`/`Makefile.am`（autotools），主体语言 **C**，与任务语言 cpp 属
  c↔cpp 兼容族；配方亦显式 `--disable-python`。
- 这是 libyal 家族第 5 次同形态误报（同 `libvsgpt 0-20240504` 已完成先例，其 readiness/
  notes 留痕为第 4 次）。编排中按 `--skip-step lang-preflight --start-note "<理由>"`
  记为**未执行**（不是通过），并另写 `feedback/pending/`。
- 该步已写出的 `env_unsupported` 终态落在共享 result 槽位
  （`$HOME/ohpcd-ai-worker-result.json`），任务成功后由同任务终态覆盖。

## 3. R6 声明（源文件改动）

- **不改上游任何 C/H 源文件、测试脚本与构建脚本**；无 `patches/` 文件。
- 唯一例外发生在 **OHOS 构建期（Conan 缓存副本上）**：把随包 `configure` 内 2 处
  `umask 077` 改写为 `umask 022`（HMDFS 必需，E011）。由配方 `_patch_hmdfs_umask()`
  完成，不进补丁、不进源码提交。

## 4. 适配决策（配方内联，依据 device-facts 与同族先例）

| # | 事项 | 处置 | 依据 |
|---|------|------|------|
| 1 | configure 的 `umask 077` | OHOS 构建期改 022，全程 umask 022 | E011；同族 libvsgpt 实测（0700 临时目录连创建者都不可写，config.guess 报 dummy.c Permission denied） |
| 2 | config.guess/config.sub 2023-06-23 不识别 OHOS | `--build/--host=aarch64-unknown-linux-gnu`（update_configure_args 替换语义） | 本版本 config.sub 同族实测拒绝 `linux-ohos`（libvsgpt 0-20240504 同年代同 timestamp）；配方写死前以设备实测为准 |
| 3 | HMDFS 上源码树脚本执行受限 | `CONFIG_SHELL=/data/service/hnp/bin/bash` 显式启动 configure；`SHELL` 同值 | 设备无 `/bin/bash`（§一.16）；解释器/CONFIG_SHELL/SHELL 三者钉同一绝对路径 |
| 4 | automake TESTS 是 bash 脚本 | `make check LOG_COMPILER="<bash>"` | 同上 |
| 5 | 测试程序读构建树内共享库 | `LD_LIBRARY_PATH` 前置 `libvslvm/.libs`（进程子树内，退出还原） | libtool RUNPATH 为 `//lib`，包内库在 `<pkg>/lib` |
| 6 | 并发超订（cpu_count=20 vs affinity=8） | `_jobs()` 缺省 2，可 `-c tools.build:jobs=N` 覆盖 | §一.7 |
| 7 | python 绑定 | `--disable-python`（pyvslvm 不在交付面） | 交付面收敛为 C 库 + 工具 |
| 8 | 零外部依赖 | 14 个 libyal 组件 standalone 内嵌（含 libbfio），W0 写 `none` | 发行包顶层目录实测 |

vslvmmount 的全部 fuse 代码在 `#if defined( HAVE_LIBFUSE )` 守卫内（vslvmtools/mount_fuse.h
与 vslvmmount.c 实读），无 libfuse 时按上游设计编译为"无挂载支持"形态；`bin_PROGRAMS` 无
条件含 vslvminfo/vslvmmount（vslvmtools/Makefile.am），两者均交付并在 commands.json 声明。

## 5. 原生探索与镜像探针（设备实测，2026-09-20）

- 脚本：`$TASK_DIR/native-probe.sh`（沙箱 HOME + 工作区 TMPDIR，tar 解包保 mtime）。
- configure rc=0（umask 补丁 2 处、`--build/--host=aarch64-unknown-linux-gnu`、
  `--disable-python`、`--enable-static-executables=no`；尾部确认 "Python (pyvslvm)
  support: no"、"vslvmtools are build as static executables: no"）。
- make -j2 rc=0；`vslvminfo -V` → `vslvminfo 20240504`、`vslvmmount -V` →
  `vslvmmount 20240504`（LD_LIBRARY_PATH 指向构建树 `libvslvm/.libs`）。
- make check（`LOG_COMPILER=/data/service/hnp/bin/bash`）rc=0：**TOTAL 3 / PASS 2 /
  SKIP 1**（SKIP = test_vslvminfo.sh，`Test input directory not found`，exit 77）。
- 消费者探针：test_libvslvm **21 项断言 0 失败**、test_ohos **31 项断言 0 失败**
  （合成 LVM2 镜像读回全链路；逐字输出 `$TASK_DIR/native-probe/out/`）。
- 探针期修正记录（均有 backtrace/取值证据）：标签须放扇区 1（check_volume_signature
  只读固定偏移 512）；元数据区头校验和在 +0（误写 +4 会覆盖签名前 4 字节）；raw
  location descriptor 的 offset 为元数据区相对偏移（解析器存 file_offset+offset）；
  元数据文本 id 须 38 字符连字符 UUID（identifier_size==39）；标签校验和须在扇区
  其余字段写完后计算；libvslvm 公共 API 返回值约定（initialize/getter=1、close=0、
  free=1、未打开 close=-1）；extent_size 按 ×512 存储。详见知识草稿 DRAFT-E593。

## 6. 上游测试清点（N）

`tests/Makefile.am` 两个 automake 注册面（与 libvsgpt 同构）：

| 注册面 | 数量 | 逐项 |
|---|---|---|
| `TESTS`（shell 入口） | 3 | test_library.sh、test_tools.sh、test_vslvminfo.sh |
| `check_PROGRAMS`（C 程序） | 20 | checksum、chunk_data、data_area_descriptor、error、handle、io_handle、logical_volume、logical_volume_values、metadata、metadata_area、notify、physical_volume、raw_location_descriptor、segment、stripe、support、tools_info_handle、tools_output、tools_signal、volume_group |
| **合计 N** | **23** | |

不计入：`TESTS` 的条件项 `test_python_module.sh`（`if HAVE_PYTHON_TESTS`，配方
`--disable-python` → 条件不成立）；`check_SCRIPTS` 的 8 个支撑脚本（含被 runner `source`
的 `test_runner.sh`）；各 C 程序内部断言数（另一计量单位）。

**下界核对（§三.27）**：上游当前 HEAD 的 `tests/Makefile.am` 注册数 = 本版本同构（20240504
为该仓库最新发布线之一），N=23 不低于上游 HEAD 注册数，无少报风险。

发布包不含 `tests/input/` 夹具（`tar tzf | grep -c "/input/"` = 0），预期 `test_vslvminfo.sh`
按上游规则 `exit 77` 记 SKIP；`test_library.sh` 的 `LIBRARY_TESTS_WITH_INPUT="handle support"`
在 `input/` 缺失时退化为无输入运行（脚本内 `if test -d "input"` 分支）。

## 7. 设备真实验证读数（W3 采信轮，2026-09-20）

- 采信轮：`tools/conan_verify_round.sh`（inode 预检过、Conan DB 两表清净、E017 镜像
  不可达自动走官方源），`conan create` 干净轮判读：构建标志计数
  `{'run_make': 10, 'calling_build': 2, 'apply_patch': 0}` → clean。
- 包引用 `libvslvm/20240504@ohpcd/stable`，包 ID `01d92cf349a0dd98ff915f4bd99a04430171517f`；
  安装树 `.conan2/p/b/libvsba47f2183e459/p`（bin/include/lib 齐）。
- 门禁：G0/G1/G2/G3/G4/L2/L4/L5 **全 PASS、实跑 4/4 无跳过**（G4：bin/ 2 文件、
  lib/ 3 .so、include/ 7 头文件；L2：vslvminfo/vslvmmount `-V` 实跑输出 20240504；
  L4：PIE=enabled、RELRO=full，NX/Canary 警告为上游默认参数、非阻塞；L5 首轮基线
  `reports/baseline.json`，19 个文件）。
- 上游测试（W3 日志逐字）：`PASS: test_library.sh` / `PASS: test_tools.sh` /
  `SKIP: test_vslvminfo.sh`，`# TOTAL: 3 / # PASS: 2 / # SKIP: 1 / # FAIL: 0`——
  与设备原生轮逐字一致；逐入口读数见 `reports/upstream-tests.md`。
- test_package（W3 内编译运行）：test_libvslvm 21 项断言 0 失败、test_ohos 31 项断言
  0 失败；vslvminfo/vslvmmount `-V | grep 20240504` 均 rc=0。
- 证据三副本（conan-create.log / conan-verify-report.md / w3-local-ci.log）于 finish
  前留存，sha256 见 `$TASK_DIR/evidence-index.json`。

## 8. 消费者测试设计（test_package，另计不混入上游 N）

- `test_libvslvm.c`：通用消费者断言——版本串（上游 20240504）、访问标志（只读库，read ==
  read_write）、codepage 正常/错误路径与 error_sprint、空白卷 check_volume_signature==0、
  handle 生命周期、无标签打开失败（错误对象文案含 metadata area descriptors）、缺文件打开失败。
- `test_ohos.c`：鸿蒙专项——`__OHOS__` 编译目标、TMPDIR 语义（存在/非 /tmp/可写）、在
  TMPDIR 下**合成合法 LVM2 物理卷镜像**（LABELONE 标签 + pv_header + 数据/元数据区描述符 +
  元数据区头 + raw location descriptor + LVM2 元数据文本：1 卷组/1 物理卷/1 线性逻辑卷，
  weak CRC-32 全部正确，初值 0xf597a6cf、无终 XOR——与 libvslvm_checksum.c 逐字一致），
  再用已安装库读回全链路：签名→打开→卷组（名/标识符/seqno/extent 大小）→物理卷
  （名/标识符/设备路径/数据与元数据区计数）→逻辑卷（名/标识符/段数）→段
  （offset=start_extent×extent_size、size=extent_count×extent_size）→条带（指向 pv0）。
  说明：逻辑卷**数据**读取路径（libvslvm_logical_volume_read_chunk_data）是内部 API
  （入参为 libfdata vector 内部对象），消费者不可达，故最深断言到条带元数据为止。
- `test()` 内另验安装后 `bin/vslvminfo -V`、`bin/vslvmmount -V` 加载共享库并输出版本串。

## 9. 后续

- 采信轮：`tools/conan_verify_round.sh`（rc=1 不进 finish；rc=3 可重试）。
- finish `built`（合并后 release upload 确认前不标 published）。
- 知识路径 B 草稿：见 `manifest.yaml` 的 `knowledge_gained`/`path_b` 与
  `knowledge/drafts/`（取号后回填）。
