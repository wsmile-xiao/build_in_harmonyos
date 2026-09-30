# 插件 .so 依赖「非系统同名库」时的产物闭包校验与运行时定位口径

> Status: DRAFT（草稿期以文件名标识；promote 时由工具分配 E 编号）
> Source: kamailio-gcrypt 6.0.6（`gcrypt.so` 依赖 `libgcrypt.so.20`）HarmonyOS PC 适配，2026-09-29
> Related: E074/E525（OHOS 禁 FIFO → `make -j1`）；R26（**系统同名库**须静态）；同族判例 kamailio-cnxcc（动态 libevent/hiredis）；P004、P013

## 背景

kamailio 的模块 Makefile 在交叉编译（`CROSS_COMPILE` 为空）时用
`pkg-config --exists libgcrypt` 探测外部库，未命中则回退
`-I$(LOCALBASE)/include -L$(LOCALBASE)/lib -lgcrypt`。这类"探测 + 回退"在交叉编译场景
有三种坏结局，而且**都不会在编译链接期暴露**：

1. 探测到**构建机系统的** libgcrypt（架构/版本错配）→ 链接通过，目标机加载失败或行为异常；
2. 链接形态固化构建机路径（RPATH / 绝对路径）→ 装机即挂；
3. 依赖库在 OHOS sysroot 与目标机 `/lib` 中**根本不存在**（libgcrypt 正是这种**非系统同名库**）
   → 运行时 `cannot open shared object file`。

因此"编译通过"对插件模块毫无说服力。本条目把本次适配固化的**构建期钉死 + 产物期证明 +
运行时定位**三段口径记录下来。

## 构建期：钉死探测结果（不让构建机系统库有机会介入）

| 手段 | 目的 |
|------|------|
| make 命令行变量 `GCRYPT_BUILDER="pkg-config libgcrypt"` | 命令行变量优先于 Makefile 内部赋值 → 强制走 pkg-config 分支，而非 `-I/-L` 回退 |
| `PKG_CONFIG_PATH=<依赖包>/lib/pkgconfig`（仅含依赖包） | 即使真跑 pkg-config，也只可能命中 conan 依赖包 |
| `LOCALBASE=<依赖包目录>` | 让 Makefile 的**回退分支**也指向依赖包（`pkg-config` 缺失时不失控） |
| `CPATH` / `LIBRARY_PATH` → 依赖包 `include`/`lib` | 无 pkg-config 时的兜底，仍只指向依赖包 |
| `CC`/`CXX` ← Conan `tools.build:compiler_executables` | 显式注入，不裸用 `${CC}`（R33） |

## 产物期：证明闭包（可脚本化、随 PR 长期回归）

四个必查项（本仓实现：`test_package/check_gcrypt_module.py`，纯 Python ELF 解析、16 项断言、
无外部工具依赖 → CI 干净环境可跑）：

1. **依赖集合**：`DT_NEEDED` 恰为预期集合（本例 `{libc.so, libgcrypt.so.20}`，无多余项）；
2. **无路径泄漏**：无 `RPATH`/`RUNPATH`（运行时定位交给部署侧，不固化构建机路径）；
3. **未定义符号 100% 可归属**：本例 49 个 = libc/CRT 9 + `libgcrypt.so.20` 17（带
   `GCRYPT_1.6` 版本标签）+ kamailio core 23；对**依赖包逐符号交叉核验**其确实导出那些
   `gcry_*` 符号（不是抽样，是全量）；
4. **依赖链闭合**：`libgcrypt.so.20 → libgpg-error.so.0`，后者在 conan 依赖图内且实测存在；
   另将许可证（`licenses/COPYING`）随包。

```bash
# 1) 依赖集合与路径泄漏
llvm-readelf -d src/modules/gcrypt/gcrypt.so | grep -E "NEEDED|RPATH|RUNPATH"
# 2) 未定义符号面全量与归类
llvm-nm -D --undefined-only src/modules/gcrypt/gcrypt.so | wc -l
# 3) 依赖包是否真的导出（逐符号核验）
llvm-nm -D --defined-only <libgcrypt 包>/lib/libgcrypt.so.20 | grep -E "gcry_(cipher|md|check_version|control|randomize|strerror|strsource)"
# 4) 依赖链闭合
llvm-readelf -d <libgcrypt 包>/lib/libgcrypt.so.20 | grep NEEDED   # 期望含 libgpg-error.so.0
ls <libgpg-error 包>/lib/libgpg-error.so.0*
```

## 运行时定位口径

依赖 .so 由 conan 依赖链提供（**不静态、不打 RPATH**），部署时经 `LD_LIBRARY_PATH`
（或等价加载路径）解析。`package_info()` 以 `libdirs=["lib/kamailio/modules"]` 声明模块目录、
`libs=[]`（模块不被链接消费，属宿主 `loadmodule` 加载的运行期组件）。

> 注意与 R26 的区别：R26 要求**系统同名库**静态链接以避免污染 `/lib`、`/lib64`；
> libgcrypt 在 OHOS 上**不是**系统同名库（sysroot 与目标机 `/lib` 均无），
> 不落入 R26 适用面，按仓库口径走 conan 依赖链。同族判例：kamailio-cnxcc（动态 libevent/hiredis）。

## 禁止项

- **写入 RPATH / 绝对加载路径**（`-Wl,-rpath`、`-Wl,-R` 等）：鸿蒙上 `$ORIGIN/../lib` 等
  相对形态不稳定，绝对路径在目标机必然失效 → "本地能跑、装机即挂"。
- **探测失败就去装构建机系统包**（`apt-get install libgcrypt-dev` 之类）：把宿主库混进
  交叉产物，且 CI 干净环境没有这些包（本地能过、CI 必挂）。

## 兜底方案

把依赖以静态形态链入（需依赖包同时发 `.a`，且许可证/仓库口径允许）。本例 libgcrypt conan 包
仅发 `.so`，且它是通用加密库（非系统同名库），故不采用，仅作特殊场景备用。

## 原则引用

P004（平台隔离的标准写法）、P013（平台限制必须降级而非绕过）。
