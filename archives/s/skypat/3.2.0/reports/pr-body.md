- **三方库名称**：skypat
- **上游版本**：v3.2.0
- **上游仓库地址**：https://github.com/skymizer/SkyPat
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新，见下方“路径 B 知识贡献说明”）
- **使用知识库**：E011（HMDFS `umask 077`/临时目录写拒绝，本 PR 补其 `mktemp -d` 变体）、E007/E160（config.guess 平台识别与显式三元组）、E528/E490（autotools 环境闭包与脚本可执行位）、E303/E270（受限域运行期能力拒绝的降级思路）；配方骨架参考 `recipe-search` 语料与 Autotools 先例

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 发布包无 `tests/` 目录；顶层 `Makefile.am` 的 SUBDIRS 仅 include/lib/examples；全部 Makefile.am 无 `TESTS`/`check_PROGRAMS` 注册；`--enable-unittest` 的 `AM_CONDITIONAL(ENABLE_UNITTEST)` 无任何引用 |
| 集成测试 | 0 | 上游未提供 |
| 其他测试 | 0 | 唯一的“测试入口”是 9 个 `examples/` 示例程序（非断言型测试套件） |
| **合计** | **0** | 清点证据见 `test_package/MANIFEST.yml`（R51） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无 |
| 集成测试 | 0 | 不变 | 上游无 |
| 鸿蒙特有测试 | 2 | **新增 +2** | `test_package/test_skypat.cpp`：SKYPAT_C fixture 断言（5 处）+ `PERFORM()` 计时契约（1 处断言 + 6 项运行期校验：经 CSVResultPrinter 验证两个性能间隔真实递增、20ms Sleep 被正确测量、perf 计数诚实降级不中止） |
| **合计** | **2** | **+2** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例（上游不存在测试用例）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无测试用例，适配后补全了测试

> - **补全的测试范围**：框架核心 API（用例注册/运行、`EXPECT_*`/`ASSERT_*` 断言、`Listener`/`CSVResultPrinter` 输出）与 `PERFORM()` 性能路径的鸿蒙运行期降级契约（perf_counter 不可用时计时仍真实、计数诚实为 0、不中止）
> - **补全原因**：上游发布包仅含示例、无任何自动化测试（清点证据见 `test_package/MANIFEST.yml`）
> - **新增测试文件清单**：
>   1. `test_package/test_skypat.cpp` — 消费者测试（2 用例、6 框架断言 + 6 项运行期校验）
>   2. `test_package/CMakeLists.txt` / `test_package/conanfile.py` — Conan L1 测试驱动（`test()` 实跑二进制）

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（上游无测试；清点证据见 `test_package/MANIFEST.yml`）
- 新增测试用例通过率：2/2（100%）；断言 6/6、运行期校验 6/6

## 补充说明

### 路径 B 知识贡献说明

本 PR 按路径 A+B 申报，携带 **1 条「一类问题」级知识草稿**（`knowledge/drafts/` 下 kv+md 成对，字段经仓内解析器校验齐全、`draft-review` 预审为“新知/create”）：

**`DRAFT-10686-skypat-perf-events-runtime-capability-probe.kv/.md`**
- **主题**：`perf_event_open` **编译可用但运行期被拒（EACCES）**——编译期头文件门控不足，须运行期能力探测与优雅降级。
- **触发实例（第一手证据）**：skypat 3.2.0 真机上 `PERFORM()` 输出伪时长 `[ TIME (ns)] 156863262856`（fib(10) 报 156.9 秒、各测量块数值相同），Debug 下断言可能中止。三层证据链：
  1. 头文件层：OHOS sysroot 内 `linux/perf_event.h` 与 `__NR_perf_event_open=241`（`sysroot/usr/include/aarch64-linux-ohos/asm/unistd.h`）均存在 → 编译通过（`HAVE_LINUX_PERF_EVENT_H=1`）；
  2. 权限层：真机 `perf_event_open` 对 **HW 与 SW 事件**一律返回 `-1, errno=13 (EACCES)`，`/proc/sys/kernel/perf_event_paranoid=-1` 也不放行（受限进程域策略）；
  3. 缺陷层：上游对 `fd=-1` 不检查，`read()` 未初始化栈缓冲 + `assert(-1 != m_Start)` 兜底 → Release 伪数据 / Debug 随机中止。
- **方案**：运行期以 fd 有效性为准（跳过无效 read/ioctl、计数返回 0），计时按“fd 有效→perf 计数器；否则 `clock_gettime`/`gettimeofday`”运行期分支回退，首次失败 stderr 报告一次；不引入平台宏（本 PR 补丁 0001/0002）。
- **查重与增量**：与 **E270**（`CLOCK_SGI_CYCLE` 被运行期拒绝→回退时钟）同属“运行期拒绝回退”但主体不同（时钟源 vs syscall 权限 + 未初始化读取修复）；与 **E303**（受限域 `opendir("/")` EACCES 身份探测）共享“运行期能力判断”理念，域不同（文件系统 vs 性能计数）；与 **E008/E076**（SELinux 使 `fstat/lseek` 返回 EACCES 的被动语义差异）不同，本条是主动能力自检与降级策略；与 **E387**（LLVM lit）、**E011**（HMDFS umask，本 PR 仅引用）无重叠。对仓库内**两处先行记录**划清边界并补全：`libcpucycles` notes（已记录“perf 不可用”，但无 errno 语义/失效模式/治理模板）与 `operations/ptrace-alternatives.md`（“paranoid 可能被锁”的粗粒度结论经实测修正：paranoid 可读为 -1，被拒的是 syscall 本身）。**本条增量** = ①errno 级语义（HW/SW 均 `-1/EACCES`）②无处理时的测量失真失效模式（伪时长/断言中止）③双通道降级实现模板与 CSV 契约回归方法；本条不主张新原则（P013/P015 已在库），主张的是既有原则在 perf 场景缺失的实现模板与失效模式。
- **影响面与语料对照**：所有以 `perf_event_open`/perf_events 计数或计时的 C/C++ 库（性能测试框架、profiler、采样/缓存分析工具），以及“编译期能力检测 ≠ 运行期权限”的受限进程/容器/安全域场景；语料对照：`libcpucycles`（已自愈参照，backend selection + SKIP）/`libpfm`（仅事件编码）/`google-benchmark`（启用硬件计数器即命中）。

### 构建环境与验证方式

- 设备真机：OpenHarmony PC（aarch64），clang/clang++ 15.0.4（OHOS SDK 26.0.0.18），Conan 2.29.1（OHOS 适配版），profile `ohos-aarch64-device`
- 依赖：运行时零依赖（zlib 未被源码引用，`--without-zlib`）；构建期 `tool_requires` automake/1.18、libtool/2.5.4（制品仓预编译）
- 本地门禁：`conan-verify` G0/G1/G2/G3/G4 全 PASS；`finish`（W2 结构 + R36 依赖 + W3 本地 CI 模拟，L0/L1/L1e/L4/L5 全 PASS）通过；W4 独立审计 0 P0/P1（1 项 P3 风格建议，见下）
- 消费者测试运行证据（conan create 实跑 CSV）：`perform_reports_plausible_intervals,5156,20227968`

### 关键适配点

1. **Bootstrap**：GitHub 发布包为 git snapshot（无 `configure`），且 CI 干净 PATH 缺 aclocal/automake/libtoolize → `tool_requires(automake/1.18, libtool/2.5.4)` + `bash -e ./autogen.sh`（E528/E490 同类预防）。
2. **HMDFS 临时目录**：toybox `mktemp -d` 目录（drwx--S---）构建用户不可写，`config.status` 报 `subs1.awk: Permission denied` / `could not setup config files machinery` → 构建目录私有 mktemp wrapper（mkdir 实现，仅注入 conanbuild PATH，E011 的 `mktemp -d` 变体，同 cln 1.3.7 先例）。
3. **平台三元组**：config.guess 不识 HarmonyOS → 显式 `--build/--host=aarch64-unknown-linux-gnu`（E007/E160）。
4. **C++17 异常规范**：profile `cppstd=17` 使 `-std=c++17` 覆盖 Makefile 的 `-std=c++11`，`Mutex::tryLock()` 定义漏写声明中的 `throw()` 成为硬错误 → 补丁 0003 补齐异常规范（与 `Mutex.h` 声明一致，`lock/unlock` 上游本就匹配）。
5. **perf 运行期降级**：补丁 0001/0002（详见路径 B 说明），`PERFORM()` 在 OHOS 上始终可运行且时长真实。

### 产物验证

| 产物 | 验证方式 | 结果 |
|------|----------|------|
| libskypat.so.3.0.1（soname libskypat.so.3） | conan create 构建 + test_package 链接 | 通过 |
| include/skypat/*.h + lib/pkgconfig/skypat.pc | G4 产物完整性 + CMakeDeps 消费者导入 | 通过 |
| test_package 消费者程序 | conan create 测试阶段实跑（`[  PASSED  ] 2 tests`，CSV 间隔 5156/20227968 ns） | 通过 |
| 纯库包 | 无可执行文件安装 → 无 commands.json（R38） | 通过 |

### 已知限制与声明

- W4 审计 P3 风格建议：`conanfile.py` 内嵌 mktemp shim 未使用 `set -euo pipefail` 安全模式开头——非阻塞，后续迭代处理。
- 按当前口径（Issue 机制已废弃，见 #9670），本 PR 不新开【知识库扩展】issue，以正文说明为准；若评审委员会需要，可补充创建并双向关联。
- 上游无自动化测试，赛道底线由 `test_package` 消费者测试覆盖。
