# DRAFT-libgmpada-1.6-libgnat-static-non-pic — 预编译 Ada 运行时非 PIC：Ada 绑定只能静态交付

> **Contributor**: qianxia | **Status**: VERIFIED DRAFT | **Updated**: 2026-09-20
> **Source event**: libgmpada 1.6 HarmonyOS PC 适配（AtomGit #8215），鸿蒙电脑原生 `conan create` 实录

## 知识类型与提升边界

本条目是路径 B 知识库扩展候选，不预占正式 E 编号，只进入 `knowledge/drafts/**`；
是否提升及最终分类由知识库维护者和评审决定。

## 适用范围

适用于同时满足以下条件的适配：

- 链接期出现 `relocation R_AARCH64_ADR_PREL_PG_HI21 ... can not be used when making a shared object; recompile with -fPIC`；
- 触发该错误的静态库**不是本项目的源码产物**，而是**工具链/第三方预编译产物**，在适配范围内无法重编
  （OHOS 上的典型例子：`gcc-ada/9.5.0` 的 `adalib/libgnat.a`、`libgnarl.a`）；
- 目标仍是 OHOS aarch64 原生。

## 使用说明（关键：先分类再处置）

1. **先问"这个 .a 谁能重编"**：
   - 能加 `-fPIC` 重编（本项目的库 / 上游一起构建）→ 走既有 **E005** 的正解（`CFLAGS="-fPIC"`）。
   - 不能重编（工具链/第三方预编译）→ 不要绕 linker，直接改交付形态（本条目）。
2. 固定 `shared=False`，在 `validate()` 对 `shared=True` 抛 `ConanInvalidConfiguration` 并写明原因。
3. 只构建静态目标；`package()` 手工安装，绕开上游同时装 .a/.so 的 `make install`。
4. 运行时目录用 glob `<toolchain>/lib/gcc/*/*/adalib` 定位（版本号是**编译器**的，不是被测库的）。

## 输入输出定义

| 项 | 定义 |
|---|---|
| 输入 | gcc-ada tool_requires 包目录；上游静态目标（`libX.a`）与 ALI 文件 |
| 关键参数 | `LDFLAGS` 追加 `-L<adalib>`；`LDLIBS` 形如 `-L<gmp> -lgmp -lgnarl`（libgnat 依赖 libgnarl，须排在其后） |
| 输出 | `lib/libX.a`、`lib/ada/adalib/X/*.ali`、`share/ada/adainclude/X/*.ads|.adb`、`share/gpr/X.gpr` |
| 禁止输出 | `lib/*.so`（OHOS 上无法产出）、构建目录、ALI 之外的中间产物 |

## 示例（libgmpada 1.6 实测片段）

```python
def validate(self):
    if self.options.shared:
        raise ConanInvalidConfiguration(
            "libgmpada is static-only on OHOS: gcc-ada's Ada runtime "
            "(adalib/libgnat.a, libgnarl.a) is non-PIC and cannot be linked "
            "into a shared object. Use shared=False.")
# build(): 只构建静态目标
#   make obj/libgmpada.a obj/gmpada.gpr LDLIBS="-L<gmp> -lgmp -lgnarl" LDFLAGS="... -L<adalib>"
# package(): 手工装 .a/.ali/.ads/.gpr，不走上游 make install
```

## 失败原文（四段式）

1. **首个错误**：`ld: cannot find -lgnat: No such file or directory`（最初用被测库版本拼 adalib 路径）
2. **根因 1**：adalib 目录是 `lib/gcc/aarch64-linux-ohos/9.5.0/adalib`，版本号属**编译器**。
3. **修复 1**：glob 定位 adalib 并 `-L`。
4. **重新验证 → 第二个错误**：`libgnat.a(a-stream.o): relocation R_AARCH64_ADR_PREL_PG_HI21 against symbol ... can not be used when making a shared object; recompile with -fPIC`
5. **根因 2**：预编译 Ada 运行时非 PIC；与 E005 同签名，但 `.a` 不可重编。
6. **修复 2**：`shared=False` + 只构建静态目标 + 手工装包。

## 与已有知识的差异（查重）

| 已有条目 | 覆盖范围 | 本条目差异 |
|---|---|---|
| **E005**（静态库非 PIC 链共享库失败） | 错误签名相同；正解是 **`CFLAGS="-fPIC"` 重编**，假设 .a 是 **本项目可重编** 的源码产物 | 本条目指出**同签名下的分叉处置**：当非 PIC 的 .a 是**预编译工具链产物**（libgnat.a）时，-fPIC 不可用；可复用的是"先分类（能否重编）再处置"的判定与"改静态交付"的完整配方动作。`draft-review` 判 `review-similar → E005`，差异即在此 |
| `DRAFT-adacgi-ada-source-library-conan-pattern` | Ada **纯源码库**（header-library）模式 | 本条目针对**产出预编译静态库 + ALI** 的 Ada 绑定，并给出共享库不可行的判定与证据 |
| `DRAFT-libgmpada-1.6-gcc-ada-dump-ada-spec-generation`（同 PR） | 用 gcc-ada 从 C 头生成 Ada 绑定规格（编译期） | 本条目是**链接期**约束（非 PIC → 只能静态），两者正交 |

## 验证证据

- 运行环境：鸿蒙电脑（HarmonyOS PC，hdc `3QC0124C20001776`），OHOS/aarch64 原生
- 命令：`conan create archives/l/libgmpada/1.6 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
- 结果：静态库构建 + 上游 `demo-static/demo` 运行 + test_package 消费者 `LIBA_GMPADA_CONSUMER_OK`，退出码 0
- 共享目标失败原文：`make: *** [Makefile:119: obj/libgmpada.so.2] Error 1`（`relocation R_AARCH64_ADR_PREL_PG_HI21 ... recompile with -fPIC`）
- 设备侧日志：`/storage/Users/currentUser/gmpada.log`

## 证据来源

- `archives/l/libgmpada/1.6/conanfile.py`（`validate` / `_ada_libdir` / `package`）
- `archives/l/libgmpada/1.6/notes.md`
