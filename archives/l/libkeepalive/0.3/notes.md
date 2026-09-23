# libkeepalive 0.3 适配笔记

## 软件信息

| 项 | 值 |
|----|----|
| 软件 | libkeepalive |
| 版本 | 0.3 |
| 上游 | SourceForge 项目 libkeepalive / http://libkeepalive.sourceforge.net/ |
| 作者 | Fabio Busatto <fabio.busatto@gmail.com> |
| 许可 | MIT |
| 构建系统 | makefile（纯 GNU Make，无 configure） |
| 产物 | `src/libkeepalive.so` |
| 依赖 | 无三方依赖（仅 libc，链接 `-ldl` 由 musl 并入 libc） |

libkeepalive 是一个 **LD_PRELOAD 拦截库**：hook `socket()`，对 AF_INET / AF_INET6
的 SOCK_STREAM socket 打开 `SO_KEEPALIVE`，并可用环境变量
`KEEPCNT` / `KEEPIDLE` / `KEEPINTVL` 覆盖 `TCP_KEEPCNT` / `TCP_KEEPIDLE` /
`TCP_KEEPINTVL`；`KEEPALIVE=off` 可关闭注入。

## 编译环境

- 编译器: OHOS clang 15.0.4（target `aarch64-unknown-linux-ohos`，`/data/service/hnp/bin/clang`）
- 构建日期: 2026-09-14
- 状态: built

## 实际编译步骤

上游是纯 Makefile 工程，顶层 Makefile 的 `default` 目标做四件事：
`make -C src/` → `make -C test/` → `cp src/libkeepalive.so libkeepalive.so` → `strip -s libkeepalive.so`。

本适配**只执行 `make -C src/`**：

```bash
make -C src CC=/data/service/hnp/bin/clang -j1
# clang -fPIC -ansi -pedantic -Wall   -c -o libkeepalive.o libkeepalive.c
# clang -shared -Wl,-soname,libkeepalive.so -o libkeepalive.so libkeepalive.o -ldl
```

上游编译选项全部保留（`-fPIC -ansi -pedantic -Wall`），无告警、无源码补丁。
`src/Makefile` 里硬编码的 `CC=gcc` 通过命令行 `CC=<conan toolchain clang>` 覆盖（R33），
不依赖 shell 的 `${CC}`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 按上游顶层 `make` 构建后，`LD_PRELOAD=libkeepalive.so ./test` 输出 `SO_KEEPALIVE is OFF`，拦截完全不生效 | OHOS 链接器在 ELF 中写入 `.codesign` 签名块；顶层 Makefile 末尾的 `strip -s` 改变了文件布局，使签名失效，OHOS 加载器随后**静默忽略**该 preload 库（不报错、不加载） | 不执行顶层 Makefile 的 `strip` 步骤，改为 `make -C src/` 直接产出带有效签名的 `.so`；或 strip 后用 `binary-sign-tool sign -selfSign 1` 重新签名 |
| 2 | （排除项）怀疑 LD_PRELOAD 在 OHOS 上不受支持 | 受控实验：自建只打印一行的 `socket()` 拦截探针库，`LD_PRELOAD` 下成功拦截，`dlsym(RTLD_NEXT,"socket")` 返回有效地址 → LD_PRELOAD 与 RTLD_NEXT 在 OHOS musl 上均可工作 | 排除该方向，问题定位到 `.so` 自身（即问题 1） |

### 问题 1 的证据（可复现的最小对照）

```
# 同一份 .so：未 strip vs strip -s
LD_PRELOAD=$PWD/u.so ./test/test   ->  SO_KEEPALIVE is ON  / TCP_KEEPCNT=9 ...
LD_PRELOAD=$PWD/s.so ./test/test   ->  SO_KEEPALIVE is OFF
# 对自建探针库做同样对照，结论一致（strip 后拦截消失）：
LD_PRELOAD=$PWD/pu.so ./test/test  ->  [probe] socket() intercepted: domain=2 type=1 proto=6
LD_PRELOAD=$PWD/ps.so ./test/test  ->  (无任何输出，未拦截)
# strip 变体全部失效：--strip-debug / --strip-unneeded / -S 均导致 OFF
# 重新签名后恢复：
strip -s r.so && llvm-objcopy --remove-section .codesign r.so \
  && binary-sign-tool sign -inFile r.so -outFile r.signed.so -selfSign 1
LD_PRELOAD=$PWD/r.signed.so ./test/test  ->  SO_KEEPALIVE is ON
```

两版 ELF 的 `.codesign`、`.text`、`.dynsym`（含导出的 `socket`）内容哈希完全一致，
且程序头（program headers）一致，差异只在 strip 后的文件布局 —— 说明不是导出符号丢失，
而是 `**.codesign` 覆盖的整文件签名在 strip 后失配**。

## 源码修改

无。`patches/` 为空，未修改上游任何源码或构建脚本。

## 依赖版本

无三方依赖。`ldd` 视角仅依赖 `libc.so`（OHOS musl；`-ldl` 不产生额外 DT_NEEDED）。

## 上游测试与验证结果

上游 **没有自动化测试目标**：顶层 Makefile 只有 `default` 与 `clean`，
不存在 `make test` / `make check`，也没有 ctest / meson test 注册项。
上游提供的测试入口是人工对比程序 `test/test.c`（由 `make -C test/` 构建为 `test/test`）。

实测（真实执行，非占位）：

```bash
cd libkeepalive-0.3.work                     # 上游源码树
make CC=clang -j1                            # 构建 src/ + test/
./test/test
# SO_KEEPALIVE is OFF                        # 基线：未 preload
LD_PRELOAD=$PWD/src/libkeepalive.so ./test/test
# SO_KEEPALIVE is ON
# TCP_KEEPCNT   = 9
# TCP_KEEPIDLE  = 7200
# TCP_KEEPINTVL = 75
KEEPCNT=7 KEEPIDLE=42 KEEPINTVL=13 LD_PRELOAD=$PWD/src/libkeepalive.so ./test/test
# SO_KEEPALIVE is ON
# TCP_KEEPCNT   = 7
# TCP_KEEPIDLE  = 42
# TCP_KEEPINTVL = 13
KEEPALIVE=off LD_PRELOAD=$PWD/src/libkeepalive.so ./test/test
# SO_KEEPALIVE is OFF                        # 开关生效
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libkeepalive.so` | aarch64 ELF 共享库，SONAME `libkeepalive.so`，`DT_NEEDED: libc.so`，带有效 `.codesign` |
| `licenses/LICENSE` | 上游 MIT 许可证 |

## 注意事项

- 该库的用途是 `LD_PRELOAD`（或 `/etc/ld.so.preload`），**不是链接期依赖**；
  消费方不应 `-lkeepalive`，而应在运行期设置 `LD_PRELOAD`。
- 任何对最终 `.so` 的 strip/后处理都会破坏 OHOS 代码签名并使其拦截静默失效；
  若必须 strip，务必随后重新自签名。
## 发现与知识

- ✅ OHOS 链接器注入的 `.codesign` 一旦被 strip 破坏，加载器会**静默忽略**该库的 LD_PRELOAD 拦截（无任何报错，表现为 socket() 未被 hook）；规避方式是不 strip 或 strip 后重签（knowledge_ref: E429）
- ✅ 上游根 Makefile 末尾的 `strip -s` 是本库在 OHOS 上失效的直接原因；配方改用 `make -C src/` 后拦截正常（knowledge_ref: E429）
- ✅ libkeepalive 的 socket() 拦截在 OHOS musl 上确实可用：`dlsym(RTLD_NEXT, "socket")` 可解析，SO_KEEPALIVE / TCP_KEEPCNT / TCP_KEEPIDLE / TCP_KEEPINTVL 受支持，KEEPALIVE=off 生效（knowledge_ref: E502）
- ✅ strip 后经 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` 重签，拦截能力恢复（实测复验）（knowledge_ref: E077）
---

**编译结束**: 2026-09-14 13:22
**最终状态**: built
