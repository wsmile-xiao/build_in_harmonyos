# 测试报告

> **项目**: libcsys
> **版本**: 5.0.0
> **测试日期**: 2026-09-14
> **测试环境**: HarmonyOS HongMeng Kernel 1.12.0 aarch64 (`uname -a` → `HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP ... aarch64`)
> **测试类型**: 上游测试套件（0 用例）+ 自补消费者功能测试

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游用例总数 (N) | 0 | — |
| 上游通过 (N′) | 0 | — |
| 自补 test_package 断言数 | 41 | 100% |
| 通过 (PASS) | 41 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |
| 测试二进制退出码 | 0 | — |

**核心功能通过率**: ✅ **100% (41/41 断言)**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。上游 5.0.0 未提供任何测试用例（清点证据见 §三），因此按用户要求自补了
41 条消费者视角断言，覆盖全部公开 API，实测全部通过；D-Bus 相关类（Battery/Power/
Storage）在无对应服务的 OHOS 环境下验证为优雅降级而非崩溃。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 | 处置 |
|----------|----------|----------|------|
| `InfoManager::update()` 空表越界 → SIGSEGV | 调用 update() 的任何程序 | 🔴 | patch 0001 修复 |
| `Power::~Power()` 条件取反 + 空表 `takeFirst()` → SIGSEGV | 任何构造 `Power` 的程序 | 🔴 | patch 0001 修复 |
| `SystemInfo::getHostname()` 恒返回空串 | 主机名显示 | 🟢 | patch 0001 修复 |
| `NetworkInfo::getIOBytes()` 空表 `removeFirst()` / 短行 `at()` 越界 → SIGSEGV | 调用 getIOBytes() 的任何程序；**远端 CI 实测崩过**（Worker `/proc/net/dev` 不可见） | 🔴 | patch 0002 修复（探针实证见 `networkinfo-probe-evidence.txt`） |
| OHOS `/proc/cpuinfo` 无 `cpu MHz` → 频率列表为空 | `CpuInfo::getCPUFrequencies()` | 🟡 | 平台限制，断言按"空或每核一条"容错 |
| OHOS 无 UPower/UDisks2/logind 服务 | Battery/Storage/Power | 🟡 | 预期降级（空 / false），断言不崩溃 |

### 2.3 可用功能清单

```
✅ FileUtil              读写文件 / 逐行读取（往返一致、错误路径返回 false）
✅ CpuInfo               核数、每核占用率、负载均值、频率（OHOS 无 MHz 时为空）
✅ MemoryInfo            内存与 swap 总量/空闲/已用
✅ SystemInfo            主机名、平台、发行版、内核、CPU 型号/核心数、用户、启动时间、运行时长
✅ NetworkInfo           收发字节计数（/proc/net/dev）
✅ DiskInfo              挂载卷列表、磁盘读写字节（/sys/block）
✅ InfoManager           构造 / update() / 核数 / 各资源时间序列
⚠️ BatteryManager        优雅降级为空列表（无 UPower）
⚠️ Power                 systemCan* 返回 false（无 logind/ConsoleKit）
⚠️ StorageManager        优雅降级为零设备/零块（无 UDisks2）
```

### 2.4 已知限制

1. OHOS `/proc/cpuinfo` 不含 `cpu MHz` 字段，`CpuInfo::getCPUFrequencies()` /
   `getCPUFrequenciesStr()` 返回空列表（`getCpuPercents()` 仍逐核返回）。
2. OHOS 无 UPower / UDisks2 / systemd-logind D-Bus 服务，`Battery` / `Storage` /
   `Power` 的能力查询返回空/`false`（不崩溃）。
3. 包未安装 CMake config 包（`package_info()` 用 `cmake_find_mode="none"`），
   下游 CMake 消费者需用 pkg-config（`csys.pc`）或直接链接。

---

## 三、测试详情

### 3.1 上游测试清点（N = 0，附证据）

在解压后的上游源码根执行：

```bash
$ grep -rn "enable_testing\|add_test\|test(" CMakeLists.txt meson.build
（无输出，退出码 1）                      # CMake 无 enable_testing()/add_test()，meson 无 test()

$ find . -iname "*test*"
（无输出）                                # 无 tests/ 目录、无 test 源文件

$ tar tzf libcsys-v5.0.0.tar.gz | grep -i test
（无输出，退出码 1）                      # 归档内无测试文件

$ cat .gitlab-ci.yml
stages: [build, test]
build_amd64:  mkdir build && cd build && cmake .. && make -j$(nproc)
uncrustify:   # stage 名为 test，实为 uncrustify 代码风格检查，非功能测试
```

**结论：上游注册 0 个测试用例**，无上游测试可运行。

### 3.2 自补消费者测试（全部通过）

`test_package/test_libcsys.cpp` 通过 `self.run()` 真实运行，逐条断言并打印汇总：

| 分组 | 断言数 | 结果 |
|------|:------:|------|
| FileUtil（写入/往返/逐行/错误路径） | 7 | ✅ 7/7 |
| CpuInfo（核数/占用率/频率/负载/格式化） | 6 | ✅ 6/6 |
| MemoryInfo（总量/空闲/swap 一致性） | 3 | ✅ 3/3 |
| SystemInfo（9 个 getter 非空 + 3 个列表 getter 可调用） | 12 | ✅ 12/12 |
| NetworkInfo（Rx+Tx 二元组） | 1 | ✅ 1/1 |
| DiskInfo（卷列表 + 读写二元组） | 2 | ✅ 2/2 |
| InfoManager（构造/update/核数/时间序列） | 5 | ✅ 5/5 |
| BatteryManager（降级为空） | 1 | ✅ 1/1 |
| Power（降级为 false） | 2 | ✅ 2/2 |
| StorageManager（降级为空） | 2 | ✅ 2/2 |
| **合计** | **41** | **✅ 41/41** |

实测输出（conan create → test_package）：

```
======== Testing the package: Executing test ========
libcsys/5.0.0 (test package): Running test()
libcsys/5.0.0 (test package): RUN: ./test_libcsys
...
  [PASS] SystemInfo::getHostname() non-empty
  [PASS] InfoManager::update() completed and reports memory
  [PASS] BatteryManager degrades to an empty list without UPower
  [PASS] Power::systemCanSuspend() degrades to false
  [PASS] StorageManager degrades to zero devices without UDisks2
libcsys test summary: assertions=41 failures=0
# 进程退出码 0
```

### 3.3 跳过的测试

无（上游 0 用例；自补 41 条断言全部执行，0 跳过）。

---

## 四、本地 CI 门禁实测（ci/conan/build_and_test.sh）

### 4.1 真实 CI 模式（prdiff，`JUNK_PR_DIFF` 提供 PR 文件清单）

```
KC_RESULT=pass
  检查模式: prdiff (12 个文件)
JC_RESULT=pass
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content
Pass rate: 100.0% (1/1)   # 退出码 0
```

### 4.2 全仓扫描模式（`CI_PACKAGES=... PKG_SCAN_ROOT=archives`，无 pr.diff）

```
JC_RESULT=fail
[FAIL] JC1: 2 个运行时状态文件被跟踪:
       archives/c/cloog/0.21.1/.build-closed
       archives/c/cloog/0.21.1/.staging-verified
L0_RESULT=fail: junk_check failed
```

**说明**：这两个文件属于 **另一个已合入 main 的包（cloog 0.21.1）**，是仓库既有存量
违规（`git ls-files` 可证其在 HEAD 中），与本包无关，按任务约束不予改动。真实 CI 以
prdiff 模式只检查本 PR 涉及的文件，因此本包不受影响（见 §4.1）。

---

## 五、关键问题分析

### 问题1: `InfoManager::update()` 段错误

**现象**：
```
$ ./probe    # 只构造 CpuInfo/CpuInfo::updateInfo() 正常
== InfoManager ==
cores: 20
（EXIT=139 SIGSEGV）
```

**根因分析**：OHOS `/proc/cpuinfo` 无 `cpu MHz` 行 → `CpuInfo::updateInfo()` 不填充
频率列表 → `getCPUFrequencies()` 返回空 → `InfoManager::update()` 中
`mCpuFrequencies[i] << xFrequencies[i];`（i 从 0 到核数-1）在空表上越界。

**解决方案**：patch 0001 改为 `xFrequencies.value(i, 0.0)`（越界返回 0.0）。

### 问题2: `Power` 析构段错误

**现象**：
```
$ ./t   # 只构造并析构 Power
constructed Power
（EXIT=139 SIGSEGV，析构函数内崩溃）
```

**根因分析**：`Power::~Power()` 为 `while (providers.empty()) { delete providers.takeFirst(); }`
—— 条件写反：无 D-Bus 提供者时 `providers` 为空，条件为真进入循环，在空表上
`takeFirst()` 越界。

**解决方案**：patch 0001 改为 `while (not providers.empty())`。

### 问题3: `getHostname()` 恒为空

**根因分析**：`gethostname()` 成功时返回 0（不是长度），而代码 `int size = gethostname(...)`
后 `QString::fromLatin1(hostname, size)` 把 0 当长度 → 空串（且缓冲区未初始化）。

**解决方案**：patch 0001 改为零初始化栈缓冲 + `QString::fromLatin1(hostname)`；实测返回 `localhost`。

---

## 六、测试环境

```
目标平台 : HarmonyOS/OHOS 6.0 aarch64 (armv8)
宿主内核 : HarmonyOS HongMeng Kernel 1.12.0 aarch64
编译器   : clang / clang++ 15 (libc++)
Profile  : ci/conan/profiles/ohos-aarch64
依赖     : qtbase-sql-dbus/6.11.1 (Qt6Core + Qt6DBus + Qt6Network), dbus/1.14.10
产物     : lib/libcsys.so.5.0.0 (SONAME libcsys.so.5), include/csys/*.h, share/pkgconfig/csys.pc
命令     : conan create archives/l/libcsys/5.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
             -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

---

*报告生成时间: 2026-09-14*
