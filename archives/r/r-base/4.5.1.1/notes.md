# r-base 4.5.1 HarmonyOS 适配笔记

## 范围

使用 CRAN 官方 R 4.5.1 源码，在 OHOS aarch64 设备原生构建。首轮关闭当前设备无完整验证条件的 X11、Tcl/Tk、Java、readline、recommended packages、ICU 和图形格式依赖。

## 构建策略

- 构建树、staging 和 TMPDIR 放在 `/data/storage/el2/base`。
- C/C++ 使用设备 HNP clang；Fortran 使用 `flang-ohos/20.1.0`。
- 上游测试入口为 `make -j1 check`；本版本补充执行 `tests/Makefile.common` 的 `test-all-devel` 族目标（DateTime/Demo/Primitive/Random/Regexp/Translation/Conditions/Misc-dev/Internet2/CRANtools/Internet-dev/System/UTF-8/Iconv），上游 `tests/*.R` 全量 68 项中实际执行 62 项全部通过；reg-large.R 被 OOM kill（32GB 设备 < 60GB 需求），5 项因具体技术原因不可执行（推荐包依赖×3、Windows-only×1、Gct harness 尾部×1），详见 reports/test-report.md §3.3 与 reports/upstream-make-check-devel.log。
- test_package 真实执行 R 脚本，覆盖版本、算术、PCRE2、矩阵、gzip 和 iconv。

## 当前状态

Round 12 设备完整 CI 已通过；Web Review 01 指出的可移动依赖与 TLS 信任链问题正在 Round 13 修复，最终状态以 Round 13 权威日志为准。

## Round 3 libcurl 接线

从 Conan curl 及其传递依赖的 cpp_info 动态构造 CURL_CPPFLAGS/CURL_LIBS，不写入缓存绝对路径；configure 前编译并运行 curl_https_probe.c，必须输出 CURL_HTTPS_CONSUMER=PASS。

## Round 4 alignof 能力兼容

截至 2026-08-08 检查 R 官方 SVN trunk、R-4-5-branch，以及 CRAN R 4.5.2、4.5.3、4.6.0、4.6.1，`dcigettext.c` 仍保留空的 C23 分支，没有可回移的正式上游修复。本版本采用编译器能力/版本守卫：仅 Clang 18 之前且 C23 分支中未定义 `alignof` 时，将其映射为标准 `_Alignof`；不按 OHOS 平台名分支，不影响 Clang 18+、GCC 和旧 C 标准路径。

## Round 5 权威本地时区契约

设备只读调查确认 `/usr/bin/param get persist.time.timezone` 返回 `Asia/Shanghai`；系统 `/system/etc/zoneinfo/tzdata` 为 OpenHarmony 打包格式，不是 R 可直接遍历的 Olson 目录。R 官方源码自带 `src/extra/tzone/zoneinfo.zip`（含 `zoneinfo/Asia/Shanghai`），因此启用 `--with-internal-tzcode`，以 R 自带、版本固定的 IANA 数据库作为 TZDIR 能力来源。最小 patch 在传统发现链前，仅当 `param` 命令存在、返回单一非空 IANA 名称且该名称在活动 tzdir 中真实存在时接受并缓存；否则透明回退原上游逻辑。未硬编码 `Asia/Shanghai` 或 UTC。

## Round 6 tzdir 候选优先级

Round 5 证明 `/etc/zoneinfo` 目录虽存在，但没有 `Asia/Shanghai` 展开文件，会遮蔽 R internal zoneinfo。0003 patch 改为先读取权威 parameter 名称，再按“R internal zoneinfo → 显式 TZDIR → 标准系统目录”的顺序，仅选择真实包含该 IANA 文件的候选，并将选中目录写入 TZDIR。具体时区值仍来自设备 parameter，未固定 TZ。


## Round 7–12 上游测试与启动器闭环

采用设备原生 `make -j1 check`。补丁 0004 保留 pipe `close()` 状态 oracle，0005 回移 R trunk r88881 的 subnormal `pretty()` 数值性质，0006 让 public/internal `bin/R` 从相邻完整布局解析可移动 R home。Round 12 完整 CI exit 0，consumer 六个功能域通过。

## Round 13 可移动运行时与 TLS 契约

最终 package 不再依赖构建机 Conan cache：`ldpaths` 只加入 `${R_HOME}/lib`，package 内复制运行时所需 `libcurl.so`，并扫描拒绝 `/storage/Users/currentUser`、`.conan2` 与 `.conan-build-r-base`。`R_SHARE_DIR`、`R_INCLUDE_DIR`、`R_DOC_DIR` 均从运行时验证后的 R home 派生。package 自带设备系统的公开 CA bundle 副本，launcher 仅在用户未显式设置 `CURL_CA_BUNDLE` 时选用它，未关闭 peer/host verification。

consumer 将最终 package 复制到不同绝对路径，在清空 R_HOME/RHOME、资源目录、CA 和 LD_LIBRARY_PATH 等环境后，使用移动副本验证 R、Rscript、RHOME、share/include/doc、PCRE、gzip、iconv、matrix 和真实 CRAN HTTPS，并核验全部 ELF NEEDED/RPATH/RUNPATH。测试不依赖原 package 或原依赖 cache 的运行时路径。

本归档只承诺 R 解释器、基础运行时和 HTTPS consumer 能力。清理后的 Makeconf 不再提供构建机依赖与 Fortran 工具链路径，因此不声明移动包可用于编译下游 C/Fortran R 扩展；该限制是显式能力边界，不以失效配置冒充支持。

## Round 14-16 移动运行时与 Rprof 修复

Round 14-15 完成静态 Flang runtime 污染处理（改用远端 external OpenBLAS 精确 binary）、私有 curl prefix-map 构建与 OpenSSL compiler metadata 精确分类，internet.R 真实 HTTPS OK。

Round 16 修复三条新轴：Rprof memory profiling 空事件（0008：ITIMER_PROF 初始延迟异常探测，回退 RPE_ELAPSED ProfileThread）；test_package 移动后 libopenblas.so.0 SONAME 缺失（conanfile 补充复制）；moved-r-base 的 R.home("share") 固化 //lib/R/share（0009：Makefile.in install sed 对资源目录改用范围限定替换）。Round 16 retry-03 完整 CI exit 0，全部 marker PASS。

## 4.5.1.1 依赖项修复（Round 17）

本版本不改动任何 patch 与功能语义，只修复 4.5.1 归档中影响下游依赖消费者与 CI 复现性的两处缺陷：

1. **test_package 硬编码宿主前缀根**。`test_package/run_test.sh` 无条件执行 `stat -c %a /storage/Users/currentUser/.harmonybrew` 并对该根 `chmod 000`；一旦目标 worker 上不存在该目录，`set -e` 会让整条测试在遮蔽步骤前直接中止，导致 r-base 无法在任何未人工预置该目录的机器上通过 CI，依赖它的下游包也因此过不了依赖闸。现改为“该根存在时才遮蔽”，并如实报告 `R_BASE_HARMONYBREW_MASK=PASS` 或 `R_BASE_HARMONYBREW_MASK=SKIPPED (root absent: ...)`；`.conan2` 缓存根遮蔽保持无条件，可移动性负向校验强度不降低。
2. **归档混入构建产物**。`test_package/` 下曾提交 `moved-r-base/`（87 MB / 2025 个文件的被测包完整副本）、`conanbuild.sh`、`conanrun.sh`、`conanbuildenv-release-armv8.sh`、`conanrunenv-release-armv8.sh`、`deactivate_conanbuild.sh`、`deactivate_conanrun.sh`。这些是 Conan/测试运行时生成物，必须由 CI 现场生成；入库既污染归档，又使测试结果随残留状态漂移（4.5.1 归档 87 MB 几乎全部来自它）。
3. **测试产物自清理**。`conan create`/`conan test` 对仓库内 `test_package` 直接以该目录自身作为 build_folder，`run_test.sh` 的 `moved-r-base` 因此落在源码树里（本地 CI 每跑一次就复现一次）。本版本在 `test_package/conanfile.py` 的 `test()` 中用 `try/finally` 无条件 `rmtree` 清理，从机制上消除归档污染，而不是依赖人工记得删除。

本版本归档只保留纯输入：`conandata.yml`、`conanfile.py`、`manifest.yaml`、`notes.md`、`patches/`、`res/`、`test_package/{conanfile.py,run_test.sh,test_r.R,MANIFEST.yml}`。

上游源码、9 个 patch 与全部构建配置与 4.5.1 完全一致，未做任何功能取舍，设备原生 `make -j1 check` 与可移动性闭环结论沿用 4.5.1 记录。

## 结束

最终状态：built —— 4.5.1.1 归档清理与 test_package 可移植性修复完成，本地 W3 完整 CI 两次从源码构建通过（Total 1 / Success 1 / Failed 0 / Pass rate 100.0%），等待 release 流水线发布到制品仓。

验证记录：

- 本地 W3 日志：`reports/w3-local-ci.log`；同目录 `.ci-result.json`（`log_sha256=2f59abdf725af7b0b037fbfab54a627261f8de491e25f4f8b1e12480147c8038`）。
- 测试报告：`reports/test-report.md`；自审记录：`reports/audit-result.json`。
- `.staging-verified` 依据 conan `test_package` 的验证结论置位（打包后的 `bin/R`/`bin/Rscript` 从移动副本运行、8 条 stopifnot、全量 ELF NEEDED/RPATH/RUNPATH 扫描），非 legacy `_step8_staging` 的 `--version` 冒烟。
- 知识沉淀：`knowledge/drafts/E545-draft-*.{kv,md}`（test_package 硬编码宿主绝对路径导致 CI 中止）、`E546-draft-*.{kv,md}`（仓库内 test_package 的 build_folder 产物污染）；`manifest.yaml: knowledge_gained` 中对应两条已引用 E545 / E546。

---

**编译结束**: 2026-09-30 13:27
**最终状态**: built
