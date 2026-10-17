# libltdl 2.6.0 测试报告（test-report）

> 被测对象：GNU libtool 2.6.0（2026-01 alpha）源码树中的 libltdl 运行时动态加载库。
> 报告日期：2026-09-22　编译平台：HarmonyOS aarch64（clang/clang++ OHOS 定制工具链）

## 环境

- 构建系统：autotools（发布 tarball 自带 configure，无需 autoreconf 自举）
- 编译器：clang / clang++（OHOS 定制，CC=clang CXX=clang++）
- Conan profile：ohos-aarch64
- 平台：HarmonyOS aarch64（uname -s=HarmonyOS, kernel 1.12.0）
- 测试 harness 修复环境：AUTOM4TE=/storage/Users/currentUser/usr/local/bin/autom4te、
  mktemp shim（E011 HMDFS umask）、PATH 补 /bin（设备 `id` 只在 /bin）、gzip shim
  （toybox gzip 不支持 `--best` 长选项）

## 上游测试套件（R51 三步法实测，权威数据）

**测试套件**: GNU Libtool 2.6.0 testsuite（Autotest，185 个测试组，覆盖 libtool/libtoolize/libltdl）。
**运行方式**: `testsuite -j4`。
**运行记录**: 
- 修复后首轮 2026-09-22 19:46:58 → 22:51 CST（150 run = 130 ok + 20 failed / 35 skipped）
- 收尾定向重跑 2026-09-22 23:05 → 2026-09-23 00:02 CST（显式重跑全部 15 个非 XFAIL 失败组，
  全套修复）：133-146 共 12 组转 ok；106/116 复现失败；185 内层重跑含 106 硬限制仍判失败
日志: `/storage/Users/currentUser/builds/libltdl-2.6.0.work/tests/testsuite.log`（+ testsuite.dir/*/testsuite.log）

| 指标 | 数值 |
|------|------|
| 总测试数 | 185 |
| 已执行（run） | 150 |
| 通过 (ok) | **142** |
| 失败 (failed) | **8**（5 个上游 expected failure/XFAIL + 3 个） |
| 非预期失败 | 3（106 versioning_script、116 lt_dladvise——平台硬限制；185 cmdline_wrap——内层重跑含 106 硬限制，非独立失败） |
| 跳过 (skipped) | **35** |

> 修复前（2026-09-22 00:58 首跑）为 80 ok / 71 failed（66 非预期，绝大多数根因于
> 本机 autom4te 缺失 @am_AUTOM4TE@ 未替换、E011 umask、PATH 缺 /bin 等环境问题，
> 已逐一修复）/ 34 skipped。
> 组 185 cmdline_wrap 为内部重跑包装（外层计 1 组）；其内层重跑含 106（versioning_script
> 硬限制），内层 46 run = 5 failed（4 XFAIL + 106），故外层 185 仍判失败——106 硬限制的
> 传播，非独立失败。

### 跳过明细（35 组，逐项技术原因）

| 组号 | 测试 | 跳过原因 |
|------|------|----------|
| 41 | test --enable-pic | 未启用 --with-pic 配置（with-pic.at:37 条件） |
| 48, 49, 50 | F77/FC/Java convenience archives | 环境无 F77/FC/GCJ 编译器 |
| 61 | preserve duplicate convenience deps | 环境无便利归档去重前置条件 |
| 64–69 | passing OBJC/OBJCXX/F77/FC/GCJ/ML64 flags | 环境无对应编译器 |
| 79 | export from a DLL with a .def | w32/mingw 平台专属（.def/EXEEXT） |
| 81 | sys_lib_search_path on w32 | w32 平台专属 |
| 85 | both of -o prog and -o prog$EXEEXT | w32（EXEEXT 非空）平台专属 |
| 90 | cwrapper string length | w32/mingw 专属（wrapper 长度语义） |
| 95–100 | OBJC/OBJCXX/F77/FC/GCJ/ML64 inferred tag | 环境无对应编译器 |
| 103 | nocase library search | w32/msys 专属 |
| 123 | loadlibrary error messages | Windows LoadLibrary API 专属 |
| 163–165 | f77demo static/shared/static+shared | 环境无 F77 编译器 |
| 166–168 | fcdemo static/shared/static+shared | 环境无 FC 编译器 |
| 169 | darwin fat compile | darwin 平台专属 |
| 173 | darwin can lt_dlopen .dylib and .so | darwin 平台专属 |
| 174 | dumpbin -symbols section hiding | MSVC dumpbin 专属（w32） |
| 176–178 | sysroot -L SYSROOT/... | 需要 --with-sysroot 交叉工具链 |

### 失败明细（8 = 5 XFAIL + 3）

**5 个 expected failure（XFAIL，上游已声明/已知行为）**：组 84（archive-in-archive 静态库含
静态库）、101（infer-tag 不支持编译器推断）、117（lt_dlopen error messages）、124（lalib-syntax
.la 语法）、158（deplibs-ident 构建树 relpath）——XFAIL 条件见 tests/*.at 的 AT_XFAIL_IF。

**3 个非预期失败（106/116 平台硬限制 + 185=106 传播；已逐一定性，非 libltdl 缺陷）**：

1. **106 versioning_script**
   - 现象：`libtool-next-version: *** unknown OS - don't know how to interpret the 'nm' output`，
     测试在 versioning_script.at:230（grep expected_version）失败。
   - 根因：上游 `libtool-next-version.in:172-186` 硬编码 `case uname -s in` OS 白名单
     （Linux|FreeBSD|NetBSD|OpenBSD / Darwin / AIX / HP-UX / IRIX / SunOS / CYGWIN*），
     HarmonyOS（`uname -s=HarmonyOS`，testsuite.log Platform 段实证 `uname -s = HarmonyOS`）
     落入 `*)` 兜底分支直接 fatal。脚本的 Linux nm_filter 本适用于 HarmonyOS 的 GNU nm
     （binutils 2.45 输出同格式），但 OS 白名单阶段即中止——上游脚本平台检测限制。
2. **116 lt_dladvise**
   - 现象：`can't open the module libdepend! error was: file not found`（期望输出
     `resident: 2 / local: 3 / global: 4 / depend: 5 / preload: 6`，实测缺 `depend: 5`）。
   - 根因：测试 `hint_ext()` 要求 `libdepend.so` 的未定义符号 `f`/`i` 在运行时 dlopen 时
     从另一已 dlopen 的 `libglobal.so`（RTLD_GLOBAL）解析。**HarmonyOS 动态链接器不做跨
     dlopen 模块全局符号解析**——最小独立 C 样例实证：`liba.so` 以 RTLD_GLOBAL 加载后，
     引用其 `foo` 的 `libb.so` 再 dlopen 报 `Error relocating ./libb.so: foo: symbol not found`
     （RTLD_GLOBAL 与 RTLD_LOCAL 结果一致，即 RTLD_GLOBAL 语义未生效）；且 `nm -D` 证实
     libglobal.so 确实导出 `f`/`i`、libdepend.so 的 `U f/U i` 确实未定义。平台运行时语义
     硬限制，libltdl 库本身编译/链接零错误。
3. **185 cmdline_wrap（非独立失败）**：外层 185 是"低 max_cmd_len 内层重跑"包装，内层把
   含 "libtool" 关键字的 46 个测试重跑一遍；内层汇总 46 run = 5 failed（4 XFAIL + 106），
   唯一非 XFAIL 失败即 106 硬限制的传播 → 外层 185 判失败。内层其余全部 ok/skipped。

### 修复过程记录（打回修复收尾，全部为测试 harness 环境修复，配方零改动）

| 修复 | 内容 | 验证 |
|------|------|------|
| AUTOM4TE | aclocal 第 771 行 `$ENV{AUTOM4TE} || '@am_AUTOM4TE@'` 未替换（设备 autom4te 在 usr/local/bin/autom4te）；设 AUTOM4TE=该路径 | aclocal exit 0，m4/ 生成 |
| E011 HMDFS umask | config.status 用 `umask 077` 建临时目录、HMDFS 上 chmod 无效（E046）→ Permission denied；mktemp shim 重置 umask 后 exec 系统 mktemp | 测试 29 实证通过 |
| PATH 补 /bin | 设备 `id` 只在 /bin（toybox），testsuite PATH 无 /bin → 子工程 configure `am_uid=\`id -u\`` 报 inaccessible → 133-146 共 12 组失败；加 /bin | 133-146 全转 ok |
| gzip shim | 设备 gzip=toybox 不支持 `--best` → `make dist-gzip` 失败；shim 翻译 `--best`→`-9` | make dist exit 0 实证 |

## test_package 消费者验证（Conan L1 测试，实质调用 ltdl API）

test_package 源码 test.c 实际调用 `lt_dlinit()` / `lt_dlopen()` / `lt_dlsym()` /
`lt_dlexit()` 完成 libltdl 运行时动态加载闭环（R34 实质依赖，非空壳）。

- Test cases: 1
- Passed: 1
- Failed: 0
- Skipped: 0

（conan create 输出：`1/1 Test #1: test_libltdl ..... Passed 0.02 sec`，
`100% tests passed, 0 tests failed out of 1`，见 reports/conan-create.log）

## 本地 CI 与门禁

- `CI_PACKAGES='archives/l/libltdl/2.6.0' zsh ci/conan/build_and_test.sh`：exit 0
  （.ci-result.json: exit_code=0，log_sha256 见该文件）
- conan-verify：PASS（G0-G4/L2/L4/L5，见 reports/conan-verify-report.md）
- L0：通过（conanfile/conandata/test_package/MANIFEST/patch 结构完整）

## 已知限制

⚠️ 部分通过（有已知限制）：

1. **上游 testsuite 仅剩 3 个失败**（106 versioning_script 的 uname OS 白名单、116 lt_dladvise
   的跨 dlopen 符号解析——均为平台硬限制；185 cmdline_wrap 为 106 硬限制在内层重跑的传播），
   均有源码行级/最小样例证据，非 libltdl 缺陷。
   libltdl 库 configure+make 阶段零错误。CI 环境不执行上游 testsuite（conan create 仅编译
   验证 + test_package 消费者冒烟），故不影响发布。
2. **35 个跳过项**为环境无 F77/FC/GCJ/OBJC 编译器或 w32/mingw/darwin 平台专属测试
   （逐项原因见上方跳过明细表），非适配问题。

## 结论

✅ 上游 testsuite 已按 R51 全量清点并实测；修复 AUTOM4TE / E011 umask / PATH /bin / gzip
后权威通过率 **142/150 run（94.7%）**、185 组口径 **76.8%**（另 35 跳过 + 5 XFAIL + 3 个：
106/116 平台硬限制 + 185 为 106 硬限制传播）。失败项全部为上游 XFAIL 或平台/上游脚本硬
限制，无 libltdl 编译链接缺陷；
test_package 消费者测试 1/1 通过（实质调用 ltdl API）。配方验证通过，可标记 published。
