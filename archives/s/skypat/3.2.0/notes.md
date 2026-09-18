# skypat 3.2.0 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac/Makefile.am；GitHub 发布包为 git snapshot，无预生成 configure）
- 编译日期: 2026-09-16
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，target aarch64-linux-ohos）
- 状态: built

## 编译步骤

配方（`conanfile.py`）内全自动：

```bash
# 1) 引导 configure（GitHub 发布包为 git snapshot，无 configure）
#    构建期 tool_requires: automake/1.18（aclocal+automake）、libtool/2.5.4（libtoolize）
#    CI 干净 PATH 仅有 SDK autoconf/autoreconf/m4，缺 aclocal/automake/libtoolize
bash -e ./autogen.sh

# 2) 配置（显式三元组规避 config.guess 不识 HarmonyOS；zlib 未被源码使用）
./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
    --without-zlib --enable-clock_gettime --enable-shared --disable-static \
    --prefix=<package_folder>

# 3) 构建与安装（HMDFS 无 jobserver FIFO，固定 -j1）
make -j1
make install
```

> configure 阶段使用构建目录内私有 mktemp wrapper（仅注入 conanbuild 环境 PATH），
> 规避 HMDFS 上 toybox `mktemp -d` 目录不可写导致 config.status 中止（E011 的
> `mktemp -d` 变体，同 cln 1.3.7 先例）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan create` 报错 `Mutex.inc:46: error: 'tryLock' is missing exception specification 'throw()'` | profile `compiler.cppstd=17` 的 `-std=c++17`（位于命令尾部，覆盖 Makefile 内的 `-std=c++11`）；C++17 将异常规范纳入函数类型并要求声明/定义匹配，而 `tryLock` 定义漏写 `throw()` | 补丁 0003：`Mutex::Status Mutex::tryLock() throw()`，与 `Mutex.h` 声明一致（`lock/unlock` 上游本就带 `throw()`） |
| 2 | `PERFORM()` 性能示例输出伪时长 `[ TIME (ns)] 156863262856`（fib(10) 报 156.9 秒，各测量块相同），Release 下静默、断言可能中止 | 头文件与系统调用号均可用（编译通过）但 `perf_event_open` 运行期返回 `-1/EACCES`（HW/SW 事件均拒绝，`perf_event_paranoid=-1` 不放行）；上游不检查 fd 与 `read()` 返回值，读取未初始化栈缓冲 | 补丁 0001/0002：运行期能力探测 + 优雅降级（计数=0、计时回退 clock_gettime/gettimeofday、stderr 报告一次） |
| 3 | `./config.status: line 867: ./confXXXXXX/subs1.awk: Permission denied` / `could not setup config files machinery` | HMDFS 上 toybox `mktemp -d` 创建 drwx--S--- 目录，构建用户不可写（E011 变体，实测复现） | 构建目录内 mktemp wrapper（mkdir 实现、可写），仅注入 conanbuild PATH |
| 4 | 发布包无 `configure`；CI 缺 aclocal/automake/libtoolize | GitHub git-snapshot 发布包 + CI 干净 PATH | `tool_requires(automake/1.18, libtool/2.5.4)` + `bash -e ./autogen.sh`（E528 同类预防） |
| 5 | config.guess/config.sub 不识 HarmonyOS | 上游 2024 年 autotools 辅助脚本 | 显式 `--build/--host=aarch64-unknown-linux-gnu`（E007/E160） |
| 6 | zlib 被 configure 默认探测（`CHECK_ZLIB` 默认 check）并可能引入系统 `-lz` | 上游历史遗留；源码无任何 zlib 调用 | `--without-zlib`（保持零依赖，避免系统同名库耦合） |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001 | lib/Support/Unix/Perf.inc | perf 计数运行期探测：`m_Fd<0` 跳过 read/ioctl、计数返回 0、首次失败 stderr 报告；`read()` 返回值校验；析构仅关闭有效 fd |
| 0002 | lib/Support/Unix/Timer.inc | 计时运行期分支：fd 有效读 perf 计数器，否则回退 `clock_gettime`/`gettimeofday`（原实现仅编译期 `#if` 门控）；同样报告一次 |
| 0003 | lib/Thread/Pthread/Mutex.inc | `tryLock()` 定义补 `throw()` 异常规范，匹配声明（C++17 硬性要求） |

补丁不含 `__OHOS__` 宏、不含绝对路径；均为上游文件修改（`-p1` 可应用）。

## 依赖版本

- 运行时依赖：无（zlib 未被使用，`--without-zlib`；pthread 由 OHOS libc 提供）
- 构建期工具（tool_requires，build context）：automake/1.18、libtool/2.5.4（制品仓预编译）

## 验证结果

```bash
# W0 版本发布检查（R35/R36，防重复适配）：
conan list "skypat/*" -r=ohpcd
#   → Found 0 pkg/version recipes matching skypat/* in ohpcd

# 上游测试清点（R51）：发布包无 tests/ 目录、无 check/TESTS 目标、
# --enable-unittest 的 AM_CONDITIONAL 在全部 Makefile.am 中无引用
#   → 上游自动化用例数 = 0（详见 test_package/MANIFEST.yml 注释）

# 配方本地验证（设备 profile，G0-G4）：
python3 scripts/ohc-run.py conan-verify skypat 3.2.0 --profile ohos-aarch64-device
#   → Verdict: PASS（G0/G1/G2/G3/G4 全 PASS；conan create 成功，test_package 通过）

# 消费者测试（conan create 阶段实跑，真实输出）：
#   test_package/build/clang-15-armv8-17-release/skypat-test-results.csv
#   → perform_reports_plausible_intervals,5156,20227968
#     （两个 PERFORM() 间隔真实递增；20ms Sleep 被正确测量为 20227968 ns）

# 真机直接运行（补丁后，同设备）：
#   [ TIME (ns)] 7656 20093125；[RESULT NUM] 0 0；[  PASSED  ] 2 tests.
#   stderr: skypat: perf_event_open is unavailable (errno=13); ...
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libskypat.so.3.0.1（soname libskypat.so.3） | 共享库（aarch64-linux-ohos） |
| include/skypat/*.h | 公共头文件（skypat.h / ADT / Listeners / Support / Thread） |
| lib/pkgconfig/skypat.pc | pkg-config 元数据 |
| share/skypat/examples/** | 上游示例源码（含 SampleMakefile） |
| licenses/LICENSE | 上游 BSD-3-Clause |

> 纯库包（无可执行文件安装），不需要 commands.json（R38）。

## 注意事项

- OHOS 运行期拒绝 `perf_event_open`（HW/SW 事件均 EACCES，`perf_event_paranoid=-1` 也不放行）：
  `PERFORM()` 的 perf 计数按"不可用=0"降级、计时回退真实时钟并 stderr 报告一次；
  该契约已由 test_package 回归固化（CSV 间隔校验）。
- 版本号策略：首次适配使用上游版本 3.2.0（R37）。
- 上游无自动化测试，赛道底线由 test_package 消费者测试覆盖（R34/R51）。

## 对话记录

### 对话 #1 [2026-09-16]

- 问题: `conan create` 首次构建失败：`lib/Thread/Pthread/Mutex.inc:46: error: 'tryLock' is missing exception specification 'throw()'`
- 处理: 确认 OHOS profile `cppstd=17` 的 `-std=c++17` 位于编译命令尾部、覆盖 Makefile 的 `-std=c++11`；补丁 0003 为定义补 `throw()`（与声明一致），不改工具链参数
- 结果: C++17 预演构建 + conan create 双验证通过

### 对话 #2 [2026-09-16]

- 问题: `PERFORM()` 在真机输出伪时长（`[ TIME (ns)] 156863262856`，fib(10) 报 156.9 秒）；实测 `perf_event_open` 运行期 `-1/EACCES`（HW/SW 均拒绝）
- 处理: 补丁 0001/0002 实现运行期能力探测（fd 有效性）+ 计时回退 `clock_gettime` + 计数诚实 0 + 一次性 stderr 报告
- 结果: 计时恢复真实（CSV: 5156/20227968 ns）；test_package 以 CSV 间隔校验把契约固化为回归测试

### 对话 #3 [2026-09-16]

- 问题: 发布包无 `configure` 且 CI 缺 aclocal/automake/libtoolize；HMDFS `mktemp -d` 目录不可写中止 config.status
- 处理: `tool_requires(automake/1.18, libtool/2.5.4)` + `bash -e ./autogen.sh`；构建目录私有 mktemp wrapper（仅注入 conanbuild PATH）
- 结果: conan-verify G0-G4 PASS；W3 本地 CI 模拟与 finish 全通过

---

**编译结束**: 2026-09-16 15:20
**最终状态**: built
状态: built
