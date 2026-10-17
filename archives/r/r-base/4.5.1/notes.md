# r-base 4.5.1 HarmonyOS 适配笔记

## 范围

使用 CRAN 官方 R 4.5.1 源码，在 OHOS aarch64 设备原生构建。首轮关闭当前设备无完整验证条件的 X11、Tcl/Tk、Java、readline、recommended packages、ICU 和图形格式依赖。

## 构建策略

- 构建树、staging 和 TMPDIR 放在 `/data/storage/el2/base`。
- C/C++ 使用设备 HNP clang；Fortran 使用 `flang-ohos/20.1.0`。
- 上游测试入口为 `make -j1 check`。
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
