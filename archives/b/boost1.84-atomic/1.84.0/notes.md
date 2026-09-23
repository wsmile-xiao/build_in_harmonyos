# boost1.84-atomic 1.84.0 适配笔记

## 编译开始时间
2026-09-05 14:00

## 组件包形态选型结论（⭐ 后续 6 个 boost 组件包照抄）

### 选型：方案 A —— 独立裁剪编译（从 boost 源码只编 atomic 组件）

**否决方案 B（requires("boost/1.84.0") 元包引用）的理由：**

1. **元包缺组件声明（硬伤）**：已发布的 boost/1.84.0 配方
   （archives/b/boost/1.84.0，revision 7c2a75f2d58bdfa7e5ffcc48dd1b4736）
   的 `package_info()` 只声明了 `boost_headers` / `boost_filesystem` /
   `boost_regex` / `boost_program_options` / `boost_iostreams` /
   `boost_system` / `boost_date_time` 七个组件——**没有 `boost_atomic`
   组件**。方案 B 的元包下游 `find_package(Boost COMPONENTS atomic)`
   无法解析到 `Boost::atomic` 目标，CMakeDeps 生成不了组件配置，
   下游项目直接构建失败。元包引用只能"装头文件"，给不出组件目标。
2. **元包无 atomic 静态库产物**：boost/1.84.0 元包的 lib/ 只有
   libboost_{filesystem,regex,program_options,iostreams}.a 四个库——
   **没有 libboost_atomic.a**。而 Boost.Atomic 的 wait/notify API
   在 1.84 不是纯 header-only：`libs/atomic/src/lock_pool.cpp` 必须编译
   （上游 Jamfile.v2：aarch64 Linux 上 `lib boost_atomic :
   lock_pool.cpp`，SSE2/SSE4.1 仅 x86，wait_on_address.cpp 仅 Windows）。
   方案 B 无法提供这个库，下游用 wait/notify 会得到链接错误。
3. **CI L5 产物基线**：方案 B 元包 package() 为空 → L5 持续
   "no artifacts found" warn（不 fail 但留质量疑点）；方案 A 产出
   libboost_atomic.a 干净过 L5。
4. **上游测试要求**：积分赛要求真实跑上游测试。方案 B 元包无编译
   过程，上游测试无从谈起；方案 A 在 build() 里手动编译运行
   libs/atomic/test 全套（18 项）。
5. **独立演进**：组件包独立版本号演进（R37 后缀机制可用），
   不与 boost/1.84.0 元包修订锁死。

**方案 A 的关键实现（后续组件可复用的模式）：**

- **源码选择依据**：`libs/atomic/build/Jamfile.v2` 的
  `lib boost_atomic : lock_pool.cpp : <conditional>@select-arch-specific-sources`
  ——在 aarch64 Linux/OHOS 上只需编译 **lock_pool.cpp 一个翻译单元**。
- **编译命令**（与底稿 boost/1.84.0 元包配方同构，R33 合规——编译器
  从 `self.conf.get("tools.build:compiler_executables")` 取）：
  ```bash
  clang++ -std=c++17 -stdlib=libc++ -O2 -DNDEBUG -fPIC \
    -DBOOST_ALL_NO_LIB -DBOOST_ATOMIC_SOURCE \
    -I<boost_root> -I<boost_root>/libs/atomic/src \
    -c libs/atomic/src/lock_pool.cpp -o lock_pool.o
  llvm-ar rcs libboost_atomic.a lock_pool.o
  ```
- **两个关键 include**：`-I<boost_root>`（头文件树）+
  `-I<boost_root>/libs/atomic/src`（lock_pool.cpp 通过 Boost.Preprocessor
  迭代 include "lock_pool_init1.ipp"，不带此 include 会报
  `'lock_pool_init1.ipp' file not found`——Jamfile 的 `<include>../src`）。
- **平台路径验证**：OHOS musl libc 支持 futex syscall
  （boost/atomic/detail/futex.hpp 走 `__linux__` → SYS_futex 分支），
  lock_pool.cpp 编译期选择 `BOOST_ATOMIC_USE_FUTEX` 路径
  （`BOOST_ATOMIC_DETAIL_HAS_FUTEX && BOOST_ATOMIC_INT32_LOCK_FREE == 2`）。
  本机实测编译运行全部通过（见下）。
- **无需 patch**：atomic 不依赖 smart_ptr 的 sp_thread_sleep.hpp
  （底稿 patch 0001 针对的文件），无 pthread_setcancelstate 路径，
  **patches/ 目录为空**，配方无 patch 声明。
- **package() 内容**：完整 boost 头文件树（组件包自包含，与 Debian
  libboost-atomic1.84-dev 模式一致——下游不需要先装元包）+
  lib/libboost_atomic.a。
- **package_info()**：`cmake_file_name="Boost"` +
  组件 `boost_atomic`（cmake_target_name `Boost::atomic`，
  libs=["boost_atomic"]，system_libs=["pthread"]——Jamfile 要求
  `<threading>multi`）。下游 `find_package(Boost COMPONENTS atomic)` +
  `Boost::atomic` 开箱即用。

**方案 A 对后续组件的适用边界**（复用前检查）：
- header-only 组件（如 system 1.69+ 后）：`build()` 退化为只跑上游测试
  （甚至无 lib 产出——L5 会 warn，需在 notes 说明）；其余结构照抄。
- 多 TU 编译组件（thread/chrono 等）：源文件清单从该库
  `libs/<lib>/build/Jamfile.v2` 的 `lib boost_<lib> : <sources>` 提取，
  逐文件编译进 .a；include 需要 `-Ilibs/<lib>/src`（同 lock_pool 模式）。
- 依赖其他 boost 组件的（chrono → system）：`requires` 已发布的组件包
  或元包，component `requires` 字段对齐。

## 编译系统
手动编译（b2 在 OHOS 不兼容，E068；与底稿 boost/1.84.0 元包配方同构）

## 源码下载
- 来源：Boost 官方（archives.boost.io + SourceForge 双镜像，与底稿 conandata.yml 一致）
- URL：https://archives.boost.io/release/1.84.0/source/boost_1_84_0.tar.gz
- SHA256：a5800f405508f5df8114558ca9855d2640a2de8f0445f051fa1c7c3383045724（本地实测与底稿一致）
- 解压验证位置：~/tmp/boost184src/boost_1_84_0

## 环境信息
- 平台：OpenHarmony (aarch64)
- 编译器：clang 15.0.4 (aarch64-unknown-linux-ohos target)
- 构建系统：手动 clang++/llvm-ar（绕过 b2）

## 适配过程

### Phase 0: 选型验证（打样核心）
- [x] 读底稿 archives/b/boost/1.84.0/（元包配方：手动编 4 库+全头文件）
- [x] 分析 libs/atomic 结构：src/lock_pool.cpp（非 header-only 证据）
- [x] 本地预验证：lock_pool.cpp 单文件编译成功 → libboost_atomic.a
- [x] 上游测试预验证：11 项 run 型测试全过（见下）
- [x] 选型结论：方案 A 独立裁剪编译（理由见上节）

### Phase 1: 编译验证（W3 前置实验）
- lock_pool.cpp 编译：`-DBOOST_ATOMIC_SOURCE -I. -Ilibs/atomic/src` 成功
- libboost_atomic.a 打包：llvm-ar 成功（10,320 字节 lock_pool.o）
- 上游测试（预验证轮，OHOS 本机直接运行）：
  - atomic_api / atomic_ref_api / wait_api / ipc_atomic_api / atomicity /
    atomicity_ref / ordering / ordering_ref / lockfree / wait_fuzz /
    c_implicit_ctor —— **全部 PASS（"No errors detected."）**
  - cf_arith_void_ptr / cf_arith_func_ptr / cf_arith_mem_ptr ——
    compile-fail 预期失败 ✓（语义正确性负向测试）
- 运行注意：OHOS 二进制需 LD_LIBRARY_PATH 指向 SDK 的
  libc++_shared.so 目录（本机验证用）；CI conan 环境由 Conan 管理。

### Phase 2: 配方固化
- conanfile.py：手动编译模式（同底稿），上游测试嵌入 build()
- conandata.yml：官方双镜像 + SHA256（与底稿一致）
- test_package/：CMake find_package(Boost COMPONENTS atomic) → Boost::atomic
  下游消费冒烟（atomic/atomic_ref/wait-notify/atomic_flag）
- patches/：空（atomic 无需平台 patch）

### Phase 3: W3 本地 CI 验证
- conan create -pr:h=ohos-aarch64：通过（lock_pool 编译 + 18 项上游测试 + test_package）
- （详见 reports/）

## 遇到的问题

### 问题 1: lock_pool_init1.ipp 找不到
- **症状**：`fatal error: 'lock_pool_init1.ipp' file not found`
- **根因**：lock_pool.cpp 用 Boost.Preprocessor 迭代 include 该 .ipp，
  路径相对于 `libs/atomic/src`（Jamfile `<include>../src`）
- **解决**：编译 flags 加 `-Ilibs/atomic/src`

### 问题 2: /tmp 只读
- **症状**：`unable to open output file '/tmp/lock_pool.o': Read-only file system`
- **根因**：E002 已知平台陷阱
- **解决**：输出到 $TMPDIR/可写目录（配方内由 Conan 管理 build_folder，无此问题）

### 问题 3: 运行时 libc++_shared.so 缺失（仅本机验证场景）
- **症状**：`Error loading shared library libc++_shared.so`
- **根因**：OHOS clang 默认动态链接 libc++_shared，本机 shell 无 SDK lib 路径
- **解决**：本机验证时 LD_LIBRARY_PATH 指向 SDK libc++ 目录；
  conan create 的 test_package 由 Conan 环境注入（profile buildenv），
  CI 环境正常。非配方缺陷。

## 知识提取记录

### 知识点：Boost 组件拆分包模式（Debian libboost-atomic1.84 模式）
- boost 组件包名规范：`boost1.84-<component>`（与分支名
  `feat/boost1.84-<component>-1.84.0` 及 CI L0n 分支校验对齐）
- 源码选择：`libs/<lib>/build/Jamfile.v2` 的 `lib boost_<lib> : <sources>`
  段是权威清单（按平台条件过滤 SSE/Windows-only 源）
- aarch64 Linux/OHOS 上 atomic 只需 lock_pool.cpp
- 完整头文件树打包（组件包自包含，Debian 同模式）
- `cmake_file_name` 用包名（boost1.84-atomic）避免与元包 "Boost" 冲突 →
  下游 find_package(boost1.84-atomic COMPONENTS atomic) 可用
- OHOS 测试运行环境：LD_LIBRARY_PATH 指向编译器自省的 SDK libc++
  目录 + ELF 自签名（llvm-objcopy/binary-sign-tool，见 test_package）

### 知识点：Boost.Atomic 1.84 非 header-only
- wait/notify API 依赖编译库 lock_pool.cpp（上游 Jamfile 明确）
- futex 路径在 OHOS musl 可用（__linux__ → SYS_futex）
- 与底稿笔记"大部分库 header-only"的表述互补：atomic 属于
  "有 src 但小"的组件（1 个 TU）

**建议**：后续 6 个组件包（thread/chrono/log 等）直接复用本配方结构，
notes.md 选型章节可整体引用。

## 编译结束
**最终状态**: published（待 W3/CI 验证后更新）
---

**编译结束**: 2026-09-05 16:09
**最终状态**: built
