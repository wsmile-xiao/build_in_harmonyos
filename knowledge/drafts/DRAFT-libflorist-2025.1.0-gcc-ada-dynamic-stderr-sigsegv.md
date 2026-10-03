# 动态链接的 gcc-ada 二进制在 OHOS 上首次 stdio stderr 访问即 SIGSEGV

- **日期**: 2026-09-27
- **软件**: libflorist 2025.1.0 构建期生成器 `c-posix` / `c-posix-signals` / gcc-ada 9.5.0
- **门禁**: `conan create` → `build()` → 执行自建构建期工具
- **状态**: DRAFT（同 stem 配对 `DRAFT-libflorist-2025.1.0-gcc-ada-dynamic-stderr-sigsegv.kv`）

## 现象

用 gcc-ada 动态链接编译出的构建期小工具，在 OHOS 上**立即段错误**，
且**在任何输出之前**退出（stdout / stderr 全空）：

```
libflorist/2025.1.0@ohpcd/stable: RUN: ./c-posix > c-posix.log 2>&1
libflorist/2025.1.0@ohpcd/stable: ERROR: Error 126 while executing    # 未签名形态
# 或签名后：
$ ./c-posix ; echo $?
139                                                                    # SIGSEGV
```

分阶段探针（在 `main` 内逐步 `fprintf` 阶段名）同样无输出，
外观上像"启动期/加载期崩溃"或"逻辑分支越界"。

## 根因定位（对照实验）

同一 OHOS aarch64 真机、同一 gcc-ada 9.5.0，逐项排除：

| 程序 | 结果 |
|---|---|
| `printf(...)` → stdout，动态链接 | 正常输出 |
| `fprintf(stderr, ...)` / `fputs(..., stderr)` | **SIGSEGV 139** |
| `write(2, ...)` 原生调用 | 正常 |
| 同一程序用 OHOS clang 编译 | 正常 |
| 同一程序加 `-static`（gcc-ada 编译） | 正常 |

结论指向"gcc-ada 动态链接产物在本运行时的 stdio `stderr` 初始化/首次写入路径"，
而非程序逻辑。`write(2,...)` 与 `-static` 均正常，说明是动态链接态下的库初始化问题。

> **说明**：未获取到可用 backtrace —— 本机 gdb 无法 ptrace，报
> `Could not trace the inferior process / ptrace: Permission denied`。
> 故根因描述限于**可观测行为**，不臆测具体符号。

**实用判据**：「任何输出前即退出且 `exit=139`」+「`write(2)` 正常」+「`-static` 正常」
⇒ 高度疑似本条。

**易混形态辨析**：

| 形态 | 退出码 | 原因 |
|---|---|---|
| 未签名 ELF | **126** `Permission denied` | OHOS 拒绝 exec 未签名二进制，**必须签名** |
| 动态链接 stdio stderr | **139** SIGSEGV | 本条，须 **`-static`** |

二者常在同一次调试中同时出现，不能混为一谈。

## 处置（已验证）

配方内对构建期工具一律加 `-static`：

```sh
gcc -O2 -static -DGENDIR="gensrc" -o c-posix          c-posix.c -lpthread
gcc -O2 -static -DGENDIR="gensrc" -o c-posix-signals  c-posix-signals.c
```

执行前必须签名：

```sh
llvm-objcopy --remove-section .codesign <tool>
binary-sign-tool sign -inFile <tool> -outFile <tool> -selfSign 1
```

修复后生成器正常工作，产出 `gensrc/posix.ads`、`posix-limits.ads`、`posix-options.ads`、
`posix-c.ads` 与 `posix-implementation-ok_signals.ads`。

## 禁止事项

| 禁止 | 原因 |
|---|---|
| 因"启动期段错误"就去排查全局构造器 / 大 BSS / 栈大小，或给程序加大量日志反复重试 | 对照实验已把自变量锁定在「动态链接 + stdio stderr」；沿错误方向排查会消耗多轮 CI 且始终不收敛（本库实际耗时多轮探针才定位） |
| 把构建期工具也编进最终交付物 | 生成器是构建期工具，不应进入 `package()`；其崩溃形态会影响任何调用者，交付出去等于把缺陷外溢 |

## 相关条目

- `DRAFT-ada-gnats-native-only-toolchain-cross-build-trap` —— 仅 OHOS 制品 / 必须原生构建
- `DRAFT-gcc-ada-ohos-link-only-libunwind` —— gcc-ada 链接契约
- `DRAFT-ohos-module-ctor-eager-dlopen-sigsegv` —— 同为 SIGSEGV 但为模块构造器 dlopen

## 溯源

task libflorist 2025.1.0 适配（分支 `feat/libflorist-2025.1.0`），2026-09-27 真机实测；
对照矩阵 5 组、每组均签名后执行。
