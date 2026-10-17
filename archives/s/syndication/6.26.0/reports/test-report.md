# syndication 6.26.0 测试报告

## 本地验证（W3，2026-09-07）

### conan create（ohos-aarch64 profile）

- RC=0，包 syndication/6.26.0 构建成功（G1/G2/G3/G4 全过）
- 上游 autotests（build() 内 ctest，沙箱化）：**3/3 通过**

| 测试 | 结果 | 耗时 |
|------|------|------|
| testpersonimpl | Passed | 0.06s |
| syndicationtest（71 feed 数据驱动：atom 28 + rdf 9 + rss2 34） | Passed | 0.20s |
| loaderutiltest | Passed | 0.04s |

### test_package（消费者视角）

- ctest：**1/1 通过**（test_syndication Passed 0.04s）
- 直跑：`PASS: parsed RSS 2.0 feed, title='KDE.news', items=2, debugInfo=608 chars`

### L1e 破坏性反向验证（R34）

- lib/ 与 include/ 分别移走后 test 失败 → 测试真实依赖被测包 ✅

### 上游测试统计（实测，find autotests tests -name "*.cpp"）

- autotests/：6 个 .cpp（testpersonimpl / syndicationtest / loaderutiltest 注册 ctest；
  testlibsyndication / benchmark 为手动工具无 add_test）
- tests/：1 个 .cpp（testloader 手动网络工具，无 add_test）
- ctest 注册 3 个全部纳入运行，全过

### 未纳入 ctest 的 .cpp 逐条说明（三选一理由：上游未注册）

| 文件 | 理由 |
|------|------|
| autotests/testlibsyndication.cpp | 命令行 feed 解析打印工具，无断言，上游未 add_test |
| autotests/benchmark.cpp | 手动基准工具（读 feed 打印耗时），无断言，上游未 add_test |
| tests/testloader.cpp | QNetworkAccessManager 在线拉取工具，需真实网络，无断言，上游 tests/ 目录无 add_test |

### L5 SONAME 门禁（非阻塞，系统级平台条件）

- `L5_RESULT=fail: soname_gate_failed`：libKF6Syndication.so 的 DT_NEEDED 记录了
  kcodecs 绝对缓存路径（/storage/.../p/lib/libKF6Codecs.so）
- 根因：OHOS 交叉编译下已发布的 kcodecs/6.18.0 包内 libKF6Codecs.so 无 DT_SONAME，
  CMake IMPORTED 目标按绝对路径链接 → 与 syndication/6.14.0（已审合入）、
  kcolorscheme 6.18.0.1 等已发布 KF6 包完全同型
- 运行时由 conan RPATH/LD_LIBRARY_PATH 部署解决，不影响构建与消费；
  Build Summary Pass rate 100.0% (1/1)，非阻塞

## 结论

- 编译状态：通过
- 上游测试通过率：3/3（100%）
- test_package 通过率：1/1（100%）
