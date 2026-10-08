# kodi-addon-inputstream 21.1.2 适配笔记

## 结论

在 HarmonyOS PC（aarch64-linux-ohos，clang 15.0.4，conan 2.29.1 OHOS 版）完成
Kodi **inputstream.adaptive** 21.1.2（MPEG-DASH / HLS / SmoothStreaming 客户端
插件，含 Widevine 单样本解密器 ssd_wv）的本地适配与全量验证：

- 上游源码 **零修改**（patches_applied: []，无平台宏依赖）；
- 产物 `inputstream.adaptive.so` + `ssd_wv.so`（Kodi dlopen 模块，相对 SONAME，
  DT_NEEDED 仅系统库 libc++_shared.so / libc.so）；
- **上游 51/51 单元测试真机通过**（TestDASHTree 32 + TestHLSTree 12 +
  TestSmoothTree 2 + TestUtils 5）；
- test_package 消费者 **18/18 检查通过**（dlopen 方式：6 版本断言 +
  9 C-ABI 工厂流程 + 3 ssd_wv 冒烟）。

## 版本映射与源码身份

| 项 | 值 |
|---|---|
| 上游 | https://github.com/xbmc/inputstream.adaptive |
| tag | 21.1.2-Omega（release commit 6ca1c7d5…） |
| addon sha256 | `50eb6617…a1af6`（conandata 校验通过） |
| Kodi SDK | xbmc 21.3-Omega，kodi-dev-kit include 子树，sha256 `a60afcb5…1aa`（与 kodi-tools / kodi-addon-screensaver / kodi-inputstream-rtmp 记录一致） |
| Bento4 | xbmc/Bento4 tag **1.6.0-639-8-Omega**，sha256 `d7fc48e5…e23d` —— 与上游自带的 `depends/common/bento4/bento4.sha256` **逐字一致**（双重验证） |
| SDK 版本宏 | `ADDON_INSTANCE_VERSION_INPUTSTREAM="3.3.0"`（versions.h:111）、`ADDON_INSTANCE_INPUTSTREAM=105`、`INPUTSTREAM_VERSION_LEVEL=4` |

## 依赖闭包（W0 已核验，制品仓 ohpcd 已发布）

- `pugixml/1.15-r0`（rev 2bb9d899…）：上游 pin 1.13，registry 无 1.13，取同系列
  1.15-r0；只用稳定 DOM 子集，API 兼容（偏差记录于 manifest.yaml）。
- `gtest/1.17.0`（rev ab1bc3bf…）：`test_requires`（host-context 测试二进制，
  不进 package_id）。
- **Bento4 不是 conan 依赖**——见下节。

## Bento4：内嵌 xbmc fork（关键决策）

上游代码对 Bento4 是 **API 硬依赖 xbmc fork**，vanilla Bento4
（registry `bento4/1.6.0-641` = axiomatic-systems 官方 v1.6.0-641，cache 配方
确认）缺失：

| fork API | 使用处 | vanilla 1.6.0-641 |
|---|---|---|
| `AP4_File(stream, factory, moov_only, movie)` 4 参构造 | CSession::PrepareStream 为无 init 段 MP4 合成 `AP4_Movie` | 无（3 参版默认工厂） |
| `AP4_AvcFrameParser::ReadGolomb`（protected）派生类调用 | AVCCodecHandler.cpp:160 | private 无此符号 |
| `AP4_UnknownUuidAtom::GetData` | CodecHandler.cpp:48 | 无 |
| `SetParentIsOwner` | wvdecrypter.cpp:430 | 无 |
| 被改写的 AP4 虚函数签名（FragmentedSampleReader.h:58 `override`） | SampleReader 层 | override 报错（链接期符号不可插件侧补救） |

评估过补丁路线：虚签名差异是 ABI 级不兼容，插件侧无法弥补——**放弃**。

**采纳方案 = 复刻上游官方 internal 流程**：上游 `ENABLE_INTERNAL_BENTO4` 默认
ON（`FindBento4.cmake` ExternalProject：下载 `depends/common/bento4/bento4.txt`
pin 的 fork tarball、`-DBUILD_APPS=OFF`、`-fPIC`、产物 `install/lib/libap4.a`
+ `install/include/bento4/*.h`；flags/sha256 随插件源码自带）。配方在
`source()` 提取 fork（conandata 第三 source 键 `bento4`），并在
`recipe-cmake/CMakeLists.txt` 里 `add_subdirectory("${BENTO4_SRC}" bento4
EXCLUDE_FROM_ALL)` 构建其自带 CMakeLists 的 `ap4` 静态库（全局
`CMAKE_POSITION_INDEPENDENT_CODE ON` 等价上游 `-fPIC`），链接进主模块、
ssd_wv 与测试；`source()` 同时把 fork 的 Core/Codecs/Crypto/MetaData 四个头
目录平铺 stage 到 `<staging>/bento4/`，复刻其 install 语义，让上游
`#include <bento4/Ap4.h>` 原样解析。

### CMP0077 坑（记录）

fork CMakeLists 声明 `cmake_minimum_required(3.10)` → CMP0077 OLD → 子目录
`option(BUILD_APPS "..." ON)` **删除父作用域同名普通变量**并按默认值重建缓存
（实测 CMakeCache `BUILD_APPS:BOOL=ON`、mp4tag 等 apps 被编译）。必须：

```cmake
set(BUILD_APPS OFF CACHE BOOL "" FORCE)   # 而非普通 set()
```

## 构建方案

- 自备 `recipe-cmake/CMakeLists.txt`（`build_script_folder` 消费），复刻
  kodi-addon-dev `build_addon()` 语义（与 rtmp/screensaver 先例同构）：
  - 63 个 ADP cpp → `inputstream.adaptive.so`（`PREFIX ""`，显式
    `-Wl,-soname,inputstream.adaptive.so`），定义
    `__STDC_FORMAT_MACROS UNICODE _UNICODE`，链 ap4 + pugixml::pugixml +
    内嵌静态库 mpegts / webm_parser；
  - wvdecrypter posix 分支 → `ssd_wv.so`（`INPUTSTREAM_SSD_BUILD` +
    `WIDEVINECDMFILENAME="libwidevinecdm.so"`，C ABI 导出
    `CreateDecryptorInstance` / `DeleteDecryptorInstance`，aarch64 atomics
    走上游 issue #1128 模式），链 ap4 + cdm adapter 源；
  - `with_tests=True` 时构建上游 `src/test` 为 `inputstream.adaptive_test`
    （gtest::gtest + ap4，SDK 头显式补入——上游依赖顶层全局
    include_directories 继承）。
- SDK 头：`conandata sources.sdk` 下载 xbmc 21.3-Omega 全量 tarball，
  `source()` 用 `--wildcards` 选择性解出 kodi-dev-kit include 子树（注意：
  tar 增量解压，须先清目录再完整解出 153 个文件）。

## test_package 设计（dlopen 方式，与 CI 同构）

消费者测试 `test_kodi_addon_inputstream.cpp` 三段共 18 项检查：

1. **版本断言（6）**：dlsym `ADDON_GetTypeVersion(105)`=="3.3.0"、
   `GetKodiVersion`、`GetAddonVersion` 等；
2. **C-ABI 工厂流程（9）**：`CreateAddonInstance`/`GetFuncTable` 固定结构体
   尺寸 static_assert（KodiToAddonFuncTable_InputStream=31*8、
   INPUTSTREAM_PROPERTY=520、AddonGlobalInterface=5*8…）、
   `GetCapabilities` 返回固定掩码 **0x5F**、无会话 `Close` 无副作用；
3. **ssd_wv 冒烟（3）**：dlopen `ssd_wv.so` + 符号解析。

`Open()` 不做端到端（需 Kodi VFS 与网络栈 stub），由上游 51 个离线单元测试
补偿覆盖。

## 上游测试门禁（R51 三步）

| 步骤 | 结果 |
|---|---|
| 1 构建（`-o with_tests=True`，INPUTSTREAM_TESTS=ON） | inputstream.adaptive_test 链接成功（gtest/1.17.0 + ap4） |
| 2 真机运行（参数=src/test/manifests） | `[==========] 51 tests from 5 test suites ran. (539 ms total)` |
| 3 计数 | **PASSED 51 / FAILED 0**（DASH 32 + HLS 12 + Smooth 2 + Utils 5） |

`conan create -o with_tests=True` 全流程内自动执行同样步骤（本次验证输出同值）。

## 本机验证记录（W3）

```bash
conan create $PKG -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing            # ✅ exit=0
conan create $PKG -o with_tests=True -pr:h=... -pr:b=... --build=missing           # ✅ exit=0, 51/51
```

失败迭代记录（供后续包参考）：
1. conan `get()` 参数名是 `destination`（不是 `dest`）；
2. HMDFS 上 GNU make 4.4.1 顶层 `-jN` 会尝试 `mkfifo` jobserver（TMPDIR 下
   `GMfifo*`）→ `Operation not permitted`，**仅警告不致命**（手动 `make -j2`
   复现证实 exit=0）；
3. 并行大 `-j` 在机器内存紧张（<1GB available）时 clang 被杀 → `Error 1`
   **无 stderr**（OOM 实锤：32GB total、used 30.9GB、free 957MB 时 20 路并行
   全灭；内存回升 3GB 后 `-c tools.build:jobs=1` 串行一次通过）。CI 机器核少
   无此风险。

## 遗留风险

- Widevine 实际解密需设备级 `libwidevinecdm.so`（OHOS 无 L1/L3 CDM 组件），
  ssd_wv 仅验证到 dlopen + 工厂符号层；与上游行为一致（无 CDM 时优雅降级）。
- `with_tests=True` 与默认选项产生两个二进制包；CI 默认路径不含测试构建，
  R51 记录由本机与本地 create 双重复核。
- pugixml 1.13 → 1.15 偏差：上游 API 面稳定，风险评估见 manifest.yaml；
  若上游升级到使用 1.14+ 新 API 需重估。
---

**编译结束**: 2026-10-02 15:39
**最终状态**: built
