# libabw 0.1.4 适配笔记

## 编译环境

- 构建系统: autotools（dist 自带预生成 `configure`，GNU **Autoconf 2.72**；单一 configure）
- 平台任务: contrib-8106（libabw 0.1.4），claimer Ember5843
- 目标平台: HarmonyOS PC arm64（`os=OHOS arch=armv8 compiler=clang 15 libc++`），本机原生构建
- 依赖: `librevenge/0.0.5`、`libxml2/2.15.3.1`、`zlib/1.3.1`；`boost/1.90.0.3` 为 **tool_requires**
- 上游: LibreOffice/Document Foundation（发布点 dev-www.libreoffice.org）
- 源码 sha256: `fa2685a3440da6e03a66a778480d93cb95f6064e4541e58e37397680760fd6a0`
- 状态: built（G0/G1/G2/G3 全过，库级 9/9 + CLI 级 4/4）

## 源码面貌（摸底结论）

- 主体 **C++**：`src/lib/` 14 个 `.cpp`、13 个头；`src/conv/{text,html,raw}` 分别产出
  `abw2text`/`abw2html`/`abw2raw`（`--enable-tools` 默认 yes）
- 交付形态：静态库 `libabw-0.1.a` + 头 `include/libabw-0.1/libabw/{libabw.h,AbiDocument.h}` + 三个 CLI 工具 + `.pc`
- 依赖探测：`PKG_CHECK_MODULES` 查 librevenge、libxml-2.0、zlib（+ 工具所需的 generators/stream 两组）；
  boost 头检查 `boost/algorithm/string.hpp`、`boost/optional.hpp`、`boost/spirit/include/qi.hpp`
- **不依赖 libwpd**（与我最初按同族印象的推测相反）：`configure.ac`、`src/lib`、`src/conv` 均无 libwpd 引用
- 上游**无测试套件**：无 `TESTS`/`check_PROGRAMS`、无 `*test*` 源文件，也不分发 AbiWord 样例文档
- 格式识别：`AbiDocument::isFileFormatSupported()` 用 `inflateInit2(&strm, 16 + MAX_WBITS)`（gzip）
  解压后要求根元素为 `<abiword>` 或 `<awml>`；**未压缩的合法 XML 也会被接受**（zlib 层回退按原始字节读）

## 编译步骤（设备实机）

```sh
cd $HOME/build_in_harmonyos
python3 scripts/ohc-run.py conan-verify libabw 0.1.4 --project-dir "$PWD"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|---------|
| 1 | `ld.lld: error: unable to find library -lxml2` | 我把所有依赖的库都复制进「只放 .a 的干净链接目录」，但 libxml2 的包**只提供带版本号的共享库**（`libxml2.so` → `libxml2.so.16` → `libxml2.so.16.1.3`），通配只复制了那个符号链接本身，目标没复制 → 悬空 | 干净目录只用于**产 `.la` 的依赖**（librevenge 家族，规避其 `libdir='//lib'` 问题）；libxml2/zlib 不产 `.la`，直接用自己的 `-L/-l` |
| 2 | `package_info(): There are '(cpp_info/components).requires' to other internal components that are not defined: ['libxml2']` | `cpp_info.requires` 里**不带 `::` 的裸名**被解释为**本包内部组件** | 写成 `<conan包名>::<组件>`；依赖无组件时用 `<包名>::<包名>` 指代整包（`libxml2::libxml2`） |
| 3 | `package_info(): ... includes package 'LibXml2::', but such package is not a a direct requirement` | 我把 libxml2 的 **CMake 目标名**当成了包名写进去 | 同上：条目用的是 conan 包名（小写 `libxml2`），与 CMake 目标名无关 |
| 4 | 测试二进制运行期 `Error relocating ./test_libabw: xmlTextReaderConstName: symbol not found` | libabw 是**静态库但链接共享的 libxml2**；`ctest` 不继承 conan 的运行时环境（`conanrun`），加载期解析不到 libxml2 符号 | 判据改由 `self.run(<exe>, env="conanrun")` 承担（同时把逐条断言打进日志）；ctest 注册保留给交互使用 |
| 5 | 断言「未压缩的合法 `<abiword>` XML 必须被拒」失败（实际被接受） | 我按「先解压再解析」的直觉写成了负例，但 `ABWZlibStream` 在 inflate 失败时会回退为按原始字节读取 | 修正为正向断言（"未压缩 <abiword> XML 被接受，流层回退为原始数据"），这条假设由设备实测纠正 |

## 源码修改

无补丁，未改动上游任何源码。

## 依赖版本

- `librevenge/0.0.5`（公开依赖；静态库，其 stream 层需要 `-lz`，已随 `REVENGE*_LIBS` 传递）
- `libxml2/2.15.3.1`（XML 读取；包内为**共享**库，消费者运行期需要它，已在 `cpp_info` 传播）
- `zlib/1.3.1`
- `boost/1.90.0.3`（tool_requires，仅构建期头文件；版本与 librevenge 依赖的 boost 对齐）

## 验证结果（设备实机实测，2026-09-14）

```text
✅   G0: PASS
✅   G1: PASS
✅   G2: PASS
✅   G3: PASS
✅ 配方验证通过: libabw 0.1.4
```

库级消费者测试（在 `conanrun` 环境下直接执行）：

```text
ok 1 - isFileFormatSupported(nullptr) reports false
ok 2 - an empty stream is not supported
ok 3 - uncompressed text is not supported
ok 4 - uncompressed <abiword> XML is accepted (the stream falls back to raw data)
ok 5 - arbitrary binary data is not supported
ok 6 - a gzip XML document with a foreign root element is not supported
ok 7 - a gzip XML document with an <abiword> root is supported
ok 8 - a gzip XML document with an <awml> root is supported
ok 9 - parse() on an unsupported stream reports failure
1..9
# 9 checks, 0 failures
```

CLI 级消费者测试（对已安装的 `bin/abw2text`）：

```text
ok 1 - installed abw2text exists and is executable: .../p/bin/abw2text
ok 2 - a missing input file fails with a non-zero exit code
ok 3 - plain text is rejected cleanly (exit 1)
ok 4 - unsupported input is rejected without a crash
```

## 可复用要点

- 与 libwpd 共用的做法：干净 `-L` 目录规避 libtool `.la`、私有头依赖用 `tool_requires`、
  `PKG_CHECK_MODULES` 逐组喂变量、CC/CXX 从 profile conf 显式导出、构建 shell 用 hnp bash。
- 本包新增的四条（见 manifest 的 `knowledge_gained`）：干净目录只该放产 `.la` 的依赖；
  `cpp_info.requires` 的命名规则（裸名=内部组件、要写 `<包名>::<包名>`）；
  静态库链共享依赖时 ctest 不能当判据；以及「上游流层可能回退读原始字节」这类
  不能凭直觉写成负例的行为。
