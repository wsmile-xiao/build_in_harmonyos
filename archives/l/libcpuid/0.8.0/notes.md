# libcpuid 0.8.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-01
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

1. init-build: `ohc-run.py init-build libcpuid 0.8.0 --url=https://github.com/anrieff/libcpuid/archive/refs/tags/v0.8.0.tar.gz --no-download`
2. cmake配置: `cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DCMAKE_SYSTEM_NAME=Linux ..`
3. 编译: `make -j2`
4. DESTDIR安装: `make install DESTDIR=$TEST_PREFIX`
5. 本地安装: `make install`
6. ELF签名: `ohc-run.py sign-elf`
7. 验证: `cpuid_tool --version` → 0.8.0
8. 预编译包: `ohc-run.py package libcpuid 0.8.0`

## 关键配置说明

- 使用 `-DCMAKE_SYSTEM_NAME=Linux` 是必须的cmake配置：
  - cmake将系统视为Linux → 自动满足 `if(Linux)` 的getauxval检测条件
  - cmake将系统视为UNIX → 自动满足 `if(UNIX)` 的_GNU_SOURCE定义条件
  - 正确生成版本化.so（libcpuid.so.18 → libcpuid.so.18.1.0）和RPATH
- 因此**不需要**为CMakeLists.txt添加OHOS条件补丁
- musl libc在_GNU_SOURCE下自动暴露cpu_set_t/sched_getaffinity等API

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake编译失败: `unknown type 'cpu_set_t'` | cmake不将OHOS识别为UNIX | 使用-DCMAKE_SYSTEM_NAME=Linux，无需补丁 |
| 2 | `HWCAP_CPUID is not defined`警告 | cmake不将OHOS识别为Linux | 使用-DCMAKE_SYSTEM_NAME=Linux，无需补丁 |
| 3 | 共享库无SONAME | cmake对未知系统不生成版本化.so | 使用-DCMAKE_SYSTEM_NAME=Linux |
| 4 | ELF未签名无法执行 | HarmonyOS要求ELF签名 | `ohc-run.py sign-elf` |
| 5 | cpu_identify()在ARM上返回空数据 | cpuid_get_raw_data()未清零结构体导致架构误判 | 补丁0003: 添加raw_data_t_constructor(data)清零raw结构体 |
| 6 | cpuid_identify_arm()不设置核心数 | 库设计缺陷，ARM单核路径不计算num_cores | 补丁0004: 添加num_cores=1和num_logical_cpus=cpuid_get_total_cpus() |
| 7 | cpu_clock_by_os()在ARM上返回-1 | 仅查找x86的"cpu MHz"字段 | 补丁0005: 添加ARM BogoMIPS和sysfs cpufreq检测路径 |

## 源码修改（3个补丁）

### 0003-libcpuid-cpuid_main.c.patch
- `cpuid_get_raw_data()`添加`raw_data_t_constructor(data)`清零结构体

### 0004-libcpuid-recog_arm.c.patch
- `cpuid_identify_arm()`添加num_cores/num_logical_cpus/total_logical_cpus

### 0005-libcpuid-rdtsc.c.patch
- `cpu_clock_by_os()`添加ARM BogoMIPS和sysfs cpufreq检测

## 验证结果

```bash
$ cpuid_tool
CPUID is present
CPU Info for type #0:
  arch       : ARM
  feat_level : ARMv8.0-A
  purpose    : general
  vendor_str : HiSilicon
  implementer: 72 (48h)
  variant    : 2 (02h)
  part_num   : 3394 (D42h)
  revision   : 3 (03h)
  num_cores  : 1
  num_logical: 16
  tot_logical: 16
```

## 功能测试对比（修复前 vs 修复后）

| API | 修复前 | 修复后 | 说明 |
|-----|--------|--------|------|
| cpuid_present() | ✅ PASS | ✅ PASS | 返回2048(HWCAP_CPUID) |
| cpuid_get_total_cpus() | ✅ PASS | ✅ PASS | 正确返回16 |
| cpuid_get_raw_data() | ✅ PASS | ✅ PASS | arm_midr正确读取 |
| cpu_identify() | ⚠️ PARTIAL | ⚠️ PARTIAL | implementer=72✅, cores=1✅; brand_str=unknown(ARM预期) |
| cpu_identify_all() | ✅ PASS | ✅ PASS | cores=1/logical=16正确 |
| cpu_clock_by_os() | ⚠️ PARTIAL | ✅ PASS | sysfs cpufreq返回1000 MHz |
| cpu_feature_str() | ✅ PASS | ✅ PASS | |
| cpuid_error() | ⚠️ PARTIAL | ⚠️ PARTIAL | "No error"而非NULL(库设计) |
| serialize/deserialize | ⚠️ PARTIAL | ✅ PASS | ARM数据正确序列化 |
| ARM feature flags | ✅ PASS | ✅ PASS | 6个特性检测 |
| cpuid_tool --report | ✅ PASS | ✅ PASS | |
| pkg-config | ✅ PASS | ✅ PASS | |

总计: 修复前 7✅/5⚠️ → 修复后 **10✅/2⚠️**

## 注意事项

- `-DCMAKE_SYSTEM_NAME=Linux`是必须的cmake配置，不需要CMakeLists.txt补丁
- musl libc在_GNU_SOURCE下（cmake自动定义）暴露所需API
- brand_str/code_name/technology在ARM上返回"unknown"（已知限制）
- 推荐使用`cpu_identify_all()`而非`cpu_identify()`
- L1/L2/L3缓存信息在ARM上不可检测（返回-1/0）

---

**最终状态**: published
