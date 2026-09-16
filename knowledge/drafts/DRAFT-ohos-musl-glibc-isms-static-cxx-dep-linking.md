# musl 下的 glibc 惯性符号与静态 C++ 依赖链接（草稿）

- **来源**：cdo 2.6.3 适配（archives/c/cdo/2.6.3/notes.md）
- **日期**：2026-09-12
- **适用范围**：OHOS/musl 上的 autotools/CMake 项目，尤其是"依赖静态 C++ 库"或"源码含 glibc 专有符号"的老代码

## 条目要素（对应路径 B 场景一的「使用说明 / 适用范围 / 输入输出定义 / 示例」）

- **使用说明**：见下方「现象 → 根因 → 解决办法」，含可直接复制的补丁/配方片段
- **适用范围**：见本文件开头的「适用范围」与 kv 的 `affected_scope`
- **输入输出定义**：
  - 输入（触发条件）：kv 的 `error_signature`（报错特征） + `trigger_tool` / `phase`
  - 输出（验证方式）：kv 的 `verification_cmd` + 本文件「验证」一节的实测结果
- **示例**：本文件中的补丁片段、探针命令与 conan 命令

## 现象一：glibc 专有类型与别名

```
libyac/clapack/F2CLIBS/libf2c/fio.h:130:8: error: unknown type name '__off64_t'
src/processManager.cc:195:7: error: use of undeclared identifier 'pthread_cancel'
```

**根因**：`sysdep1.h0` 对 `__linux__` 一律 `#define OFF_T __off64_t` 并启用
`USE_LARGEFILE`（fopen64/fseeko64/stat64 等别名）；musl 无此类型/别名。musl 也不实现
线程取消（`pthread.h` 无 `pthread_cancel` 声明；`PTHREAD_CANCELED` 宏仍存在，
不能拿它做能力探测）。

**修法**：按 libc 能力分流（不是平台宏）：

```c
#if defined(__linux__) && defined(__GLIBC__)
#define USE_LARGEFILE
#define OFF_T __off64_t
#endif
#if defined(__linux__) && !defined(__GLIBC__)
#define OFF_T off_t
#define FSEEK fseeko
#define FTELL ftello
#endif
```

## 现象二：C 驱动探测静态 C++ 依赖

```
configure: error: Could not link to PROJ library!
config.log: ld.lld: error: undefined symbol: operator delete(void*)
            >>> referenced by c_api.cpp.o in archive .../libproj.a
```

**根因**：proj ≥ 6 是 C++ 实现，制品仓给的是静态 `libproj.a`；上游用
`AC_CHECK_LIB([proj],[proj_create])` 以纯 C 驱动链接探测，不自动追加 libc++。

**修法**：LDFLAGS 补 `-lc++ -lc++abi`（仓内 mtbl/audiofile/cif-api 同款先例）。

## 验证

- cdo/2.6.3：`conan create -pr:h=ohos-aarch64-wsl -pr:b=default` 通过，产物
  `bin/cdo` 为 `ELF 64-bit LSB pie, ARM aarch64`；
- config.log 与编译日志保存于 cdo 的 reports/。

## 边界与注意

- `pthread_cancel` 不可用时不得写空壳 stub（R8）：本次仅退化为"随进程退出"，
  且该函数只在 `cdo_exit()` → `std::exit()` 的 teardown 路径上被调用，已在 notes 说明；
- 补丁中不要引入平台宏，用 libc 能力宏（`__GLIBC__`）或标准特性宏。

## 相关

- **预审相似条目**：E072（config.sub 未识别 ohos 三元组）、E092（CMake 不认识 HarmonyOS 平台名）——本条聚焦 libc 能力探测与静态 C++ 依赖链接，与之互补

- cdo 补丁：`0001-libf2c-sysdep1-libc-off-t.patch`、`0003-process-manager-libc-pthread-cancel.patch`
- 仓内同类先例：mtbl 1.7.1、audiofile 0.3.6、cif-api 0.4.2（`-lc++`）；classads 1.0.10（libtool 不为 clang++ 追加运行库）
