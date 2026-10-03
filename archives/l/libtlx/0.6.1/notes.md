# libtlx 0.6.1 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists，4.1.2 驱动）
- 编译日期: 2026-10-02
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos 目标，OHOS SDK 26.0.0.18）
- 设备: HarmonyOS PC（aarch64，本机原生）
- 状态: built（本地 conan create + 上游测试全绿）

## 软件形态

libtlx（上游名 tlx）= **header-only 为主（183 个 .hpp）+ 少量编译库（47 个 .cpp → libtlx.a）**。
编译单元覆盖：string 算子族（base64/escape/hexdump/split/ssprintf/trim 等 36 个）、
digest 四族（md5/sha1/sha256/sha512）、logger/core、multi_timer、thread_pool、
timestamp、port/setenv、algorithm/parallel_multiway_merge、cmdline_parser、
backtrace（OHOS 下空实现）、die/core。
上游默认 TLX_BUILD_STATIC_LIBS=ON / TLX_BUILD_SHARED_LIBS=OFF，本配方跟随（static-library）。

## 编译步骤

1. 源码：conandata.yml 官方 GitHub tag tarball（v0.6.1，sha256=24dd1acf…dad769）
2. 补丁：0001-cmake-min-version-for-cmake4.patch（唯一补丁，见下）
3. 本机 conan create：
   ```bash
   conan create . -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 \
     -pr:b=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 \
     --build=missing -c tools.build:jobs=2
   ```
4. 上游测试（设备端原生构建真跑）：
   ```bash
   cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DTLX_BUILD_TESTS=ON \
     -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++
   make -j2        # 51 个目标全部编译成功（41 测试 + 6 build_only + libtlx.a）
   ctest           # 需 LD_LIBRARY_PATH=<ohos-sdk>/llvm/lib/aarch64-linux-ohos → 41/41 全绿
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake configure 直接报错拒配 | 上游 `cmake_minimum_required(VERSION 2.8.12)`，CMake 4.x 已移除 <3.5 兼容 | 补丁 bump 为 `3.5...3.22`（知识库 E103 同结论，与 2026-06 历史归档 archives/t/tlx 踩坑记录一致） |
| 2 | ctest 首轮 41/41 全 Failed | 测试二进制动态链接 libc++_shared.so，设备默认搜索路径不含 ohos-sdk 运行库目录 | `export LD_LIBRARY_PATH=<ohos-sdk>/llvm/lib/aarch64-linux-ohos` 后 41/41 全绿；属运行环境问题非代码问题 |
| 3 | cmake --build 不识别 -j2/--parallel 参数 | 本机 CMake 4.1.2 的 OpenDesk 环境包装差异 | Makefile 生成器直接 `make -j2` 绕过 |
| 4 | CMake configure 打印 "System is unknown to cmake"（HarmonyOS 未注册平台） | CMake 官方平台列表无 HarmonyOS | 无害警告，Threads/Pthread 检测正常通过，不影响构建 |

## 源码修改

- **patches/0001-cmake-min-version-for-cmake4.patch**：CMakeLists.txt 第 11 行
  `cmake_minimum_required(VERSION 2.8.12)` → `cmake_minimum_required(VERSION 3.5...3.22)`。
  唯一修改，1 行 diff，标准 a/ b/ 前缀，patch -p1 干净应用已验证。

## 平台可移植性核验（W0-3）

- 交付头树 grep ISA 专属头/内联汇编：0 命中
- backtrace.cpp glibc execinfo 路径：上游自带 `#if defined(__GNU_LIBRARY__)` 守卫，
  OHOS musl 下自动降级 `TLX_HAVE_BACKTRACE_FUNC=0`（空实现），无需补丁
- siphash_sse2 仅 x86 SSE2 路径，由上游 `#if defined(__SSE2__)` 守卫，aarch64 自动跳过
- 无 .S 汇编、无 arch 目录、无 glibc 专属头（features.h 检测在守卫内）

## 依赖版本

- 零 conan 依赖（requires/tool_requires 均空）
- 上游唯一硬依赖 pthread（find_package(Threads REQUIRED)；musl libc 集成）
- 可选 boost 组件：上游 CMake 零引用（grep boost 无命中），不引入
- cmake 4.1.2 / clang 15.0.4 / make 4.4.1

## 验证结果

```bash
# 上游测试（41 个 ctest 目标，设备端真跑）
$ ctest
100% tests passed, 0 tests failed out of 41
Total Test time (real) =  30.97 sec

# 消费者探针（静态 libc++ 链接，本机验证）
$ ./consumer_probe
900150983cd24fb0d6963f7d28e17f72      # tlx::md5_hex("abc") ✓（与 python hashlib 一致）
ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad  # sha256 ✓
5:usr                                  # tlx::split('/', "/usr/bin/test/") ✓
1                                      # btree_set::count ✓
1 1                                    # LruCacheSet exists/size ✓

# conan create（详见 reports/ 与 .ci-result.json）
libtlx/0.6.1: Package created + test_package 消费者测试通过
```

## test_package 设计要点

- **静态 libc++ 链接（-static-libstdc++）**：消费者二进制免 LD_LIBRARY_PATH 直跑，
  CI 干净环境无运行库路径依赖（本机已实测 exit 0；动态链接版本在无
  LD_LIBRARY_PATH 时报 "Error loading shared library libc++_shared.so"）
- consumer.cpp：digest 四族已知答案向量（RFC 1321/6234 标准向量 + python
  hashlib 交叉验证）、string 算子族、btree_set/btree_map、LruCacheSet/Map、
  RingBuffer、ThreadPool、Delegate、ssprintf、CountingPtr、SplayTree、
  sort/parallel_mergesort、multiway_merge、TLX_VERSION 宏断言
- ohos_special_test.cpp：`#ifdef __OHOS__` 真实逻辑（非空壳）——OHOS 宏探针、
  字节序/位宽、静态库符号链接完整性、线程（pthread musl）、文件系统路径行为

## 注意事项

- 本配方包名 libtlx（archives/l/libtlx/），与 2026-06 历史归档 archives/t/tlx/0.6.1
  （file:// 源、无 conanfile、测试未启用）不同：本次为正式 conan 配方交付，
  官方 URL + sha256 + 上游测试真跑统计
- 上游 install(EXPORT tlx-targets) 导出目标无 NAMESPACE：CMakeDeps 消费侧
  `find_package(tlx)` + `tlx::tlx`（conan 生成）；pkg-config 名 tlx
- 交付物 libtlx.a 约 5.6M + 183 个头文件；无 bin 可执行 → 库类型，无 commands.json

**编译结束**: 2026-10-02
**最终状态**: built
