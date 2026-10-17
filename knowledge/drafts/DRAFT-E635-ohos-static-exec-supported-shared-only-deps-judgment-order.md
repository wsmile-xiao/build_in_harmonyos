# DRAFT-E635-ohos-static-exec-supported-shared-only-deps-judgment-order：OHOS 工具链支持 -static 可执行，「-static 失败」先查依赖侧 .a 再动补丁

> Contributor: libstorj-1.0.3 任务 | Status: Draft | Updated: 2026-09-21
> Source: libstorj 1.0.3 适配（feat/libstorj-1.0.3）
> 对应：`knowledge/drafts/DRAFT-E635-ohos-static-exec-supported-shared-only-deps-judgment-order.kv`

## 现象

上游 Makefile.am 把 CLI 或测试程序以 `-static` 整体静态链接（libstorj 1.0.3 的
`storj_LDFLAGS = -Wall -static`、`tests_LDFLAGS = -Wall -g -static -lmicrohttpd`）。
适配时的惯性做法是"OHOS 不支持静态链接，先删 -static"——本任务实测证明这个
前提**不成立**，删早了会留下不必要的补丁面。

## 实测事实（2026-09-21，OHPC HAD-W24 / llvm 15.0.4 / ohos-sdk 26.0.0.18）

```console
$ clang -static hello.c -o hello && file hello
hello: ELF executable, 64-bit LSB arm64, static, not stripped
$ ./hello; echo $?
0
```

静态 musl + libclang_rt 在 OHOS SDK sysroot 里齐备，静态可执行**可链接、可运行**。

## 真正的失败面：依赖侧归档

conan 依赖制品是否带 `.a` 与包而异（libstorj 1.0.3 依赖实测）：

| 依赖包 | p/lib 实物 | -static 链接 |
|---|---|---|
| nettle/3.10.2.1 | 仅 `.a` | ✓ 可用 |
| libmicrohttpd/1.0.1 | 仅 `.a` | ✓ 可用 |
| libuv/1.52.1.1 | `.a` + `.so` 双形态 | ✓ 可用 |
| json-c/0.18 | `.a` + `.so` 双形态 | ✓ 可用 |
| **libcurl/8.5.0** | **仅 `.so`** | ✗ `-lcurl` 必失败 |

## 判读序（固定三步，别跳）

1. **探针工具链**：`clang -static hello.c` → 产出 ELF EXEC 且运行 rc=0 ⇒ 工具链支持；
2. **逐依赖查归档**：`ls <dep package_folder>/lib/*.a`——任一依赖只有 `.so` ⇒
   `-static` 全量静态链接必失败（libtool/ld 在静态模式找不到 `.a`）；
3. **处置取小**：只删上游 `-static`（补丁），库本体仍按 R26 静态优先
   （--enable-static --disable-shared）；不要为凑 -static 去改依赖 shared 选项
   （那会触发整条闭包源码重编，代价与失败面都大）。

## 关联条目差异

- E028（configure-static-only）管"共享库覆盖系统库导致符号不完整"的运行期冲突面；
  本条管**构建期** `-static` 的工具链能力与依赖归档判读序，两者不重叠。
- E467 管 AutotoolsDeps LIBS 全量链接导致 conftest 运行失败；本条在其基础上
  提醒：静态/共享判定还要看**交付产物的 DT_NEEDED**（本任务消费者 .a + 共享依赖
  混链，运行期靠 conanrun 注入 LD_LIBRARY_PATH）。
