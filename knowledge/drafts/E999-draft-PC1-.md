# E999 — OHOS/musl 下上游头文件未覆盖 `__OHOS__`/`__linux__` 分支时 htole32/16/64 宏未声明导致链接失败

## 错误特征

链接阶段（非编译阶段）报 undefined symbol，且与字节序宏相关：

```text
ld.lld: error: undefined symbol: htole32
>>> referenced by src/poly.c:1206
>>>               ./poly.o:(ntru_to_arr)
>>> defined in: ./libntru.so
>>> did you mean: EES449EP1
clang-15: error: linker command failed with exit code 1
```

伴随编译期警告（可被 -Wimplicit-function-declaration 捕获）：

```text
warning: call to undeclared function 'htole32'; ISO C99 and later do not
support implicit function declarations
```

## 触发条件

- 适用平台：HarmonyOS PC / OpenHarmony（musl libc，`__OHOS__` + `__linux__` 已定义、`__GLIBC__` 未定义）；同理影响 Alpine 等 musl 发行版
- 触发工具：clang + ld.lld（`--no-allow-shlib-undefined` 生效时链接即失败）
- 阶段：linking（共享库或测试可执行连接）
- 项目特征：上游头文件按操作系统宏条件定义字节序宏，但未覆盖 musl 分支

## 根因分析

上游 `ntru_endian.h` 仅为 `__APPLE__`、`__MINGW32__`、`__GLIBC__ < 2.9`、
`__FreeBSD__`、`__OS2__` 定义或包含 `htole32`/`htole64`/`htole16` 的提供者。
OHOS 的 musl libc 上：

- `__OHOS__` 与 `__linux__` 均被定义；
- `__GLIBC__` 未被定义（musl 非 glibc）；
- 上游因此落入所有条件分支之外，`htole*` 宏从未声明；
- musl 实际在 `<endian.h>` 中提供 `htole16/32/64`（与 `htobe*` 对应），但上游从未包含该头。

最终：源文件以隐式函数声明编译通过（warning），共享库导出未定义符号引用，
链接器在 `--no-allow-shlib-undefined` 下直接失败。

## 解决方案

### 推荐方案（source-patch，已验证）

在字节序头文件增加 musl/一般 Linux 分支，包含 `<endian.h>`：

```c
#ifdef __GLIBC__
... 原 glibc 分支 ...
#elif defined(__OHOS__) || defined(__linux__) || defined(__FreeBSD__)
/* musl libc (HarmonyOS/OHOS, Alpine) 和 FreeBSD 在 <endian.h> 提供 htole32/64/16 */
#include <endian.h>
#endif
```

要点：

- 判定条件必须是「无 `__GLIBC__`」，而不是仅判断 `__OHOS__`：同样覆盖 Alpine
  等 musl 发行版，且不破坏 glibc 平台原有行为；
- glibc 平台 `<endian.h>` 本身已提供 `htole*`，该分支不触发，向后兼容；
- 小端 aarch64 平台上 `htole*` 为恒等宏，无性能影响。

### 禁止做法

- ❌ 用 `#define htole32(x) (x)` 硬编码小端恒等：在真大端平台（如 OHOS big-endian
  移植或反例平台）会静默产生错误字节序，且掩盖 musl 头文件真实可用性；
- ❌ 删除 `--no-allow-shlib-undefined` 缓解：会掩盖所有未定义符号类问题。

## 验证

```bash
# 1. 宏探测：确认 OHOS 上 __OHOS__/__linux__ 定义、__GLIBC__ 未定义
clang --target=aarch64-unknown-linux-ohos -E -P -x c macro_probe.c

# 2. 打补丁后全量上游测试（libntru 实测）
make -f Makefile testham CC=clang AR=llvm-ar && LD_LIBRARY_PATH=. ./testham
# -> 11/11 用例通过 (testham 全功能构建)

# 3. 小端恒等回归护栏（鸿蒙专项测试断言）
htole32(0x01020304) == 0x01020304  # 平台自检通过
```

libntru 0.5.0 实测：补丁前 `make testham` 链接失败（上述 undefined symbol），
补丁后 testham 11/11、testnoham 10/10、鸿蒙专项 test_ohos 16/16 全部通过。

## 适用边界与反例

- 适用：任何使用 `htole*`/`htobe*` 且字节序头按 OS 宏条件定义的 C 库在 OHOS /
  musl 发行版的适配；`/proc/cpuinfo` 探测类（SSSE3/AVX2 汇编路径）与本问题无关。
- 反例：纯小端且自行定义恒等宏的库（无需修补）；glibc 平台（`<endian.h>` 已提供）
  若上游已有 `<endian.h>` 包含则本补丁无额外效果。
- 边界：若上游同时在大端目标编译，`htole*` 应为真实字节交换而非恒等，需以
  musl 头文件实现为准，不做手工恒等替代。

## 关联条目

- similar_to: E493, E203, E020, E014, E085（musl 缺 glibc 扩展符号/不透明类型族，
  均以 source-patch + 条件编译守卫解决，但均未覆盖 endian 宏族与 `<endian.h>`）
- 查重结论（七轴）：
  - exact_duplicate=false、causal_duplicate=false；
  - trigger_overlap=true（同属 musl 缺 glibc 扩展，触发面有重叠但符号族不同）；
  - solution_overlap=partial（共享 source-patch + #ifdef 守卫模式，`<endian.h>`
    include 方案未被既有条目覆盖）；
  - combination_novelty=true、boundary_novelty=true、test_migration_novelty=true
    （端序恒等断言随鸿蒙专项测试迁移）。