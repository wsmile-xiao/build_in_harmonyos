# ldc 1.42.0 — 鸿蒙 PC conan 制品（LDC / LLVM D Compiler）

`os=OHOS, arch=armv8`(= aarch64) 的 **tool 包**：提供 D 语言编译器 `ldc2`（及 DMD 命令行
兼容前端 `ldmd2`）与 **druntime + Phobos** 运行时。下游含 D 源码的项目可在真机上
`conan create` 时 `tool_requires` 本包来编译 D 代码。

上游：<https://github.com/ldc-developers/ldc> · LDC 1.42.0 基于 **DMD 前端 v2.112.1**。

## 前提

所用 conan 的 settings 须含 `os=OHOS`（大写）；stock conan 2 默认不含。推荐在
`~/.conan2/settings_user.yml` 的 `os:` 下加 `    OHOS:`，或使用 OpenHarmonyPCDeveloper
分发的 conan。

## 出包（鸿蒙 PC 真机原生）

```bash
conan create . -pr ohos-native
```

源码由 `conandata.yml` 的 url 在 `conan create` 时下载并做 sha256 校验。

> ⚠️ **自举要求**：D 无法从 C/C++ 侧自举（LLVM 不含 D 前端），而设备/NDK 不带任何 D
> 编译器。故构建期需一个**引导编译器**——本配方从 `conandata.yml` 的 `bootstrap`
> 自动取得上游预编译 `ldc2`（alpine/musl 变体，与 OHOS 的 musl 同族，实测可在设备运行），
> 并在使用前自动 `binary-sign-tool` 自签（OHOS 要求，否则 exec 报 Permission denied/rc=126）。

## 包内容

- `bin/ldc2`、`bin/ldmd2`（DMD 命令行兼容）、`bin/ldc-build-runtime`、`bin/ldc-profdata`
  / `ldc-profgen` / `ldc-prune-cache`、`bin/timetrace2txt`、`bin/ddemangle`
- `lib/libdruntime-ldc.a`、`lib/libphobos2-ldc.a`（运行时静态库）
- `lib/libLLVM.so`（运行期 `ldc2` 的 `NEEDED`，来自本仓 `llvm/20.1.0`）
- `include/d/`（druntime + Phobos 的 D 模块源码）、`etc/ldc2.conf`
- 所有 ELF/`.so` 已经 `binary-sign-tool` 自签

## 消费（作 tool 依赖）

```python
def build_requirements(self):
    self.tool_requires("ldc/1.42.0")

def build(self):
    pkg  = self.dependencies.build["ldc"].package_folder
    ldc2 = pkg + "/bin/ldc2"          # D 编译器
    # 编译并链接 D 程序（运行时已随包交付，无需额外 -L）
    #   ldc2 app.d -of=app -L-lz -L-lm
```

`package_info()` 已导出 `DC` / `DMD` 指向 `bin/ldc2`，并把 `bin/`、`lib/` 加入
`PATH` 与 `LD_LIBRARY_PATH`（运行期需 `lib/` 上的 `libLLVM.so`）。

## OHOS 适配要点

本包对上游做了 **2 处运行时补丁**（见 `patches/0001-ohos-thread-gc-signals.patch`
与 `notes.md`）：

1. **SIGRTMIN 在 OHOS 上不可达**：实测只有 35 号信号无法送达处理函数（自投递与跨线程
   投递均不触发），而 `SIGRTMIN+1`(36) 及 `SIGUSR1/2` 正常。druntime 的 GC
   `thread_suspendAll()` 恰用 `SIGRTMIN` 停线程供扫描 → 永久阻塞 → 运行时死锁。
   改用 `SIGUSR1`/`SIGUSR2`，与上游为 OpenBSD 提供的既有分支同构。
2. **OHOS musl 缺 pthread cancellation 家族**：`pthread_setcancelstate` 等未导出，
   而 druntime 引用它导致链接失败；采用上游同一函数 `else` 分支的 no-op 语义。

另需：`config.guess` stub（设备 `uname` = `HarmonyOS`，cmake/LLVM 均不识别）、
`TMPDIR` 指向可写目录（OHOS 上 `/tmp` 只读）、ELF 签名。

## 上游测试实测

druntime + Phobos 共 236 个测试模块，逐个运行结果：

| 范围 | PASS | FAIL | TIMEOUT | SKIP（无 unittest） | 通过率 |
|------|------|------|---------|--------------------|--------|
| druntime | 52 | 2 | 1 | 5 | 52/55 = **94.5%** |
| Phobos | 125 | 6 | 1 | 44 | 125/132 = **94.7%** |
| **合计** | **177** | 8 | 2 | 49 | **177/187 = 94.7%** |

剩余失败项均为平台固有限制（Windows 专有 API、musl 的 `fclose`/`tmpfile` 语义、
`/usr/share/zoneinfo` 缺失、libcurl 未加载等），详见 `notes.md`。
