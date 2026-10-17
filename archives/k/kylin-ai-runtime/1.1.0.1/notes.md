# kylin-ai-runtime 1.1.0.1 — 适配笔记

## 上游
- 仓库: https://gitee.com/openkylin/kylin-ai-runtime
- 源码: openKylin 官方打包 tag `build/1.1.0.1-ok0.9`
  - commit: `172314c21d7bf3be95dadaf162042cddffd7c4e4`
  - gitee `repository/archive` 端点按 User-Agent 过滤，对 conan 下载器返回 HTML
    反爬页 → `source()` 改用 Git clone 固定 tag
- 产物: AI 运行时守护进程 `bin/kylin-ai-runtime`（application 包，无 cpp_info）
- Build-Depends: cmake、glib-2.0(giounix/gdbus-codegen)、jsoncpp、spdlog/fmt、
  openssl、curl、icu、pulseaudio、libsodium、grpc/protobuf、nlohmann-json

## 结构（CMake，单守护进程）
- 主目标 `kylin-ai-runtime`：src/ 下 services/engine/config/encryption/APIs/utils 等
- 链接/依赖: KylinAiProto(gdbus glue)、KYAI_KNOWLEDGE_BASE_CLIENT(gdbus 客户端 .so)、
  VECTOR_DB(grpc 客户端 .so)、jsoncpp、openssl、curl、icu、glib/gio-unix、
  pulseaudio、spdlog/fmt、libsodium、nlohmann-json、KylinAiEngine 头
- 上游 `test/` 目录: 13 个 .cpp 源文件，其中 CTest 仅注册 **5 个** 可执行用例
  （testencryption / testaes256 / testenginemanager / testmodelstatustracker /
  testsystemoperation），其余 8 个（logger/rsa2048/pbkdf2/model* /processor 等）
  未接入 CMakeLists，非活跃用例

## 私有依赖 vendor（R49 staging）
制品仓无以下 openKylin 私有库配方，L0i 要求 `requires()` 只声明已发布包，故在本配方
`source()` 内 vendor 构建/取头，装入 staging 前缀供主构建消费：

| vendor | 来源 | 用途 |
|---|---|---|
| kylin-ai-proto | libkylin-ai-system-private `debian/1.2.0.1-1` 内嵌 ai-proto | KylinAiProtoConfig + Functions 宏 + gdbus XML×7 + grpc vector-db protos |
| kysdk-vector-engine-client | upstream/1.2.0.0 | grpc 客户端 SHARED 库（VECTOR_DB pc） |
| document-qa-client | kylin-ai-document-qa-service **build/1.2.0.0-ok0.7** | gdbus 客户端 SHARED 库（KYAI_KNOWLEDGE_BASE_CLIENT pc） |
| kysdk-ai-common 头 | kysdk-ai-common **build/1.1.0.1-ok0.3** | 仅头使用（含 AISDK_SSL_CERTIFICATE_ERROR） |

- docqa 必须取 `build/1.2.0.0-ok0.7`（非 upstream）：runtime ok0.9 需要
  `KnowledgebaseErrorCode::KNOWLEDGEBASE_VECTOR_DATABASE_DATA_UNAVAILABLE`，仅 ok0.6+ 头有
- kysdk-ai-common：制品仓已发布 1.1.0.1 头较旧（缺 `AISDK_SSL_CERTIFICATE_ERROR`），
  故 vendor ok0.3 头放 KYAI_EXTRA include 首位，同时保留发布依赖满足 find_package

## 适配要点（6 个补丁）
1. 0001 主 CMakeLists：`jsoncpp`→`JsonCpp::JsonCpp`、`crypto`→`OpenSSL::Crypto`、
   `curl`→`CURL::libcurl`、`pulse/pulse-simple`→`PkgConfig::LIBPULSE`（补 libpulse-simple
   模块）、`ICU`→`find_package(icu CONFIG)+icu::icu`；pkg_check_modules 块后补
   `link_directories`；`install` 的 /usr/bin|/etc|/usr 绝对路径越权改前缀相对
2. 0002 jsoncpp 头前缀 + fmt 12 / icu 兼容：44 处 `<jsoncpp/json/...>`→`<json/...>`；
   `std::atomic<bool>` 日志参数加 `.load()`（3 处)、KnowledgebaseErrorCode 加
   `static_cast<int>`（9 处）、logger.h 补 `#include <fmt/ranges.h>`（fmt::join）、
   util.cpp 移除 `#include <unicode/ustdio.h>`；test/CMakeLists 同步
3. 0003 ai-proto 宏路径变量化：gdbus-codegen `/usr/bin`→`${KYLAI_GDBUS_CODEGEN}`、
   gdbus XML `/usr/share`→`${KYLAI_GDBUS_PROTOCOL_DIR}`、grpc proto→`${KYLAI_GRPC_PROTOCOL_DIR}`、
   grpc_cpp_plugin find_program→`${KYLAI_GRPC_CPP_PLUGIN}`（可外部钉死）
4. 0004 ai-proto `install(DIRECTORY protocols/usr/ DESTINATION /usr)` 绝对路径越权→前缀
5. 0005 vecclient：`pkg_check_modules(grpc)+find_package(Protobuf)`→
   `find_package(gRPC CONFIG)/find_package(Protobuf CONFIG)`（grpc 配方 cmake_find_mode=none，
   注入 gRPC_DIR/Protobuf_DIR/absl_DIR 使用上游安装 config），链接目标
   `grpc++/protobuf`→`gRPC::grpc++/protobuf::protobuf`；install 绝对路径改前缀
6. 0006 docqa-client `install(.pc DESTINATION /usr/share/pkgconfig)`→前缀相对

## 关键坑 1：glib 静态内嵌 → 同进程两份 gobject（本库特有）
- 现象: daemon 启动即断言
  `GLib-GObject:ERROR:../gobject/gtype.c:2555:g_type_register_static: assertion failed:
  (static_quark_type_flags)` + `Bail out!`
- 根因: glib/2.88.0 制品仓配方 **static-only**（全机无 shared glib，只产 `.a`）。
  `libkyai-knowledgebase-client.so` 静态内嵌一份 glib（`nm -D` 可见 6 个
  `T g_type_register_static`），主二进制又静态链一份 glib → 同进程两套 gobject
  quark/type 表，类型注册时 quark 表不一致触发断言
- 修复: conanfile.py 内用 `clang++ -shared -fPIC -Wl,--soname` + `--whole-archive`
  从 conan 静态归档（glib/gobject/gmodule/gthread/gio + pcre2/libffi/libintl 静态归档）
  合成 5 个共享库，写 staging/lib 并签名；`_augment_pkg_configs()` 给 glib-2.0/gobject/
  gio/gmodule/gthread/gio-unix pc 的 `Libs:` 前置 `-L<staging>/lib`，使全部
  `-lglib-2.0` 命中同一份共享库；`package()` 一并发布并签名。实测静态归档为 PIC
  （合成 .so `readelf -d` 无 TEXTREL），修复后 `libkyai-knowledgebase-client.so` 的
  `T g_type_register_static` 计数 = 0
- 诊断特征: gobject/gtype.c 断言 + 主二进制或某 .so `nm -D` 出现 `g_type_register_static`；
  统一动态链接同一份 glib 即解

## 关键坑 2：OHOS 未签名 .so → rc=127
- 现象: daemon 启动 `rc=127`（musl loader 找不到可加载对象），`ldd` 正常
- 根因: OHOS 强制加载带 `.codesign` 段的已签名 ELF。上游 pulseaudio/17.0.1 包全部
  `.so` 未签名（上游 recipe gap）→ 加载失败
- 修复: test_package 的 `_sign_unsigned_libs()` 遍历依赖 lib 目录，对缺 `.codesign`
  的 `.so*` 复制到 `~/.cache/kylin-ai-runtime-test/signed_libs` 并用
  `binary-sign-tool sign -selfSign 1` 签名后 prepend 到 LD_LIBRARY_PATH（不改上游包）
- 诊断特征: rc=127 + `readelf -S` 缺 `.codesign`

## 关键坑 3：fmt 12 / icu 兼容
- fmt 12 移除 ostream/枚举格式化回退：源码日志中 enum 需 `static_cast<int>`、
  `std::atomic<bool>` 需 `.load()`、`fmt::join` 需显式 `#include <fmt/ranges.h>`
- icu 配方以 `--disable-icuio` 构建，源码不得 `#include <unicode/ustdio.h>`

## 关键坑 4：CMake 缺 Platform/HarmonyOS → 共享库无 DT_SONAME（E537 变体）
- 现象: CI L5a 报 `libkyai-knowledgebase-client.so` / `libkysdk-vector-engine-client.so`
  缺少 DT_SONAME；`readelf -d` 无 SONAME，链接命令无 `-soname`
- 根因: OHOS PC 上 `uname -s`=HarmonyOS，CMake 探测出 `CMAKE_SYSTEM_NAME=HarmonyOS`，
  但 CMake/OHOS SDK 均无 `Platform/HarmonyOS.cmake`，平台未设置
  `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG` → 上游 `set_target_properties(...
  VERSION 0.0.1 SOVERSION 1)` 被静默忽略，产出无 SONAME 的无版本 `.so`
- 修复: 在 vendor 两个共享目标构建时经 `extra_defs` 传
  `CMAKE_SHARED_LINKER_FLAGS=-Wl,-soname,lib<name>.so`（无需改上游源码/补丁）
- 说明: 保持无版本 `.so`（与 DT_NEEDED 一致），仅补相对 SONAME；
  glib 合成库本身已用 `-Wl,--soname` 显式设置，不受影响

## 其他
- spdlog 1.17 不传播 fmt::fmt（SPDLOG_FMT_EXTERNAL）→ 配方显式 requires fmt，
  CMakeLists 显式链 `fmt::fmt`
- header-only 组件 include 不传播 → 经 toolchain 变量 `KYAI_EXTRA_INCLUDE_DIRS` 注入
- application 包（无 cpp_info）的 test_package 不会自动传播 requires → test_package
  内显式 `self.requires(ref, transitive_libs=True)` 以得到完整 conanrun LD 闭包
- OHOS 无 `id` 命令、无 `/bin/true`；`pkill -f <name>` 会误杀自身命令行
- 制品仓依赖: zlib/1.3.2、openssl/3.5.8.1、spdlog/1.17.0、fmt/12.2.0、jsoncpp/1.9.8.1、
  curl/8.22.0、icu/76.1、glib/2.88.0、pulseaudio/17.0.1、libsodium/1.0.20、grpc/1.84.0、
  nlohmann-json/3.11.2、libkylin-ai-system-private/1.2.0.0、kysdk-ai-common/1.1.0.1
- 产物: `bin/kylin-ai-runtime`、`lib/libkyai-knowledgebase-client.so`、
  `lib/libkysdk-vector-engine-client.so` + 5 个合成 glib 共享库（均带 `.codesign`）

## 上游测试（R51 三步法）
1. **清点**: 上游 `test/CMakeLists.txt` 注册 5 个 `add_test` 用例（目录下另有 8 个未接入
   CMake 的 .cpp，不计入）
2. **运行**: 主 `build()` 内构建这 5 个 test 可执行文件并在 OHOS aarch64 上执行
3. **结果**（conan create 日志）:

| 用例 | 结果 | 退出码 |
|---|---|---|
| testencryption | PASS | 0 |
| testaes256 | PASS | 0 |
| testenginemanager | PASS | 0 |
| testmodelstatustracker | PASS | 0 |
| testsystemoperation | PASS | 0 |

通过率 **5/5 = 100%**。**口径声明（检视修正）**：其中 testenginemanager 已由
补丁 0002 整体重写（上游原用例依赖旧版 aiengine + baidu 云引擎/网络凭据，
离线 CI 不可运行），重写后为 20 行最小化冒烟（单例 manager 可获取 + 非法
引擎名返回空指针），故该行 PASS 仅代表重写后冒烟口径，不等价于上游原用例
全部断言；其余 4 例为上游原样断言。任一用例 rc≠0 现已 raise ConanException
使构建失败（检视问题 #3）。新增消费者冒烟 1 个入口（test_package）：daemon
后台启动存活 5s 探针 + 3 项断言（rc=1 仅命中降级标记才判 PASS，检视问题 #8）。

## 路径判定
A + B（`application` 包依赖闭包补齐 + 「静态内嵌第三方库导致同进程重复全局状态」
是 kylin-ai 系列可复用诊断/修法：统一合成共享库动态链接）。
---

**编译结束**: 2026-09-28 20:09
**最终状态**: published
