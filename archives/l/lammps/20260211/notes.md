# lammps/20260211 适配笔记

任务号 8011，档位【中】，适配路径 **A**（本包不申请路径 B/C，见文末判定）。

## 交付声明（3+2 行最小口径）

- 适配路径：路径 A（直接适配，stock CMake 默认包集 + 显式关闭外部依赖/加速后端；未申请路径 C）。
- 使用知识库：复用三条既有家法——OHOS 平台识别 `CMAKE_SYSTEM_NAME=Linux`（先例
  `archives/a/afmize/2.0.2`）、非根工程根 `build_script_folder="cmake"`（先例
  `archives/a/alfa/2.2/conanfile.py:98`、`archives/a/azure-identity-cpp/1.13.3/conanfile.py:83`）、
  关构建期下载与测试面（`DOWNLOAD_POTENTIALS`/`ENABLE_TESTING` 族）；`recipe-search lammps`
  在 6173 条语料中零同族先例。
- 知识库扩展：DRAFT-lammps-20260211-k0-help-version-wrapper-entry（判定 = create：新增 K0 包装入口机制，见「K0 包装入口」小节；复用族查重与命中数仍见文末「路径 B 查重」小节；
  本 PR 对 `knowledge/` 的改动文件数为 0）。
- 关联 Issue：无需（B=hit 不建【知识库扩展】Issue；未申请路径 C 故无【高难度挑战】Issue）。

## 源码

- 官方 tag `patch_11Feb2026`（注意：`release_11Feb2026` 这个 tag 不存在，codeload 404）。
- URL（**本窗 09-24 15:16 起为提交态**）：`https://codeload.github.com/lammps/lammps/tar.gz/refs/tags/patch_11Feb2026` + 显式 `filename: lammps-patch_11Feb2026.tar.gz`。
  此前写的是 `https://github.com/lammps/lammps/archive/refs/tags/patch_11Feb2026.tar.gz`（同一份 tar、同一 sha256）。改走 codeload 的依据：框架 E017 注入的 `ghfast.top` 镜像已失效，而 B 机 13:5x 实测 `github.com/...archive/...` 直连 `code=000`；仓内定案见 `经验文档/经验库/09-11-测试与PR.md`（约 101 行，#41834 实证 + 156+ 已合并配方同策略，无后缀 URL 必须显式 `filename`）。⇒ `conanfile.py` 的 `source()` 同步扩成透传 `("url","sha256","filename")`，否则 `filename` 被静默丢弃＝等于没换。**sha256 逐字未改**；换后 G2/G3/conan-verify/W3 全绿（15:39 轮 `exit_code=0`；最终轮收尾读数以文末两行与「收尾时间线与订正」为准）。软件级与版本级 `manifest.yaml` 的 `source.url`/`filename` 已同步。
- 大小 159,775,060 字节；sha256 `b9ba0e368ee5af93f038b913e09a02b777a365ac6aea141842ded9b98b1efa8e`。
- sha256 同值处＝**两处**：`conandata.yml` 与版本级 `manifest.yaml`；软件级
  `archives/l/lammps/manifest.yaml` 按 `afmize/2.0.2` 先例不记 sha（只记 version/path/status/
  build_system/language/artifacts/tests），不要为凑"三处同值"去给它补哈希字段。
- 归档内不残留任何镜像域、`file://` 或本地路径（提交态已按 `git show HEAD:` 逐字核过）。
  ⚠ 但要记录一件事：W3 的预下载步骤会在**运行期**把 `conandata.yml` 改写成镜像列表
  形态，历史上其 `trap` 还原点晚于镜像改写（`ci/conan/build_and_test.sh:1179`），落盘态**仍是列表形态**，日志里"已还原为官方 URL"字面不准确。
  ⇒ **工作区脏的 conandata.yml 绝不能进提交**（PF7/R39 黑名单），本包每次提交前都用
  `git show HEAD:` 复核。15:39 轮（取源已改 codeload）实测活文件回到标量形态（`grep -Ec "ghfast|gh-proxy|mirror|file://"` = **0**）。⚠ 订正（审计 r3）：早稿所称「框架自行清掉了陈旧的 `conandata.yml.ghfast-bak`」不成立——盘上该文件仍在（另有 09:32 的 `conandata.yml.orig`，换源前内容），二者均被忽略规则覆盖、不会进 PR。该现象依赖镜像当时的可用性，**不作为可复现前提**——判据仍是逐次 `git show HEAD:` 复核。

## 本包关键适配点

1. **CMake 工程根不在源码根**：该 tag 的归档根目录没有 `CMakeLists.txt`，工程根是
   `cmake/CMakeLists.txt`（`project(lammps ...)`，并用
   `get_filename_component(LAMMPS_DIR ${CMAKE_CURRENT_SOURCE_DIR}/.. ABSOLUTE)` 回指源码根）。
   配方因此用 `cmake.configure(build_script_folder="cmake")`，构建目录保持在源码根
   （`cmake/Modules/PreventInSourceBuilds.cmake` 禁止 in-source）。
2. **不需要 MPI**：`cmake/CMakeLists.txt` 里 `BUILD_MPI` 默认取 `${MPI_FOUND}`，
   本机无 MPI ⇒ 走 `else()` 分支编译内部 `mpi_stubs` 目标（`install(TARGETS mpi_stubs ...)`）。
   为可复现性显式 `-DBUILD_MPI=OFF`，不引 openmpi 依赖（避免撞 PF4/依赖未发布）。
3. **构建期下载默认开启**：`DOWNLOAD_POTENTIALS` 默认 ON，会从
   `https://download.lammps.org/potentials` 拉大电势文件 ⇒ 显式 OFF，
   保证 CI 干净环境可复现。（此处原还写了 `DOWNLOAD_PKGFILES=OFF`，但本 release
   源码树**无此开关**，已随下方核对记录一并删除——留在这里会让审查员以为存在第二个下载面。）
4. **OHOS 平台识别**：沿用已入库的正解（afmize/2.0.2 同族做法）
   `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`，
   不注入任何 `__OHOS__` 宏（PF5 干净），不打任何源码补丁（`patches: {}`）。
5. **静态库**：`BUILD_SHARED_LIBS` 本版本默认即 OFF，仍显式写明；产物只有 `bin/lmp`
   可执行 + 静态 `liblammps`，不污染系统 `/lib`（R26）。
6. `-j1`：`cmake.build(cli_args=["--parallel","1"], build_tool_args=["-j1"])`（R9/设备内存纪律）。

## 包集收缩口径（不隐瞒）

LAMMPS 的 CMake 构建**默认不启用任何 `PKG_*`**（`cmake/CMakeLists.txt` 的
`foreach(PKG_WITH_INCL GRAPHICS KSPACE PYTHON ...)` 只在 `PKG_<X>` 为真时才
`include(Packages/<X>)`），即 stock 默认集合 = base styles（含 `lj/cut`、`atomic`、
`nve`、`bin` 邻居，正好覆盖 `bench/in.lj`）。本配方在该默认之上**显式**关闭了 29 个
需要外部库/下载/加速后端的包：

GPU、KOKKOS、OPENMP、INTEL、MOLFILE、NETCDF、VTK、H5MD、ADIOS、KIM、
COMPRESS、GRAPHICS、PYTHON、MDI、PLUMED、QMMM、SCAFACOS、MACHDYN、MBX、COLVARS、
LEPTON、ML-IAP、ML-HDNNP、ML-PACE、ML-QUIP、VORONOI、KSPACE、EXTRA-COMMAND、DPD-SMOOTH。

> **开关名逐个核对（09-24 主理-24）**：上面这张清单不是照抄文档，而是逐个对上游定义面核过的——方法：`os.walk` 排除 `build/` 后，把 `cmake/CMakeLists.txt` 里 `set(STANDARD_PACKAGES ...)`/`set(SUFFIX_PACKAGES ...)` 两个池（87 + 6，并集 93 个）取出来当判据，因为上游是 `option(PKG_${PKG} ...)` **动态构造**，直接 grep `PKG_<名字>` 会把不存在的名也判成存在。结果：**29/30 命中，2 个幻影已删除** —— `PKG_USER-INTEL`（本 release 无此包，真名 `INTEL` 且已在列）与 `DOWNLOAD_PKGFILES`（全树无 `option()`/`set()`/`${}` 引用）。其余普通开关（`BUILD_MPI`/`BUILD_OMP`/`BUILD_SHARED_LIBS`/`BUILD_TOOLS`/`BUILD_LAMMPS_GUI`/`WITH_SWIG`/`LAMMPS_INSTALL_RPATH`/`DOWNLOAD_POTENTIALS`/`USE_INTERNAL_LINALG`/`CMAKE_EXPORT_COMPILE_COMMANDS`）逐个核过均真实定义。⚠ 因删的是构建期传入的 cache 变量，属**改构建逻辑**，故本轮之后重跑了 `finish`（含 G2 `conan create` 与 W3 本地 CI 模拟），未沿用旧绿灯。
另关闭 `BUILD_TOOLS`（msi2lmp 等辅助工具）、`BUILD_LAMMPS_GUI`、`WITH_SWIG`、
`BUILD_OMP`（OHOS clang 的 OpenMP 运行时未证）、`BUILD_MPI`。
⇒ 这是**默认配置 + 显式关闭外部依赖项**，不是"缩到最小可跑集"意义上的裁剪；
base 包集未删任何一项。若要开 MANYBODY/MOLECULE 等纯内部包，只需加 `-D PKG_X=ON`。

## R51 上游测试三数（注册 / 实跑 / 通过）

- 注册面（全树 `CMakeLists.txt` 85 个）：`add_test(` / `create_test_sandbox(` /
  `lammps_add_test(` 注册调用 **127 处**；其中 `unittest/` 子树 **106 处**、vendored `lib/kokkos/**` **21 处**
  （formats 24、fortran 15、utils 13、commands 12、force-styles 12、c-library 11、
  python 10、cplusplus 5、根 4）。统计口径 = 解包后全树 CMakeLists.txt-only 裸 grep（与 manifest R51 注与审计 r3/r4 复算一致；旧 python 遍历脚本漏计 kokkos 的 9 处，2026-09-25 订正弃用）（HMDFS readdir
  负缓存会漏目录，toybox ls 的数不可信）。
- 本归档构建内实跑的上游用例：**3**（见下"实跑明细"），通过 **3**。
- 上游 gtest/ctest 树**未构建未运行**，具体技术原因（逐条带判定行，非"没环境"）：
  1. `unittest/CMakeLists.txt:13` 定义
     `GTEST_URL = https://github.com/google/googletest/releases/download/v1.17.0/googletest-1.17.0.tar.gz`，
     `unittest/CMakeLists.txt:25` 用 `ExternalCMakeProject(googletest ${GTEST_URL} ...)`
     在 **configure 期**下载并二次构建 gtest/gmock ⇒ 构建期联网，违反 CI 干净复现
     （与本包 `DOWNLOAD_POTENTIALS=OFF` 同一口径），且会把 googletest 变成第二个 sha256 源；
  2. `unittest/fortran/CMakeLists.txt:14` `enable_language(Fortran)`（15 个注册项）
     ⇒ 设备工具链只有 clang/clang++，无 Fortran 编译器；
  3. `unittest/python/`（10 个）与 `PKG_PYTHON` 绑定需要 target python 解释器 + SWIG；
  4. `cmake/Modules/Testing.cmake:4` `option(ENABLE_TESTING "Enable testing" OFF)`
     默认关；开启则 `cmake/Modules/Testing.cmake:69` `enable_testing()` +
     `:72` `add_subdirectory(${LAMMPS_UNITTEST_DIR} ...)`，约 106 个 tester 可执行文件
     全部要链接 `liblammps.a`，`-j1` 下单机耗时远超 W3 3600s 预算。
  ⇒ 申报口径只写"注册 127（unittest/ 106 + vendored kokkos 21）、实跑 5（上游 3 + K0 包装入口 2）、通过 5"，**不把未跑项写成通过**。
- 实跑明细（test_package 内，均套 `timeout(1)`）：
  1. `lmp -in in.lj -log log.lammps -screen none`（上游 `bench/in.lj` 原文件，100 步）；
  2. `lmp -h`（CLI 面：usage 含 `-in`，banner 含 `11 Feb 2026`）；
  3. `lmp -version` ⇒ **本 build 不支持该选项**，上游以 rc=1 报
     `ERROR: Invalid command-line argument: -version (src/lammps.cpp:490)`；
     测试据此把它做成**参数校验探针**（断言 rc 必为 1、输出含
     `Invalid command-line argument`），不假装版本旗标可用；版本串的正面证据
     由 `lmp -h` 与 `log.lammps` 首行两处给出；
  ⇒ 上面 1-3 才是"上游输入/上游 CLI 面"，计入三数的**实跑 3 / 通过 3**。
  4. control 自证：同工具链编译运行 `test_package/control.cpp` 打印 `CONTROL_OK`，
     用来把"设备工具链挂了"与"lammps 挂了"分开。
  ⇒ **口径对账**：版本级 `manifest.yaml` 的 `test_package_result` 写 `TOTAL=4 PASS=4`，
     那个 4 = 上述 1-3 再加 control 自证；而三数里的"实跑 3"只算上游输入。
     两个数不是矛盾，是不同维度（上游面 3 / test_package 面 4），正文与本 notes 一律按此措辞。

## test() 探针写法与 W3 的 L1d 闸（一次真实撞闸记录）

首版 `test_package/conanfile.py` 把两处逻辑写在 `test()` 里：
① `self.run("timeout 1 true", ...)` 作为 timeout(1) 可用性守卫；
② `self.run("... -version > version.out 2>&1; echo rc=$? > version.rc", ...)` 用 shell
取回退出码再在 Python 侧断言 `rc == 1`。
W3 的 **L1d** 是对 `test_package/conanfile.py` 源码的**单行正则**
（`ci/conan/build_and_test.sh:1455-1457`：`grep -qE "self\.run.*(echo|print|true)"`），
两处都被判中 ⇒ `L1_RESULT=fail: fake test detected`，`finish` 以 `FINISH_RC=2` 停在 Step5。
同一次运行里 L1a/L1b 都是 pass（test_package 确实执行），预下载也是 `[done]`；汇总里那句
`❌ Pre-download: conandata.yml 已还原为官方 URL` 是 `scripts/ohc/workflow_checks.py:219-221`
对失败后末 20 行统一加 ❌ 前缀造成的装饰，不是独立失败项。

处置（**不是削弱测试，而是把判断放到它该在的地方**）：
- ①：环境能力守卫不该伪装成一条测试。改为 `shutil.which("timeout")` 解析不到就抛
  `ConanException`——比跑一次占位命令更准（占位命令的 rc 与 timeout 是否存在并不等价）。
- ②：把"必须以 rc=1 失败"的判断下沉到 `test_package/version_probe.sh`，`test()` 只
  `self.run("sh version_probe.sh ...")`；脚本断言 rc 必须为 1、`version.out` 必须含
  上游诊断串，任一不满足即非零退出（挂起会以 `rc=124 → unexpected exit code` 暴露）。
  脚本非零退出会直接让 test 失败，Python 侧还额外复核 `version.out` 的诊断文本。
  形态依据 = 仓内先例 `templates/test_package-executable/`（shell 判断放脚本，配方只调用）。
- 同时修掉了 `test.sh` 的一处真 bug：原写
  `timeout 60 "$LMP" -version > /dev/null 2>&1 && exit 1`，在 `set -e` 下"上游如期拒绝"
  反而会让脚本以 1 退出（`A && B` 在 A 失败时返回 A 的状态）。现由 `version_probe.sh` 承担。
- 措辞与计数同源修正：`MANIFEST.yml` 的 `assertion_count` 由 12 改为**实测 13**
  （= `conanfile.py` 内 `raise ConanException` 处数：`test()` 11 + `_read()` 2），
  软件级 `archives/l/lammps/manifest.yaml` 的 `tests:` 同步为 13；本 notes 早先写的
  "9 处显式断言"是第三个不一致的数，已一并改掉。`build_files` 补 `version_probe.sh`。

## 路径 B 查重（宽口径，命令原文 + 命中数）

作用域与基线：在**当时的检出工作区**内对 `archives/` 与 `knowledge/` 两棵树跑全文检索，该工作区的基线为 `origin/main`；命令原文里的 `cd` 路径是执行当时那个 worktree 的目录名，复核时换成自己的 worktree 即可（命中数只取决于树内容，不取决于目录名）。⚠ 命中数已按审计 r3 实测订正（第二条命令实际含 `scripts/`，260→267 即因带上 scripts/），标题措辞已同步。

```
cd <自己的 lammps worktree>
grep -rn CMAKE_SYSTEM_NAME archives knowledge | wc -l        # 5457 命中
grep -rn build_script_folder archives knowledge scripts | wc -l  # 267 命中（含 scripts/）
grep -rn DOWNLOAD_POTENTIALS archives knowledge | wc -l      # 10 命中行（5 个文件，其中 2 个是被 gitignore 的 reports/ 日志）
grep -rn ENABLE_TESTING archives knowledge | wc -l           # 114 命中
grep -rln lammps archives knowledge                          # 32 个文件：本包新目录 + knowledge/recipes/catalog.tsv 1 个索引条目
python3 scripts/ohc-run.py recipe-search lammps              # 语料 6173 条零命中
```

**判定 = create（2026-09-25 K0 新令后由 hit 升级）**：CMAKE_SYSTEM_NAME / build_script_folder / ENABLE_TESTING 三族的复用面如上（命中数为量证，不构成新条目）；但为满足 K0 新令新增的**包名包装入口机制**（主命令名≠包名且上游仅认单横线 -h 时，随包提供包名 --help/--version 包装）可跨库复用 ⇒ 随本 PR 成对提交 `DRAFT-lammps-20260211-k0-help-version-wrapper-entry.{kv,md}`，判定 create。原 hit 结论的查重事实保留如下——
`CMAKE_SYSTEM_NAME=Linux` 处理 OHOS 平台识别（5457 处，`archives/a/afmize/2.0.2` 即先例）、
非根工程根用 `cmake.configure(build_script_folder=...)`（267 处，如
`archives/a/alfa/2.2/conanfile.py:98`、`archives/a/azure-identity-cpp/1.13.3/conanfile.py:83`）、
关测试/关构建期下载（ENABLE_TESTING 114 处）。LAMMPS 的 `cmake/` 布局属第二类，
不构成新机制；`lammps` 配方本身零同族先例（recipe-search 零命中），但没有需要外化的新经验。

## test_package 判定行

见 `test_package/MANIFEST.yml`（**16 处**显式断言（K0 包装入口 +3：wrapper 存在、--help banner、--version 串），口径 = `conanfile.py` 内
`raise ConanException` 的处数（`test()` 14 + `_read()` 2），见上一节；任一 rc 非预期或 rc=124 直接抛
ConanException 使 W3 失败，不静默跳过）。人工复现入口：`test_package/test.sh`。

## 已知风险 / 未做项

- `PKG_KSPACE`/`MANYBODY` 等内部包未开（按 stock 默认），若任务后续要求"全功能"需另评估。
- 上游 `lmp` 不实现 `--version`/`--help`（均 rc=1，仅认 `-h`）；按 K0 新令（2026-09-25）随包提供包名包装入口 `bin/lammps`（见「K0 包装入口」小节），`commands.json` 的 executable 已指向它，`lmp` 本身保持上游原面。
- 首次执行新编译二进制可能触发鸿蒙安全弹窗；本 test_package 全部外部调用套了
  `timeout(1)`，弹窗导致的挂起会以 rc=124 失败暴露，不会无界跑。
## K0 包装入口（2026-09-25 新令合规）

K0 新令（2026-09-25）：可执行结构完整性要求主命令能响应 --help 或 --version 之一且 rc=0；主命令名与包名不一致时必须随包提供同名或带包名前缀的包装入口。本包实测：主命令 `lmp` 的 --help/--version 均 rc=1（`Invalid command-line argument`，src/lammps.cpp:490）、仅 `-h` rc=0，且 lmp ≠ lammps ⇒ 合规动作：

- 配方 `package()` 生成 `bin/lammps`（POSIX sh，0755，`save`+`chmod`，无上游补丁）：`--help` 委托同目录 `lmp -h`；`--version` 打印 `lammps 20260211 (patch_11Feb2026)` 后 rc=0；其余参数原样 `exec lmp "$@"`。**不改上游参数解析、不动 lmp 二进制**（前任多窗红线继续有效）。
- `commands.json` 的 `executable` 改指 `lammps`（框架 L2 烟测按声明入口跑 --version/--help，预期由 skip 转 pass；若新轮 W3 仍 skip，按实况在验证小节记录）。
- `test_package` 新增包装入口断言（存在性 + --help rc=0 含 banner + --version rc=0 含版本串），显式断言计数 13 → 16。
- 条文侧引用的 (E447) 在本仓知识库是 SDL2 vendored Find 桥接，同名不同义；包装入口机制以随 PR 草稿 `DRAFT-lammps-20260211-k0-help-version-wrapper-entry.{kv,md}` 申报 create。

## 收尾时间线与订正

- 文末收尾两行由 `finish ... built` 真实回写；其覆盖范围自本轮起以本节为准：finish = G2 `conan create` → 打包 → `conan-verify` → W3 本地 CI 模拟 → 档案关闭，**判绿依据 = `manifest.yaml status: built` 且 `.ci-result.json` `exit_code=0`**。
- ⚠ 驱动退出码语义订正（审计 r3 P2）：历史上同一轮出现过 `FINISH_RC=2`——step5b = 框架解析器把 `root_cause: |` YAML 块标量当空值的假阳性；step8 = `gen_summary` 框架缺陷。二者均非本包缺陷、档案仍成功关闭（`.handoff.json` `exit_reason=finish_success`）。判读顺序：先看 `manifest.yaml status` 与 `.ci-result.json`，再看驱动 rc。
- ⚠ `archive_dir` 订正（审计 r3 P2）：证据件里的 archive_dir 是**构建当时**的 worktree 路径。本 worktree 经两次无损 `git worktree move`（主理-24 → 主理-26 → 主理-30，分支与 HEAD 连续），旧证据里的 `主理-24-lammps-20260211` 与现目录名不同名但同一实体；收尾提交 `c23da2076` 提交信息中「archive_dir 指向本 worktree」按字面不成立（该轮构建时目录名为主理-24-*），以本节为准。
- 历史轮次：15:17 轮（错传状态参数 failed，已由 454ba3f63 以事实来源覆盖）→ 16:54 / built 轮（c1de39c79 删幻影开关后重跑）→ 本轮（K0 包装入口改动后重跑，读数见文末两行）。
---

**编译结束**: 2026-09-25 01:56
**最终状态**: built
