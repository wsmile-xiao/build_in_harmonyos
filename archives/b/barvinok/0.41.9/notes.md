# barvinok 0.41.9 适配记录

## 源码、依赖与构建

- 源码：`https://downloads.sourceforge.net/project/barvinok/barvinok-0.41.9.tar.bz2`
- SHA256：`78bcf1b0843f976961b344a7f86a49b1250064dfde004df98fec48408bc94a3a`
- 许可证：GPL-2.0-only（源码包 `LICENSE`）
- 依赖：`gmp/6.3.0.1`、`ntl/11.6.0.2`；W0 已在 `ohpcd` 核验两个依赖的 recipe 可用。
- 构建系统：Autotools；默认静态构建，使用包内 PolyLib/isl，关闭 PET、GLPK、cddlib、TOPCOM 可选集成。

## 适配实现

- E007 补丁覆盖主工程、isl 和 PolyLib 的 `config.guess/config.sub`，共 6 个平台识别补丁。
- native OHOS 构建仅在 `settings_build.os == "OHOS"` 时通过 `/system/bin/sh` 启动官方 configure，并保留 Conan 生成的完整参数；Linux/WSL 交叉构建仍使用 Conan Autotools 默认流程。
- E011：`config.status` 内嵌的 `(umask 077 && mktemp/mkdir)` 子 shell 会覆盖构建期外层 umask，HMDFS 上生成的 0700 临时目录随后不可写。补丁 0003（主工程）、0006（isl）、0007（isl/interface）、0011（PolyLib）把生成模板里的 `umask 077` 改为 `umask 022`（与 adns/aespipe 同类先例一致）为主修复；配方中外层 `umask 002` 保留仅作兜底。`/data/local/tmp` 不可假设可写。
- 通过 `_XOPEN_SOURCE=700` 修复 isl 的 `ffs()` configure 探测。
- 静态主包保留 `barvinok`、`polylibgmp`、`isl`，并为内嵌 isl 的 Python ctypes 回归测试额外生成独立共享 isl 测试库；该测试库不改变最终静态包形态。
- 0008 通过 `isl/python/isl.py.top` 读取 `ISL_PYTHON_DLNAMEDIR`，由配方把独立共享 isl 测试库路径注入运行环境，避免直接修改生成的 `isl.py`；上游裸 `except:` 会吞掉首次 `cdll.LoadLibrary` 的真实异常并静默回退 `CDLL(None)`（表现为误导性的 `so=<python 主程序>` 符号未找到），0008 在回退前把原始异常与 `find_library` 结果打到 stderr，使 CI worker 日志可见真实 dlopen 错误。
- 0012 `polylib/errors.c` 修复上游在 `-DNDEBUG` 下把 `pthread_once`、`pthread_key_create`、`pthread_setspecific` 放在 `assert` 副作用中的问题，避免 PolyLib 异常栈未初始化导致顶层测试 SIGSEGV。

## 失败排查与可迁移经验

1. profile 将 `CONFIG_SHELL`/`SHELL` 指向不存在或不能正确执行 `pwd` 的 bash 时，Autoconf 报 `getcwd`/working directory 错误；native OHOS 应使用 `/system/bin/sh`，并先核验 shell 路径。
2. HMDFS 下 `umask 077` 创建的 configure 临时目录可能出现 `drwx--S---`，随后 `config.status` 无法写入 `subs1.awk`（`Permission denied`）；先保留 `config.log`/失败目录并检查实际权限，不要只看 `C compiler cannot create executables` 摘要。判定方法是同一目录内分别用 `umask 077` 与 `umask 022` 做 `mktemp -d` + 写入的最小复现。
3. 只加载 `conanbuild.sh` 运行测试会导致 GMP 符号找不到；测试必须加载 `conanrun.sh`，并补充主工程、PolyLib、isl 和 zsolve 的 `.libs` 到 `LD_LIBRARY_PATH`。
4. 静态 OHOS 包直接运行 `isl_test_python.py` 会因 `isl_dlname=''` 无法通过 ctypes 加载；独立共享 isl 测试库可验证 Python 绑定，而不会把全部静态测试改成共享链接。
5. CI 预下载脚本对 `barvinok-0.41.9.tar.bz2` 的连字符文件名存在截断行为，曾把 404 页面写入错误缓存键；恢复时同时核验缓存文件名、文件大小和 SHA256，不能只相信“已缓存”。
6. E135（ELF 签名）：本地 W3 全绿的 `isl_test_python.py` 在 CI worker 上挂为 `LoadLibrary(...libisl.so.23.5.0): Permission denied`，且上游 `isl.py` 的裸 `except:` 吞掉该异常后回退 `CDLL(None)`，报出误导性的 `Symbol not found: isl_ctx_alloc so=<python 主程序>`。定位靠两步：0008 升级回显真实 dlopen 错误 + 配方在 make check 失败时把 `isl/isl_test_python.log` 打到控制台。worker 的 HNP python 拒载未签名 .so（本机 python.org HNP 放行）——修复为配方内 `_sign_ohos_shared_library`：llvm-objcopy 清旧段 → binary-sign-tool 自签（签名是该文件最终一次修改，符合 ELF 签名操作顺序）。

## 鸿蒙端验证

验证环境为 `ssh hm` 的原生 HarmonyOS PC arm64 hishell，远端 worktree 为
`/storage/Users/currentUser/ws/barvinok-0.41.9`，使用 OHOS profile 和 Conan 2.29.1。

- `preflight_check.sh barvinok/0.41.9`：通过。
- `ohc-run.py conan-verify barvinok 0.41.9`：G1、G0、G2、G3、G4 通过；L2、L4、L5 因无 cache 路径跳过，不能表述为已通过。
- W3 本地 CI：通过；证据来自 `finish` 的本地 CI 模拟结果和归档测试报告。
- 内嵌 isl：15/15 通过。
- barvinok 顶层测试：10/10 通过。
- `test_package`：CMake 公开 C API 测试 1/1、安装后 `iscc` 功能测试 1/1 通过。
- 上游 Automake 计数目标合计 25/25（100%），新增消费者测试 2/2（100%）。

## 当前限制

- 尚未推送分支、创建远端 PR 或运行远端 CI；因此不能把“本地鸿蒙 W3 通过”表述为“平台评审已通过”。本轮将 0008 和配方重构后尚未重新取得鸿蒙 W3 证据。
- `finish` 的 Step 8 `gen_summary` 触发框架现有 `'str' object has no attribute 'append'`；未手工修改 `SUMMARY.md`。
- Step 10 关于 `packaging/` 和 `.staging-verified` 的提示属于旧工作流文件，当前归档规范已将其标记为弃用；未为消除提示而加入废弃文件。

**编译结束**：2026-08-27
**当前状态**：补丁重构后的原生 OHOS W3 已重跑通过（12:53，.ci-result.json exit_code=0；上游 25/25、test_package 含 `set -eu` 修改后的 conan test 复验通过）；W4 独立审计 P0=0/P1=0。归档标记 `pending_ci`，远端 CI 绿后按 post-merge 流程升级 `built`/`published`。
---

**编译结束**: 2026-08-27 12:00
**最终状态**: pending_ci

7. E135 第二/三迭代（CI #33756/#33806 与本机对照实验）：
   - `binary-sign-tool -selfSign 1` 自签 isl 本体后，worker 仍拒绝，且报错名以绝对路径开头。musl 加载失败的报错形态可区分拒绝位置：依赖链失败报 soname 并带 `(needed by ...)` 后缀；只有 dlopen 的顶层文件被拒时才直接报调用方传入的绝对路径。据此判定 #33806 是**顶层库自身被 worker 拒绝**，而非 libgmp 依赖。
   - 此前 "无法拿到完整错误" 实为配方自己的 `probe_output[:400]` 截断了 OSError 全文（回溯前缀恰好吃满 400 字符）。教训：诊断输出必须按行结构化、单行短（≤80 字符）、把 reason 放尾部切片保留，禁止对多行 traceback 做整体截断。
   - 本机 08-28 下午曾出现"上午签名中午后被拒"的**假象**：真实原因是诊断实验把 `llvm-objcopy --remove-section .codesign` 作用到了 conan 缓存里的制品原件（`libgmp.so.10.5.0` 518528→514432 字节），签名随内容失效。`conan remove gmp/6.3.0.1 -c && conan download gmp/6.3.0.1 -r=ohpcd` 还原后，2026-08-12 发布的旧签名照常加载。教训：**任何 objcopy/签名类写操作只对副本目录做，绝不指向 `~/.conan2/p/*/p` 缓存路径**；诊断前先 `stat` 比对目标文件大小/时间，防止把自己的实验当平台行为。
   - 修复（配方代 `18a43ac0` 之后）：`_prepare_ohos_shared_dependency_chain` 解析 `llvm-readelf -d` 的 NEEDED，非系统项（libc.so 等在 `/system/lib(64)` 存在的跳过）从依赖包目录 **dereference 复制**为同名普通文件放进 isl 的 `.libs`，逐个重新自签；`_probe_ohos_dlopen` 先依赖后顶层逐文件短行判决，仅 isl 顶层失败致命。isl 无 RPATH/RUNPATH，`.libs` 已在探针与 `make check` 的 `LD_LIBRARY_PATH` 最前，搜索命中确定性可推。`test_package` 同样问题（`test_barvinok` 动态 NEEDED ntl/gmpxx/gmp）由 `test_package/conanfile.py::_prepare_ohos_signed_runtime_dir` 处理：对 test 可执行文件与 `iscc` 做 NEEDED 闭包，逐个复制+自签到 `build/signed-libs`，ctest 经 `TEST_PACKAGE_LD_LIBRARY_PATH`（CMakeLists 带守卫的 `set_tests_properties ENVIRONMENT`）与 iscc 驱动的内联 `LD_LIBRARY_PATH` 前缀生效。本机验证：isl 15/15 + 顶层 10/10 + ctest 1/1 + iscc 断言，探针仅拒"缓存被污染件"，自签链全 OK。
   - **worker 策略定案（#33869，CI-006，结构化探针首次全量回显）**：三条判决全部 `Permission denied`——(a) 本配方构建期新自签的 `.libs/libgmp.so.10`；(b) 制品仓发布链签名的 `p/gmpaa.../lib/libgmp.so.10`；(c) 新自签的 `.libs/libisl.so.23.5.0` 顶层。即 **worker 的 `dlopen()` 拒载一切用户目录 .so，与签名无关**（连同 H1"旧签名依赖"与 H4"软链接"一并排除）。但 #32474 的 14/15 通过证明同一 worker 上 **exec 时加载**（进程 NEEDED）同样这些文件正常——被禁的是 dlopen 代码路径本身。
   - 降级方案演进（不改测试实质，worker 每一步都有日志判决）：
     a) **LD_PRELOAD 被 worker 忽略**（#33895，CI-004）：`make check` 带 `LD_PRELOAD=<自签 isl>` 执行时 14/15 通过（证明**新自签库的 exec-NEEDED 加载在 worker 可用**），但 python 测试里主 dlopen 仍拒、`find_library=None` 后 `CDLL(None)` 报 `isl_ctx_alloc` 找不到（so=python3 主程序）——预载库没有进入进程，musl 语义与 glibc"preload 静默失败继续跑"一致。
     b) 最终方案 = **嵌入式 Python 启动器**：`isl/Makefile.am` 的 `PY_LOG_COMPILER = $(PYTHON)` 允许用 `make check PYTHON=<launcher>` 换解释器。launcher.c（配方内生成、构建目录内编译）以 NEEDED 直接链 `libisl.so.23` 与 HNP `libpython3.12.so`（rpath），启动即把自签 isl 映射进进程全局符号域；launcher 内 `PySys_SetArgvEx`（先 `Py_DecodeLocale` 转 wchar_t——直接传 char** 会段错误/乱码 argv）+ 脚本目录插入 sys.path 复刻真实 python 语义。上游 0008 链路最终走 `CDLL(None)` 命中全局符号，测试执行真实 isl 计算。
     c) 本机验证（同一 musl 家族）：`SCOPE OK`（无 dlopen、无 LD_PRELOAD 下 `CDLL(None).isl_ctx_alloc` 解析成功）；用配方方法 `_build_ohos_isl_python_launcher` 直接产出 launcher 并跑真实 `isl_test_python.py` rc=0。`AM_TESTS_ENVIRONMENT` 自带 `export PYTHONPATH=interface`，嵌入式解释器继承，`import isl` 无需额外注入。
   - 知识沉淀候选（待 CI 定案后评估【知识库扩展】）：E135 需增补"worker 上 dlopen 与 LD_PRELOAD 双拒、仅 exec-NEEDED 可加载用户新自签库；ctypes 类测试的嵌入式启动器配方模式（`make check PYTHON=<launcher>`）；musl 报错形态判据（顶层绝对路径 vs `soname (needed by ...)`）"；本 PR 内先以 notes 留档。
8. 路径 B 归并（赛事口径，2026-08-28）：本包新解决经验已按"知识库基于提交的三方库项目、draft 随正常 PR 提交"的运营口径并入本 PR——新增配对草稿 `knowledge/drafts/E2166-draft-7A4A.{kv,md}`（worker dlopen/LD_PRELOAD 双拒边界 + musl 报错形态判据 + 诊断/缓存红线）与 `E2167-draft-7A4A.{kv,md}`（嵌入式 python 启动器配方模式，含 prescan 派生规则）；路径 B 申请正文随档 `reports/issue-body.md`（.gitignore 的 reports/ 规则按 appconfig 先例 -f 跟踪）。PR 前缀与适配路径字段同步改为【知识库扩展】/路径 B（含 A）。
9. sourceforge 出口不稳定（2026-08-28 晚，CI 连续 IncompleteRead）：worker 与本机均出现 sourceforge CDN 传输到 ~65% 掐线（nchc 镜像本机实测 SSL UNEXPECTED_EOF；jaist 在 worker DNS 不解析 #34033；白天 15-21 点同链路完全正常，晚高峰劣化）。框架预下载对 sourceforge 是透传（`build_and_test.sh` `get_mirrors()` 该分支返回 `[url]`，无国内镜像映射），不会兜底。配方两级加固：① `source()` 主路径向 conan 下载器传官方镜像网候选（nchc/cytranet/freefr，同域名族符合 R39）+ retry=3/retry_wait=15；② 主路径全挂时 `_resumable_source_download()` 用 `Range: bytes=<已收字节>-` 断点续传跨 8 轮×多 URL 拼接，sha256 强校验后才解压（掐线特征是固定位置截断，续传可收敛而重试/换镜像不能）。conandata.yml 保持官方单 URL；`conan source` 与续传路径本机实跑通过（189 文件展开、临时文件清理）。
