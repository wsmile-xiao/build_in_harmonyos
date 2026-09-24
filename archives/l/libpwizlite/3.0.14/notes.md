# libpwizlite 3.0.14 — 适配笔记

> 档案创建时间: 2026-09-22
> 最后更新: 2026-09-22
> 状态: built（本机 conan create 全绿：test_package 8/8 断言过，N=0+消费者兜底）

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libpwizlite |
| 版本 | 3.0.14（forgemia 项目 2270 最新 upstream tag） |
| 构建系统 | CMake (C++17) |
| 源码 | https://forgemia.inra.fr/pappso/libpwizlite/-/archive/upstream/3.0.14/libpwizlite-upstream-3.0.14.tar.gz |
| sha256 | 74c57dd532275d301480697fbdfe7120b072c56ba60ac388e5f27d3591fdac06 |
| 任务背景 | libpappsomspp 0.11.26 前置链第 3 件（pappsomspp 命脉前置） |

## 二、W0 依赖核验
- boost：⚠️ 制品仓全线（1.84/1.85/1.90/1.91）只带 filesystem/iostreams/program_options/regex
  编译库，且 1.91.0 连头模块都砍（logic/math/multi_index/numeric/ublas/spirit/interprocess/locale）
  → 选 boost/1.84.0（头全 + 有 iostreams/filesystem .a），thread/chrono 缺口 vendor 补
- zlib/1.3.1 ✅（注意非 PIC → 静态交付）
- 无 Qt 依赖

## 三、关键适配点

### 3.1 boost thread/chrono 编译库缺口（本件最大坑）
- pwiz 的 SpectrumWorkerThreads/SpectrumList_* 用 boost::thread/chrono/mutex 编译符号
  （thread::start_thread_noexcept、chrono::steady_clock::now、thread_detail::enter_once_region 等）
- 制品仓 boost 无 libboost_thread/libboost_chrono
- **修法**：vendor boostorg/thread + boostorg/chrono（tag boost-1.84.0，与 boost/1.84.0 头版本
  严格匹配）共 8 个 .cpp，构建期编成 libboost_thread_vendored.a + libboost_chrono_vendored.a，
  llvm-ar 解包后并入 libpwizlite.a（消费者单库闭环）
- **ar 合并三坑**：①llvm-ar 不能直接把 .a 并入 .a；②CMake 对象后缀是 .cpp.obj 不是 .o；
  ③merge 后需 --build=<pkg>/* 强制重建（conan 缓存复用旧包二进制）

### 3.2 OHOS musl pthread 缺口
- boost/core/detail/sp_thread_sleep.hpp 用 pthread_setcancelstate（OHOS musl 无）
- 豁免宏 BOOST_SP_NO_PTHREAD_SETCANCELSTATE（boost/1.85.0 配方 R8 注释同款）

### 3.3 上游构建系统四坑（patch 0001-0004）
- 平台分支：CMAKE_SYSTEM_NAME=HarmonyOS 下 UNIX 未定义 → unix-toolchain.cmake 跳过（同 libodsstream）
- CPack：CPACK_RESOURCE_FILE_LICENSE 指向 tag tarball 不带的 debian/copyright → 硬失败 → 改条件判断
- Boost targets：上游链 Boost::iostreams 等 module-mode targets；conan CMakeDeps 1.84 导出
  Boost::iostreams/filesystem/headers → patch 改链（thread/chrono 用 headers 兜底，符号由 vendored 补）
- Boost 版本下限：上游 1.88，制品 1.84 → 放宽至 1.84

### 3.4 上游测试口径（N=0 如实申报 + 消费者测试兜底）
- 上游无测试框架：无 tests/ 目录、无 add_test/enable_testing、无 check 目标
  （CMakeLists 的 "/tests/" 只是 CPack 打包忽略项）
- test_package/test_pwizlite.cpp：mzML 解析消费者测试 8 断言（MSDataFile 打开最小
  indexedmzML、spectrum list 访问、spectrum(0) 惰性加载、id/index 往返）全过
- mzML 格式三细节：根元素 indexedmzML 大小写敏感；mzML 1.1 用 cvList 非 cvLabel；
  spectrumList 必须在 run 内；pwiz fillInCommonMetadata 会用文件名覆写空 run id

## 四、R 条款对照
- R26：非系统同名库；zlib 非 PIC → 静态交付（patch 0003 守卫 shared 目标）
- R28/R34：test_package 调真实 API（MSDataFile mzML 解析）
- R32：settings.os 判断 in ("Linux","OHOS")
- R38：纯库无 bin 产物
- R39：conandata URL 是官方 forgemia tag 归档

## 五、源码修改清单
| 文件 | 原因 | 方式 |
|------|------|------|
| CMakeLists.txt | HarmonyOS 平台分支 | patch 0001 |
| CMakeLists.txt | CPack license 条件化 | patch 0002 |
| src/CMakeLists.txt | Boost targets + static-only 守卫 | patch 0003 |
| CMakeStuff/toolchains/unix-toolchain.cmake | Boost 版本下限 1.88→1.84 | patch 0004 |

另 vendor：vendor-boost-libs/（boostorg/thread+chrono tag boost-1.84.0 源码 8 cpp +
构建 CMakeLists）。

## 六、本机验证
```bash
cd ~/huawei/worktrees/j669539/libpwizlite-3.0.14
conan create archives/l/libpwizlite/3.0.14 -pr:h=~/.conan2/profiles/ohos-aarch64 \
  -pr:b=~/.conan2/profiles/ohos-aarch64 --build=missing -c tools.build:jobs=2
# → merged 8 vendored boost objects into libpwizlite.a；test_package 8/8 全过
```

## 七、对话记录
### 对话 #1 — 2026-09-22
**操作**: 全链适配（vendored boost thread/chrono + 4 补丁 + test_package）
**结果**: conan create 全绿
**当前状态**: 待归档收尾 → push → PR → CI → 提审
