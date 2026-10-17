# osrm-backend 26.5.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 3.18+，设备 cmake 4.1.2）
- 编译日期: 2026-09-12
- 编译器: clang/clang++ 15.0.4（OHOS SDK，-stdlib=libc++，C++20）
- 状态: built（conan-verify G0-G4 全部 PASS，2026-09-12 conan-verify70）

## 编译步骤

1. W0 依赖核对：fmt/rapidjson/sol2/tbb/lua/libarchive/boost 等制品仓均已发布；flatbuffers 25.12.19 与 libosmium 2.23.0 由本任务依赖拓扑先行适配（各自独立 PR）
2. `conan create` 交叉构建（profile ohos-aarch64，BUILD_SHARED_LIBS=OFF，--build=missing），15 个直接依赖
3. test_package：消费者程序 13 项真实 API 断言 + osrm-extract --version 契约
4. 上游测试：解析 CTestTestfile 注册表，显式 `cmake.build --target` 构建 14 个 *-tests 可执行文件并逐个 `--log_level=test_suite` 运行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | package_info 阶段报 direct dependency 未使用 | conan 2.29 对 cpp_info.requires 双向校验：直接依赖缺一不可；override=True 声明不建图边不能入列 | cpp_info.requires 列全 14 个非 override 直接依赖；zlib 保留 override=True 仅做版本解析（详见图谱草稿 DRAFT-conan-cppinfo-requires-override-duality） |
| 2 | 测试可执行文件未构建（executables=0） | 上游 add_test 注册但 EXCLUDE_FROM_ALL，不在默认 ALL 目标 | 配方 build() 解析 CTestTestfile 提取 14 个目标名，逐个显式 --target 构建 |
| 3 | 消费者/测试可执行运行时缺 libtbb/libarchive | 共享传递依赖在 conan 缓存，VirtualRunEnv 不聚合全图组件 libdirs | test() 与 build() 显式构造 LD_LIBRARY_PATH 并注入 os.environ 传播给嵌套 make |
| 4 | 87 个测试成员 TU 链接期框架符号重复 | 上游将 <boost/test/unit_test.hpp> 广泛包含，改 included 模式时成员 TU 重复编译框架 | 0005 补丁：成员 TU 回退非 included 声明头，仅 10 个 BOOST_TEST_MODULE 主 TU 保留 included |
| 5 | std::countl_zero/popcount/atomic_ref 缺失 | OHOS libc++15 标准库覆盖不足 | 0002/0003/0004 补丁：__builtin_clzll/__builtin_popcountll/__atomic_compare_exchange_n 回退，保留原语义 |
| 6 | test-data 步骤 md5sum.js 崩溃（V8 Check failed） | 设备 node v26.8.1 在 musl/OHOS 不可用 | 0006 补丁：md5 校验改系统 md5sum，去除 timer.js 包装 |
| 7 | storage-tests dev/shm 用例失败 | OHOS /dev/shm 为 namefs tmpfs，非特权进程 mkdir EACCES；实现正确回退 HOME，测试硬断言 /dev/shm | 0007 补丁：用例增加 /dev/shm 可写性探测，不可写时 BOOST_TEST_MESSAGE 跳过（计入跳过账），真 Linux 语义不变 |

## 源码修改

补丁清单（conandata.yml，全部 portability）：
1. patches/0001-boost-components-test-headers-libarchive-target.patch — 裁剪未用 boost 组件、测试主 TU 改 Boost.Test included 模式、LibArchive 目标名对齐 CMakeDeps
2. patches/0002-msb-countl-zero-fallback.patch — msb() builtin 回退
3. patches/0003-popcount-builtin-fallback.patch — bit_range size() builtin 回退
4. patches/0004-atomic-ref-builtin-fallback.patch — compare_and_swap builtin 回退
5. patches/0005-test-member-non-included.patch — 测试成员 TU 回退非 included，消除框架符号重复
6. patches/0006-testdata-makefile-node-free.patch — test/data Makefile 去 node 依赖
7. patches/0007-shm-lockdir-ohos-skip-probe.patch — dev/shm 锁目录用例平台可写性探测

## 依赖版本

flatbuffers/25.12.19、libosmium/2.23.0、boost/1.84.0、tbb、fmt、lua、sol2、rapidjson、protozero、vtzero、expat、bzip2、lz4、libarchive、zlib（override 统一 1.3.1.1）

## 验证结果

```bash
# 上游测试（Boost.Test 14 套件逐个运行，exit code 判定）
UPSTREAM LEDGER executables=14 cases_executed=407 cases_failed=0
# 分套件：contractor5 customizer3 engine40 extractor30 library-contract1 library-customize1
#         library-extract8 library-partition1 library-tests108 partitioner26 server16
#         storage24 updater5 util139
# 消费者测试
test_osrm_backend consumer: OK (13 checks)
osrm-extract --version → 26.5.0 ✓
# 官方门禁
conan-verify: G0/G1/G2/G3/G4 全部 PASS（conan-verify70）
```

## 测试口径（四维账本）

- N_static = 398（tag v26.5.0 源码 BOOST_*_TEST_CASE 静态逐项统计；分目录 util129 library119 engine40 extractor30 partitioner26 storage25 server16 contractor5 updater5 customizer3）
- N_executed = 407 实例次（数据集驱动用例按数据行多次执行，util-tests 139 = 注册 129 + 数据集 10 行）
- 失败 0；条件跳过 1（storage get_lock_dir_uses_dev_shm_on_linux，OHOS /dev/shm namefs 限制，见 #7）
- library 组守恒：library-tests108 + extract8 + contract1 + customize1 + partition1 = 119 = 静态 library 目录注册数
- N_consumer = 1（test_package 消费者程序，13 项断言）

## 注意事项

- conan 2.29.1 每次create 使用随机新构建目录，无增量续编；G2 的 3600s 超时在共享设备高负载下无法容纳含全量测试套件的冷构建，需预热缓存后跑官方 conan-verify（构建日志存 reports/conan-create-full.log）
- /dev/shm 不可写是 OHOS 全局环境特征，任何依赖 /dev/shm 的上游测试都会命中
- 设备 node 在 musl 上不可用，上游脚本层 node 依赖（md5sum.js/timer.js）需替换为 POSIX 工具
---

**编译结束**: 2026-09-12 19:39
**最终状态**: built
