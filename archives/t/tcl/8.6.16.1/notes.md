# tcl 8.6.16.1 适配 notes（R37 递增修订版）

## 版本说明（R37）
- 官方 main 已有 `archives/t/tcl/8.6.16`（2026-07-29 合入，status=built）。同版本配方目录不可复用（L0j 门禁、一库一版本），本修订以 **8.6.16.1** 为适配修订版本号提交。
- **上游源码仍为 tcl 8.6.16 官方 release tarball**（SourceForge 官方源，sha256 `91cb8fa6…a14a5`，与 8.6.16 配方一致）；补丁、构建、测试逻辑继承 8.6.16 已合入配方的 OHOS 适配成果。

## 继承的 OHOS 适配要点（自 8.6.16 配方，逐项保留）
1. **系统识别**：build() 生成 `uname` shim（`-s`→Linux、`-r`→6.6、`-m`→aarch64，其余透传 `/system/bin/uname`）置于 PATH 前，configure 另传 `tcl_cv_sys_version=Linux-6.6` 缓存，使 `SC_CONFIG_SYSTEM` 走 Linux 分支启用共享库。
2. **E011**：主 configure 及 `pkgs/` 全部子包 configure 的 `umask 077` 文本替换为 `022`，并 `os.chmod(0o755)` 恢复可执行位（HMDFS 重写文件丢 exec 位）。
3. **HMDFS noexec**：改生成的 Makefile，子包 configure 统一经 `bash $$i/configure` 显式执行（直接执行报 Error 126）。
4. **DT_SONAME**：Makefile 注入 `-Wl,-soname,$(TCL_LIB_FILE)`（libtcl8.6.so 需 SONAME，L5 门禁）。
5. **-j1 构建**：OHOS 不支持 make jobserver 的 mkfifo。
6. **package() 产物**：`bin/tclsh8.6`（缺失即失败）、`lib/*.so*|*.a`、公共头、`tclConfig.sh`、`lib/tcl8.6` 运行时库（init.tcl/encoding）、`lib/tcl8` 模块目录（msgcat/tcltest——缺了 `clock format` 必挂）；`tclConfig.sh` 前缀 `/usr/local`→`${TCL_ROOT}`，由 package_info 注入解析。
7. **OHOS 签名**：`llvm-objcopy --remove-section .codesign` + `binary-sign-tool selfSign` 重签 `tclsh8.6`。
8. **package_info**：`TCL_ROOT`/`TCL_LIBRARY`/`PATH`/`LD_LIBRARY_PATH` 注入 build/run 环境，供下游 `tool_requires` 直接执行 tclsh。

## 上游测试口径（规则 5 + rule4）
- `make test-tcl`（`ERROR_ON_FAILURES=1`，任一用例失败即 tcltest exit 1 → 构建失败）全量驱动 `tests/` 的 **152 个 .test 文件**（官方 tarball 实测 `tests/` 目录 152 个，tcltest 框架；用例总数以真机 `L1_UPSTREAM_RESULT` 实跑统计为准，8.6.16 配方真机实测约 47,105 用例）；统计行 `L1_UPSTREAM_RESULT` 解析 Total/Passed/Skipped/Failed 并如实上报。
- OHOS 上 `TESTFLAGS="-skip thread-5.2"`：HMDFS pthread 对 detached thread 的 join 崩溃（上游探针），thread 语义其余用例完整覆盖。
- **环境失败白名单**（HMDFS 沙箱语义差异，与 #3521 评审接受记录一致）：`env-*`、`safe-16.`、`filename-12.7/12.8`、`io-40.`、`chan-io-40.`、`zlib-8.10`、`filesystem-1.30.3`、`cmdAH-6.3`、`socket_inet6-13.1`、`unixInit-3.1`、`fCmd-28.*`、`filename-11.17.7/11.17.8/11.18/11.19/11.20/11.22/11.23/11.24/11.25`、`filename-14.7/14.15`；精确匹配 `cmdAH-25.2.1`、`cmdAH-28.5`、`cmdAH-29.4`、`cmdAH-29.4.1`、`exec-9.1/9.2/9.5`、`exec-13.3`、`exec-14.4`、`iocmd-11.4`。**白名单外的失败仍致命**（ConanException）。
- 本修订真机实跑确认新增 6 项豁免：HMDFS 上执行**不存在的命令**返回 `EACCES`（permission denied）而非 POSIX `ENOENT`（no such file or directory），exec-9.1/9.2/9.5、exec-13.3、exec-14.4、iocmd-11.4 六用例均为该单一根因（upstream_test.log 逐一核对），精确匹配豁免。
- 上游测试 2/3 号补丁：cmdAH.test 顶层夹具与 mtime/owned 用例在 `/tmp` 只读时回退到可写构建目录，保证后续用例不被中断。

## 依赖说明
- 配方无 conan `requires`：zlib 由 OHOS 工具链 sysroot 提供（configure 检测到 `zlib.h` 即链系统 zlib，缺失时上游 `compat/zlib` 兜底）。8.6.16 配方 manifest 曾声明 `zlib/1.3.1` 但 conanfile 并未 requires，本版修正 manifest `dependencies: []`，与配方实际一致（R52 审计一致性）。

## 消费者测试
- `test.c`：C API 七断言（CreateInterp/Init/patchLevel==8.6.16/expr 2+3==5/concat 内容校验）。
- `test_tclsh.tcl`：七断言（patchlevel/算术/列表/字典/init.tcl 存在/msgcat 1.6/clock format 1970-01-01）。
- 断言合计 14；两断言文件中的 `8.6.16` 为**上游 patchLevel**（源码未变，不随配方修订号改）。

## 真机验证（2026-09-26）
- 环境：HarmonyOS PC 真机 aarch64，OHOS NDK clang 26.0.0.18（`/data/service/hnp/bin/clang`），Conan 2.29.1，profile `ci/conan/profiles/ohos-aarch64`。
- `ohc-run.py conan-verify tcl 8.6.16.1` 全门禁通过：G0/G1/G2/G3/G4/L2/L4/L5 ✅，Verdict PASS（报告 `reports/conan-verify-report.md`，2026-09-26T17:05）。
- 上游测试实跑（G2 内 `make test-tcl`）：`L1_UPSTREAM_RESULT files=1 total=47105 passed=43606 failed=55 file_errors=0 pass_rate=92.57%`；55 项失败全部命中环境失败白名单（含本修订新增 exec/iocmd 6 项，见上），白名单外 0 失败。
- 消费者测试（test_package）：14/14 通过（test.c 二进制直跑 PASS + `tclsh8.6 test_tclsh.tcl` PASS）。
- 产物核验（G4/L5）：`bin/tclsh8.6`（链接器自签）、`lib/libtcl8.6.so`（DT_SONAME=`libtcl8.6.so`）、`lib/libtclstub8.6.a`、公共头、`tclConfig.sh`（TCL_ROOT 前缀）、`lib/tcl8.6`（init.tcl/encoding）、`lib/tcl8`（msgcat/tcltest）齐备。
- 首轮验证曾因 6 项 HMDFS EACCES 语义失败（exec-9.1/9.2/9.5/13.3/14.4/iocmd-11.4），确认单一根因后精确匹配补入白名单，二轮全绿（本文件上方已有记录）。
