# libclaw 1.7.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-18
- 编译器: clang/clang++ 15 (HarmonyOS PC 真机, /data/service/hnp)
- 状态: built (待真机预检确认)
- 申请人: waylong, 队伍: 龙骑士

## 上游信息
- 名称: libclaw 1.7.4 ("C++ Library Absolutely Wonderful")
- 上游仓库: https://libclaw.sourceforge.net/
- 源码: https://prdownloads.sourceforge.net/libclaw/libclaw/libclaw-1.7.4.tar.gz
- sha256: 0be289da7f43b1892575f14b27860af5d1e1f6961eae11653d64e625fd7924b7
  (与 Debian libclaw_1.7.4.orig.tar.gz 同值, launchpad/pureos 双源交叉确认)
- 许可证: LGPL-2.1-or-later
- 构建入口: 顶层 CMakeLists.txt (cmake_minimum_required 2.6, C++03 时代项目)

## 编译步骤
1. 同步上游 main, 创建分支 feat/libclaw-1.7.4
2. conan create archives/l/libclaw/1.7.4 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
3. CMake configure (POLICY_VERSION_MINIMUM=3.5, SYSTEM_NAME=Linux, INSTALL_LIBDIR=lib) → build (-j1) → install → .so 自签名
4. test_package: 编译 test_libclaw.cpp (6 个 CHECK) → ctest -R test_libclaw → 输出 HMBS 双标记

## 上游测试审计结论
- 1.7.4 发布包无测试套件: 顶层 CMakeLists.txt 无 enable_testing/add_test;
  1.7.4 文件清单无 test/ 目录 (test/check-examples.sh 仅见于 master 后续分支);
  examples/ 下 20+ 子目录均为演示程序 (main.cpp 输出 .plot 数据, 无断言).
- 按 no_tests 口径: build() 不调用 ctest; test_package 每次运行重发
  HMBS_UPSTREAM_TEST_RESULT status=no_tests (bwm/0.6.3 先例, 覆盖 Conan 缓存命中场景).

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake >= 4 拒绝 cmake_minimum_required(2.6) | 上游 2016 年写法, Compatibility with CMake < 3.5 已移除 (Debian #1113128 同因) | 补丁 0001 提升至 3.5; 配方 toolchain + env 双设 CMAKE_POLICY_VERSION_MINIMUM=3.5 (devil/leptonica 先例, E103) |
| 2 | 全局 -std=c++03 与 Boost 1.91 头文件冲突 | 上游写死 C++03, Boost>=1.84 要求 C++14+ | build() 内 tolerant 子串替换删除该 flag (原 0002 上下文补丁因 hunk 漂移在真机报 "source file is different", 改为永不失败的 replace, 缺失则跳过), 由 ohos-aarch64 profile 的 C++17 接管 |
| 3 | FindJPEG/FindPNG/FindBoost 找不到 Conan 产物 | 上游用老式模块 + include_directories, 不认 Conan config 包 | generate() 传入 JPEG_INCLUDE_DIR/JPEG_LIBRARY、PNG_INCLUDE_DIR/PNG_LIBRARY、BOOST_ROOT 绝对路径 (stiff/opencv 先例) |
| 4 | 安装路径为空导致装到 "/" | 上游 CLAW_INSTALLDIR_LIB 取未定义的 CMAKE_INSTALL_LIBDIR | 传入 -DCMAKE_INSTALL_LIBDIR=lib |
| 5 | 上游自带 libclaw-config.cmake 与 Conan 生成冲突 | cmake-module/ 安装旧式变量配置 | CLAW_INSTALL_CMAKE_MODULES=OFF, 消费者统一用 Conan config (libclaw::libclaw) |
| 6 | OHOS 加载器拒载未签名 .so | 真机 dlopen 校验代码签名 (libjpeg-turbo 先例) | package() 后对 lib/*.so* 去旧 .codesign 并 selfSign 重签 |
| 7 | Boost thread/system 需求 | claw_logger 链接 Boost thread+system | 依赖 boost/1.91.0 (含 thread 组件的 CMake 构建版); 1.84.0 仅 header-only 不满足 |
| 8 | configuration_file.cpp:444 `no viable conversion from 'std::istream' to 'bool'` (真机 2026-09-18 compile 失败) | 删除 -std=c++03 后改用 C++17; C++11 起 istream::operator bool 为 explicit, `bool x = stream` 拷贝初始化不再合法 | 补丁 0002: 改为 `static_cast<bool>( text::getline(is, line) )`, 显式转换, 语义不变 |
| 9 | functional.hpp 11 处 `std::unary_function`/`binary_function` 在 C++17 被移除 (同 profile cppstd=17 下必现, gif.cpp 等已包含该头) | C++11 弃用、C++17 移除; 上游 2011 年代码 | 补丁 0002: 去掉基类、自带 argument_type/result_type (含 unary_compose 的 F1/F2 传递), dawg/1.2 先例; 不向 std 注入, 不改调用方 |
| 10 | rectangle.tpp:143 / box_2d.tpp:139-140 `use 'template' keyword` (真机 2026-09-18 compile 失败, 0002 通过后下一错误) | 两阶段查找: position/first_point/second_point 为依赖名, 成员模板须加 template 关键字; 旧 GCC 宽松, 现代 clang 严格拒绝 | 补丁 0003: 3 处加 `template` (position./first_point./second_point. + `template cast_value_type_to<U>()`); 全仓 .tpp/.hpp/.cpp 已扫, 仅此 3 处 |
| 11 | tween/single_tweener.cpp `boost::bind` 处 `non-const lvalue reference to double cannot bind to temporary` (真机 2026-09-18 compile 失败, 0003 通过后下一错误, Boost 1.91) | 新 Boost.Bind 经 `rrlist`/`std::get` 完美转发, `_1` 以右值传入 `local_swap(double&, double&)`; 且 `m_callback(val)` 本就传临时值 | 补丁 0004: `local_swap` 第二形改为按值 (`double b`), 体简化为 `a = b` (旧 `b = t` 只写丢弃的临时量, 语义不变); 全仓仅此 1 处 bind |
| 12 | tween/easing/easing_elastic.cpp:31 `fatal error: 'boost/math/constants/constants.hpp' file not found` (真机 2026-09-18 compile 失败, 76% 处, 0004 通过后下一错误) | 所需 boost/1.91.0 为子集构建 (BOOST_INCLUDE_LIBRARIES=filesystem;iostreams;program_options;regex;thread), 安装树根本无 boost/math/ 头; 上游 master 后续已改用硬编码 pi, 不再依赖 boost/math | build() 内新增 tolerant 替换 _drop_boost_math_dep: 删 include 行、全树扫描替换 `boost::math::constants::pi<double>()` 为硬编码 pi 字面量 (与 master 同值), 缺失则跳过; 不换 boost 版本、不加新依赖 |
| 14 | test_package 链接 `undefined reference due to --no-allow-shlib-undefined: libintl_bindtextdomain/...` (真机 2026-09-18 test_package 阶段; 主库编译通过) | 上游非 WIN32 不链接 intl, 以为 glibc libc 自带 gettext; OHOS musl 无 libintl 实现, claw_application (application.cpp bindtextdomain/textdomain/dgettext) 与 claw_logger (log_level/log_stream_uniq dgettext/dngettext) 的 .so 带未定义 libintl_* 符号, 可执行链接时被 --no-allow-shlib-undefined 拒绝 | build() 内 tolerant 替换 _disable_nls 禁用 NLS (E027; dos2unix/diction 先例): claw_gettext.hpp 去 <libintl.h>、宏改为原文回送, application.cpp 按行前缀过滤去 setlocale/bindtextdomain/textdomain 共 4 调用; 原 0005 上下文补丁因 application.cpp hunk 行号漂移 (@@ -38, 实际构造函数在 CLAW_MK_STR 宏之后) 在真机报 "source file is different" 编译失败, 改为永不失败的 replace, 缺失则跳过; 英文回退, 不新增 gettext 依赖 |
| 13 | test_package `fatal error: 'boost/function.hpp' file not found` (真机 2026-09-18 test_package 构建失败; 主库已编过进入 test 阶段) | 主配方 `requires("boost/1.91.0")` 缺 `transitive_headers/libs`, 公开头 (base_tweener.hpp 含 boost/function.hpp) 的 Boost -I 不传播给消费者 (yomm2/c10t 先例); test_package 仅 requires tested_reference_str, CMakeDeps 未给 Boost 生成配置 | 主配方四依赖加 transitive_headers/transitive_libs=True; test_package 显式 requires 同版本 boost/1.91.0 保底 (find_package(Boost) 必有 Conan 配置) |
| 15 | CI #53954 `ld.lld: relocation R_AARCH64_ADR_PREL_PG_HI21 ... recompile with -fPIC` (libclaw_graphic.so 链接 static libz.a 失败; shared=False 默认构建仍触发) | 上游无视 BUILD_SHARED_LIBS, 7 个库永远同时编 SHARED + -static 两种; SHARED 链接 static-only 无 fPIC 的 zlib/1.3.1 (R26 系统同名库, ./configure --static), aarch64 拒绝非 PIC 重定位 (E005); zlib 已发布不可在本 PR 改 (R37) | build() 新增 tolerant 正则 _respect_conan_shared_option: shared=False 时把 7 个非后缀目标的显式 SHARED 改写为 STATIC (静态归档不链接故无需 PIC, -static 兄弟目标重编相同内容, install/属性行全部继续有效); shared=True 保持上游原样 |

## 源码修改
- patches/0001-cmake-minimum-required-3-5.patch: 顶层 + examples/tween 的 cmake_minimum_required 2.6 → 3.5
- patches/0002-cxx11-cxx17-compat.patch: configuration_file.cpp 显式 bool 转换 + functional.hpp 去 unary/binary_function 基类自带 typedef (dawg/1.2 先例)
- patches/0003-dependent-template-keyword.patch: rectangle.tpp/box_2d.tpp 依赖模板名加 template 关键字 (3 处)
- patches/0004-boost-bind-rvalue-compat.patch: single_tweener.cpp local_swap 第二形按值 (Boost 1.91 bind 右值转发)
- conanfile.py build()::_drop_cxx03_flag: tolerant 删除全局 -std=c++03 (原 0002 上下文补丁, 真机 apply 失败后改; POSIX 兼容, 无平台宏)
- conanfile.py build()::_disable_nls: tolerant 禁用 NLS (原 0005 上下文补丁, application.cpp hunk @@ -38 行号漂移在真机报 "source file is different" 后改; 子串替换 + 行前缀过滤, 缺失则跳过, POSIX 兼容, 无平台宏)
- conanfile.py build()::_drop_boost_math_dep: tolerant 删除 easing_elastic.cpp 对 boost/math 的依赖 (子集 boost 无该头; 上游 master 同方案用硬编码 pi; 全树扫描, 无平台宏)
- 补丁与替换均无 __OHOS__ 平台宏, 符合 R8/PF5

## 依赖版本
- boost/1.91.0 (thread 编译版)
- libpng/1.6.39
- libjpeg-turbo/3.0.4
- zlib/1.3.1 (经 libpng 传递, 显式声明保版本一致)

## test_package 设计 (R34)
- test_libclaw.cpp 真实调用三类 API: tween single_tweener (checks 1-2)、box_2d 几何 (checks 3-4)、configuration_file ini 解析 (checks 5-6)
- 非空壳: 链接 7 个 claw 库 + Boost thread; 反向验证 (移除产物则链接失败) 天然成立
- ctest -R test_libclaw 运行, 输出 HMBS_TEST_PACKAGE_RESULT (discovered=passedCount=6) 与 no_tests 上游标记

## 验证结果
- 本地 (Windows) 未运行 conan (按任务守则, 真机验证由 HMBS 后台执行)
- 待真机预检: conan create 全链路 + ctest 6/6 + no_tests 标记; 日志回填 PR 正文通过率

## Windows 检出说明 (给后端)
- 上游 main 含非法文件名 archives/g/gama/2.29/patches/0002-dataparser-ungated.patch<CR><CR>,
  Windows 无法检出; 本机用底层对象直读重建 74781 文件, 该文件缺失.
- 后端在 Linux 提交前须执行 git checkout -- 上述文件 (或 git reset --hard) 恢复,
  确保本 PR 只含 archives/l/libclaw 内容, 不误删 gama 文件.

---

**编译结束**: 2026-09-18
**最终状态**: built (待真机 evidence 确认后由 HMBS 提交)
