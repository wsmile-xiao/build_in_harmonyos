# libabw-tools 0.1.3 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-19
- 编译器: clang 15 (aarch64, OHOS 6.0)
- 状态: built（本地 CI 模拟 G0-G5 全 PASS，制品发布由平台 release 流水线在合入后执行）

## 编译步骤

本包 = libabw 上游源码树（0.1.3）的整树构建产物：`src/lib` 的静态库 `libabw-0.1.a` + `src/conv` 的三个转换工具 `abw2text` / `abw2html` / `abw2raw`（Debian/Ubuntu 才拆成 -tools 包，本仓按 libmwaw-tools 先例整树交付）。

1. conan source 下载 libabw-0.1.3.tar.xz（dev-www.libreoffice.org 官方发布目录，与 libabw 0.1.4 同目录，sha256 实测）
2. 依赖从 ohpcd 制品仓解析：librevenge/0.0.5、libxml2/2.15.3.1、zlib/1.3.1；boost/1.90.0.3 为 tool_requires（仅自身 TU 需要 boost 头，不进公开头文件与链接接口）
3. librevenge 三个库经「只放 .a 的干净 -L 目录」引用（规避其 .la 记录 libdir='//lib' 导致 libtool 'was moved'）；libxml2 与 zlib 不产 .la，直接用各自包目录的 -L/-l
4. `./configure --build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-gnu --prefix=/ --enable-static --disable-shared --disable-dependency-tracking`，REVENGE_*/LIBXML_*/ZLIB_* 五组 PKG_CHECK_MODULES 变量逐个导出（设备无 pkg-config，该宏在 CFLAGS 非空时短路）
5. LDFLAGS 注入 `-Wl,-rpath,<libxml2 包>/lib`：工具是 PIE 且链共享 libxml2，CI L2 冒烟门禁无 LD_LIBRARY_PATH 跑 bin/*，须内嵌 RPATH（musl 支持，sfic 0.1.7 对 libtdb 同款先例）
6. make && make check（留痕）&& make install，打包 bin/(3 工具) + lib/libabw-0.1.a + include/libabw-0.1/

## 遇到的问题与解决方案

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| 消费者链接报 `undefined symbol: xmlReaderForIO` 等 libxml2 符号 | `package_type="application"` 在 conan 2.29.1 `transform_downstream` 里把下游 require 强制 `libs=False/headers=False`，共享依赖 libxml2 只经本包传播，被 traits 清零（zlib 因同时经 librevenge/library 路径传播才幸存） | package_type 改 `static-library`（主交付物就是静态库 libabw-0.1.a）：static-library 向下游传播 libs；libxml2 为唯一共享依赖，追加 `run=True` 使其进入消费者运行环境 |
| configure 报 unknown host type / config.sub 拒绝 | 无——0.1.3 dist 的 config.sub 经设备实测已接受 `aarch64-unknown-linux-gnu` 两三元组（rc=0 原样通过），无需补丁 | 常规 build/host 配对 |
| config.status 写临时文件 Permission denied | setgid 临时目录下 configure 硬编码 `umask 077`（0.1.3 恰 2 处，契约同已验证的 0.1.4） | 配方 build() 内联 umask 077→022 改写（无补丁） |
| 工具 L2 冒烟无法无 LD_LIBRARY_PATH 运行 | 工具 PIE 链共享 libxml2.so.16，ohpcd libxml2 只发带版本号共享库 | LDFLAGS 注入 -Wl,-rpath 内嵌运行时路径（sfic 先例） |

## 源码修改

无补丁（`patches_applied: []`）。0.1.3 与已合入验证的 libabw/0.1.4 的 configure.ac 仅版本号不同、src/lib/Makefile.am 逐字节相同、公开 API 未变，0.1.4 的 OHOS 构建机制（umask 恰 2 处、config.sub 两三元组 rc=0）整体平移到 0.1.3 并逐项对 tarball 复核。

未修改上游测试用例（上游无测试套件）。

## 依赖版本

- librevenge/0.0.5 (conan, ohpcd 已发布)
- libxml2/2.15.3.1 (conan, ohpcd 已发布；唯一共享依赖，require 附 run=True)
- zlib/1.3.1 (conan, ohpcd 已发布)
- boost/1.90.0.3 (tool_requires, 仅构建期头文件)
- 运行时（消费者/工具）: libc++_shared.so / libc.so + libxml2.so.16（RPATH 已内嵌）

## 验证结果

conan create（ohos-aarch64 profile，clang 15）全绿，test_package：

CLI 冒烟（test_libabw_cli.sh, 7 断言全过）:
abw2text --version → abw2text 0.1.3
abw2html --version → abw2html 0.1.3
abw2raw --version → abw2raw 0.1.3
+ 缺失文件/纯文本/非法输入拒绝等边界用例

C++ API 实质测试（test_libabw_tools.cpp: 链接静态 libabw-0.1.a，调 ABWParser::isFileFormatSupported 对内存流做格式分类）:
9 checks, 0 failures（空流/纯文本/非压缩 XML/gzip XML/foreign root 等边界）

本地 CI 模拟（CI_PACKAGES 定向 + JUNK_PR_DIFF，含 PR diff）:
G0 / KC(KC1-5) / JC(JC1-6, prdiff 11 文件, 涉及软件数 1) / L0 / L1 / L1e(R34 负向) / L2（三工具 --version，无需 LD_LIBRARY_PATH）/ L4（无补丁）/ L5 全部 pass，Pass rate 100.0%

## 注意事项

- 上游 make check 无自动化测试（无 automake TESTS/CTest 注册），功能验证依赖 test_package 消费者用例
- commands.json 已声明 3 个工具；binary 字段在发布制品仓后改 true
- package_type 必须保持 `static-library`：改回 application 会复现 libxml2 符号丢失（见上表）

## 最终状态

- 状态: COMPLETED
- conan create + test_package: PASS（C++ 9/9、CLI 7/7）
- 本地 CI 模拟 G0-G5: 全部 PASS（Pass rate 100.0%）
- 交付: archives/l/libabw-tools/0.1.3/ (conanfile.py + conandata.yml + test_package + notes.md)
