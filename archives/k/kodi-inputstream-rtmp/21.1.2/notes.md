# kodi-inputstream-rtmp 21.1.2 适配笔记

## 结论

适配成功：权威 CI（ci/conan/build_and_test.sh，profile ohos-aarch64）PASS。

## 版本映射与源码身份

- 产品版本 `21.1.2` ↔ 上游 tag `21.1.2-Omega`（xbmc/inputstream.rtmp，
  release commit `fb2745b7768c9babd922dbaf0d811968814306b9`）。
- 归档 `https://github.com/xbmc/inputstream.rtmp/archive/refs/tags/21.1.2-Omega.tar.gz`
  SHA256 `b7223a30d2774e4c7cbd6c4f8a266bf4d186d160590077be627bd0490d80645c`。
  conandata.yml 以 gh-proxy 镜像列为首选、GitHub 直连为镜像（kodi-tools/21.3 先例）。

## 依赖闭包（制品仓已发布，conan download --only-recipe 探测通过）

- `librtmp/2.4_git20190330`（静态 + fPIC，编入插件模块）
- `openssl/3.5.6`（静态 PIC 归档 libssl.a/libcrypto.a，编入插件模块）
- zlib：**链接 OHOS 系统 libz.so**（见下）

## 首轮 CI 失败与修复（zlib PIC 问题）

首轮 conan create 链接失败：`ld.lld: error: relocation R_AARCH64_ADR_PREL_PG_HI21
cannot be used against symbol 'z_errmsg'; recompile with -fPIC`（zutil.o in
libz.a）。根因：conan zlib/1.3.1 包刻意只出**静态非 PIC** 归档——其配方注明
"zlib is a system same-name library (/lib/libz.so*)"，按 R26 只建静态避免
.so 污染，且 configure 未注入 -fPIC。非 PIC 归档无法链入 aarch64 共享模块。

修复（本配方内，零越界改动）：静态 librtmp/openssl 均为 PIC，仅 zlib 换系统库——

- CMakeDeps 把 librtmp 的传递依赖（`openssl::openssl;zlib::zlib`）挂在辅助
  接口 target `librtmp_DEPS_TARGET` 上：清空其 INTERFACE_LINK_LIBRARIES 即把
  非 PIC 的 libz.a 移出链接线（librtmp 自身的 PIC 归档仍经
  `librtmp::librtmp` 正常链入；注意不能清 `librtmp::librtmp` 本身的接口——
  那会把 librtmp.a 的路径也剪掉，导致 RTMP_* 变成未定义符号）；
- 显式链接 `librtmp::librtmp + openssl::openssl + z`（系统 libz：SDK sysroot
  usr/lib/aarch64-linux-ohos/libz.so 是链接期导入库（SONAME=libz.so），产物记录
  DT_NEEDED=libz.so；运行时由 OHOS musl 加载器按 /etc/ld-musl-aarch64.path 默认
  搜索路径命中系统组件 /system/lib64/chipset-sdk-sp/libz.so（symlink →
  libshared_libz.z.so，SONAME=libshared_libz.z.so，OHOS 系统 zlib 实现）——
  实测 env -i（空环境、无 LD_LIBRARY_PATH）dlopen 成功且 /proc/self/maps 显示
  映射的正是该文件；与 /usr/lib/libz.so.1 无关）；
- 本包 cpp_info.requires 置空（模块自含：rtmp/openssl 已编入，zlib 走系统），
  消费者无需附加链接要求。

## 构建方案

1. **Kodi 构建系统缺失**：上游 CMakeLists.txt 的 `find_package(Kodi REQUIRED)` +
   `build_addon()` 需要 Kodi 源树 cmake 模块。registry 无 kodi 包 → 仿
   kodi-platform/20250416 自备 `recipe-cmake/CMakeLists.txt`
   （`cmake.configure(build_script_folder="recipe-cmake")`），上游源码零修改。
2. **RTMP 查找**：上游 `FindRTMP.cmake` 走 pkg-config 找系统 librtmp。改为
   `find_package(librtmp CONFIG REQUIRED)` + 链接 CMakeDeps target
   `librtmp::librtmp`。注意 librtmp 包的 `cpp_info.includedirs` 指向
   `include/librtmp`（其设计消费者用 `#include "rtmp.h"`），而上游代码用
   `<librtmp/rtmp.h>`/`<librtmp/log.h>` → conanfile `generate()` 把 include 的
   **父目录**经 CMake 变量 `RTMP_INCLUDE_PARENT` 注入（不硬编码路径）。
3. **kodi-dev-kit 头**：上游代码 include `<kodi/General.h>`、
   `<kodi/addon-instance/Inputstream.h>`。registry 无 kodi 包 → 从
   xbmc 21.3-Omega 归档（SHA256 `a60afcb5…31aa`，与 kodi-tools/21.3 conandata
   记录一致）取 `xbmc/addons/kodi-dev-kit/include/kodi` **原样**内嵌到版本目录
   `kodi-dev-kit/kodi`（152 个头文件，~1.8MB；注意内嵌路径归一化掉了
   `include/` 段——仓库 .gitignore 有 `archives/**/include/` 规则，头树必须
   不含 `include/` 路径组件才能入库；CMake include 路径相应指向
   `kodi-dev-kit/`，`<kodi/...>` 解析不变；provenance 记录于版本
   manifest.yaml）。
4. **API 版本兼容核对**（21.1.2 插件源码 vs 21.3-Omega 头）：
   - `CInstanceInputStream` 的 `Open/Close/GetCapabilities/ReadStream/PosTime/
     GetTime/GetTotalTime` override 签名逐一匹配（Inputstream.h:1208/1240/1253/
     1293/1641/1651/1696）；
   - `CAddonBase::CreateInstance(const IInstanceInfo&, KODI_ADDON_INSTANCE_HDL&)`
     匹配（AddonBase.h:386）；
   - `ADDONCREATOR` 宏存在（AddonBase.h:1855）；
   - inputstream instance API `ADDON_INSTANCE_VERSION_INPUTSTREAM = 3.3.0`
     （versions.h:111）。
5. **产物**：单一共享模块 `lib/libinputstream.rtmp.so`（上游 Kodi 运行时名
   `inputstream.rtmp.so`；包内采用标准 lib 前缀以贴合 ELF/Conan 惯例，SONAME
   相对路径）。`addon.xml.in` 的 `@ADDON_DEPENDS@`/`@PLATFORM@` 占位符由 Kodi
   宿主安装流程展开，不在本包范围。

## test_package 设计

上游无测试套件（见下方 NO_UPSTREAM_TESTS 证据）。消费者测试为真实编译+链接+运行，
两部分共 21 项断言（任一失败进程返回非零）：

**Part 1 —— 链接期入口版本断言（6 项）**

- 链接产物 .so，调用 `ADDONCREATOR` 导出的纯函数
  `ADDON_GetTypeVersion`/`ADDON_GetTypeMinVersion`（无宿主可执行），
  断言 inputstream=3.3.0、general=1.0.5/1.0.4、main=2.0.2/2.0.0；
- 副作用验证：vendored 头确实编进模块；.so 的 DT_NEEDED（libssl/libcrypto/libz）
  在执行时解析成功。

**Part 2 —— dlopen + C ABI 工厂的完整消费者流程（15 项，review rule12 整改）**

以最小 Kodi 宿主桩走一次真实的实例声明/打开流程（包不安装头文件，宿主与
二进制插件只通过稳定 C ABI 交互——测试按 c-api 头逐字转写结构体并以
static_assert 固定布局，防漂移）：

1. `dlopen` 打包产物——测试二进制本身链接产物，加载器已按 DT_SONAME
   `libinputstream.rtmp.so`（配方显式 `-Wl,-soname`，CI L5a 门禁断言）完成
   映射，`dlopen(SONAME)` 确定性附加到已加载模块——即二进制插件宿主获取
   模块句柄的标准方式；随后 `dlsym` `ADDON_Create`/`ADDON_GetTypeVersion`
   工厂导出；
2. 宿主桩填充 `AddonGlobalInterface`（stub `free_string`/`addon_log_msg`，
   空 `toAddon`）→ `ADDON_Create` 真实实例化 `CMyAddon`（`CAddonBase`），
   断言 `addonBase` 句柄与 `toAddon->create_instance/destroy_instance/destroy`
   布线非空（即 `CAddonBase` 构造期真实运行）；
3. 宿主填充 `KODI_ADDON_INSTANCE_STRUCT`（type=105、version="3.3.0"）→
   `toAddon->create_instance` 走真实 `CMyAddon::CreateInstance` 多实例路径
   构造 `CInputStreamRTMP`，断言实例句柄、`open/close/get_capabilities`
   函数表布线以及 `toAddon->addonInstance == instance.hdl` 均非空/一致；
4. `get_capabilities` 精确断言上游实现返回的
   `INPUTSTREAM_SUPPORTS_IPOSTIME|SEEK|PAUSE`（0x1A）；
5. 真实 `Open` 流程受控失败并正确传播：非法 RTMP URL
   （`RTMP_Alloc→RTMP_Init→RTMP_SetupURL` 解析失败）与不可达服务器
   （`rtmp://127.0.0.1:1/live`，loopback 1 端口连接拒绝——实测 probe）
   均经真实 librtmp 会话路径返回 false、不崩溃；
6. `close` 后再次 `get_capabilities` 断言实例状态一致；最后
   `destroy_instance→destroy→dlclose` 无崩溃收尾。

- L1e 破坏性反测天然成立：移走 lib/ 后可执行文件加载即失败。

关键依据：`kodi/versions.h` 的 `*_USED` 宏由 Kodi 构建系统注入；本配方不定义
`BUILD_KODI_ADDON`（它仅被 versions.h 查询用于裁剪版本分支），因此所有版本分支
均编译进模块，测试断言稳定成立。Part 2 的 C ABI 结构转写与 21.3-Omega
kodi-dev-kit c-api（addon_base.h、inputstream.h）逐字段核对，并有
static_assert 布局守卫。

## 上游测试门禁（NO_UPSTREAM_TESTS）

已核查入口与证据：

- 源码归档无 `tests/` 目录；
- `CMakeLists.txt`：无 `enable_testing()`/`add_test()`/CTest（全文 41 行，仅
  find_package + build_addon）；
- `Jenkinsfile`：单行 `buildPlugin("Omega")`，仅构建；
- `.github/workflows/build.yml`（名为 "Build and run tests"）：唯一 job 为构建；
  "Debian package test" 走 xbmc 主干的 `debian-addon-package-test.sh`
  （`sudo apt-get build-dep` + fakeroot/dpkg 打包冒烟），非测试套件且需 sudo/apt；
- `azure-pipelines.yml`（Windows/UWP CMake 构建）、`appveyor.yml`、`.travis.yml`：
  均为 build-only 配置。

结论：上游无可在本环境运行的真实测试套件 → `NO_UPSTREAM_TESTS`。

## 遗留风险

- Kodi 宿主运行时行为未端到端覆盖（设备无 Kodi）：test_package Part 2 已以
  宿主桩覆盖 C ABI 工厂实例化、capabilities 与 Open 失败路径，但真实 RTMP
  流会话（成功连接后的读流/demux）、addon.xml 元数据展开、Kodi 对 API 版本
  3.3.0 的接受度仍需宿主侧验证。
- `inputstream.rtmp` 的 Makefile 路径（upstream 输出名）与包内
  `libinputstream.rtmp.so` 的文件名差异由宿主打包层桥接。
- zlib 运行时解析依赖 OHOS 系统组件：产物 DT_NEEDED=libz.so，由加载器在
  /etc/ld-musl-aarch64.path 默认搜索路径内命中
  /system/lib64/chipset-sdk-sp/libz.so（symlink → libshared_libz.z.so），
  无需 LD_LIBRARY_PATH（env -i 实测可解析）。标准 OHOS 系统镜像零额外分发；
  仅非标准/裁剪镜像需保证任一默认搜索路径存在可解析的 libz.so（如保留该
  系统组件，或随包分发 libz.so 并注入 LD_LIBRARY_PATH）。
- RTMP 是明文协议；librtmp 的 openssl-3.x 兼容补丁已在 librtmp 包内解决
  （CRYPTO 分支），本包不涉及。
