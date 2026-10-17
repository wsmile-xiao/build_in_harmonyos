# libical3 3.0.20 适配笔记

## 定位
libical 3.0 版本线（iCal 3.0），与仓内 libical/4.0.1（4.x 线）并存。
多版本并存先例：boost/boost1.84/boost1.90（独立包名+独立目录），同
kconfig 三版本（6.14.0/6.18.0/6.26.0）模式。

差异化：4.0.1 关闭 GLIB 绑定（无 glib 依赖）；本 3.0.20 启用 ICAL_GLIB
（glib/2.88.3 + libxml2/2.15.3.1），产出 libical-glib.so（GObject 绑定），
供需要 GLib 日历生态的下游使用。

## 编译环境
- 构建系统: cmake
- 编译器: clang 15.0.4 (aarch64-linux-ohos)
- 构建日期: 2026-09-13
- 状态: verified

## 依赖（W0 已核全部发布）
- glib/2.88.3 (shared, 组件 glib/gobject/gmodule/gthread/gio)
- libxml2/2.15.3.1 (shared)
- perl/5.42.2 (tool_requires, 3.0 线源码生成必需)

## 关键适配点（踩坑记录）

### 1. pkg-config 依赖解析（最大坑）
上游 FindGLib/FindLibXML 用 pkg_check_modules 找 glib-2.0/gobject-2.0/
libxml-2.0。三个障碍：
- conan glib 包安装的 .pc 文件 prefix=/（安装期 --prefix=/，路径 broken）
- glib-2.0.pc 的 Requires: proxy-libintl——proxy-libintl/0.5 包没装 .pc，
  pkg-config 解析直接整体失败
- Requires.private 引用 libpcre2-8/libffi/zlib——传递依赖的
  package_folder 在 conan 2.29 的 self.dependencies 里为 None（只填
  直接依赖），无法加入 PKG_CONFIG_PATH

修法（配方 _generate_pkg_config_fix）：
- 复制 glib 系+libxml-2.0 的 .pc 到 generators/pc-fix/
- prefix 行改写为真实包目录
- Requires 行按逗号拆分剔除 proxy-libintl
- Requires.private 整行置空（pkg_check_modules 非 static 模式只取
  CFLAGS/LDFLAGS，private 不参与；置空避免存在性校验失败）
- PKG_CONFIG_PATH 在 build() 里用 Environment().vars().apply() 包裹
  cmake.configure()（CMake helper 不读 preset 的 environment 字段，
  配方自身 buildenv_info 也不进 conanbuild.sh 生效路径）

### 2. 链接期库路径（LIBRARY_PATH）
上游 FindLibXML 只取 pkg-config 的 --libs-only-l 结果（仅 -lxml2，无
-L 路径）传给 target_link_libraries → 链接 ical-glib-src-generator 时
"unable to find library -lxml2"。修法：env.prepend_path("LIBRARY_PATH",
glib/libxml2 包 lib 目录)——clang/lld 认可，等效 -L。

### 3. 构建期工具就地运行（generator）
ical-glib-src-generator（生成 libical-glib 源码的工具）构建后立即运行：
- 链接 shared glib/libxml2 → LD_LIBRARY_PATH 前置依赖包 lib
- 上游 CMAKE_CROSSCOMPILING 分支要求导入 native 构建的 generator
  target——OHOS-on-OHOS（构建机=目标机同架构）不需要，配方
  replace_in_file 砍掉该分支走普通路径

### 4. OHOS soname 规则
3.0.20 的 VERSION/SOVERSION 块（if(NOT ANDROID) 包裹，单行属性格式）：
删除（HMDFS 绝对 soname/$ORIGIN 不稳定），同 4.0.1 处理。ohos-cmake-rules.cmake
注入相对 soname 规则（-Wl,-soname,./ 前缀）。

### 5. 上游测试运行时路径
测试二进制 NEEDED 相对 soname（./libical.so 等），工作目录 build/bin：
- 构建产物 lib*.so* 复制到所有 CTestTestfile.cmake 所在目录及其上溯
  lib 位置（覆盖 bin/../lib 等）
- zoneinfo 目录复制到 build/../zoneinfo（builtin_timezones 测试用）
- ctest 用 CTEST_OUTPUT_ON_FAILURE 运行，glib/libxml2 so 进
  LD_LIBRARY_PATH

### 6. 语言预检误判说明
lang-preflight 初次判定 perl（src/Net-ICal-Libical/Makefile.PL 是上游
遗留的未完成 perl 绑定死代码目录，构建系统完全不引用）。本体是
project(libical C) 的 CMake 工程（152 C 文件）。按 R47 边界规则（辅助
脚本不构成主体）在剔除死代码目录的干净源码视图复检：cpp/cmake 匹配。

## 验证
- 源码 SHA256:
  e73de92f5a6ce84c1b00306446b290a2b08cdf0a80988eca0a2c9d5c3510b4c2
- OHOS conan create 验证通过（shared=True，含上游测试）
- 上游 CTest: 48/48 通过（100%），无注册测试被跳过
  - N=48 口径：src/test/CMakeLists.txt 注册的 ctest 目标数
    （testme×13 + icalrecurtest×2 + parser-*.ics×34，其中
    timezones 因 USE_BUILTIN_TZDATA=ON 不注册、stow 仅 buildme
    不注册、BIGFUZZ 关闭）——本地实测 ctest -N = 48
- Conan test_package: 1/1 通过
- 直接消费验证: PASS: libical C API (VEVENT summary + today) +
  PASS: libical-glib bindings (VEVENT summary)
- Full reference:
  libical3/3.0.20#ef913a5da543b562087e995bdf75b732:dc28935ec6800431699680a0d7977c3672b19cae

## 上游测试用例对比（N 口径）
上游默认形态注册 48 个测试目标（ctest -N 实测），适配后同口径 48/48
通过——无跳过、无豁免。

## 交付物
| 文件 | 说明 |
|------|------|
| libical-3.0.20-ohos-aarch64 conan 包 | ical/icalss/icalvcal/ical-glib (.so+.a) |
---

**编译结束**: 2026-09-14 00:56
**最终状态**: published
