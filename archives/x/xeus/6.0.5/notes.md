# xeus 6.0.5 适配笔记

## 编译环境
- 构建系统: cmake (3.16+)
- 编译日期: 2026-09-29
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 上游测试入口核验（R51 三步法）

### 第一步 · 清点

xeus 6.0.5 在 `test/` 目录提供基于 doctest 的测试套件：

```
test/CMakeLists.txt       — 测试构建配置
test/test_main.cpp        — doctest 主入口
test/test_xbase64.cpp     — base64 编解码测试
test/test_xbasic_fixed_string.cpp — 固定字符串测试
test/test_xhash.cpp       — hash 算法测试
test/test_xhelper.cpp     — 辅助工具测试
test/test_xin_memory_history_manager.cpp — 内存历史管理器测试
test/test_xsystem.cpp     — 系统工具测试
test/test_unit_kernel.cpp — 内核单元测试
test/xmock_interpreter.*  — Mock 解释器
test/xmock_server.*       — Mock 服务器
```

CMake 注册 7 个测试用例（通过 `add_test`）：
- test_xbase64
- test_xbasic_fixed_string
- test_xhash
- test_xhelper
- test_xin_memory_history_manager
- test_xsystem
- test_unit_kernel

测试依赖：doctest (test framework), nlohmann_json, Threads

### 第二步 · 运行

上游测试需要 `XEUS_BUILD_TESTS=ON` 构建。由于 conan 配方默认关闭测试
（XEUS_BUILD_TESTS=OFF，减少构建时间），上游测试在单独的构建中执行：

```bash
cd archives/x/xeus/6.0.5
mkdir -p build_test && cd build_test
cmake .. -DXEUS_BUILD_TESTS=ON \
    -DCMAKE_PREFIX_PATH="$(conan info nlohmann_json/3.12.0 --paths | grep package_folder | cut -d: -f2):$(conan info libuuid/2.42.2 --paths | grep package_folder | cut -d: -f2)"
make -j2
ctest --output-on-failure
```

### 第三步 · 回填

上游测试在本地构建环境中实际执行，使用 `XEUS_BUILD_TESTS=ON` 构建配置。

```bash
cd archives/x/xeus/6.0.5
mkdir -p build_test && cd build_test
cmake .. -DXEUS_BUILD_TESTS=ON \
    -DCMAKE_PREFIX_PATH="$(conan info nlohmann_json/3.12.0 --paths | grep package_folder | cut -d: -f2):$(conan info libuuid/2.42.2 --paths | grep package_folder | cut -d: -f2)"
make -j2
ctest --output-on-failure
```

**ctest 原始输出：**

```
Test project /data/storage/el2/base/cache/xeus-upstream-test
      Start 1: test_xbase64
  1/7 Test #1: test_xbase64 ......................   Passed    0.03 sec
      Start 2: test_xbasic_fixed_string
  2/7 Test #2: test_xbasic_fixed_string ..........   Passed    0.03 sec
      Start 3: test_xhash
  3/7 Test #3: test_xhash ........................   Passed    2.72 sec
      Start 4: test_xhelper
  4/7 Test #4: test_xhelper ......................   Passed    0.03 sec
      Start 5: test_xin_memory_history_manager
  5/7 Test #5: test_xin_memory_history_manager ...   Passed    0.03 sec
      Start 6: test_xsystem
  6/7 Test #6: test_xsystem ......................   Passed    0.03 sec
      Start 7: test_unit_kernel
  7/7 Test #7: test_unit_kernel ..................   Passed    0.03 sec
100% tests passed, 0 tests failed out of 7
```

**上游测试统计：用例总数 7，通过 7，失败 0，跳过 0**

| 用例名称 | 说明 | 状态 | 耗时 |
|---------|------|------|------|
| test_xbase64 | base64 编解码测试 | ✅ Passed | 0.03s |
| test_xbasic_fixed_string | 固定字符串测试 | ✅ Passed | 0.03s |
| test_xhash | hash 算法测试 | ✅ Passed | 2.72s |
| test_xhelper | 辅助工具测试 | ✅ Passed | 0.03s |
| test_xin_memory_history_manager | 内存历史管理器测试 | ✅ Passed | 0.03s |
| test_xsystem | 系统工具测试 | ✅ Passed | 0.03s |
| test_unit_kernel | 内核单元测试 | ✅ Passed | 0.03s |

**日志路径**: `/data/storage/el2/base/cache/xeus-upstream-test/Testing/Temporary/LastTest.log`

## 编译步骤

1. 下载源码（GitHub jupyter-xeus/xeus tag 6.0.5）
2. 创建 conanfile.py 和 conandata.yml
3. 运行 conan create：
   ```bash
   conan create archives/x/xeus/6.0.5 \
       -pr:h=ci/conan/profiles/ohos-aarch64 \
       -pr:b=ci/conan/profiles/ohos-aarch64
   ```
4. 验证产物（include/xeus/*.h, lib/libxeus.a）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直接下载超时 | 网络限制 | 使用 ghfast 镜像下载 |
| 2 | CMake try_compile 失败 | lld 无法加载 libxml2.so.16 | CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY |
| 3 | CompilerWarnings -Werror 致命 | clang 15 部分转换警告 | XEUS_WARNING_AS_ERROR=OFF |
| 4 | shared library SONAME 问题 | OHOS rpath 限制 | 仅构建 static library |

## 源码修改

无补丁。上游 CMakeLists.txt 交叉编译干净，仅需 CMake 变量调整。

## 依赖版本

- nlohmann_json: 3.12.0
- libuuid: 2.42.2
- doctest (tests only): 2.4.11

## 验证结果

```
conan create archives/x/xeus/6.0.5 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
  xeus/6.0.5: Package folder: .../p
  xeus/6.0.5: Libraries: ['xeus']
  xeus/6.0.5: Package 'xeus/6.0.5' created
```

## 交付物

| 文件 | 说明 |
|------|------|
| include/xeus/*.h | 公共头文件（xinterpreter, xmessage, xjson, xbase64, xhash 等） |
| lib/libxeus.a | 静态库 |
| lib/cmake/xeus/ | CMake 配置文件 |
| licenses/LICENSE | BSD-3-Clause 许可证 |

## 注意事项

- nlohmann_json 版本必须与构建时一致（find_dependency 要求精确匹配）
- 仅构建 static library（shared 在 OHOS 上有 SONAME/rpath 问题）
- 测试套件需要单独构建（XEUS_BUILD_TESTS=ON）
---

**编译结束**: 2026-09-29 10:52
**最终状态**: built

### 对话 #3 [2026-09-29] 提交前审计修复：鸿蒙测试去断言化

- 问题：提交前只读审计发现 test_ohos_xeus.cpp 含 15 处 assert()，违反「新增鸿蒙特有测试不能是断言」规则；且 Release 构建（NDEBUG）下 assert 全部为空操作，旧 2/2 PASS 属虚通过，未真正校验任何行为。
- 操作：
  1. 照 audio-resampler 0.7 先例模式重写 test_ohos_xeus.cpp：9 个检查点全部改为 `if (异常) { fprintf(stderr, ...); return 1; }` + 结尾 `printf("OHOS PASS: ...")`，0 处 assert。
  2. 手动编译调试（clang++ + libxeus.a + libuuid.a）定位真实语义：is_complete_request_impl 对非空代码返回 "unknown"（桩实现），据此将检查改为空代码→complete、非空代码→unknown，9 检查点全绿 EXIT=0。
  3. 修正 manifest.yaml 过时统计（upstream_passed 0→7、upstream_skipped 7→0、test_passed 0→9）。
  4. 重跑 conan create（EXIT=0，test_xeus_consumer PASS + test_ohos_xeus OHOS PASS）→ 重跑 finish（conan-verify G0–G4 PASS、W3 全 pass、.ci-result.json 重新生成 exit_code=0）。
- 结果：门禁全绿。审计中另发现 CONAN_HOME 内存在陈旧全局 profile（profiles/ci/conan/profiles/ohos-aarch64，gcc15/无 os.version），相对路径解析失败时会误命中，跑 conan 必须用 profile 绝对路径。
- 日志：/data/storage/el2/base/cache/xeus-conan-create-final.log、/data/storage/el2/base/cache/xeus-finish-final.log、reports/conan-verify-report.md、reports/w3-local-ci.log

### 对话 #4 [2026-10-06] AI 审查修复（atomgit-bot 代码检视 3 项）

- conandata.yml（P2）：网页端应用建议时产生了重复 `url:` 键的损坏 YAML（PyYAML 后键覆盖碰巧可解析）；修正为单键、仅官方 GitHub 源（镜像 fallback 由 CI 自动注入）。
- test_xeus_consumer.cpp（P2）：原校验全靠 assert，Release/NDEBUG 下为空操作、测试形同空壳；改为显式检查（kernel_info 实现名 + execute_request 回调触发与 status==ok），失败 fprintf(stderr)+return 1，0 处 assert。
- test_ohos_xeus.cpp（P3）：删除 make_unique 之后不可达的 `if (!kernel)` 空指针判断（make_unique 失败抛异常而非返回空）。
- 重验：conan create EXIT=0（logs: /data/storage/el2/base/cache/xeus-conan-create-review-fix.log），test_xeus_consumer 与 test_ohos_xeus 均实际执行并 PASS（OHOS PASS 行正常输出）。

### 对话 #5 [2026-10-10] 人工审查 rule4 少报修复（口径修正）

- 审查裁决：上游实测 N=64 > 声明 N=7 → 少报 FAIL。实测口径为 doctest TEST_CASE，我们声明的 7 是 ctest 可执行文件数。
- 取证：LastTest.log 各二进制 doctest 汇总行 —— xbase64=2, xbasic_fixed_string=36, xhash=2, xhelper=11, xin_memory_history_manager=3, xsystem=2, unit_kernel=8，合计 64，64 全过 0 失败 0 跳过（与审查实测完全一致，测试真实性不受影响，纯属声明口径错误）。
- 修复：manifest test_results upstream_total 7→64（附口径注释与各二进制用例分布）、test_passed 9→66；PR 正文两张统计表与通过率同步改为 64/66 口径，补充说明注明口径差异。
- 经验：声明用例数必须用「用例」口径（doctest TEST_CASE / ctest Test 数），不能用「测试可执行文件」数，rule4 实测一律按用例算。
