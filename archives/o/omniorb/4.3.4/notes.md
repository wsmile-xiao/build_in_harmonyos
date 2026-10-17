# omniorb 4.3.4 适配笔记

## 编译环境
- 构建系统: autotools（autoconf configure + 自有 mk/*.mk 递归 make，非 automake）
- 上游发布: 2026-01-05，omniORB-4.3.4.tar.bz2（2635770 字节）
- 编译器: clang/clang++ 15（HarmonyOS PC aarch64 真机 / CI）
- 状态: built（首轮仅完成工作树，真机 `conan create` 预检尚未执行；结果回填后修正）

## 上游源码审计（实测，非推断）

审计对象为官方发布包（sha256 见 conandata.yml，已用 FreeBSD ports 记录与 Fossies 双重交叉验证一致）：

1. **构建系统**：顶层 `configure`（autoconf 2.71 生成）+ `GNUmakefile.in` + `mk/beforeauto.mk.in` 自有递归体系；`make` 默认目标即 `export`（构建全部库/工具），`make install` 支持 `DESTDIR`（`INSTALL*DIR` 变量）。
2. **平台检测**：`configure.ac` 以 `$host` 匹配 `*-*-linux-*` 定平台（Linux），但自带 `bin/scripts/config.guess/config.sub` 为 2001 版——实测 `config.sub aarch64-unknown-linux-ohos` 返回 `Invalid configuration`（exit 1），原生猜测在真机必然失败（E007 错误模式）。
3. **CPU 检测**：`configure.ac` 的 processor case 无 `aarch64-*`（仅 `arm64-*`/`arm-*`），aarch64 上 `PROCESSOR_NAME=UnknownProcessor`；已确认 `PROCESSOR_DEFINE` 在任何源码/mk 文件中无实际消费（`__arm64__` 与 `__processor_unknown__` 全树零命中），属无害未知，不打补丁。
4. **测试存在性**：全树无 `tests/`/`test/` 目录；对全部 `GNUmakefile.in` 与 `mk/*.in`（含 `src/**` 与 examples）执行 `^check[ :]` 搜索零命中；全树唯一含 `test` 字样的文件是 `idl/COS/RDITestTypes.idl`（接口定义，非测试）。结论：上游无测试套件，`MANIFEST.yml` 按 `upstream_tests_exist: false` + `no_tests` 标记处理；配方 `build()` 在真机对解包源码重跑等价扫描，若未来上游出现测试条目则直接失败而非静默跳过。
5. **依赖**：`AM_PATH_PYTHON` 要求 Python 3（构建 omniidl 后端用）；`--with-openssl` 默认 `no`（缺席不报错，仅关闭 SSL 传输与 httpcrypto）；`AC_CHECK_LIB(z/zstd)` 缺席时自动关闭 ZIOP。结论：配方零 conan 依赖，SSL/ZIOP 特性在真机按自动探测结果如实记录。
6. **产物**：默认同时构建 static + shared（`--disable-static` 可关静态库，无 `--disable-shared`）；库含 omnithread、omniORB4（orbcore）、omniDynamic4、omniCodeSets4、COS 系列；工具含 omniidl、omniNames、catior/convertior/genior、nameclt；自带 `.pc` 文件烘焙了 `prefix=/`，`package()` 中删除，消费者走 CMakeDeps。

## 适配改动

| # | 改动 | 原因 |
|---|------|------|
| 1 | `patches/0001-bin-scripts-config.sub.patch`：接受 `aarch64` CPU 与 `linux-ohos` OS | 2001 版 config.sub 校验 `aarch64-unknown-linux-ohos` 直接报错；补丁无 `__OHOS__` 平台宏，纯三元组识别（E007/c-ares 模式） |
| 2 | `generate()` 显式 `--build/--host=aarch64-unknown-linux-ohos`（两者相等） | 相等即 native 构建，`AC_RUN_IFELSE` 特性探针照常执行；不依赖真机 `uname` 返回值，确定性最高（ocl-icd 已合入先例） |
| 3 | `generate()` 以 `PYTHON=<绝对路径>` 传入解释器（优先 hmbs 注入，否则 PATH 查找） | omniidl 后端构建期即需 Python；R33 模式：generate 期解析为绝对路径，不裸用 shell 变量 |
| 4 | `build()` 串行 `make -j1` | 上游递归 make + stub 子 make 并行安全性未经验证；与 hmbs `tools.build:jobs=1` 一致 |
| 5 | `build()` 末尾源码审计并发 `HMBS_UPSTREAM_TEST_RESULT no_tests` 标记 | 无测试套件的上游按守则输出 `status:no_tests/discovered:0/executed:0 + reason`，数字来自实际扫描 |
| 6 | `package()` 删除 `lib/pkgconfig/*.pc`，保留其余全部安装产物 | 上游 `.pc` 的 `prefix=/` 会毒化下游 pkg-config；CMakeDeps 元数据由 `package_info()` 提供 |
| 7 | `package_info()` 仅声明安装树实际存在的库（存在性过滤） | ZIOP/COS 系列是否构建取决于真机自动探测；缺失即 ConanException，不发货不对的 `-l` |
| 8 | `conandata.yml` url 改为有序列表（`master.dl.sourceforge.net` 在前、官方 redirector 在后） | 2026-09-30 预检首包 `IncompleteRead` 抖动后重试才成功；同官方后端不同入口，sha256 不变 |
| 9 | `build()/package()` 双层守卫（均走 Autotools helper，不断工具链环境）：generate() 存 build-scope 脚本 zzz_hmbs_shell 导出 CONFIG_SHELL/SHELL=/bin/sh（排序在 conanautotoolchain 之后，聚合 conanbuild.sh 以好值结尾）+ build()/package() 内 os.environ 覆盖并 scrub 生成 .sh 中残留旧路径；make/install 显式传 SHELL=/bin/sh | 2026-09-30 预检致命错误 `configure[139]: /data/service/hnp/bin/bash: inaccessible or not found`（Error 127）：`ohos-aarch64` profile 经 `[buildenv]` 注入 `CONFIG_SHELL` 指向 hnp bash，autoconf 经该变量 re-exec 自身；单层 os.environ 在 Autotools helper 采源 conanbuild.sh 后被旧值覆盖而无效，故加 generate() 层 Environment 脚本（聚合后以好值结尾）+ build/package 层磁盘 scrub，helper 不断工具链环境、Makefile SHELL 固定为 HMBS 保证的 /bin/sh |
| 10 | `build()` 内 E011/E129 + HMBS `[unsafe_local_mktemp]` 双修复（均走 Autotools helper，不断工具链）：① `_fix_autoconf_umask()` 将 `configure` 内全部 `umask 077` 改为 `umask 022`（c-ares 0003-configure.patch 同语义，内联替换免行号漂移）；② `HMBS_AUTOCONF_MKTEMP_FALLBACK=1` 时 `_enable_mktemp_fallback_shim()` 在 `build_folder/hmbs-mktemp-shim` 下放 `#!/bin/sh` 的 `mktemp` 垫片（`*conf*` 参数直接 `exit 1` 触发 Autoconf `mkdir` 回退，其余委派真实 `mktemp`），仅 `autotools.configure()` 前前置 `PATH`、之后立即恢复（cyrus-sasl-login 同模式，`#/bin/sh` 为 HMBS 保证值） | 2026-10-01 预检致命错误 `./config.status[837]: can't create ./confvD91gQ/subs1.awk: Permission denied` + `configure: exit 1`（HMBS 平台诊断 `[unsafe_local_mktemp]`，`local_mktemp=1`）：autoconf `umask 077 && mktemp -d "./confXXXXXX"` 在 HMDFS 上产出属主不可写的 setgid 目录（E011），后续 `subs1.awk` 写入必然失败；垫片仅在 configure 期生效、不影响 make/install，其余 `mktemp` 调用原样委派，健康机（fallback≠1）仅 umask 位变化 |

## test_package 设计（消费者视角，2 用例）

- 用例 1 `omniidl_codegen`：对 `mini.idl` 运行包内 `omniidl -bcxx`，要求生成非空 `mini.hh`/`miniSK.cc`（空输出判失败，防止"exit 0 但无产出"式假通过）。
- 用例 2 `echo_collocated`：按上游 `src/examples/echo/eg1.cc` 模式（`echo.idl` 为上游原文拷贝），`ORB_init` → RootPOA 激活 servant → 同进程 `echoString` 调用 → 精确比对回包 `"Hello, HarmonyOS!"`。
- `test()` 按实际执行结果计数并输出 `HMBS_TEST_PACKAGE_RESULT{discovered:2}`；任一失败抛异常。

## 验证结果

```bash
# 2026-10-01 真机预检 failed（compile）：致命错误
#   ./config.status[837]: can't create ./confvD91gQ/subs1.awk: Permission denied
#   configure: exit 1（HMBS 平台诊断 [unsafe_local_mktemp]，local_mktemp=1）
#   源码下载本轮实际已成功（twds 首包超时后按序重试，master.dl 节点成功解包），
#   conandata.yml 有序列表保持不变（sha256 不变）。
# → 本轮新增 build() 内双修复（均走 Autotools helper，不断工具链环境）：
#   ① configure 内 umask 077→022 内联替换；② fallback=1 时 configure 期专用
#   mktemp 垫片（*conf* 失败触发 mkdir 回退，其余委派，之后恢复 PATH）。
# 本轮修改后待 HMBS 复检；数字回填前 PR 正文测试栏保持"待真机预检回填"，不估算。

# 2026-09-30 真机预检 failed（compile）：两处问题
#  1) 源码首包 IncompleteRead 抖动（重试后成功下载）→ conandata.yml 已改为
#     有序列表（master.dl.sourceforge.net 在前、官方 redirector 在后，sha256 不变）
#  2) 致命错误 configure[139]: /data/service/hnp/bin/bash: inaccessible or not found
#     （Error 127）→ 首版 Environment.define()+os.environ 修法经复查无效
#     （profile [buildenv] 在运行时重新注入覆盖，tack E386 已实证）；
#     已改为双层守卫（均走 Autotools helper，不断工具链环境）：
#     generate() 存 zzz_hmbs_shell 脚本导出好值 +
#     build()/package() 内 os.environ 覆盖并 scrub 生成 .sh 残留旧路径
# 本轮修改后待 HMBS 复检；数字回填前 PR 正文测试栏保持"待真机预检回填"，不估算。
#  – config.sub 补丁此前已在本机用 Git 自带 sh 实测：
#    未补丁 `config.sub aarch64-unknown-linux-ohos` → Invalid configuration (exit 1)
#    已补丁 → 输出 aarch64-unknown-linux-ohos；x86_64-pc-linux-gnu 与
#    arm-unknown-linux-gnueabi 回归输出不变；`git apply --check` 通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Autotools 配方（库 + 工具双产物，`cpp_info.bindirs=["bin"]`） |
| conandata.yml | 官方 SourceForge URL + sha256 + 1 个 portability 补丁 |
| patches/0001-bin-scripts-config.sub.patch | config.sub 三元组识别补丁（已做 apply + 功能验证） |
| test_package/ | omniidl 代码生成 + Echo 同进程调用（2 用例） |
| manifest.yaml / notes.md / README.md / commands.json | 元数据与文档（commands.json 因含 bin/ 工具产物，type=tool） |

## 注意事项

- `manifest.yaml` 状态暂标 `built`，含义为"配方完整、待真机验证"，并非"已验证通过"；预检结论出来后按实际修正为 published/failed。
- omniidl 安装脚本的 `#!` 为构建期 Python 绝对路径；消费者若换解释器可用 `python3 $(which omniidl)` 显式调用，test_package 已覆盖直接执行路径。
- 若真机存在系统 zlib/zstd/OpenSSL 开发文件，ZIOP/SSL 会自动启用并多出对应库文件（`package_info` 存在性过滤已兼容）；notes 此处记录的"关闭"结论以预检日志为准。
- 本机为 Windows（大小写不敏感 + 2001 版脚本无 aarch64），`archives/l/libXext|libxext` 的状态显示差异为环境 artifact，未改动，不在本 PR 范围内。

---
**编译结束**: 首轮工作树完成，真机预检待执行
**最终状态**: built（待验证）

## 2026-10-02 真机 evidence 修复（no_tests 拒收 → custom 功能检查证据）

- 真机返回 incomplete（evidence）：清单表明上游存在测试，no_tests/0 不允许通过；
  上游标记为 build() 内源码审计输出的 status:no_tests（source audit）。
- 复核上游源码（.hmbs/src 内解包树）：无 tests/ 或 test/ 目录；267 个
  GNUmakefile.in/mk 文件 ^check 目标零命中（dir.mk 仅有 Check for Python
  注释行）；src/examples/ 为交互式演示（README.unix 明示 try out，需手动
  make），非自动化套件。formal 总数确为 0，审计原文完整保留在
  test_package/MANIFEST.yml。
- 按 libcec/7.1.1 经验改用 custom 功能检查作为上游证据（本轮适配该经验，
  不复制其路径/版本/补丁）：新增 test_package/test_upstream_checks.cpp
 （8 项无硬件检查：ORB_init、RootPOA 解析/命名、string_dup 往返、Any 长整/
  字符串插取、TypeCode 种别、POAManager 查询、omniidl -V 真执行；所用符号
  均在上游头文件核对：CORBA_ORB.h/CORBA_String.h/CORBA_Any.h/CORBA_TypeCode.h/
  poa.h，man omniidl 确认 -V 语义；单进程本地调用，不开监听端口，无 SKIP
  分支；输出 UPSTREAM_CHECK_CASE + UPSTREAM_CHECK_SUMMARY 确定性协议）。
- test_package/CMakeLists.txt 注册 upstream_checks 到 ctest；conanfile.py
  test() 单次确定性运行并逐行解析 SUMMARY 与 CASE 交叉校验（恒等式自检 +
  cli/omniidl_version PASS 非空证据），上报 HMBS_UPSTREAM_TEST_RESULT
 （framework:custom，discovered:8）；主配方 build() 删除 no_tests 标记输出
  （上游证据唯一来源改为 test_package，与 libcec 主配方无标记一致）。
- MANIFEST.yml 改为 upstream_tests_exist:true、total:8、method:auto，审计
  保留 formal-0 原文并声明替代执行方法；消费者 2 用例与 HMBS_TEST_PACKAGE_RESULT
  不变。
- 本轮修改后待 HMBS 复检；数字回填前 PR 正文测试栏保持待预检回填，不估算。

## 2026-10-02 CI #66639 修复（真机通过、CI 失败分歧）
- 现象：HMBS 真机预检通过（8/8），CI Worker OpenHarmonyPCDeveloper-CI-033
  在 `src/lib/omniORB` stub 生成步失败：`omniidl` 报
  `Could not open IDL compiler module _omniidlmodule.so`，
  内因 `Error loading shared library .../build-release/lib/_omniidl.cpython-312-aarch64-linux-ohos.so: Permission denied`。
- 判定：同树 `libomnithread` 链接正常（读即可），仅 `dlopen`（需 PROT_EXEC
  mmap）失败，指向 `/storage` 构建树 noexec 而 `TMPDIR`（`/data/...`）可执行；
  另有版本化软链 `*.so -> *.so.4 -> *.so.4.3` 在 HMDFS 上不可靠（E018/E050）。
  与 HMBS 真机通过的差异为 Worker 挂载/策略不同，非配方逻辑问题。
- 修复（均在 `build()` 内联源码替换，无新增 patch 文件，健康机零行为变化）：
  1) `_fix_makefile_symlinks`：`mk/beforeauto.mk.in` 与 `mk/unix.mk` 的
  `ExportSharedLibraryToDir` 中 `ln -s` 改为 `cp -f`，导出即为实文件；
  2) `_patch_omniidl_noexec_fallback`：`omniidl.in` 仅在 `Permission denied`
  时把真实扩展字节拷贝到 `TMPDIR` mkdtemp 目录并重试导入（先 `sys.path`，
  再显式文件位置），首导入成功时不进入分支。
- 待 HMBS 预检与 CI 复检验证；若复现则按新日志再定位，不改测试口径。

## 2026-10-02 CI #67804 复发加固（同一 Permission denied，原回退未生效）
- 现象：CI Worker OpenHarmonyPCDeveloper-CI-034 在同一位置失败
 （`src/lib/omniORB` stub 生成步，`build-release/lib/_omniidl.cpython-312-*.so:
  Permission denied`），错误文本与 #66639 逐字节一致，说明首轮回退分支
  根本没有执行，而非执行了仍失败。
- 根因（对照 `.hmbs/src` 解包树实测，非推断）：
  1) 只补了 `omniidl.in`，漏了 `omniidlrun.py`。两文件含完全相同的
  `import _omniidl` 致命块；`AC_CONFIG_FILES` 只从 `.in` 生成构建期
  `omniidl`，而 `omniidlrun.py` 被 `dir.mk` 原样 export，检入的 shell
  包装 `omniidl` 直接 exec 它。构建期实际走哪条路径取决于 VPATH 解析，
  只补其一即留一条必死路径。
  2) 首轮回退只试单个基目录（`TMPDIR` 或 `/tmp`）：CI Worker 上
  `TMPDIR`/`TMP` 未设置，`/tmp` 可能不存在或同样 noexec，
  `mkdtemp` 抛异常后直接 `raise _first_msg`，无任何诊断输出，
  故日志与修复前无法区分。
- 加固（`conanfile.py`，健康机仍零行为变化，首导入成功不进分支）：
  `_patch_omniidl_noexec_fallback` 改为对 python3 的 `omniidl.in` 与
  `omniidlrun.py` 双文件打同一补丁（幂等标记复用）；
  回退内搜索面扩大为 `archlibdir + binarchdir + 全部 sys.path 条目 +
  binarchdir 旁 sibling lib/`（去重，最多取 4 个候选，`.so` 结尾优先、
  同类按字节数降序）；可执行基按序尝试 `TMPDIR/TMP/TEMP`、
  `/tmp`、`/data/local/tmp`、`~/.cache`（不存在则 `makedirs`，
  仍不可用记入诊断换下一个）；每次拷贝后 `invalidate_caches` 并先走
  `sys.path` 导入、再走 `spec_from_file_location` 显式加载；
  成功在 stderr 留 `HMBS noexec fallback: loaded ...`，
  全部失败打印候选与各基结果后才抛原始异常（下轮日志可直接定位）。
  仅 permission 类 `ImportError`（`permission denied`/`eacces`/`eperm`，
  大小写不敏感）进分支，`No module named` 等仍立即抛出以保留包布局诊断。
- AI Review P3（`conandata.yml` 明文 http 源）：无 https 等价源
  （该 host 的 https 变体在真机报 TLS hostname mismatch），按审查建议的
  保留方案，在注释中显式声明防篡改依据为 Conan 强制 `sha256` 校验
  （与官方发布逐字节一致，已交叉验证），仅作下载通道。
- 待 HMBS 预检与 CI 复检验证；是否有效以下一轮真机/CI 结果判定。

## 2026-10-03 CI #68143 扩大可执行候选（回退已执行但候选全灭）
- 现象：CI Worker OpenHarmonyPCDeveloper-CI-033 在同一位置失败，
  但本轮日志证明 #67804 回退分支实际执行了：
  `TMPDIR(/storage/.../.cache/tmp)` 与 `~/.cache` 均为
  `import failed: Permission denied`（与构建树同一 HMDFS noexec），
  `/tmp` 为 `mkdtemp failed: Read-only file system`，
  `/data/local/tmp` 为 `not a dir`。
  结论：不是回退未生效，而是全部已有候选在该 Worker 上都不可用；
  真机通过是因为 HMBS 注入的 TMPDIR 指向可执行文件系统。
- 修复（`conanfile.py` 内联回退体，健康机零行为变化）：
  1) 可执行基按序扩展为 `TMPDIR/TMP/TEMP/XDG_RUNTIME_DIR/RUNNER_TEMP`、
  `/dev/shm`、`/var/tmp`、`/tmp`、`/data/local/tmp`、`$HOME`、`~/.cache`
  （tmpfs 候选在前；真机 HMBS TMPDIR 仍排首位命中，原成功路径不变）；
  2) 每次 `copyfile` 后追加 `os.chmod(_dst, 0o755)`（OHOS musl 的
  `Permission denied` 亦可能来自文件模式而非挂载 noexec；失败记入诊断，
  不中断后续导入尝试）；
  3) 重试前一次性采集 `df -T` 与 `mount`（仅保留含 storage/shm/tmp 的行，
  截断后记入诊断），下轮日志可直接看到 Worker 的可执行挂载映射；
  失败汇总截断从 12 条放宽到 20 条，避免新诊断挤掉各基结果。
- 待 HMBS 预检与 CI 复检验证；是否有效以下一轮真机/CI 结果判定。

## 2026-10-03 CI #68271 memfd 逃生通道（文件系统候选全部阵亡）
- 现象：扩展后的重试同样跑到穷尽：`/dev/shm` 存在但 `mkdtemp`
  `Permission denied`，`/var/tmp` 与 `/data/local/tmp` 不是目录，
  `/tmp` 只读，`$HOME`、`~/.cache`、`TMPDIR` 全部
  `import failed: Permission denied`（均无 `chmod failed`，即 chmod 已成功，
  仍 dlopen 失败，确认为挂载级 noexec 而非文件模式问题）。
  结论：该 Worker 上所有可写目录都在 HMDFS noexec 上，任何落盘拷贝都不可能
  dlopen 成功；机器人建议的 `$REPO_ROOT/.ci_logs/` 同在 `/storage` 挂载下，
  经证据评估同样不可执行，不采用。
- 修复（`conanfile.py` 回退体末尾新增 memfd 层，仅在全部文件系统基失败后执行，
  原致命路径不变）：`os.memfd_create` 建匿名文件 → 字节拷贝 → 显式
  `ExtensionFileLoader('_omniidl', '/proc/self/fd/N')` 加载（后缀无关，无需
  落盘，不经过任何挂载的 noexec 检查）；`MFD_CLOEXEC|MFD_EXEC` 均经 getattr
  兼容取值，fd 常驻 `sys._omniidl_memfds` 防关闭；任一环节异常记入诊断后沿用
  原始异常抛出。HongMeng 若不支持 memfd（ENOSYS）则诊断留痕、无回退风险。
  2026-10-03 补：CI #68527（Worker 019）摘要中无任何 memfd 字样，巨型单行诊断
  疑似被 [:20] 截断或摘要窗口裁掉，故 memfd 结论另起独立 stderr 行
  `HMBS memfd outcome:` 输出，不再依赖联合行的尾部位置；成功路径原有的
  `memfd-loaded` 行保持不变。
- 待 HMBS 预检与 CI 复检验证；是否有效以下一轮真机/CI 结果判定。

## 2026-10-03 CI #68962 设备私目录逃生（memfd 同样被禁）
- 现象：完整日志证实 memfd 已执行但同样失败：
  `memfd load failed: ImportError('Error loading shared library
  /proc/self/fd/3: Permission denied')`（3 个候选全部一致），即 HongMeng
  沙箱连匿名文件 exec 映射都拒绝；同时回退首基为
  `/storage/.../.cache/tmp`（CI worker 的 TMPDIR 已被覆写为 HMDFS 路径），
  启动 env 的 `TMPDIR=/data/storage/el2/base/cache` 在 omniidl 运行时已丢失；
  `df/mount` 在该 worker 不可用（FileNotFoundError）。
  另发现 `_fix_makefile_symlinks` 全轮空转（两条精确 `ln -s` 模式零命中，
  但构建仍在执行 `ln -s`，空格/制表符不一致）。
- 修复（`conanfile.py`，健康机零行为变化）：
  1) 回退基按 E528 扩展设备私目录：env 新增 `DOWNLOAD_CACHE/
  HNP_PRIVATE_HOME/HNP_PUBLIC_HOME/HMBS_OMNIIDL_EXEC_BASE`，硬编码新增
  `/data/storage/el2/base/cache`、`/data/storage/el2/base`、`/data/cache`
 （均在 `/dev/shm` 之前）；诊断截断 [:20]->[:40]；
  2) `build()` 在 make 前按序探测
  `/data/storage/el2/base/cache > /data/storage/el2/base > TMPDIR >
  DOWNLOAD_CACHE > /data/cache`，首个存在目录写入
  `HMBS_OMNIIDL_EXEC_BASE`（专用名，不会被 conanbuild.sh 覆盖），随
  os.environ 透传进 make/omniidl；
  3) `_fix_makefile_symlinks` 保留精确替换并在零命中时回退为通用
  `ln -s`->`cp -f` 替换（计数打日志），确保导出即实文件；
  4) AI Review P3：补丁头两行 git CRLF warning 文本已删除；
  test_package CMake 最低版本 3.15->3.18（find_program REQUIRED 需 3.18）。
- 待 HMBS 预检与 CI 复检验证；是否有效以下一轮真机/CI 结果判定。

## 2026-10-04 CI #70493 分诊（configure 期 can't fork，配方零改动）
- 现象：CI Worker OpenHarmonyPCDeveloper-CI-033 在 conan-build-test 步失败，
  致命行仅 `.../b/configure[36]: can't fork - try again` 后
  `ConanException: Error 1 while executing`（autotools.configure）。
  同轮预下载多条 `[fail] [Errno 2] No such file or directory: 'curl'`（Worker
  缺 curl，回退 conan 下载，属环境缺件）。无 config.log 失败块、无 conftest
  调用、无编译器报错，与既往各轮（noexec/dlopen、memfd、umask）症状均不同。
- 判定（infra，不改配方）：`can't fork - try again` 为 shell fork() 返回 EAGAIN
 （pid/内存/cgroup 配额耗尽或瞬时过载），发生在 configure 第 36 行、早于任何
  配方逻辑（shell 守卫/umask/mktemp 垫片/编译器探针均未参与此时序）；配方
  make 保持 -j1，无 fork 风暴源。按守则 infra 故障（Worker/工具链临时故障）
  不修改代码、不空提交、不重触发，等待稳定窗口由 HMBS 统一 /rebuild 验证。
- AI Review 192480743 核对（commentId=192480743）：
  P1“CI 仍无通过”非代码缺陷，待稳定窗口 rebuild 闭合；
  P2 明文 http 源已按建议保留方案处理（conandata.yml 注释载明该 host https
  变体在真机报 TLS hostname mismatch、无 https 等价源，防篡改由 Conan 强制
  sha256 保证，与官方发布逐字节一致）；
  P3 补丁 CRLF warning 已删（本树补丁首行即 `diff --git`，验证通过）、
  P3 CMake 最低版本已为 3.18（find_program REQUIRED 合规），均无需再改。
- 待 HMBS 在稳定窗口 /rebuild 与 CI 复检验证；是否有效以下一轮 CI 结果判定。

## 2026-10-10 CI #74775 exec 位修复（挂载非 noexec，0644 是真因）

- 现象：CI Worker OpenHarmonyPCDeveloper-CI-012 同一位置失败，但完整日志给出
  决定性反证：同一 /storage 构建树中新编出的 C 可执行文件
  `../../../bin/omkdepend` 正常运行并产出依赖，而仅 `dlopen()` 刚编出的
  `_omniidl...so` 报 `Permission denied`。若挂载是 noexec，两者应同时失败。
  结论：挂载可执行，真正的区别是文件创建模式——可执行文件经
  `install -c -m 0755`（INSTEXEFLAGS）创建，共享库经 `install -c -m 0644`
  （INSTLIBFLAGS）+ `cp -f` soname 拷贝（0644）创建；OHOS/HMDFS 忽略事后
  chmod（与 HMBS 上报的 chmod 能力 0 一致），于是之前所有回退拷贝
  （copyfile + chmod，仍为 0644）在所有基目录上以完全相同错误失败——包括
  在 HMBS 真机上可执行的 /data/storage/el2/base/cache；memfd 经
  /proc/self/fd 的失败是另一机制（proc 访问限制），非决定性。
- 修复（`conanfile.py`，健康机零行为变化）：
  1) `_fix_makefile_symlinks`：`ln -s` 改为 `$(INSTALL) -m 0755`（不再是
  `cp -f`），soname/libname 拷贝在创建时即带可执行位，复刻已验证可跑的
  omkdepend 安装路径；构建树内 `import _omniidl` 首试即应成功，回退分支不进。
  2) omniidl 回退体：拷贝改用 `os.open(O_WRONLY|O_CREAT|O_TRUNC, 0o755)` 按
  字节写入（创建即 0755，不再依赖 chmod）；候选源与落盘目标的 octal 模式
  记入诊断（`src-modes=` 单行 + 各失败行 `[dstmode=...]`），下轮日志无论成败
  都是决定性证据。
  3) `package()` 新增 `_copy_exec` 助手：`_omniidl` 的 materialize/mirror
  同样创建即 0755（.py 文件不受影响，仍普通拷贝）。
- 若下轮仍失败且日志显示目标模式仍为 0644，则“创建模式亦被忽略”得证，
  届时改走上游 Windows  precedent 的 `OMNIIDL_EXECUTABLE` 独立可执行文件路线
  （解析器静态链入 omniidl 二进制，彻底不走 dlopen；已在本机完成源码级可行性
  确认：`idlpython.cc` 尾部 `#ifdef OMNIIDL_EXECUTABLE` 内含 main +
  PyImport_AppendInittab）。
- 待 HMBS 预检与 CI 复检验证；是否有效以下一轮真机/CI 结果判定。

## 2026-10-11 CI #81330 独立 omniidl 可执行文件（dlopen 全灭后的路线切换）

- 现象：CI Worker OpenHarmonyPCDeveloper-CI-030 上 #74775 的 0755 补丁已生效
  （日志可见 `install -c -m 0755` 执行、`src-modes=...:0o750/...:0o640`、
  各回退拷贝 `[dstmode=0o755/0o750]`），但 dlopen 仍在所有基目录、所有模式、
  经 memfd 全部报 `Permission denied`。文件模式理论被决定性证伪：
  同一 /storage 树中新编 C 可执行文件（omkdepend）可运行，只有新编 .so 的
  dlopen 被拒——沙箱按“装载方式”而非路径/模式拦截。
- 修复（`conanfile.py`，上游 Windows `OMNIIDL_EXECUTABLE` precedent）：
  1) 新增 `_probe_libpython()`：在 worker 上用解释器 sysconfig 定位
  libpython（静态归档优先，完整自包含；否则共享 + rpath），拿不到则回退
  旧脚本路径（真机与健康机不受影响）；
  2) 新增 `_patch_omniidl_executable()`：向 `src/tool/omniidl/cxx/dir.mk`
  的 autoconf 段追加独立二进制规则（`idlpython.cc` 以
  `-DOMNIIDL_EXECUTABLE` 单独编出 `idlpython_exe.o`，与原 OBJS 及探测到的
  libpython 链成 `bin/omniidl_static` 并 export），`mk/unix.mk` 的 OMNIIDL
  改指该二进制——全部桩生成不再经过任何 .so 装载；
  3) `build()` 设 `PYTHONHOME=<解释器自带 prefix>`（对系统 python 是空操作，
  保证独立二进制找到标准库）；
  4) `package()` 把编出的 `omniidl_static` 作为 `bin/omniidl` 发货，纯
  Python 树同步归一到 `lib/python/<tree>`（独立二进制内嵌搜索路径，零环境
  可用），`_fix_omniidl_python_layout` 校验同步接受该位置。
- 待 HMBS 预检与 CI 复检验证；是否有效以下一轮真机/CI 结果判定。

## 2026-10-11 真机预检 PySys_SetArgv 编译失败（Python 3.14 wchar_t 修复）

- 现象：真机 `conan create` 在 `src/tool/omniidl/cxx/idlpython_exe.o` 失败：
  `idlpython.cc:1641:3: error: no matching function for call to
  PySys_SetArgv`，候选为 `PySys_SetArgv(int, wchar_t **)`，
  实参为 `char **`。此前 OBJ 编译（`idlpython.o`，模块形态）正常，
  只有新增 `-DOMNIIDL_EXECUTABLE` 的 main() 分支触发（上游该分支是
  Win32 专属，从未在 Unix 上以 Python 3 构建过）。
- 根因：Python 3 起 `PySys_SetArgv`/`Py_SetProgramName` 改为 `wchar_t`
  接口；上游 `OMNIIDL_EXECUTABLE` main() 仍按 Python 2 的 `char **`
  调用，在 Python 3.14 头下无法转换。
- 修复（`conanfile.py`，最小内联改写，无行号漂移）：
  1) 新增 `_fix_idlpython_pyargv()`：`build()` 中 patch 后对
  `src/tool/omniidl/cxx/idlpython.cc` 做正则改写——`PySys_SetArgv(argc,
  argv);` 换成 `Py_DecodeLocale` 逐个解码后传 `wchar_t **`，同文件若有
  `Py_SetProgramName(argv[0]);` 同理加宽；缺失时补 `#include <stdlib.h>`
  （`malloc` 声明）；无匹配时仅日志跳过，不改变构建流程；
  2) 独立二进制链接改用 `$(filter-out idlpython.o,$(OBJS))`，避免模块形态
  `idlpython.o` 与 `-DOMNIIDL_EXECUTABLE` 的 `idlpython_exe.o` 符号重复。
- 待 HMBS 预检复检验证；是否有效以下一轮真机结果判定。

## 2026-10-11 真机预检 export 自拷贝失败（omniidl_static 已在终点）

- 现象：上轮 PySys_SetArgv 加宽生效（本轮 `idlpython_exe.o` 仅剩 3 个
  warning，链接 `clang++ -o .../b/bin/omniidl_static ... -lpython3.14`
  成功），但 `export` 在 `dir.mk:173` 失败：
  `cp: '.../b/bin/omniidl_static' is '.../b/bin/omniidl_static'`。
- 根因：注入规则把链接产物直接定为
  `$(BASE_OMNI_TREE)/$(BINDIR)/omniidl_static`（即终点 `b/bin/`），而
  `export::` 又用 `$(INSTALL)` 把它装回同一目录——GNU cp 视同文件拷给
  自己而报错。与上轮 argv 类型错误不同域，属规则自指。
- 修复（`conanfile.py`，与上轮不同策略）：保留 `all::` 原地链接，
  `export::` 改为 `(test -f $(HMBS_OMNIIDL_STATIC_EXE))` 存在性校验，
  不再自拷贝；健康机行为不变（二进制本就在终点）。
- 待 HMBS 预检复检验证；是否有效以下一轮真机结果判定。

## 2026-10-11 CI #82966 libpython 探测加固（静态路线在 CI 未生效）

- 现象：真机预检通过，CI Worker（#82966，与 #81330 同错位）在同一 stub 生成步失败：
  `Could not open IDL compiler module _omniidlmodule.so`（`.../build-release/lib/_omniidl.cpython-312-*.so:
  Permission denied`），回退诊断跑满全部基目录（`/dev/shm` mkdtemp 拒绝、`/tmp` 只读、
  `/data/local/tmp` 非目录、`$HOME`/`~/.cache`/TMPDIR 全部 import 拒绝）。
  该错误文本只来自 python 脚本（omniidl.in/omniidlrun.py），独立二进制报的是另一文本
 （`Could not open Python files`），故 CI 上 OMNIIDL 仍指向脚本，#81330 静态路线根本没接管。
- 根因：`_probe_libpython()` 只看 LIBDIR/LDLIBRARY/LIBPYTHON 三个变量；任一 worker 的开发文件
  若在 LIBPL、exec_prefix/lib 或版本化子目录（或 LIBDIR 是设备上不存在的构建期路径），
  探测即回 `(None, None)`，`build()` 仅 warning 后静默沿用必死的脚本路径。旧探测在真机命中
 （shared `-lpython3.14`），在 CI worker（python 3.12）大概率脱靶——属探测覆盖不足，非模式/权限理论问题。
- 修复（`conanfile.py` 仅 `_probe_libpython`，健康机命中路径与返回值不变）：
  1) 增查 LIBPL/BLDLIBRARY/VERSION/ABIFLAGS/Py_ENABLE_SHARED/base_exec_prefix 并全量打日志；
  2) 查 `python3-config --ldflags --embed`（HMBS 绝对路径 sibling 优先，否则 PATH）并记录 rc 与输出；
  3) 组装 LIBDIR/LIBPL/prefix-lib/base-prefix-lib/system-lib 候选目录，逐个列出 `libpython*` 命中；
  4) 精确命中（静态 .a 直连、共享 -L/-l+rpath）优先，glob（.a 优先、.so* 次之）其次，
     config 答案再次之；仍无文件命中时回 unverified `-lpython<LDVERSION>` 让链接步骤决定，
     不再静默回脚本（缺开发文件则在静态二进制链接处 loud 失败，而非 stub 处 dlopen 失败）。
- 机器人建议的 `$REPO_ROOT/.ci_logs/`（同 /storage 挂载）经证据评估与 $HOME 同命运，不采用；
  本轮不改测试口径、不改 fallback 语义。
- 待 HMBS 预检与 CI 复检验证；是否有效以下一轮真机/CI 结果判定。

## 2026-10-12 CI #85708 真正有效的 IDL 驱动重定向（beforeauto.mk.in）

- 现象：#82966 加固（多源 libpython 探测）合入后 CI #85708 同错复现，但完整日志给出决定性
  新证据：探测已命中（glob shared `.../lib/libpython3.12.so`，`OMNIIDL now points at
  bin/omniidl_static`），且 `clang++ -o .../b/bin/omniidl_static ... -lpython3.12` 链接成功，
  但桩生成步仍执行 `../../../bin/omniidl`（脚本）并以同一 dlopen EACCES 失败。
- 根因（对照 `.hmbs/src` 源码实测）：`mk/unix.mk:144` 的 `OMNIIDL` 重定向从未生效——实际
  生效的是 `mk/beforeauto.mk.in:74` 原生分支 `OMNIORB_IDL_ONLY = $(TOOLBINDIR)/omniidl -bcxx`
 （config.status 据此生成 beforeauto.mk；相对路径 `../../../bin/omniidl` 即 TOOLBINDIR 形态，
  而非 unix.mk 的绝对 BASE_OMNI_TREE 形态；unix.mk:145 的同名定义被遮蔽）。此前各轮只改
  unix.mk，故静态二进制编出却无人调用。
- 修复（`conanfile.py` 仅 `_patch_omniidl_executable` 追加一段，机制与已验证的 symlink 补丁同）：
  同样在 pre-configure 期把 beforeauto.mk.in 原生分支改指 `$(TOOLBINDIR)/omniidl_static -bcxx`
 （rtems/vxWorks/mingw 系他平台不动；cross 分支 `@OMNIIDL@` 与本次 native 构建无关不动）；
  排序天然成立（src/tool 先于 src/lib，-j1 串行，日志证实静态二进制先于 stub 步骤编出）。
  缺 anchor 时 warning + 返回 False（沿用旧脚本路径，loud 失败，不静默）。
- 机器人“只读 /tmp”诊断仍不采用：本轮证据证明失败与临时目录无关（可执行基全灭且与 dlopen
  拦截机制正交），静态路线才是对因修复。
- 待 HMBS 预检与 CI 复检验证；是否有效以下一轮真机/CI 结果判定。

## 2026-10-12 真机 omniidl_static 路径错配（stub 报 No such file）

- 现象：#85708 重定向生效后，真机 `conan create` 在 `src/lib/omniORB` 桩生成步失败：
  `../../../bin/omniidl_static: No such file or directory`（Error 127），
  而静态二进制本身已链接成功（`pyargv fix: widened argv` 生效、无编译错误）。
- 根因（对照 `.hmbs/src` 源码实测）：注入规则把产物直链到
  `$(BASE_OMNI_TREE)/$(BINDIR)/omniidl_static`（源码树 `bin/`），而桩驱动经
  `$(TOOLBINDIR)/omniidl_static = $(TOP)/$(BINDIR)`（构建树 `bin/`）解析；
  `export::` 仅做 `test -f` 存在性校验，从不把二进制拷到构建树，
  故 `src/tool` 先编出、`src/lib` 仍找不到——属上一轮为避自拷贝而引入的路径错配。
- 修复（`conanfile.py` 仅注入的 make 块，照抄上游 Win32 `$(omniidl)` 原模式）：
  本地链接 `omniidl_static` 再经 `$(ExportExecutable)` 拷到
  `$(EXPORT_TREE)/$(BINDIR)`（即桩步骤要 exec 的 TOOLBINDIR）；
  链接目标与安装终点不同，不再自拷贝；`mk/unix.mk` 与 `beforeauto.mk.in`
  的 `omniidl_static` 指向不动。健康机行为不变（同目录多一个可执行文件）。
- 待 HMBS 预检复检验证；是否有效以下一轮真机结果判定。

## 2026-10-12 真机 omniidl_static 报 No module named omniidl（独立二进制已运行）

- 现象：上一轮路径修复生效（`../../../bin/omniidl_static` 已能执行），
  但桩生成步改报 `omniidl: Could not open Python files for IDL compiler`
  `Please put them in directory .../.harmonybrew/opt/python@3.14/bin`
  `(The error was 'No module named 'omniidl'')`（Error 1）。
- 根因（对照 `idlpython.cc` 内嵌 `omniidl_string` 与日志实测，双重叠加）：
  1) `build()` 曾导出 `PYTHONHOME=<解释器 prefix>`，内嵌解释器的 getpath
  据此把 `sys.executable` 派生到 harmonybrew 目录下，treedir 相对搜索
  （`treedir/lib/python`）永远指不到我们的树——日志里让用户把文件放到
  harmonybrew/bin 即此劫持的直接证据；
  2) 构建树布局（`<build>/bin` 下的可执行文件、Python 源在源码树）
  本就不同于内嵌搜索期望的 `<treedir>/bin + <treedir>/lib/python` 安装布局，
  即使去掉 `PYTHONHOME`，`import omniidl.main` 仍无处解析。
- 修复（`conanfile.py` 仅 `build()` 中 `_patch_omniidl_executable` 成功分支）：
  1) 不再导出 `PYTHONHOME`（显式 `pop`，链接的 libpython 自带 prefix，
  标准库无需它）；2) 把两处源码内 Python 包根
  （`src/tool/omniidl/python3` 含 `omniidl.main`，
  `src/lib/omniORB/python3` 含 `omniidl_be/cxx` 后端）经 `PYTHONPATH`
  透传进 make/omniidl 环境（与既有 `HMBS_OMNIIDL_EXEC_BASE` 同通道）；
  安装消费侧不动（`package()` 仍归一 `lib/python` 供零环境使用）。
- 待 HMBS 预检复检验证；是否有效以下一轮真机结果判定。

## 2026-10-12 真机 omnicpp 在桩生成步报 inaccessible（独立二进制前端已跑通）

- 现象：上一轮 `PYTHONPATH` 修复生效（`Preprocessing .../Naming.idl` 已打印、
  `Running front end` 已进入），但紧接着 ` /bin/sh: omnicpp: inaccessible
  or not found`，`omniidl: Error running preprocessor`（Error 1）。
- 根因（对照 `omniidl/main.py:104-116` 与 `cccp/dir.mk` 实测）：`main.py`
  按 `[dirname(_omniidl.__file__), dirname(sys.argv[0])]` 定位预处理器；
  静态注册的 `_omniidl` 无 `__file__`（首候选跳过），而 make 以相对路径
  `../../../bin/omniidl_static` 调用，次候选相对桩 CWD
 （`build-release/src/lib/omniORB`）解析到 `src/lib/bin` 而非 `TOP/bin`，
  双双脱靶后回退到裸名 `omnicpp`，又不在 `PATH` 中。上游脚本流不触发，
  是因 `_omniidl.__file__` 指向 `TOP/lib`——`cccp/dir.mk` 在 unix 上正是把
  `omnicpp` 导出到 `$(EXPORT_TREE)/$(LIBDIR)`，首候选即命中。
- 修复（`conanfile.py` 仅静态 exe 分支追加，零上游改动）：`make` 前把构建树
  `build_folder/build-release/{lib,bin}`（与 `package()` 取二进制同口径）
  前置进 `PATH`（与 `PYTHONPATH` 同通道透传进 make/子 shell；目录彼时可尚不
  存在，`sh` 在 exec 时才查找；`omnicpp` 由 `install -m 0755` 落盘，可执行位
  在创建时即有）。健康机仅多两个 `PATH` 条目。
- 待 HMBS 预检复检验证；是否有效以下一轮真机结果判定。

## 2026-10-12 真机 omnicpp 仍报 inaccessible（PATH 前置零效果，改源码级定位）

- 现象：上一轮 `PATH` 前置后，真机 `conan create` 在同一桩生成步以逐字节
  相同的 `omnicpp: inaccessible or not found` 失败（`Preprocessing` 与
  `Running front end` 仍正常）。`PATH` 修改对子 shell 零效果。
- 根因（对照 `main.py:104-116` 与 conan `Autotools.make` 环境机制复核，
  与上一轮“相对路径 + 不在 PATH”假设不同域）：`Autotools.make` 在每次
  执行前重新采源聚合 `conanbuild.sh`（generate 期 `PATH` 值），覆盖
  `build()` 内对 `os.environ["PATH"]` 的运行时前置；新增变量
  （如 `HMBS_OMNIIDL_EXEC_BASE`）能透传，唯独 `PATH` 被重置。
  故上一轮“前置即可被 `/bin/sh` 解析”假设无效；`main.py` 的裸名回退
  仍在旧 `PATH` 下解析。已在本机模拟复现：相对 `../../../bin` 在
  `src/lib/omniORB` 下解析到 `TOP/bin`，而 unix `omnicpp` 在 `TOP/lib`。
- 修复（`conanfile.py` 新增 `_patch_omniidl_preprocessor_paths`，构建期
  调用，零上游文件新增）：直接补 `src/tool/omniidl/python3/omniidl/main.py`
  的候选表——追加 `sys.argv[0]` 的 abspath 目录、`sys.executable` 目录及
  每个候选的 abspath 形态与 `../lib` 兄弟目录；既有 `isfile` 循环随后即
  命中 `TOP/lib/omnicpp` 绝对路径，不再依赖 `PATH`。`PATH` 前置保留仅作
  纵深，健康机只多几次 `isfile` 检查。已在本机用临时 `TOP/bin+TOP/lib`
  布局模拟验证：候选表含 `TOP/lib` 且 `isfile(TOP/lib/omnicpp)` 命中。
- 待 HMBS 预检复检验证；是否有效以下一轮真机结果判定。
