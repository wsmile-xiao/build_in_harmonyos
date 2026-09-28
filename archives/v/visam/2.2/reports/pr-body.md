## PR 信息

- **三方库名称**：visam（V-ISAM，GnuCOBOL 的 ISAM 处理器 / libvisam）
- **上游版本**：2.2
- **上游仓库地址**：http://inglenet.com/gnucobol.html（官方发行包 http://inglenet.com/Products/GnuCOBOL/visam-2.2.tar.Z，sha256 `cdf4db8f5b6dedb4038ed4049d4e9990d321154021d3dc604ed6468ba112e1ec`，`tar.Z` / LZW）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E007（config.guess 无法识别 HarmonyOS 系统）、E434（VPATH 构建规避 in-tree copystamp）、E490（configure 前恢复 Autotools helper 执行位）、E429（草稿：bash + GNU cat 的 heredoc 失败导致 autoconf conftest 为空）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无单元测试框架（无 check 框架、无测试数据基准） |
| 集成测试 | 0 | `tests/Makefile.am` 只声明 `noinst_PROGRAMS = mvtest detest00 detest01 jvntest mvtest2`，**没有 `TESTS=` 也没有 `check_PROGRAMS`**，`make check` 只编译不执行——实测三个子目录均为 `make[1]: Nothing to be done for 'check'.`（`reports/03-make-check.log`） |
| 其他测试 | 5 | 上游真实测试入口是 `tests/` 下 5 个测试程序：detest00（多索引建库/写/顺序读）、detest01（第二索引定位顺序读）、mvtest（事务压测 isbegin/iscommit/isrollback）、mvtest2（非事务压测）、jvntest（多文件多索引，读 `TESTDATA`）；需手工运行 |
| **合计** | **5** | 注册用例数 **0**（清点证据见 `reports/03-make-check.log`、`reports/test-report.md` §1.1） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无 |
| 集成测试 | 0 | 不变 | 上游无注册用例 |
| 其他测试（上游 5 个测试程序） | 5 | 不变 | 5 个程序共 7 次调用全部 rc=0，未删改任何上游用例（`reports/04-*.log`） |
| 鸿蒙特有测试 | 3 | 新增 3 | `test_package/main.c` 消费者用例 3 条断言：`deccvdbl`/`dectodbl` 十进制往返精度（唯一需要 OHOS `ecvt(3)` 兼容垫片的调用链）、`iswrite` 写入 200 条、`isread(ISFIRST/ISNEXT)` 顺序读回 200 条 |
| **合计** | **8** | **+3** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 说明：2 个补丁只改 `build_aux/config.guess` 与 `build_aux/config.sub`（构建期平台三元组识别），
> **未触碰** `tests/` 下任何测试程序、`tests/TESTDATA` 或 `tests/Makefile.am`。
> 上游 5 个测试程序按原样编译并按原样运行。

> 补充（构建期选项，非测试改动）：配方按上游 `configure` 支持的方式启用
> `--enable-logging`（事务/日志 API 必需，默认 `woth_logging=no`）与
> `--enable-thread-safe --with-pthread`（详见「补充说明」问题 6），
> 属上游既有选项，未改上游任何测试用例语义。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无（自动化注册的）测试用例，适配后补全了测试（请在下方说明）
- [ ] **否**，上游已有测试用例覆盖

> - **补全的测试范围**：以消费者视角补全 3 条端到端断言，覆盖两条对 OHOS 适配最关键的路径——
>   ① `ecvt(3)` 兼容垫片（OHOS musl 缺该 glibc 扩展）；② ISAM 写/读主流程（静态库真实链接后可用）。
> - **补全原因**：上游 `make check` 的自动化注册用例数为 **0**（只有 `noinst_PROGRAMS`，无 `TESTS=`），
>   上游的 5 个测试程序是手工驱动的开发期程序（需在工作目录放置 `TESTDATA`、无预期输出基准、
>   不进 CI），无法作为包发布后的消费者回归；因此需要补全可自动执行的消费者用例。
> - **新增测试文件清单**：
>   1. `test_package/main.c` — 消费者断言主体（仅 include 公开头 `visam.h`，调用 `deccvdbl`/`dectodbl`/`iswrite`/`isread` 等公开 API，自带 `[PASS]/[FAIL]` 计数与汇总）
>   2. `test_package/conanfile.py` — `test()` 阶段编译并运行上述消费者程序（`RESULT: OK` 才通过）
>   3. `test_package/CMakeLists.txt` — 用 `CMakeToolchain` + `find_package` 消费已发布包
>   4. `test_package/MANIFEST.yml` — 上游测试清点证据与断言计数申报

## 验证结果

- 编译状态：**通过**（`conan create` 干净构建 rc=0；`conan-verify` G0–G4 全 PASS；独立 `clean-verify` 仅凭官方 tarball + 2 个补丁完成 configure → make → make install，安装产物 2 bin + 2 lib）
- 上游测试用例通过率：**7/7（100%）** —— 5 个上游测试程序共 7 次调用全部 rc=0（detest00 200 → 建库/写/读回 200；detest01 → 顺序读 39 条；mvtest create + 200 → 事务压测 OPS OVERALL 5135；mvtest2 create + 200 → OPS OVERALL 5314；jvntest 5）
- 新增测试用例通过率：**3/3（100%）**（`conan create` 与 `conan-verify` 两次独立执行确认，输出 `RESULT: OK`）
- W3 本地 CI 模拟（与平台 CI 同脚本）：`G0 pass / KC pass / JC pass（涉及软件数 1，Junk Files 0）/ L0 pass / L1 pass / L2 pass / L5 pass`，`L4 warn`（非阻断），Pass rate 100%（`reports/w3-local-ci.log`）
- 产物：`lib/libvisam.a`（静态，已并入 ecvt 垫片，20 个成员）、`bin/vcheck`、`bin/vrecover`、`include/visam.h`、`include/vdecimal.h`、`include/visam_rename.h`

## 补充说明

**适配方式**：3 个补丁，均只改 Autotools 构建脚本的平台/权限适配，**不改任何 C 源码、不注入 `__OHOS__`/`-D__OHOS__`**：

1. `patches/0001-build_aux-config.guess.patch` — 上游 `config.guess`（2020-04-26）无 HarmonyOS 分支，设备 `uname -s` 为 `HarmonyOS` 时 configure 直接 `cannot guess build type`（E007）。补丁新增 `*:HarmonyOS:*:*` 分支，并修正确认返回约定（该版必须 `echo "$GUESS"; exit`，只赋值会穿透到兜底通道继续报错）。
2. `patches/0002-build_aux-config.sub.patch` — 上游 `config.sub`（2020-05-04）不认 `ohos`，补三处：KERNEL-OS 识别表、OS 类型白名单、`linux-ohos)` 归一化分支（缺第三处会被 `linux*)` 改写成 `linux-gnu-ohos`）。
3. `patches/0003-configure.patch` — configure 内生成 config.status 的临时目录创建两处 `umask 077` → `umask 022`（E136/E129/E112）。CI worker 上 HMDFS 对 umask 077 新建目录强制 setgid，导致 config.status 无法写入 `./confXXXXXX/subs1.awk` 而报 `could not setup config files machinery`；本机 `/storage` 直挂不复现（实测该目录为 `drwxrws--x` 且可写），属 CI worker/真机环境特定。与已合入的 `a52dec/0.7.4`、`teseq/1.1.1`、`vttest/2.7-20251205` 同款补丁。

**关键适配点（10 类问题，逐条记于 `notes.md`）**：

| # | 问题 | 根因 | 处理 |
|---|------|------|------|
| 3 | `source directory already configured` | 官方 tar 是作者机器上的工作副本（含 `config.status`/`config.h`/`Makefile`/`stamp-h1`/`.deps` 与 9 个无关 core dump） | `build()` 先 `make distclean` 并兜底清理残留（E434） |
| 4 | `undefined reference due to --no-allow-shlib-undefined: ecvt` | OHOS musl libc 不提供 glibc 扩展 `ecvt()`，`libvisam/isdecimal.c` 依赖它做 double→十进制串转换 | 配方自带 `ohos-ecvt-shim.c/.h`（glibc 语义等价：`%.*e` 舍入 + decpt/sign）；编译期 `-include` 声明消除隐式声明告警，经 `extra_ldflags` 注入并在安装时 `ar r` 并入 `libvisam.a` 使其自包含 |
| 5 | `islogopen` 返回 `ENOLOG=128` | `--enable-logging` 默认关闭（`configure.ac` 默认 `woth_logging=no`） | 配方加 `--enable-logging` |
| 6 | `mvtest` SIGSEGV（rc=139） | 在库内 20 个关键函数插桩定位到 `vtranshdr`：非 pthread 分支下 `VB_GET_RTD` 展开为 `&vb_rtd_data`，`vb_get_rtd()`/`vb_init_rtd()` 永不执行（`vb_init_rtd` 唯一调用点在 `vb_get_rtd` 内），`cvbtransbuffer` 恒为 NULL，写事务头时空指针解引用 | 用上游既有选项 `--enable-thread-safe --with-pthread` 走到 `HAVE_PTHREAD_H` 分支；**无需改上游源码** |
| 9 | `make install` 报 `build_aux/install-sh: can't execute: Permission denied`（exit 2），G0 干净构建验证失败 | 官方 `tar.Z` 里 `build_aux/*` 全为 0644（补丁与 tar 均无法设置权限位），而 autoconf 的 `MKDIR_P` 探测**只接受 GNU coreutils 版 mkdir**，非 GNU 环境回退 `build_aux/install-sh -c -d` 撞上无执行位 | 按 E490（`rec_impl: conan-recipe`）在 `build()` 首步 `_restore_autotools_modes()` 恢复 `configure`/`config.guess`/`config.sub`/`install-sh`/`missing`/`depcomp`/`compile` 为 0755 |
| 10 | **CI worker**：`config.status` 报 `./confXXXXXX/subs1.awk: Permission denied` → `could not setup config files machinery`，conan create 53s 失败（本机不复现） | autoconf 生成的 config.status 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录；HMDFS 对 umask 077 新建目录强制 setgid，owner 也无法写入（E136/E129/E112） | `patches/0003-configure.patch` 两处 `umask 077` → `022`（teseq/vttest/a52dec 同款先例） |

**构建依赖**：无外部库依赖（源码 `#include` 全量清点仅标准头与本库内部头；W0 预检 `ci/scripts/preflight_check.sh visam/2.2` 输出「无依赖需要检查」）。

**静态库说明**：本包与仓库主流一致构建为静态库（`--disable-shared --enable-static`）。OHOS 上普通可执行文件无法通过 `DT_NEEDED` 加载用户自建共享库（实测连新编的最小 `libfoo.so.1` 同样失败，属平台限制，与 visam 无关）；上游测试程序与消费者用例均静态链接，真实可跑。

**源码 URL 说明（PF7 例外）**：上游唯一官方发行地址为 `http://inglenet.com/Products/GnuCOBOL/visam-2.2.tar.Z`，该站点**无 HTTPS 监听、无 GitHub 镜像**，因此 `conandata.yml`/`manifest.yaml` 中的官方源为明文 http（R39 官方托管例外）。CI 的镜像 fallback 机制不受影响。

**已知限制**：上游 `make check` 注册用例数为 0（`noinst_PROGRAMS` 而非 `TESTS=`/`check_PROGRAMS`），平台 CI 的 `make check` 同样不执行用例；本包的上游测试验证以 5 个测试程序手工实跑 + 消费者用例自动执行共同构成，证据见 `reports/test-report.md` 与 `reports/04-*.log`。

**门禁余项说明（已核验非本包问题，本 PR 不做越权修改）**：`finish` 的 W5 知识图谱完整性检查（step5b）会报告

```
⚠️ 字段缺失: E219.kv: root_cause 为空 / E253.kv: root_cause 为空
            E305.kv: root_cause 为空 / E305.kv: rec_approach 为空
```

经逐条核验，这三条（E219=python/CI、E253=OCaml、E305=字体数据包）**均为其他软件的既有条目**，
且其字段正文**实际存在**（分别 5 / 10 / 4 行正文），只是写法使用 YAML 块标量 `root_cause: |`，
而校验脚本 `scripts/ohc/workflow_checks.py` 的朴素解析 `re.match(r"^(\w+):\s*(.*)")` 会把 `|`
当作空值（`val == "|"`）判定；全仓 541 条知识条目中仅这 3 条使用块标量写法。该缺陷位于框架侧
（`scripts/`），与本包的配方、补丁、测试均无关。

按「不改动他人资产、不越权改框架」的协作约束，本 PR **不包含** `knowledge/graph/` 下任何条目，
也不修改 `scripts/`；已验证的等值改写方案（块标量 → 双引号标量，值与原文逐字节相等，可令该探针
转绿）仅供框架侧修复时参考。
