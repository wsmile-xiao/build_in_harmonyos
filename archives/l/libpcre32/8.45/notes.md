# libpcre32 8.45 适配笔记

## 定位
- 上游 PCRE 8.45 的 32 位库（--enable-pcre32），产物 libpcre32（-lpcre32）
- 依赖：无外部依赖（仅 -lm）

## 编译环境
- 构建系统: autotools（configure.ac）
- 编译器: clang/clang++（OHOS aarch64）
- 状态: built（conan create 全流程通过）

## 构建要点
- configure 参数：`--enable-pcre32 --disable-pcre8 --disable-pcre16`
- 3 个 OHOS 补丁（沿用 libpcre16 已验证方案）：
  - 0001 config.guess：识别 HarmonyOS（aarch64-unknown-linux-ohos）
  - 0002 config.sub：接受 ohos 基本系统 + linux-ohos 组合
  - 0003 configure：临时目录 umask 077→022（HMDFS 0700 不可写）

## 测试
- 上游 make check：RunTest 套件（pcre32 目标）26 项 PASS
- test_package 消费者 4 断言：pcre32_compile("a.c+") + exec("abcccxyz")
  匹配长度断言 + 无匹配不误报 + pcre32_free 生命周期

## 遇到的问题与解决方案
| # | 问题 | 解决方案 |
|---|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 0001 patch：添加 aarch64-unknown-linux-ohos 识别 |
| 2 | config.sub 拒绝 linux-ohos 组合 | 0002 patch：添加 ohos* + linux-ohos* |
| 3 | configure 临时目录 Permission denied | 0003 patch：umask 077→022 |
| 4 | pcre32 API 传 char* 编译/运行异常 | 消费者用例用 PCRE_UCHAR32（unsigned int）码元数组显式转换 |

## 验证
- 本地 `conan create . --profile=ohos-aarch64`：test_pcre32: OK (compile+exec roundtrip)
