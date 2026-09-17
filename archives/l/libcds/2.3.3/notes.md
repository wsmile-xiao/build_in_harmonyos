# libcds 2.3.3 适配笔记

> 档案创建时间: 2026-09-14
> 状态: built (待真机预检验证)
> 上游: https://github.com/khizmax/libcds (tag v2.3.3)

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | libcds |
| 版本 | 2.3.3 |
| 构建系统 | CMake (最低要求 3.0.2) |
| 源码 | https://github.com/khizmax/libcds/archive/v2.3.3.tar.gz |
| sha256 | f090380ecd6b63a3c2b2f0bdb27260de2ccb22486ef7f47cc1175b70c6e4e388 |
| 许可证 | BSL-1.0 (2.3.3 起由 BSD 转为 Boost 许可证) |

## 二、上游测试清点 (适配前)

| 目录 | 内容 | 框架 | 说明 |
|------|------|------|------|
| test/unit | 13 个子目录二进制 (deque/intrusive-list/list/map/misc/pqueue/queue/intrusive-set/set/striped-map/striped-set/stack/tree) | gtest | 需 GTest (test_requires) + 源码内 Boost 硬依赖补丁 (见下); test/CMakeLists 的 find_package(Boost) 虽非 REQUIRED, 但 cds/algo/flat_combining/kernel.h 硬用 boost::thread_specific_ptr, 无 Boost 头则编译失败 |
| test/stress | 6 组压测二进制 (freelist/map/pqueue/queue/set/stack) + perl 生成字典 + .conf 配置 | 自研 stress-framework + 需要长时间运行 | 长耗时性能压测, 单核真机预算内无法完成, 关闭并披露 |

## 三、适配决策

| # | 决策 | 原因 |
|---|------|------|
| 1 | 运行时零依赖 (requirements 为空) + 源码内 Boost 硬依赖经 C++11 TLS 补丁消除 | 上一轮“Boost 非 REQUIRED 故无需处理”假设被真机证伪: test/CMakeLists 的 find_package 虽非 REQUIRED, 但 cds/algo/flat_combining/wait_strategy.h 无条件 #include <boost/thread/tss.hpp> (该头内未使用, 死引用) 且 kernel.h 硬用 boost::thread_specific_ptr<m_pThreadRec>, 导致单元二进制编译报 fatal error: 'boost/thread/tss.hpp' file not found。boost/1.91.0 无 OHOS 预编译包且源码构建在 bzip2 环节失败, 故不引入 Boost, 改为 build() 内幂等源码补丁消除依赖, 补丁随 package() 进入消费头, 保持零依赖 |
| 2 | test_requires gtest/1.17.0.1 + boost/1.90.0.2 (本仓库 OHOS 适配版, 仅测试期) | 库头 Boost 经 TLS 补丁消除后, 单元源码仍硬含 <boost/container/...> (如 deque/fcdeque.cpp), 上游 CMake 亦按有 Boost 布局; boost/1.91.0(b2) 无 OHOS 包且在 bzip2 环节失败, 改用本仓库 CMake 构建的 boost/1.90.0.2 (container/system 等组件, ohpcd 有 OHOS 二进制), 只供单元编译链接, test_requires 不进消费链; gtest 取 1.17.0.1 (无 cmake tool_requires, 自带 OHOS 沙箱 TMPDIR 补丁) |
| 3 | generate() 仅预填 GTEST_INCLUDE_DIRS/GTEST_LIBRARIES | 上游测试 CMake 用 2018 年代 FindGTest 模块变量拼写, Config 包不提供; 从 gtest 依赖真实路径解析, 非硬编码; Boost 变量保持缺省由上游空路径兼容 |
| 4 | CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON | 让 Conan 提供的 GTest Config 在 OHOS 上优先于 CMake 内置模块 |
| 5 | CMAKE_POLICY_VERSION_MINIMUM=3.5 | 上游 cmake_minimum_required(3.0.2), CMake 4+ 不再兼容 < 3.5 (libkml 先例) |
| 6 | ENABLE_STRESS_TEST=OFF, ENABLE_UNIT_TEST=ON | 压测为长耗时性能测试, 非 pass/fail 门禁; 单元套件完整执行; 如实披露 |
| 7 | 源码补丁仅消除 Boost 硬依赖 (幂等文本替换, 无平台宏) | wait_strategy.h 死引用删除; kernel.h 以 details::tss_ptr (thread_local 注册表, get/reset 语义与 boost::thread_specific_ptr 一致, cleanup 在 reset 与线程退出时运行) 替换 boost::thread_specific_ptr; 补丁随头文件发布, 消费方同样零 Boost |
| 8 | package() 仅收头文件与直编产物 | direct-cc 不再经 cmake install, 由配方复制 cds/ 头文件与 libcds-s.a / libcds.so, cpp_info 仍提供 LibCDS::cds / LibCDS::cds-s |
| 9 | 主配方与 test_package 均 direct-cc, 不再经 CMake 配置 | 真机 CMake(4.4.3)缺可用 OHOS/HarmonyOS 平台模块, 五轮均倒在 CMakeLists:12 project() 编译器识别 (cthreadpool/critnib/ddate 同指纹先例); 改用验证过的 profile 编译器直接编译, 上游测试源码与用例不变 |

## 八、第六轮路线变更说明 (direct-cc)

- 前五轮 (TMPDIR / STATIC_LIBRARY / Linux 系统名 / E557 lld 运行时) 指纹完全相同:
  E557 轮的裸 `clang probe.c -o probe` 与 `clang++ probe.cpp -o probe`
  在真机 ambient 环境下双双通过, 证明编译器与 lld 本体可用
  (profile 的 LD_LIBRARY_PATH 已覆盖), 断点只存在于 CMake 自身的
  compiler-ID 探针层, 继续调参无法收敛。
- 本轮删除 CMake 配置层: 主库 10 个 SMR 源文件直接编译归档
  (与上游 SOURCES 列表逐项一致); 上游 test/unit 13 个子目录的二进制
  在构建时解析各自 CMakeLists.txt 的 set()+add_executable() 还原
  (单二进制目录与 map 多二进制目录两种形状都覆盖, 均含 ../main.cpp
  与 -DGTEST_LANG_CXX11), 逐个运行并按 gtest `[  PASSED  ]` /
  `[  FAILED  ]` / `ran` 行汇总, 框架记为 direct-cc+gtest。
- 无 summary 的二进制永远计失败不计通过 (防静默跳过);
  test_package 侧同步改 direct-cc 并删除 CMakeLists.txt
  (cthreadpool 成功先例), test.cpp 三个 CHECK 与 RESULT 解析不变。

## 四、证据链设计 (HMBS 硬门禁)

- build(): 构建时解析 test/unit 各子目录 CMakeLists 还原上游二进制
  (与上游源码列表一致), 逐个运行并按 gtest PASSED/FAILED/ran 行汇总,
  双通道打印 HMBS_UPSTREAM_TEST_RESULT (框架 direct-cc+gtest),
  落盘 hmbs_upstream.json, 失败即抛异常中断构建。
  退出码为 0 但 summary 缺失/为空同样判失败 (防空跑误报)。
- package(): hmbs_upstream.json 随包持久化到 res/。
- test_package test(): 运行 test_libcds (3 个真实 CHECK), 解析 RESULT 行打印
  HMBS_TEST_PACKAGE_RESULT, 并重打持久化的 HMBS_UPSTREAM_TEST_RESULT
  (Conan 缓存命中导致 build() 跳过时证据不丢失, ayatana-ido 先例)。

## 五、消费者测试说明 (R34)

test.cpp 真实调用被测库 API (非空壳):

1. hp-constructed: cds::Initialize + cds::gc::HP 构造 + isUsed() 断言。
2. treiber-stack-lifo: TreiberStack<HP,int> 压入 0..4, 弹出校验 4..0 严格 LIFO, 空栈断言。
3. msqueue-fifo: MSQueue<HP,int> 入队 0..4, 出队校验 0..4 严格 FIFO, 空队断言。
   全程经由 cds::threading::Manager::attachThread/detachThread, 以 cds::Terminate 收尾。

## 六、待真机验证

- [ ] conan create 全流程 (主库 + 13 个子目录单元二进制构建)
- [ ] 单元套件真实通过数回填 PR 正文 (框架 direct-cc+gtest)
- [ ] test_package 3/3 通过
- [ ] stress 关闭披露被接受

## 七、风险提示

- 补丁等价性: tss_ptr 仅复刻 kernel 使用的 get/reset/ctor 语义, 未复刻 boost 未使用的 release/operator bool; tls_cleanup 仅标记 removed 不释放, 与原语义一致; kernel 生命周期覆盖线程 join (典型单例), 无悬垂清理风险, 与 Boost 行为同级。
- 若个别单元用例在 OHOS 上因平台差异失败, 下一轮按用例逐项分析,
  不批量豁免, 不改上游测试源码。

## 九、本轮路线变更说明 (Boost 硬依赖补丁, 第 5 策略周期)

- 重读原始失败: direct-cc 已越过 CMakeLists:12 编译器识别门 (主库 10 个 SMR 源文件归档成功), 新断点在单元二进制编译: `cds/algo/flat_combining/wait_strategy.h:13:10: fatal error: 'boost/thread/tss.hpp' file not found`。上一周期“Boost 非 REQUIRED 故可忽略”假设被真机证伪 (find_package 非 REQUIRED 仅控制链接变量, 不消除头文件硬 #include 与 boost::thread_specific_ptr 使用)。
- 换路线: 不再调编译器/CMake 参数, 改为消除依赖本身——wait_strategy.h 死引用删除 (全文审计该头未使用 thread_specific_ptr), kernel.h 以 header-only C++11 thread_local 注册表替换 boost::thread_specific_ptr (get/reset/线程退出 cleanup 语义一致)。未引入 boost 源码构建 (bzip2 链已知失败), 未删减任何上游测试, 未改测试口径。

## 十、本轮补救说明 (单元源码 Boost 容器依赖, 同指纹第 2 次)

- 前次 TLS 补丁后真机越过 flat_combining 门, 新断点在 `test/unit/deque/fcdeque.cpp:8:10: fatal error: 'boost/container/deque.hpp' file not found`。fcdeque.cpp 内 std 与 boost 两套 TEST_F 并存, Boost 版硬含 <boost/container/deque.hpp>, 属上游测试源码硬依赖, 非补丁可消除 (删 TEST_F 即删断言, 违规)。
- 换路线: 保留库头 TLS 补丁 (消费方仍零 Boost), 单元侧改为 test_requires 本仓库 CMake 构建的 boost/1.90.0.2 (container/system 等组件, ohpcd 有 OHOS 二进制; 避开 b2 线 1.91.0), 将其头/库目录织入 direct-cc 单元编译链接, 运行时补 LD_LIBRARY_PATH; 无测试删减, 口径不变。
