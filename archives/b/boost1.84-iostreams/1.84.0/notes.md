# boost1.84-iostreams 1.84.0 适配笔记

## 编译开始时间
2026-09-05 20:30

## 组件包形态选型结论（沿用 boost1.84-atomic 打样，见其 notes.md）

### 选型：方案 A —— 独立裁剪编译（从 boost 源码只编 iostreams 组件）

**否决方案 B（requires("boost/1.84.0") 元包引用）的理由：**

1. **元包 iostreams 不完整（硬伤）**：boost/1.84.0 元包的 iostreams 段
   只编了 4 个 TU（file_descriptor/mapped_file/zlib/gzip）：
   - **缺 bzip2.cpp**：元包注释"skip bzip2/lzma/zstd - no system libs"。
     而 bzip2/1.0.8 已在制品仓（W0 已验证），本组件包补齐 bzip2 后端
     （上游 Jamfile 在系统有 libbz2 时编入 bzip2.cpp）。
   - **缺 BOOST_IOSTREAMS_USE_DEPRECATED 宏**：上游
     libs/iostreams/build/Jamfile.v2 line 120 对 lib boost_iostreams
     定义 `<define>BOOST_IOSTREAMS_USE_DEPRECATED`。不带此宏时
     file_descriptor.cpp 的 deprecated 构造/open 重载
     （file_descriptor(handle_type, bool) 等，POSIX 下 handle_type=int）
     不会被编译——实测元包 4 TU 库链接 deprecated_file_descriptor_test
     报 `undefined symbol: file_descriptor(int, bool)`。
2. **元包组件声明的依赖面窄**：元包 package_info 的 boost_iostreams
   组件 requires ["boost_headers", "boost_system", "zlib::zlib"]，
   没有 bzip2。下游用 bzip2 filter 时元包链接不了 libbz2。
3. **独立演进**：组件包独立版本号演进（R37 后缀机制可用），不与
   boost/1.84.0 元包修订锁死（元包同版本 revision 已冻结，无法补
   bzip2/USE_DEPRECATED——修改同版本会被 cnb.cool 409 拒绝）。
4. **上游测试要求**：积分赛要求真实跑上游测试。iostreams 上游测试
   （libs/iostreams/test/Jamfile.v2，非 Windows + zlib/bzip2 启用 + 无
   LARGE_FILE_* + 无 liblzma/libzstd 配置下生效的 48 项 = 47 run +
   1 compile-fail）全套在本配方 build() 里手动编译运行；
   方案 B 元包无此过程。

**方案 A 的关键实现（沿用已验证模式）：**

- **源码清单（上游 Jamfile 权威）**：
  `lib boost_iostreams : file_descriptor.cpp mapped_file.cpp
  + zlib-requirements(zlib.cpp gzip.cpp) + bzip2-requirements(bzip2.cpp)`
  - lzma.cpp/zstd.cpp 需要 liblzma/libzstd，本包不引入（同元包口径）。
  - **编译必带 `-DBOOST_IOSTREAMS_USE_DEPRECATED`**（上游 Jamfile
    line 120，deprecated 重载的实现守卫）。
- **依赖**：zlib/1.3.1 + bzip2/1.0.8（制品仓均在库，conan requirements，
  include/lib 从依赖 package_folder 取——R33 合规不用 shell 环境变量）。
- **上游测试**（libs/iostreams/test/Jamfile.v2 test-suite iostreams）：
  上游 Jamfile 测试注册条目 56（三模式 grep 口径：53 个 test-iostreams
  行含 1 个 rule 定义行 + 2 个 compile-fail-iostreams 行含 1 个 rule
  定义行 + 1 个 test-suite 汇总行），其中**真实测试目标 53 个**（无条件
  45 = 44 run + 1 compile-fail；条件 8 = bzip2_test、zlib 块
  write_failure/gzip/zlib_test、lzma_test、zstd_test、large_file_test×2）。
  本配置生效 48 项真跑：
  - run 型 47 项：42 项单源 + code_converter_test（附加
    detail/utf8_codecvt_facet.cpp 源）+ deprecated_file_descriptor_test
    （带 USE_DEPRECATED 宏变体）+ grep/regex_filter_test（链接
    boost_regex）+ zlib/gzip/bzip2/write_failure 压缩 4 项（本包
    zlib+bzip2 后端已启用，条件注册分支生效，真跑）
  - compile-fail 型 1 项：deprecated_file_descriptor_test 不带宏编译应失败
  - 未执行 5 项均为上游条件/平台门控（非适配删减）：
    windows_pipe_test 为 Windows-only（`<build>no
    <target-os>windows:<build>yes`，非 Windows 上游自身不构建）；
    lzma_test/zstd_test 需 liblzma/libzstd（NO_LZMA/NO_ZSTD 语义，
    本包后端裁剪决策未引入）；large_file_test×2 需
    LARGE_FILE_TEMP/KEEP 环境变量（上游默认不设即不注册执行）
  - 测试辅助库（仅编译入 build_folder，不入 package 产物）：
    boost_unit_test_framework 19 TU（同 log 包先例）+
    boost_filesystem 9 TU（temp_file/operations 夹具）+
    boost_regex 5 TU（grep/regex_filter 测试，元包同款清单）
- **无需平台 patch 于 iostreams 自身源码**：但继承元包 0001
  （sp_thread_sleep.hpp 的 pthread_setcancelstate 守卫）——iostreams
  TU 经 smart_ptr 头链触及该文件（本地实测：不带 patch/宏时
  file_descriptor.cpp 编译报 pthread_setcancelstate undeclared）。
- **package() 内容**：完整 boost 头文件树（组件包自包含，Debian
  libboost-iostreams1.84-dev 同模式）+ lib/libboost_iostreams.a。
- **package_info()**：`cmake_file_name="boost1.84-iostreams"` +
  组件 `boost1.84_iostreams`（cmake_target_name
  `boost1.84-iostreams::iostreams`，libs=["boost_iostreams"]，
  requires=["boost1.84_iostreams_headers", "zlib::zlib",
  "bzip2::bzip2"]）。下游 `find_package(boost1.84-iostreams
  COMPONENTS iostreams)` + `boost1.84-iostreams::iostreams` 开箱即用，
  zlib/bzip2 传递依赖由 Conan 自动链接。

## 编译系统
手动编译（b2 在 OHOS 不兼容，E068；与底稿 boost/1.84.0 元包配方同构）

## 源码下载
- 来源：Boost 官方（SourceForge + archives.boost.io 双镜像，与底稿 conandata.yml 一致）
- URL：https://archives.boost.io/release/1.84.0/source/boost_1_84_0.tar.gz
- SHA256：a5800f405508f5df8114558ca9855d2640a2de8f0445f051fa1c7c3383045724（与底稿一致）
- 解压验证位置：~/tmp/boost184src/boost_1_84_0

## 环境信息
- 平台：OpenHarmony (aarch64)
- 编译器：clang 15.0.4 (aarch64-unknown-linux-ohos target)
- 构建系统：手动 clang++/llvm-ar（绕过 b2）

## 适配过程

### Phase 0: 选型验证
- [x] 读底稿 archives/b/boost/1.84.0/（元包 iostreams 段：4 TU 无 bzip2 无 USE_DEPRECATED）
- [x] 读 boost1.84-atomic/wave/log 先例（手动编译 + 上游测试嵌入模式）
- [x] W0 依赖检查：zlib/1.3.1 ✅ bzip2/1.0.8 ✅（conan download 验证）
- [x] 上游 Jamfile 解读：源清单 + USE_DEPRECATED + 测试清单

### Phase 1: 编译验证（W3 前置实验，本机 OHOS 直接运行）
- [x] 5 TU 编译（带 patch + USE_DEPRECATED）：全过
- [x] libboost_iostreams.a 打包：220,552 字节
- [x] 冒烟：gzip/zlib/bzip2 round-trip + file_descriptor + mapped_file 全过
- [x] 测试辅助库编译：UTF 19 TU + filesystem 9 TU + regex 5 TU 全过
- [x] 上游测试 48/48（47 run + 1 compile-fail）全过（详见 test-report.md）
- 发现问题 1：不带 patch 时 file_descriptor.cpp 报 pthread_setcancelstate
  undeclared（smart_ptr → sp_thread_sleep.hpp 链）——继承元包 0001 patch 解决
- 发现问题 2：元包式编译（无 USE_DEPRECATED）时 deprecated_file_descriptor_test
  链接失败——按上游 Jamfile 补宏解决（这是元包的一个隐藏缺陷，本组件包修正）

### Phase 2: 配方固化
- conanfile.py：手动编译模式 + zlib/bzip2 requirements + 上游测试嵌入 build()
- conandata.yml：官方双镜像 + SHA256（与底稿一致）+ 0001 patch 声明
- test_package/：CMake find_package(boost1.84-iostreams COMPONENTS iostreams)
  → boost1.84-iostreams::iostreams 下游消费冒烟（三压缩 + fd + mmap）
- patches/：0001-ohos-pthread-cancel-fix.patch（与元包/atomic/log/wave 同款）

### Phase 3: W3 本地 CI 验证
- conan create -pr:h=ohos-aarch64：通过（5 TU 编译 + 48 项上游测试 + test_package）
- （详见 reports/）

## 遇到的问题

### 问题 1: pthread_setcancelstate 编译错误
- **症状**：`error: use of undeclared identifier 'pthread_setcancelstate'`
- **根因**：iostreams TU 经 boost/shared_ptr.hpp → smart_ptr 链触及
  sp_thread_sleep.hpp，OHOS musl 无此 API
- **解决**：继承元包 0001 patch（BOOST_SP_NO_PTHREAD_SETCANCELSTATE
  特性检测宏守卫，R8 合规非平台宏）

### 问题 2: deprecated_file_descriptor_test 链接失败（元包隐藏缺陷）
- **症状**：`ld.lld: error: undefined symbol:
  boost::iostreams::file_descriptor::file_descriptor(int, bool)`
- **根因**：上游 Jamfile 编译 lib boost_iostreams 时带
  `<define>BOOST_IOSTREAMS_USE_DEPRECATED`（line 120），deprecated
  构造/open 重载的实现段被此宏守卫；元包配方漏带宏 → 符号未编译。
  POSIX 下 handle_type=int，故 mangled 名为 file_descriptor(int, bool)。
- **解决**：本组件包编译 5 TU 时带 `-DBOOST_IOSTREAMS_USE_DEPRECATED`
  （与上游 Jamfile 完全一致）

### 问题 3: /tmp 只读（E002）
- **解决**：所有临时产物写 build_folder（Conan 管理），无 /tmp 依赖

## 知识提取记录

### 知识点：Boost.Iostreams 组件包模式
- iostreams 源清单 = 基础 2 TU（file_descriptor/mapped_file）+
  按启用后端追加（zlib:+2 gzip/zlib；bzip2:+1；lzma/zstd 本包未启用）
- **编译必带 BOOST_IOSTREAMS_USE_DEPRECATED**（上游 Jamfile line 120），
  否则 deprecated 重载符号缺失——元包漏带是实际缺陷
- 上游测试 48 项（47 run + 1 compile-fail）需要三个测试辅助库：
  unit_test_framework/filesystem/regex（测试期编译，不入包）
- 压缩后端依赖经 conan requirements 引入（zlib/1.3.1 + bzip2/1.0.8），
  组件 requires 里声明传递链接

## 编译结束
**最终状态**: built（W3/CI 验证后更新）
---

**编译结束**: 2026-09-05 21:18
**最终状态**: built
