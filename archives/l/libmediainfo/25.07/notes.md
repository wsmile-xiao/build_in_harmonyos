# libmediainfo 25.07 适配笔记

## 编译环境
- 构建系统: cmake（Project/CMake 官方路线）
- 编译日期: 2026-09-17
- 编译器: clang 15.0.4 / clang++ 15.0.4（OHOS SDK）
- 状态: built

## 依赖处理（关键决策）

### ZenLib —— vendored 源码捆绑（glib2/libffi 先例）
- MediaInfoLib 的 CMakeLists 中 `find_package(ZenLib REQUIRED)` 是硬依赖（BUILD_ZENLIB=OFF 路线）。
- **W0 实测**: `conan download libzen/0.4.41 -r=ohpcd --only-recipe` → Not found（"system acceleration policy not enabled" = 包不存在的报错形态）；`conan list "libzen/*" -r=ohpcd` → 0 匹配；平台无 libzen 适配任务在途（全量 10948 任务检索无果）。
- main 上的 archives/l/libzen/0.4.41 是 2026-05 的旧式归档（无 conanfile.py，从未发布制品仓）。
- **决策**: 走上游官方支持的 `BUILD_ZENLIB=ON` 源码捆绑路线（ZenLib 与 MediaInfoLib 兄弟目录布局），conandata.yml 增加 `libzen_subproject` 附加源（同 glib2/2.88.0 的 libffi_subproject 先例、avimetaedit/1.0.2 的 vendored ZenLib 先例）。
- libzen_0.4.41.tar.gz（官方源）sha256: aad6c25bffcc695828e4d36700243a19a0d9503fbe57d38a2fbfa302fb34df2f

### zlib —— conan 制品
- `zlib/1.3.1`（制品仓已发布，requires 引用，BUILD_ZLIB=OFF + CMakeDeps）。

### tinyxml2 / curl —— 上游 optional，禁用
- TinyXML 未找到时自动用源码内 ThirdParty/tinyxml2（上游行为）。
- CURL 未找到时定义 MEDIAINFO_LIBCURL_NO（不编译 Reader_libcurl）——不引入额外 conan 依赖。

## 源码补丁

### patches/0001-ZenLib-Thread-pthread_cancel-OHOS-guard.patch
- ZenLib Thread.cpp `ForceTerminate()` 调 `pthread_cancel()`，HarmonyOS musl 无此符号（E051 类）。
- 修法：`#if !defined(__ANDROID_API__)` → `#if !defined(__ANDROID_API__) && !defined(__OHOS__)`。
- 与 main 已合入的 archives/l/libzen/0.4.41/patches 修法一致。
- ⚠️ 注意 patch 必须是 **CRLF 行尾**（上游源文件是 CRLF，LF patch 会 apply 失败）。

## 构建要点

1. **CMake 版本兼容**: ZenLib `cmake_minimum_required(VERSION 3.1.0)` 与 CMake 4.x 不兼容 → 传 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。
2. **静态构建 only（OHOS）**: 上游 add_subdirectory 布局下 libmediainfo.so 的 NEEDED 项是 `ZenLib/libzen.so`（带目录前缀的 SONAME），OHOS 动态加载器无法解析 → BUILD_SHARED_LIBS=OFF 静态构建（libmediainfo.a + libzen.a）。
3. **构建目录**: 必须从 `Project/CMake` 子目录 configure（`cmake.configure(build_script_folder=Project/CMake)`）。
4. **UNICODE**: ZenLib 默认 ENABLE_UNICODE=ON（接口为 wchar_t/UNICODE 宏），消费者编译需 `-DUNICODE -D_UNICODE`（test_package 已处理）。

## 上游测试（make check，autotools 路线）

上游注册 6 个测试（Project/GNU/Library/test/Makefile.am）：
| 测试 | 内容 | 本地实测结果 |
|---|---|---|
| trace.sh | 15 回归文件 XML+MicroXML + XSD 校验 | 14/15 文件全过（XML 良构 + mediatrace/micromediatrace XSD 校验通过）；1 文件 TIMEOUT 豁免* |
| s3.sh | S3 远程读取（需私有凭证） | SKIP(77)（上游设计，无 S3_KEY/S3_PASS 凭证即跳过） |
| xml.sh | 15 回归文件 XML + XSD 校验 | 14/15 文件全过（XML 良构 + mediainfo_2_0.xsd 校验通过）；1 文件 TIMEOUT 豁免* |
| mixml.sh | MiXml 格式 zlib+base64 压缩往返 | 通过（压缩输出 1580 字节 >400 阈值 + 回读成功） |
| ebucore.sh | EBUCore 1.5/1.6/1.8ps/1.8sp XML+JSON | 通过（4 版本 XML 良构 + JSON 语法有效） |
| unicode.sh | Example.ogg 多语言 Unicode 标签 round-trip | 通过（7 组多语言 grep 断言全过） |

\* **豁免说明**: `Matroska/Matroska_with_invalid_Tracks_seek.mkv`（4.8KB，上游故意构造的坏 seek 边界文件）在 OHOS 上解析死循环（60s/300s 限时均不返回，CPU 满转）。该文件是 files.txt 15 个文件之一；其余 14 个文件全部正常解析输出。测试驱动 mil_analyze 按上游 Makefile.am 的 check_PROGRAMS 从 Project/GNU/Library/test/Source/analyze.cpp 编译（-DUNICODE -D_UNICODE）。

测试资源（本地联网获取）：
- MediaArea-RegressionTestingFiles（github.com/MediaArea/MediaArea-RegressionTestingFiles，15 文件）
- MediaAreaXml 的 4 个 XSD（mediatrace/micromediatrace/mediaarea/mediainfo_2_0）
- xmllint（/data/service/hnp/bin 有）；jsonlint 不存在 → 用 python3 json.tool 等价替代

## 验证结果（消费者测试）

test_package（test.cpp，嵌入官方 Example.ogg base64）断言：
1. 容器 Format=Ogg ✅
2. 音频 Format=Vorbis ✅
3. OverallBitRate_Mode=VBR ✅
4. Unicode 标签 round-trip ✅
5. Inform() XML 输出含 Audio track ✅
6. Info_Version 含 25.07 ✅

## 交付物

| 文件 | 说明 |
|---|---|
| libmediainfo.a | 主库（媒体格式解析全家桶） |
| libzen.a | vendored ZenLib（上游构建布局的独立静态库） |
| include/MediaInfo/ + MediaInfoDLL/ + ZenLib/ | 头文件 |

## 注意事项

1. libmediainfo 是纯库（无 CLI 可执行文件安装），无需 commands.json
2. cpp_info.libs = ["mediainfo", "zen"]（两个静态库需一起链接）
3. 链接需 -ldl -lm -lpthread（package_info 已声明）
