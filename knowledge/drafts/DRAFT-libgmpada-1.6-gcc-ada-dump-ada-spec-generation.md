# DRAFT-libgmpada-1.6-gcc-ada-dump-ada-spec-generation — gcc-ada 无 C++ 前端时生成 Ada 规格

> **Contributor**: qianxia | **Status**: VERIFIED DRAFT | **Updated**: 2026-09-20
> **Source event**: libgmpada 1.6 HarmonyOS PC 适配（AtomGit #8215），鸿蒙电脑原生 `conan create` 实录

## 知识类型与提升边界

本条目是路径 B 知识库扩展候选，不预占正式 E 编号，只进入 `knowledge/drafts/**`，
不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则；是否提升由维护者和评审决定。

## 适用范围

适用于同时满足以下条件的库：

- 用 `gcc`/`g++` 的 `--dump-ada-spec`（`-fdump-ada-spec`）从 C/C++ 头文件自动生成 Ada 绑定规格；
- 构建环境里的 Ada 工具链是 ohpcd 的 `gcc-ada/9.5.0`——它以 `--enable-languages=c,ada` 构建，**没有 g++**；
- 目标是 OHOS aarch64（构建与运行都在设备/worker 原生环境）。

## 使用说明

1. 把上游默认的 C++ 驱动改成 gcc-ada 的 `gcc`，并在 dump 调用上加 `-fsyntax-only`。
2. 不要信任上游对 dump 产物的 glob/改名约定，先在配方里显式生成目标 `.ads`。
3. 生成后让上游 `make` 因时间戳直接跳过原目标，构建继续。

## 输入输出定义

| 项 | 定义 |
|---|---|
| 输入 | 一个内容为 `#include <lib.h>` 的临时头文件；`-I` 指向该库的头文件目录 |
| 命令 | `gcc -I<inc> -Wall -Wextra -fsyntax-only --dump-ada-spec tmp.h` |
| 输出 | 当前目录下 `<header>_h.ads`（例如 `gmp_h.ads`），内含 `package <header>_h is` |
| 失败模式 | 去掉 `-fsyntax-only` → 驱动尝试链接，`undefined reference to main`；用 `g++` → command not found；glob `*_gmp_h.ads` → 不匹配 |

## 示例（libgmpada 1.6 实测片段）

```python
# conanfile.py build() 内，make 之前
obj = os.path.join(self.source_folder, "obj"); os.makedirs(obj, exist_ok=True)
open(os.path.join(obj, "tmp.h"), "w").write("#include <gmp.h>\n")
self.run("cd {obj} && {cxx} -I{inc} -Wall -Wextra -fsyntax-only --dump-ada-spec tmp.h"
         .format(obj=shlex.quote(obj), cxx=shlex.quote(gcc_ada_gcc),
                 inc=shlex.quote(gmp_includedir)), env="conanbuild")
# 把 package gmp_h 改名 TMP_gmp_h，套用未修改的上游 gmp-h.ads.sed
self.run("sed -e 's/^package gmp_h is$/package TMP_gmp_h is/' "
         "-e 's/^end gmp_h;$/end TMP_gmp_h;/' obj/gmp_h.ads | sed -f gmp-h.ads.sed > src/gmp-h.ads")
```

## 失败原文（四段式）

1. **首个错误**：`gcc ... --dump-ada-spec tmp.h` →
   `.../ld: crt1.o: in function \`_start': undefined reference to \`main'` / `collect2: error: ld returned 1 exit status`
2. **根因**：OHOS gcc 驱动包装器按 `-c/-S/-E/-fsyntax-only` 判定是否链接，`--dump-ada-spec` 不在白名单。
3. **修复**：加 `-fsyntax-only`。
4. **重新验证**：第二次失败变为 `sed: obj/*_gmp_h.ads: No such file or directory`（产物是 `obj/gmp_h.ads`），
   改为配方显式生成 `src/gmp-h.ads` 后通过。

## 为什么这是一类新问题（而非单库补丁）

判据三条：

1. **换库仍会遇到**：任何"用 C 头自动生成 Ada 绑定规格"的 Ada 库（GMP 之外的 MPFR、MPC、ncurses 等绑定，
   以及同一作者的 GNU Ada 绑定系列）在 OHOS 上都会命中同一个驱动行为，与具体库名无关。
2. **可写成判定树**：
   ```
   需要 --dump-ada-spec？
     ├─ 工具链有 g++？ ── 无（ohpcd gcc-ada 只 enable c,ada）→ 必须用 gcc 驱动
     ├─ 调用是否带 -c/-S/-E/-fsyntax-only？ ── 否 → 驱动按"链接"处理 → 报 undefined reference to main
     └─ 产物名 = <header>_h.ads / package <header>_h
          └─ 上游 glob/sed 是否按 *_<header>_h 约定？ ── 否 → 配方须显式生成目标 .ads
   ```
3. **仓内无同类**：`draft-review` 对本条目判 `verdict=create`（无相近条目）；配套的
   `DRAFT-libgmpada-1.6-libgnat-static-non-pic` 判 `review-similar → E005`，已在各自 md 写明
   "同签名、异处置"的差异（E005 的正解 -fPIC 对预编译 libgnat.a 不可用，须改静态交付），
   两条各自独立、互不重复主张。

## 与已有知识的差异（查重）

| 已有条目 | 覆盖范围 | 本条目差异 |
|---|---|---|
| `DRAFT-adacgi-ada-source-library-conan-pattern` | Ada **源码库**的 Conan 配方模式（header-library、tool_requires、conanbuild 消费） | 本条目是**从 C 头生成 Ada 规格**的编译期代码生成问题，与分发/配方模式正交 |
| `DRAFT-libgmpada-1.6-libgnat-static-non-pic`（同 PR） | Ada 绑定共享库不可行（libgnat 非 PIC） | 本条目是编译期从 C 头生成 Ada 规格，与链接形态正交 |
| `DRAFT-adacgi-ada-source-library-conan-pattern` | Ada 源码库（header-library）Conan 配方模式 | 本条目是规格**代码生成**，与分发/配方模式正交 |

## 验证证据

- 运行环境：鸿蒙电脑（HarmonyOS PC，hdc `3QC0124C20001776`），OHOS/aarch64 原生
- 命令：`conan create archives/l/libgmpada/1.6 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
- 结果：`[ok] generated src/gmp-h.ads from .../obj/gmp_h.ads`；随后 Ada 单元全部编译通过；
  test_package 消费者输出 `LIBA_GMPADA_CONSUMER_OK`（退出码 0）
- 设备侧日志：`/storage/Users/currentUser/gmpada.log`
- 失败证据：``undefined reference to `main'``（首次）、`sed: obj/*_gmp_h.ads: No such file or directory`（第二次）

## 证据来源

- `archives/l/libgmpada/1.6/conanfile.py`（`_generate_gmp_h_spec`）
- `archives/l/libgmpada/1.6/notes.md`
