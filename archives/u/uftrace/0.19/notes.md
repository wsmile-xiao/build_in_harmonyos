# uftrace 0.19 适配笔记

## 库概述
- 上游: https://github.com/namhyung/uftrace
- 版本: v0.19
- 许可证: GPL-2.0
- 构建系统: 手写 `./configure` 脚本（**非 autotools**，无 config.guess/config.sub）生成 `.config`，再由 Makefile 消费
- 产物: `uftrace` 主二进制 + 5 个 `libmcount*.so` 插桩库（`libmcount.so`、`-nop`、`-fast`、`-single`、`-fast-single`）

## W0 依赖结论
- 依赖数量: 0 个**必需**依赖（上游明确"can be built without any external libraries"）
- 可选依赖（本版全部禁用）:
  - libelf / libdw（elfutils 0.195，仓库已适配 built）
  - capstone（5.0.7，已适配）
  - ncurses（6.6，已适配）
  - libpython / libluajit / libunwind / libtraceevent（均未适配，OHOS 上风险高）
  - libstdc++（cxa_demangle，OHOS 用 libc++ 而非 libstdc++）
- 是否需要拆分依赖适配: 否（第一版无外部依赖，可后续渐进启用 elfutils/capstone/ncurses）
- 阻塞点: 无

## W1 源码/构建系统分析
- 手写 configure：开头 `if [ $(uname -s) != "Linux" ]` 检查，OHOS 上 `uname -s` 返回 `HarmonyOS`（见 E007/E140/E160），需补丁放宽
- 依赖探测走 `check-deps/`（编译/链接探测程序，结果以文件形式落盘），`make -si` 容错，探测失败自动 OFF
- libelf 用 `-lelf` 直接链接；libdw/ncurses/capstone 用 `pkg-config` 探测
- 无 libelf 时 uftrace 内置 `symbol-rawelf.c` 兜底解析器，可正常编译运行
- 交叉编译: `--arch=aarch64` + 环境变量 `CC`；configure 读 `CC=${CC:-${CROSS_COMPILE}gcc}`
- 源码中无 `pthread_cancel`、无 glibc `error()`、无 `-ldl` 依赖，dlopen/dlsym（musl 支持）为运行时动态符号解析
- `doc/` 无预生成 man 页（仅 .md/.html），`make install` 会走 pandoc 构建 man 页 → 改用 package() 手动复制产物
- 构建系统移植风险集中在 `-pg`/`-finstrument-functions`/`-fpatchable-function-entry` 插桩与 aarch64 汇编（`arch/aarch64/`），需真机验证

## 适配要点
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 "uftrace is only supported on Linux" 退出 | OHOS `uname -s` 返回 `HarmonyOS` | 补丁 0001: `uname -s != "Linux"` → 同时接受 `HarmonyOS` |
| 2 | 可选依赖链接失败/拖慢构建 | libpython/libstdc++ 等在 OHOS 上不适用 | `--without-*` 全部禁用，走内置 rawelf 兜底 |
| 3 | `make install` 依赖 pandoc 构建 man 页 + ldconfig | OHOS 无 pandoc，install 目标附带 doc | package() 手动复制 uftrace + libmcount*.so |
| 4 | OHOS lld 加载 libxml2.so.16 失败 | SDK lld 的动态依赖不在默认库路径 | 构建期前置 `LD_LIBRARY_PATH=<sdk>/native/llvm/lib`（同 etsh/abuild） |
| 5 | 鸿蒙 XPM 要求签名 | 可执行文件与 .so 需代码签名 | package() 内 `binary-sign-tool` 对产物签名（同 elfutils/capstone） |
| 6 | make 报 `misc/version.sh: Permission denied` (Error 127) | HMDFS 上 chmod 不生效，脚本无执行位（E087） | 补丁 0002: Makefile 中 `version.sh`/`gen-autoargs.py` 改用 `sh`/`python3` 前缀执行 |
| 7 | `utils/symbol.c:730` 编译报 `strcmp` 少参数 | rawelf 兜底路径 upstream typo：`strcmp` 应为 `strlen`（libelf 路径正确，禁用 libelf 才暴露） | 补丁 0003: `symbol-rawelf.h` 的 `elf_for_each_comment` 宏 `strcmp`→`strlen` |
| 8 | make 报 `ar: inaccessible or not found` (Error 127) | OHOS 无 GNU ar，工具链在 `/data/service/hnp/bin` 但不在 make 的 PATH（E012） | build() 注入 `PATH=/data/service/hnp/bin` + `AR=llvm-ar` |
| 9 | 上游单元测试 96 个用例整体 SIGSEGV | OHOS `dl_iterate_phdr` 对 non-PIE 主程序返回错误的 `dlpi_addr`（堆地址），`unittest.c` 据此算出的 `load_base` 把每个 `func_*` 测试函数指针都变成野指针 | 补丁 0005: unittest 编译加 `-no-pie` + 强制 `load_base=0`（non-PIE 下 `st_value` 本就是绝对地址）；签名后 fork 子进程可正常运行，保留上游 fork 测试隔离 |
| 10 | 符号表重建越界写 | 符号表 func_* 符号（102）> 测试槽位（96），`update_test_cases` 越界写 | 补丁 0005: 加 `i >= num` 边界检查 |
| 11 | 签名重排 section 使测试用例表指针失效 | `binary-sign-tool` 重排 ELF section，`uftrace.unit_test` section 里的绝对 name/func 指针失效 | 补丁 0005: 强制从符号表重建测试用例表 |
| 12 | `mcount_agent` 测试死循环 | OHOS 禁止 Unix domain socket `bind()`（EPERM）+ `/tmp` 只读，mcount agent 永远起不来，`while(!agent_run)` 死循环 | 补丁 0009: agent 未启动时超时返回 `TEST_SKIP` |

## 运行时风险（真机验证重点）
- uftrace 动态追踪依赖 perf_event / ptrace。strace 6.19 经验表明 OHOS SELinux `adhoc_bin` 域可能禁止 ptrace（E009）；perf_event 可用性未验证
- 静态插桩（`-pg`/`-finstrument-functions`）需重新编译目标程序，不依赖 ptrace，可作为 OHOS 上的可用路径
- libmcount 运行时查找依赖 `-L <path>` 选项或编译进二进制（`INSTALL_LIB_PATH`）的绝对路径；交叉编译重定位后需用 `-L` 显式指定

## 验证结果（真机 shadow CI，2026-09-18）
- 真机 IP 10.62.178.77:2222，隔离 job `uftrace-0.19-shadow-20260917`，profile ohos-aarch64
- 结果全绿：
  - `L0_RESULT=pass: all checks passed`
  - `L1_RESULT=pass: upstream tests + test_package executed`
  - `L2_RESULT=pass: uftrace --version OK`
  - `L4_RESULT=pass: patches clean`
  - `L5_RESULT=pass: bin/ has content`
  - `Total: 1  Success: 1  Failed: 0`
- 上游单元测试（`tests/unittest`，96 个 TEST_CASE）：**93 ran successfully / 0 failed / 3 skipped / 0 signal caught**
  - 3 个 SKIP 均为 OHOS 平台硬限制，有具体技术原因：
    - `mcount_agent`：OHOS 禁止 Unix domain socket `bind()`（EPERM），agent 无法启动 → 补丁 0009 超时 SKIP
    - `mcount_pmu_event`：OHOS 无 perf_event 权限（`Permission denied`）→ 测试自行 SKIP
    - `symbol_read_build_id`：OHOS 无对应 build-id 读取环境 → 测试自行 SKIP
- 产物：`bin/uftrace` + 5 个 `libmcount*.so`，全部经 `binary-sign-tool` 代码签名成功
- 上游功能测试（`tests/runtest.py`，12 个）未执行：需要 perf_event 动态追踪 + 可插桩目标程序，OHOS 上 perf_event 权限被拒（`failed to open 'cycles' perf event: Permission denied`），属平台能力边界

## 遗留 / 后续
- 动态追踪（perf_event）与静态插桩（-pg）的实际追踪能力，需在真机上用 `uftrace -L <lib/uftrace> <program>` 做端到端验证（静态插桩不依赖 perf_event，可作为 OHOS 上的可用路径）
- 可选特性（libelf/libdw/ncurses/capstone）仍为禁用状态，可渐进启用（对应依赖仓库已适配）
- issue 编号待补

---

**创建日期**: 2026-09-17
**状态**: built（真机 shadow CI 全绿：L0/L1/L2/L4/L5 pass；上游单元测试 93/96 通过、0 失败、3 平台 SKIP）
