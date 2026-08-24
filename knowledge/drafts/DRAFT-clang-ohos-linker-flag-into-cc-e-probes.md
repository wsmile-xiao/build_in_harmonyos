# DRAFT-clang-ohos-linker-flag-into-cc-e-probes：OHOS 宿主 clang 把链接期选项带进 $CC -E 预处理探测

> Contributor: i686-elf-binutils 2.46.1 适配 | Status: Draft | Updated: 2026-08-23
> Source: archives/i/i686-elf-binutils/2.46.1

## 现象

GNU binutils (autotools) 在 OHOS 宿主用 clang 配置时,configure 的 $CC -E 预处理
模式头文件探测 (AC_CHECK_HEADERS) 误判:HAVE_LIMITS_H/HAVE_FCNTL_H/HAVE_SPAWN_H
被判定为 no,随后 libiberty 编译报 LONG_MIN undeclared (fibheap.c)、O_* undeclared
(pex-unix.c)、posix_spawn undeclared。

## 根因分析

- 构建宿主 clang 在每次编译调用 (含 $CC -E 预处理探测) 注入链接期选项 -fuse-ld=lld。
- 该选项在预处理上下文未被使用,clang 向 stderr 打印 "argument unused during
  compilation" 告警。
- autoconf 旧式预处理模式头文件检查把任何 stderr 视为失败 → 头文件探测全 no。

## 解决方案

build() 向 CPPFLAGS 追加 -Wno-unused-command-line-argument,精准抑制该单条诊断:

```python
os.environ["CPPFLAGS"] = (
    (os.environ.get("CPPFLAGS", "") + " -Wno-unused-command-line-argument").strip()
)
```

## 跨库复用证据

- i686-elf-binutils 2.46.1 (本候选)、x86_64-elf-binutils 2.46.1、
  riscv64-elf-gdb 17.2 三处注释+修复逐字同款。
- 仓库 archives 共 20 个文件含 -Wno-unused-command-line-argument (gdal/hydra/
  kvazaar/octave/proj/inotify-tools/lttoolbox/wal2json/x86_64-elf-grub 等)。

## 验证证据

- round-5 conan create PASS;make check 0 unexpected failure (2244 pass/3 XFAIL/
  44 untested/269 unsupported)。
- 修复后头文件探测恢复 yes,libiberty 无 LONG_MIN/O_*/posix_spawn 编译错误。

## 禁止做法

- 不要用平台宏 (__OHOS__) 硬编码或预置 HAVE_*_H 答案。
- 不要全局 -Wno-error 或只在 CFLAGS 加抑制 (会掩盖真实错误或漏掉 $CC -E 阶段)。

## 知识库查重结论

- E063 (-Werror 泛告警)、E266 (lld 缺 libxml2 链接期)、E321-draft-78CB (SDK lld
  flavor 修复)、E327-draft-configure-raw-lib-probe、DRAFT-tmate-ohos-autotools-
  probe-alignment (include 顺序) 机制均不同:本文机制为 "$CC -E 预处理探测 stderr
  污染"。
- 检索词 unused-command-line / argument unused / Wno-unused / HAVE_LIMITS_H /
  HAVE_FCNTL_H / HAVE_SPAWN_H 在 knowledge/** 全目录 grep 0 命中。
- 无既有条目覆盖,本条目为新增候选。

## 关联条目

- 相关: E063、E266、E321-draft-78CB、E327-draft-configure-raw-lib-probe、
  DRAFT-tmate-ohos-autotools-probe-alignment
