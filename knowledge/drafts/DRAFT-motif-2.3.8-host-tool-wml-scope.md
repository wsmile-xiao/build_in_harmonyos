# DRAFT-motif-2.3.8-host-tool-wml-scope：全树 make 被 host-only 工具拖垮时收缩构建作用域

> Status: Draft | Updated: 2026-09-13
> Source: motif 2.3.8 HarmonyOS PC 适配（libXm.so.4）
> 对应：knowledge/drafts/DRAFT-motif-2.3.8-host-tool-wml-scope.kv
> 关键词：Motif, tools/wml, wmluiltok, host 工具, 交叉编译, undefined symbol main, 作用域收缩

## 现象或适配场景

Motif 全树 `make` 在 `tools/wml` 目录终止；此前 `lib/` 下的目标库已经编译成功：

```text
libtool: link: clang -o wmluiltok wmluiltok.o
ld.lld: error: undefined symbol: main
>>> referenced by crt1.c:18 (.../aarch64-linux-ohos/Scrt1.o:(_start_c))
clang-15: error: linker command failed with exit code 1
make[2]: *** [Makefile:495: wmluiltok] Error 1
make[1]: *** [Makefile:394: all-recursive] Error 1
make: *** [Makefile:451: all-recursive] Error 1
```

## 根因

`wmluiltok` 是**构建期 host 工具**（`.l` 经 lex/flex 生成、在构建机上运行，用于把 WML 编译成
UIL 资源）。上游 `Makefile` 假设 host==target 的本地构建，交叉编译到 OHOS 时该生成器产物
没有 `main`，而链接又按目标可执行文件进行（以 `Scrt1.o` 的 `_start_c` 引用 `main`），必然失败。
这是**构建作用域**问题，与要交付的 `libXm`/`libMrm` 目标产物无关。

## 修复步骤

1. 配方把构建与安装限定到 `lib/`：

```python
autotools.make(args=["-C", "lib", "-j1"])                # build()
autotools.make(args=["-C", "lib", "check", "-j1"])       # 层1 上游测试痕迹（automake check 目标）
self.run(f"make -C lib install DESTDIR={pkg} -j1")       # package()
```

2. 在 `notes.md` 与版本级 `manifest.yaml` 中如实登记：全树 make 的原始错误、作用域收缩的理由、
   未构建的组件（`tools/`、`clients/`、`demos/`、`doc/`），不静默丢组件。

## 验证方式

- 原始失败留证：`ld.lld: undefined symbol: main` → `make[2]: *** [Makefile:495: wmluiltok] Error 1`。
- 作用域收缩后 `conan create` 全链路绿：`libXm.so.4.0.4`（SONAME `libXm.so.4`）、
  `libMrm.so.4.0.4`、222 个 `Xm/*.h`（`include/**/*.h` 合计 226）；`test_package assertions=18 failures=0`。

## 适用范围和安全边界

适用于所有"顶层 Makefile 混编 host 工具 + 目标库"的 autotools 上游。边界：只交付库时收缩到
`lib/` 是**如实登记的作用域决定**，不是掩盖失败——不得据此删掉上游测试调用（`make -C lib check`
仍须执行），也不得把 host 工具失败的日志当作"平台不支持整个包"的理由。
