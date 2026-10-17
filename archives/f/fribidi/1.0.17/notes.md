# fribidi 1.0.17 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-10-08
- 编译器: clang/clang++ (aarch64-unknown-linux-ohos)
- 状态: built (本地探索构建 + conan create ohos-aarch64 全绿)

## 源码信息
- URL: https://github.com/fribidi/fribidi/releases/download/v1.0.17/fribidi-1.0.17.tar.xz
- SHA256: 6949dcde27d41cebad1fd741fcafc36d55a1020d2d872d4a6eb3914caabbada2
- 格式: tar.xz
- 上游 tag: v1.0.17

## 1.0.16 → 1.0.17 上游变化（NEWS）
- Unicode 字符数据库升级到 v18.0.0
- 性能优化：FSI 基方向解析、N0 括号配对、嵌入层级解析、reorder_line 不再有二次方最坏情况
- 修复 fribidi_set_reorder_nsm() / fribidi_set_mirroring() 在 log2vis 之前调用不生效的问题
- 修复 N0 括号配对按规范等价性匹配（UAX #9 BD16）
- 修复字符集等价表解析的栈缓冲区溢出与尾部 '_' 越界读
- fribidi-main: 修复内嵌 NUL 字节行/输出截断
- 生成并安装 fribidi(1) man page（本次适配的关键新依赖）
- 构建修复若干（MSVC、MinGW、GCC 14 警告）

## 编译步骤
1. 下载源码 tarball（sha256 实测见上）
2. 打补丁:
   - 0001-config.guess.patch: HarmonyOS 系统识别（E007，aarch64-unknown-linux-ohos）——沿用 1.0.16 的 0002 补丁，dry-run 验证对 1.0.17 适用
   - 0002-no-help2man-keep-prebuilt-man.patch: 移除 bin/Makefile.in 的 %.1: % 规则（见下"新增问题"）
3. conanfile.py build() 内运行时修复（OHOS 分支）:
   - E165: configure shebang /bin/sh → /system/bin/sh
   - E110: configure umask 077 → 002（HMDFS 临时目录权限）
4. `./configure --prefix=$DEFAULT_PREFIX`
5. `make -j1`（HMDFS 不支持 mkfifo，禁并行）
6. `make check` — automake TESTS 4 目标全 PASS
7. `make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 OHOS | E007: GNU config.guess 无 HarmonyOS 检测分支 | 沿用 1.0.16 config.guess 补丁（0001，dry-run 实测对 1.0.17 适用，识别 aarch64-unknown-linux-ohos） |
| 2 | 1.0.16 的 0003-config.sub.patch 无法应用 | 1.0.17 捆绑新版 config.sub (2025-07-10)，上游已原生支持 ohos* OS 与 linux-ohos* kernel-OS；旧补丁锚点消失 | 不再需要 config.sub 补丁（实测 `sh config.sub aarch64-unknown-linux-ohos` 原生通过） |
| 3 | config.status "can't create ./confXXXXXX/subs1.awk: Permission denied" | E110: HMDFS 限制 umask 077 创建的临时目录（700 权限） | conanfile.py build() 中 replace_in_file 修改 umask 077→002（探索构建实测复现并修复） |
| 4 | configure shebang `#!/bin/sh` | E165（1.0.16 已知，保持修复） | build() 中 replace_in_file 修改 shebang |
| 5 | **新增**: make 死于 `bin/fribidi.1 Error 127`，日志 `../missing[85]: help2man: inaccessible or not found` | 1.0.17 新增 dist_man_MANS + `%.1: %` help2man 重生成规则；OHOS worker 无 help2man；tarball 已自带预生成 bin/fribidi.1 但二进制重建触发 man 重生成 | 0002 补丁删除 bin/Makefile.in 的 `%.1: %` 规则块，直接采用 tarball 预生成 man page（探索构建实测修复后全绿） |
| 6 | make -j2 报 "mkfifo: Operation not permitted" | HMDFS 不支持 FIFO 创建 | 使用 make -j1（沿用 1.0.16 结论） |

## 依赖版本
无外部依赖（纯 C，无 requires）

## 产物
- lib/libfribidi.so.0.4.0 (共享库)
- bin/fribidi (命令行工具)
- share/man/man1/fribidi.1 (man page，1.0.17 新增)
- include/fribidi/*.h (头文件)
- lib/pkgconfig/fribidi.pc

## 验证结果（2026-10-08 本机 aarch64 HarmonyOS 实测）
- 探索构建（tarball+补丁+umask 修复）: configure/make/make check/make install 全链 rc=0
- make check: automake TESTS 注册 4 目标全 PASS:
  - PASS: BidiTest.txt（UAX #9 一致性，BidiTest-18.0.0.txt，490852 条断言级数据行）
  - PASS: BidiCharacterTest.txt（字符级一致性，BidiCharacterTest-18.0.0.txt，91710 条断言级数据行）
  - PASS: run.tests（6 个字符集 input/reference 文件对全过）
  - PASS: test-reorder-nsm
  - 汇总行（test/ 与 unicode-conformance/ 各一次）: # TOTAL: 2, # PASS: 2 × 2
- CLI 冒烟: `echo "سلام" | ./bin/fribidi` 正确输出 RTL 重排；`./bin/fribidi --version` 输出 "fribidi (GNU FriBidi) 1.0.17"
- conan create -pr=ohos-aarch64: 全绿（见 reports/conan-create.log）
- test_package: test_fribidi 4 项断言（版本串含 1.0.17 / UTF-8 转换 / log2vis / 镜像字符 U+0028→U+0029）全 PASS

## 测试口径说明（rule4，禁虚报）
- 上游 N = automake TESTS 注册测试目标数 = **4**（BidiTest.txt、BidiCharacterTest.txt、run.tests、test-reorder-nsm）
- BidiTest.txt / BidiCharacterTest.txt 为 Unicode 官方一致性数据文件（490852 / 91710 条数据行），作为"说明"注明数据规模，不计入 N（automake 按文件计 1 目标）
- 适配后 = 上游 4（make check 在 build() 内同平台执行，不修改不跳过）+ 新增 test_package 消费者测试 1（4 项断言）
- 合计 = 5；通过率 5/5 = 100%

## 注意事项
- fribidi 同时提供 autotools 和 meson 两种构建系统, 此处使用 autotools（沿用 1.0.16 口径）
- 1.0.17 起新版 config.sub 原生支持 ohos，后续版本跟进无需 config.sub 补丁
- man page 相关补丁（0002）为构建环境适配（非 OHOS 专属，任何无 help2man 的环境均适用），platform_only=False
- 构建产物包含可执行文件 fribidi, 顶层 commands.json 已登记（R38）

---

**编译结束**: 2026-10-08
**最终状态**: built
