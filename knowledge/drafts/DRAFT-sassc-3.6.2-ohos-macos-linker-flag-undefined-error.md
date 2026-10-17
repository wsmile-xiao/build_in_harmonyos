# sassc/3.6.2 — macOS 专用链接参数 `-Wl,-undefined,error` 在 OHOS ELF ld.lld 的适配（构建层移除）

> Draft: DRAFT-SASSC-362-MACOS-LINKER-FLAG-UNDEFINED-ERROR
> Stem: `sassc-3.6.2-ohos-macos-linker-flag-undefined-error` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-SASSC-362-MACOS-LINKER-FLAG-UNDEFINED-ERROR
- **严重度**: 2
- **类别**: platform-linker-flag
- **触发工具**: make|Makefile|sassc|ld.lld|clang|LDFLAGS|-Wl,-undefined
- **阶段**: build|link

## 错误特征

```
ld.lld: error: unknown argument: '-undefined'
undefined,error
LDFLAGS.*-Wl,-undefined
```

## 可复现问题

sassc/3.6.2（libsass 官方命令行编译器）在 OHOS 适配时，链接阶段稳定失败：
`ld.lld: error: unknown argument: '-undefined'`。定位到其 Makefile 第 17 行无条件
`LDFLAGS  += -Wl,-undefined,error`——这是 macOS/Darwin 专用链接参数。

## 根因分析

- macOS 的 Darwin ld 支持 `-Wl,-undefined,error`：把链接中未定义的符号视为错误；
- OHOS 工具链使用 **ELF 格式的 ld.lld**，`-undefined` 是 Darwin 模式选项，ELF 模式
  不识别 → 直接 `unknown argument` 链接失败（ld.lld 对未知参数是硬报错，不静默忽略）；
- 上游 autotools/Makefile 项目常把 Darwin 专用链接参数**无条件写进 LDFLAGS**，在
  Linux/OHOS 上链接阶段必炸——这是跨库可复用的诊断模式（sassc 只是其中一个实例）。

## 推荐方案 / 修复

在**构建层**移除或条件化 LDFLAGS 中的 `-Wl,-undefined,error`：

- **首选**：配方 `apply_conandata_patches` 应用补丁删除该行（sassc 用
  `patches/0001-makefile-ohos.patch`），minimal-recipe-diff，不改上游业务源码；
- **兜底**：build() 用 make 命令行变量整体覆盖 LDFLAGS（去掉该参数）或经
  EXTRA_LDFLAGS 透传。

ELF lld 不需要该参数（未定义符号默认报错，或由 `--no-allow-shlib-undefined` /
`--unresolved-symbols` 控制），移除**不影响 Linux/OHOS 链接语义**。

## 验证

- 平台/版本：OpenHarmony PC / ohos-aarch64（clang 15 + ld.lld，libc++）
- 方式：`conan create archives/s/sassc/3.6.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
- 结果：补丁后链接通过（exit 0）；test_package R34 真实执行 sassc 编译 SCSS，
  输出 `OK: sassc compiled SCSS (variable interpolation) to CSS`

## 推广价值

适用于**任何上游 Makefile/configure 的 LDFLAGS 硬编码 macOS/Darwin 专用链接参数**
（`-Wl,-undefined,error`、`-Wl,-undefined,dynamic_lookup` 等）的 autotools/make
项目在 OHOS（ELF lld）上的适配——错误特征一致、修复路径一致，可跨库复用。
