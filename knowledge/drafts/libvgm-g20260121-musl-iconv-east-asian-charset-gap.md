# libvgm g20260121 — musl iconv 缺东亚遗留码表（CP932/Shift-JIS 等），运行时优雅降级（draft）

**Category**: portability | libc | ohos · **Severity**: 3 · **Tool**: clang/cmake/conan

## 症状

**构建期完全无报错**——CMake FindIconv 探测成功（真机日志
`Performing Test Iconv_IS_BUILT_IN - Success`，`Found Iconv: /lib64/libc.so`），
字符集转换代码正常编译链接。问题只在**运行时**暴露：调用
`iconv_open("UTF-8", "CP932")` 返回 `(iconv_t)-1` 且 errno=ENOENT——
musl 的 iconv 根本不实现该编码。

libvgm 的具体场景（g20260121，master `57585ea`）：

```text
player/vgmplayer.cpp:198  CPConv_Init(&_cpcUTF16, "UTF-16LE", "UTF-8")  → OK
player/gymplayer.cpp:59   CPConv_Init(&_cpc1252,  "CP1252",  "UTF-8")  → OK
player/s98player.cpp:130  CPConv_Init(&_cpcSJIS,  "CP932",   "UTF-8")  → -1/ENOENT
```

## 根因

musl 的 iconv 只实现了 Unicode 系（UTF-8/16/32、UCS-2/4）、ISO-8859-1..16、
CP1250-1258、KOI8-R 一类单字节编码；**日/中/韩遗留多字节码表（CP932/Shift-JIS、
GBK/CP936、Big5/CP950、EUC-JP/EUC-KR）刻意不提供**（体积与维护考虑）。
glibc 全带，所以任何在 glibc Linux 上跑过的代码都默认"iconv 什么都能转"。

探测陷阱：CMake `FindIconv`（以及绝大多数构建期探测）只验证 iconv_open
**函数存在且可链**，不验证**编码集覆盖**；musl 两者拆开——函数在 libc 里，
码表不在。

## 对策

1. **首选优雅降级**（libvgm 上游自带，可作范式）：转换句柄初始化失败时置空，
   使用点判空跳过，功能降级但进程不崩——libvgm 真机上 S98 标签保持原文
   不转换，VGM/GYM（主格式）标签转换不受影响，播放完全正常。
2. 需要正确转换中日韩编码时：自带码表（如 ICU、libiconv 完整版、iconv
   嵌入式实现）或预转换数据，不要依赖 musl。
3. 配方侧：无需补丁，把"哪些编码可用/不可用"记入 notes.md 与 PR 说明，
   避免下游误以为标签转换全量可用。

判别口诀：**iconv 探测过 ≠ 编码转得动**；涉及 CJK 遗留编码的库，
在 OHOS 上按"运行时可能不可用"设计。

## 验证

真机（HarmonyOS aarch64，musl）`conan create` + test_package 全绿
（36/36 断言）；configure 日志确认 Iconv_IS_BUILT_IN Success 经
/lib64/libc.so；CP932 不可用结论来自 musl 源码字符集表 + s98player.cpp
失败分支代码审查（`if (retVal) _cpcSJIS = NULL;`）。
