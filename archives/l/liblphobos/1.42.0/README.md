# liblphobos 1.42.0 — 鸿蒙 PC conan 制品（D 语言标准库 Phobos）

`os=OHOS, arch=armv8`(= aarch64) 的 **library 共享库包**：交付 LDC 运行时套件中的
**Phobos（D 标准库）+ druntime** 共享库（`libphobos2-ldc-shared.so.112` /
`libdruntime-ldc-shared.so.112`）与 D import 源码（`include/d/`）。
与已发布的 `ldc/1.42.0` 工具包（tool，仅静态库）互补：编译 D 代码用
`tool_requires("ldc/1.42.0")`，链接标准库消费本包。

上游：<https://github.com/ldc-developers/ldc> · DMDFE 前端 v2.112.1 ·
源码 sha256 `9bb0f628f869f7fc7b53c381a79742d29c17552c6f1a56b0a02aa289e65a0e3b`
（conandata.yml 仅官方 URL 一条）。

## 前提

- conan settings 须含 `os=OHOS`（大写，同 ldc 包要求；stock conan 2 默认不含，
  推荐 OpenHarmonyPCDeveloper 分发的 conan 或 `settings_user.yml` 手工添加）。
- 构建期 `tool_requires("ldc/1.42.0")`（D 引导编译器；ohpcd 已发布含二进制，
  rrev `591fc840…`，`tool_requires` 直接命中，无需现场编译 ldc）。

## 出包（鸿蒙 PC 真机原生）

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build="liblphobos/*"
```

> **构建方式说明**：上游钦定的独立构建工具 `ldc-build-runtime` 在 OHOS 动态链接
> 不可运行（缺 `libgcc_s.so.1`/`_Unwind_*`，ldc 任务实测），故配方复刻其
> `runCMake()` 官方参数（`LDC_EXE_FULL`/`DMDFE_MINOR_VERSION=112`/
> `DMDFE_PATCH_VERSION=1`/`TARGET_SYSTEM=Linux;UNIX;musl`/`BUILD_SHARED_LIBS=ON`），
> 直接驱动上游 `runtime/CMakeLists.txt`，全部为上游官方构建入口参数。

## 包内容

- `lib/`：release + debug 两套共享库实体（`libphobos2-ldc-shared.so / .so.112`、
  `libdruntime-ldc-shared.so / .so.112` 等 12 个文件，SONAME 软链已实体化）
- `include/d/`：druntime（`object.d`/`core/`/`ldc/`/`etc/`/importc 头）+ Phobos（`std/`）
- `licenses/`：Boost Software License（druntime/Phobos）+ BSL（ldc 附加组件）
- 所有 `.so` 已经 `binary-sign-tool` 自签（OHOS 要求，否则 dlopen 报错）

## OHOS 适配要点（详见 notes.md）

1. **GC 线程挂起信号**：druntime `thread_suspendAll()` 用 `SIGRTMIN(35)` 停线程，
   OHOS 内核对 35 号实时信号不投递（`pthread_kill` 返回 0 但处理函数永不触发，
   多线程程序死锁）→ 补丁改用 `SIGUSR1/SIGUSR2`（上游 OpenBSD 同构分支）。
2. **pthread cancellation + glibc 特有符号**：OHOS musl 不导出 `pthread_cancel`
   家族；共享库把 `core/internal/elf/dl.o` 整体打入，残留 glibc 特有的
   `program_invocation_name` → `shim/pthread_cancel_shim.c` 编 PIC 对象，
   经上游 runtime CMake 的 `LD_FLAGS` 链入 `.so`。
3. **签名**：OHOS 要求被 exec/dlopen 的 ELF/`.so` 有签名 → 构建期自签全部产物。

## 消费（库依赖）

```python
def requirements(self):
    self.requires("liblphobos/1.42.0")

def build_requirements(self):          # D 源码还需要编译器
    self.tool_requires("ldc/1.42.0")
```

```bash
# D 程序链接本包共享库（test_package/test_liblphobos.sh 为可运行样例）
ldc2 -conf= -I<本包>/include/d -defaultlib=phobos2-ldc-shared,druntime-ldc-shared \
     -L-L<本包>/lib -L-lz -L-lm app.d -of=app
```
