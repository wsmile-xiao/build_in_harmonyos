# access_profiler 20260924 适配笔记

## 编译环境
- 构建系统: custom（上游 Boost.Build/Jamfile，无 configure/make install；配方直编译）
- 编译日期: 2026-09-24
- 编译器: clang/clang++ 15.0.4（OHOS aarch64，conan profile ohos-aarch64）
- 状态: built（conan-verify 通过 + W3 本地 CI 通过；未上传制品仓）

## 编译步骤

```bash
# 直编译（无 configure；CXX/AR 由 profile conf 注入，R33）
clang++ -std=c++17 -O2 -fPIC -fexceptions -c access_profiler.cpp -o access_profiler.o
llvm-ar rcs libaccess_profiler.a access_profiler.o

# 上游测试（Jamfile `exe test : test.cpp`；1 个独立上游用例）
clang++ -std=c++17 -O2 test.cpp libaccess_profiler.a -o test && ./test
# => stdout: 55，access_profile.out: test / 52: 1（与上游 README release 输出一致）

# 消费者用例（仅公开头文件 + 公开 API instrument_type<T> + 静态库）
clang++ -std=c++17 -O0 consumer_access_profiler.cpp libaccess_profiler.a -o consumer_test && ./consumer_test
# => consumer: 100 samples aggregated -> seq=100 temperature=100 humidity=300（exit 0）

# 鸿蒙专项测试（aarch64 单步/自动初始化路径）
clang++ -std=c++17 -O2 ohos_special_test.cpp libaccess_profiler.a -o special_test && ./special_test
# => SPECIAL-TEST-WORKLOAD-OK（exit 0），access_profile.out 含 test / 52: 1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aarch64 编译失败：`uc->uc_mcontext->__ss.__rflags` 无此成员 | 上游单步代码为 Darwin/x86 专属（`__ss`/`__rflags`/`__eflags` 指向 sigcontext 特定布局），aarch64 的 mcontext 是 `pstate` 结构 | `#ifdef __aarch64__` 分支改用 `uc->uc_mcontext.pstate` 的 SS 位（0x200000）启停单步 |
| 2 | 运行期 SIGSEGV（静态初始化/装载期崩溃，main 未进入；二分实测：仅含外部链接全局对象时崩溃，改 static 后正常） | OHOS PIE 装载期对外部链接（默认可见性）全局对象（std::mutex/unordered_map/vector/pthread_key_t）的初始化路径异常 | 全部改为 `static` 内部链接：pagemutex/pagemap/typemutex/typemap/next_typeidx/access/last_page（非公开 API，header 未声明，不影响消费者） |

## 源码修改

- `patches/0001-access_profiler.cpp.patch`：① 7 个外部链接全局对象改 static（装载期崩溃修复）；② segv/single_step handler 单步路径 aarch64 pstate SS 位。
  - 补丁不含 `__OHOS__` 平台宏（用标准 `__aarch64__` 架构宏，符合 R8/PF5）。
- `conanfile.py`：custom 直编译（无 configure），静态库，`cpp_info.libs=["access_profiler"]`；R33 编译器从 profile conf 读取。
- `conandata.yml`：shoco 同款 patches 声明。

## 依赖版本

- 无外部 Conan 依赖（零依赖 C++ 库；运行期需要 libc/libc++_shared）。

## 验证结果

```bash
# conan-verify 全部门禁通过（G0-G4 + L2/L4/L5）
python3 scripts/ohc-run.py conan-verify access_profiler 20260924  # exit 0

# 上游测试 1/1 通过：test（stdout=55，access_profile.out = test / 52: 1）
# 消费者用例通过：consumer_access_profiler -> 100 samples aggregated（exit 0）
# 鸿蒙专项测试通过：ohos_special_test -> SPECIAL-TEST-WORKLOAD-OK（exit 0）
# 证据日志（命令/cwd/exit_code/绝对路径/SHA-256）见 reports/test-report.md
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py + conandata.yml | 直编译配方（静态库） |
| test_package/ | L1 消费者测试（CMake + test.cpp 字段聚合断言） |
| patches/0001-access_profiler.cpp.patch | aarch64 单步 + 装载期全局对象适配 |
| consumer_access_profiler.cpp | 消费者用例（公开 API，业务语义字段聚合） |
| ohos_special_test.cpp | 鸿蒙专项测试（aarch64 单步/自动初始化路径） |

## 注意事项

- 库是"重型"字段访问分析库：通过保护页 + SIGSEGV/SIGTRAP 单步记录堆对象字段访问，仅建议 debug 构建使用（上游 README 明确 release 会被寄存器缓存优化，热区计数大幅减少但仍可记录，实测 release 输出 test / 52: 1 与上游一致）。
- 需依赖 C++ 异常（`-fexceptions`）与 `__cxa_demangle`（libc++abi，随 libc++_shared）。
---

**编译结束**: 2026-09-24 04:29
**最终状态**: built
