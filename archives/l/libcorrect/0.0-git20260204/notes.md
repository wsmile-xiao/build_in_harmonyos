# libcorrect 0.0-git20260204 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，无 option() 开关）
- 编译日期: 2026-10-02
- 编译器: clang（OHOS aarch64 本机工具链 /data/service/hnp/bin/clang）
- Profile: ci/conan/profiles/ohos-aarch64（compiler=clang 15, os=OHOS 6.0, arch=armv8）
- 状态: built（零补丁）
- 上游快照: quiet/libcorrect master（无正式 release），pax 头 commit ee82e6673a806dfdf0a969b975ab36596ecc5401，成员 mtime 全部 2026-02-05 → 版本号 0.0-git20260204（仓库 master-only 上游命名规则）

## W0 依赖核验（适配前第一件事）
- 库本体: `nm -D libcorrect.so` 只见 calloc/free/malloc/memcpy/memset/printf/putchar/puts——纯 libc，无第三方依赖。
- 测试框架: 上游 tests/ 为手写 C main + CTest add_test 注册，**不用 check 框架**。按派工要求对制品仓 check 供给做了核验：`conan download "check/master" -r=ohpcd --only-recipe` 报 registry 限流（system acceleration policy not enabled），`check/0.15.2` 存在（2026-08-04 revision 6d41c307）；但本包测试不需要 check，**无裁测**，如实记录。
- libfec 互操作: 上游 `find_library(FEC fec)` 在 OHOS aarch64 无系统 libfec 时自然失败（HAVE_LIBFEC 未定义），对应互操作测试不被注册——与上游自己 GitHub CI runner 行为一致，非裁测。

## 编译步骤（W3 本地 conan create 实录）

```bash
cd archives/l/libcorrect/0.0-git20260204
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 \
               -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → 上游 4 ctest 全过（HMBS_UPSTREAM_TEST_RESULT passed, 4/4）
# → test_package 2 可执行文件全过（test_correct, test_correct_ohos）
```

配方内做对上游 CMake 的三件事：
1. `generate()`: os=OHOS 时显式 `cmake_system_name=OHOS` / `cmake_system_processor=aarch64`（E092/libaec/libbgcode 先例）。副作用是 configure 被标记为交叉——顺带跳过上游 `-march=native` SSE4.1 探测（aarch64 上本来就编不过）。
2. `build()`: `cmake.build()` 后显式构建 `test_runners` 聚合目标（上游测试可执行文件全部 EXCLUDE_FROM_ALL，这是上游 `make check` 的官方入口），再进 `tests/` 子目录跑 ctest。
3. `package()`: 删除 libfec API-compat shim（libfec.a + fec.h——上游 install OPTIONAL 会把它带进来，本包不得遮蔽真 libfec 包），并按 shared 选项只保留单变体（上游 add_library 显式 SHARED/STATIC 关键字无视 BUILD_SHARED_LIBS，两变体都会构建）。

## 对话记录

### 对话 #1 [2026-10-02] — 上游源码本机验证
- 操作: 下载 master tarball（sha256=4eb509e9...7ed54），CMAKE_SYSTEM_NAME=OHOS 配置 + make 编译 → 全过；`make test_runners` + `cd tests && ctest` → **4/4 passed，总耗时 121.74s**（convolutional 39.6s / conv-shim 62.1s / RS 7.9s / RS-shim-interop 12.2s）
- 发现: 根目录 ctest 报 "No tests were found"——上游 `enable_testing()` 在 tests/CMakeLists.txt 而非顶层（CMake 的子目录注册语义），必须在 tests/ 子目录跑。已固化进 conanfile.py 并记入知识草稿。
- 消费者验证: 手写 test.c（RS 255,223 + conv 1/2 K=7 往返）静态链接实测通过，作为 test_package/test.c 蓝本。

### 对话 #2 [2026-10-02] — 平台差异核验
- 发现: aarch64/OHOS 下上游自身平台门控生效——SSE4.1 探测失败（x86intrin.h 不存在）、libfec 探测失败（无系统 libfec），两者都是上游设计如此（上游 GitHub CI runner 同样无 libfec），SSE/libfec 条件测试不被注册，**不属于裁测**。
- 发现: 上游 .so 无 SONAME（E077 家族已知问题）→ 默认 static 规避，conanfile 注释记录。
- 断言计数（进 PR 统计表口径）: convolutional_test 24 校验点、convolutional_shim_test 12、reed_solomon_test 32、reed_solomon_shim_interop_test 16，ctest 条目口径 4。

### 对话 #3 [2026-10-02] — 配方固化 + conan create
- 操作: 按上述三件事写 conanfile.py（ctest 解析沿用 libbgcode 的 LastTest.log fail-closed 解析器），conan create 双 profile 本机验证全绿。

## 已知限制
- shared=True 时 DT_NEEDED 会烤进包路径（上游无 SONAME）——默认 static 不受影响；如后续下游要动态版，参照 E077/libaec 家族的 SONAME 处理再起 0.0-git20260204.1。
- libfec API-compat shim（上游 targets: shim / fec_shim_*）不随包发布——它是上游测试夹具 + 可选兼容层，真需要 libfec API 的消费者应直接依赖 libfec 包。
- 卷积码测试的 BER 断言依赖 rand() 序列（测试自身 srand(time(NULL))），理论上有极小概率瞬时波动——上游在 x86 CI 上同样如此，未观察到失败。
