# robin-map 1.3.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE 库）
- 编译日期: 2026-09-04
- 编译器: OHOS Clang 15.0.4（设备原生，host=build=OHOS aarch64，无交叉）
- CMake: 4.1.2（设备 /data/service/hnp）
- 状态: built

## W0/W0b 与知识库使用记录

- W0 依赖预检：robin-map 无运行时依赖，preflight_check.sh 通过；测试依赖
  Boost 1.86.0 源码头文件由 conandata.yml test_sources 直接下载并校验 SHA256，
  不依赖 Conan 制品仓。
- W0b 历史核验（两点均已逐项比对遵循）：
  - archives/t/tsl-robin-map/1.3.0/（同源码同版本，已验证）：配方骨架、
    header-only Boost.Test 补丁、CMAKE_POLICY_VERSION_MINIMUM=3.5
    （上游 cmake_minimum_required 3.3 与 CMake 4.x 兼容性）。
  - archives/r/robin-map/1.4.1/（同名不同版本）：canonical 名打包方式
    （cmake_find_mode=none + 上游 tsl-robin-map Config.cmake）、R32/E092
    OHOS 映射、-static 测试链接。
  - 两份历史均为设备原生工具链可迁移环境，本机实测确认可迁移。
- 语言预检 lang-preflight：cpp 100% 匹配（5 个源文件全为 C++）。

## 编译步骤

1. `init-build` 下载官方 v1.3.0 tarball（SHA256 a8424ad3…与 tsl-robin-map/1.3.0 一致）
2. `conan create`：CMakeToolchain 配置 → `cmake --build` → `cmake --install`
   （1.3.0 顶层配置时 IS_SUBPROJECT=FALSE 自动启用 install；无
   TSL_ROBIN_MAP_ENABLE_INSTALL 选项，该选项为 1.4.x 新增）
3. 嵌套构建 tests/（Boost.Test 头文件模式，-isystem 引入 Boost，
   -DBOOST_DISABLE_THREADS），静态链接 `tsl_robin_map_tests`
4. 设备原生执行上游测试 `--log_level=test_suite`
5. test_package：find_package(tsl-robin-map) + tsl::robin_map 消费者测试

## 测试统计（四口径）

| 口径 | 数值 |
|------|------|
| 上游源码静态声明 | 65（57 BOOST_AUTO_TEST_CASE + 8 BOOST_AUTO_TEST_CASE_TEMPLATE，4 个测试套件） |
| 实际执行（Boost.Test 展开实例） | 132 |
| 通过 / 失败 / 跳过 | 132 / 0 / 0（`*** No errors detected`） |
| 新增消费者测试 | 1（robinmap_test，3 个显式断言） |

说明：8 个模板用例按类型参数在运行时展开，65 个静态声明对应 132 个
执行实例；与 tsl-robin-map/1.3.0、robin-map/1.4.1 的执行数 132 一致。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首次 G2 失败：Patch file does not exist | 归档补丁文件遗漏未提交 | 从 tsl-robin-map/1.3.0 复制同源码补丁（cmp 逐字节一致） |
| 2 | CMake 4.x 拒绝 cmake_minimum_required(3.3) | CMake >=4.0 移除 <3.5 兼容 | CMAKE_POLICY_VERSION_MINIMUM=3.5（继承 tsl-robin-map/1.3.0） |
| 3 | Boost 头文件触发 -Wold-style-cast -Werror | 上游将严格警告用于测试 TU | 补丁切换 header-only Boost.Test + -isystem（继承） |
| 4 | Boost 引用 pthread_setcancelstate | OHOS pthread 无线程取消 API | BOOST_DISABLE_THREADS（继承） |

## 源码修改

应用 `patches/0001-use-header-only-boost-test.patch`（portability）：
tests/CMakeLists.txt 移除预编译 Boost::unit_test_framework 链接，
tests/main.cpp 改用 `<boost/test/included/unit_test.hpp>`；不改测试逻辑与断言。

## 依赖版本

- 运行时依赖：无（纯头文件库）
- 测试依赖：Boost 1.86.0 源码头文件（SHA256 校验）

## 验证结果

```bash
ohc-run.py conan-verify robin-map 1.3.0   # G0-G4 + L2/L4/L5 全部 PASS
# 上游 Boost.Test：132/132，*** No errors detected
# test_package：robinmap_test PASSED（1 -> one / 2 -> two）
```

## 注意事项

- 双名说明：同一上游源码 1.3.0 已有 tsl-robin-map/1.3.0（PR #7520）；本包
  按 Conan Center 规范名 robin-map 补齐 1.3.0（robin-map/1.4.1 PR #2952
  已确立双名并存先例）。conan 引用名 robin-map/1.3.0，CMake 包名仍为
  上游 tsl-robin-map / tsl::robin_map，与 Homebrew、nanobind 下游一致。
- 库类型，无 commands.json（R38）。
- make jobserver mkfifo 告警为设备 HMDFS 限制，make 已回退正常构建，不影响结果。
---

**编译结束**: 2026-09-05 00:23
**最终状态**: built

## 路径 B 判断与知识库使用记录

- 判断时点：第一次真实构建（conan create 全绿）后。
- 本适配的技术要点（E092 映射、R32 平台判断、BOOST_DISABLE_THREADS、
  CMAKE_POLICY_VERSION_MINIMUM、header-only Boost.Test 补丁）全部已存在于
  知识库/历史归档（tsl-robin-map/1.3.0、robin-map/1.4.1），无新增可复用知识。
- 过程中遇到"JC5 full 模式整仓扫描命中无关库基线垃圾阻塞 W3"（上游
  2026-09-03 合入的 util-linux-login/.ci-trigger），查重命中已有草稿
  knowledge/drafts/DRAFT-jc-full-scan-baseline-noise-exemption.kv
  （同错误签名 JC5/blocked_by_JC/full 模式，已含两次验证实例），按查重
  规则不重复立项，路径 B 不触发。
- 本次处置采用同草稿 fallback 层级允许的替代方案：生成仓库根 pr.diff
  模拟 CI checkout-pr 的 prdiff 范围（junk_check 最高优先源），仅覆盖本
  PR 的 9 个交付文件；全程未修改、未清理、未提交无关库文件，符合该草稿
  forbid 条款（不把他人库/框架改动混入当前 PR）。
- 遗留框架问题（非本 PR 范围）：util-linux-login/.ci-trigger 未登记
  JC5_ALLOWED，建议框架维护者单独处理。
