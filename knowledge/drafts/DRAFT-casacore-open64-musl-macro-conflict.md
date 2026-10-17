# musl/OHOS `#define open64 open` 宏与 C++ 成员函数名冲突

- **Draft ID**: DRAFT-casacore-open64-musl
- **来源软件**: casacore 3.7.1（PR #8131）
- **阶段**: compile/link
- **severity**: 2

## 现象

三种报错形态（同一根因的不同切面）：

1. 链接期：`ld.lld: error: undefined symbol: casacore::VirtualColumnEngine::open(unsigned long long, casacore::AipsIO&)`，`referenced by ... (vtable for ...)`
2. 编译期：`out-of-line definition of 'open' does not match any declaration`
3. Makefile 期：`No rule to make target 'm', needed by '<target>'`（裸名库变量被 CMake 记为 FILEPATH 相对路径）

## 根因

OHOS（musl）`fcntl.h` 在 `_LARGEFILE64_SOURCE || _GNU_SOURCE` 下定义 `#define open64 open`（LFS64 折叠）。**OHOS clang 无条件预定义 `_GNU_SOURCE`**，因此 TU 内一旦 include 过 `fcntl.h`，宏必然生效。软件中名为 `open64` 的 C++ 成员函数（casacore `DataManager::open64` 虚函数族）在声明/定义/调用处被按各 TU 的 include 顺序**不一致地**展开为 `open`，导致 vtable 槽位名跨 TU 不一致 → 链接失败。

## 修复方案（三层，全部需要）

1. **成员函数名**：对每个 `open64` 声明/定义/调用点前置 `#undef open64`（portability 补丁，21 处）
2. **C 函数别名**：全局定义软件的 no-LFS 开关（casacore：`AIPS_NOLARGEFILE`），避免 `fopen64/lseek64` 别名依赖；musl off_t 恒 64 位，无功能损失
3. **find_library(m/pthread)**：OHOS sysroot 对 CMake 不可见导致 NOTFOUND。**不要传裸名**（会被记为 FILEPATH 相对路径），用 `clang -print-file-name=libm.a` 解析 sysroot 真实路径，经 `CMAKE_LIBRARY_PATH`/`CMAKE_INCLUDE_PATH` 提供给 CMake

## 参考

- casacore 3.7.1 `archives/c/casacore/3.7.1/patches/0002-undef-open64-to-avoid-musl-macro-conflict.patch`
- casacore 3.7.1 `conanfile.py` `_sysroot_libdir()` + `AIPS_NOLARGEFILE`
