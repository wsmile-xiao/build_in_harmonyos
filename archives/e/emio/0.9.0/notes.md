# emio 0.9.0 适配笔记

## 编译环境
- 构建系统: cmake (header-only INTERFACE target)
- 编译日期: 2026-09-03
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos, OHOS SDK 26.0.0.18)
- 状态: built

## 编译步骤

1. 官方源码: https://github.com/Viatorus/emio (tag 0.9.0 tarball, sha256 63b1eca2…d87b)
2. Conan 配方（header-only）: conanfile.py 打包 include/emio/ 头文件目录 + LICENSE，
   无依赖、无编译产物；conandata.yml 指向官方 tag 源并记录 sha256。
3. Conan 验证: `ohc-run.py conan-verify emio 0.9.0` → G1-G4/L2/L4/L5 全通过
   （conan create 干净构建 + test_package 消费者测试通过）。
4. 上游单元测试: emio_test (Catch2 v3.4.0) 141 用例运行，138 通过；
   test_format_string.cpp 4 用例被工具链 clang15.0.4 IR-gen SIGSEGV 硬阻塞（见台账）。
5. HarmonyOS 专项测试: harmonyos-test/harmonyos_emio_test.cpp 编译运行通过（arm64 ELF, exit 0）。
6. finish W3 本地 CI 模拟通过（本地提交后 incremental 模式）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 判 mixed(cargo) | 上游 test/fuzzy/dragon4/rust_ref/ 含交叉验证用 Rust cdylib 参考实现，被 lang_detect 全文件扫描当作项目 manifest | 按 R47 边界规则"辅助工具不算主体"判定：顶层 manifest 为 CMakeLists.txt、源码 98% cpp，任务语言 cpp 成立，工具误判为框架边界缺陷并记录证据 |
| 2 | G2 conan create 报 include 路径不存在 | conan copy() 不递归拷贝目录，include/emio 未进包 | package() 改用 shutil.copytree 安装 include/emio 头文件目录 |
| 3 | test_format_string.cpp 编译 SIGSEGV (exit 139) | OHOS SDK clang 15.0.4 对 emio namespace 级 constexpr 代码 IR 生成崩溃（-O0~-O3、多组 flag、Catch2 v3.4.0/v3.7.1 均复现；最小复现 min2.cpp 亦可复现，fsyntax-only 通过） | 外部工具链硬阻塞；其余 26 个测试 TU 正常编译运行，台账记录 4 用例未运行 |
| 4 | 3 个上游用例失败（tmpfile 返回 nullptr） | 系统 /tmp 为只读 erofs 挂载，glibc tmpfile() 硬编码 /tmp 不尊重 TMPDIR | 环境硬阻塞（非库缺陷）；其余 138 用例全绿 |
| 5 | W3 junk_check 拦到其他库 HEAD 基线文件（embree/flatcv/libmorton/goaccess 等 3+1 个） | 未提交时 diff 为空，junk_check 回退 full 模式扫描整仓 | 本地提交 emio 变更后 W3 走 incremental 模式只检查本 PR 文件；基线噪声哈希记录、原样未动 |

## 依赖版本

- 构建期: 无第三方依赖（header-only，零依赖）。
- 测试期: Catch2 v3.4.0 + fmt 9.1.1（仅本地上游测试用，FetchContent 拉取，不入配方）。

## 验证结果

- conan create emio/0.9.0@ohpcd/stable: 成功（G2 PASS，test_package 消费者测试通过）
- 上游 emio_test: 141 运行 / 138 通过 / 3 环境硬阻塞 / 4 工具链硬阻塞（台账: .oh-executor/emio-0.9.0-r01-upstream-test-ledger.md）
- HarmonyOS 专项测试: 编译 0 错误，运行 exit 0
- 全量通过率: 138/146 = 94.5%（实际执行 138/141 = 97.9%）

## 发现与知识

✅ emio 为 C++20 header-only 库（CMake INTERFACE target），无需编译产物；Conan 配方应声明 `package_type = "header-library"`，`package()` 用 `shutil.copytree` 安装 `include/emio/` 头文件目录（`conan.tools.files.copy` 不递归目录），`package_info()` 置空 libdirs/bindirs 并声明 `cmake_target_name = emio::emio` (knowledge_ref: emio-header-only-packaging)

✅ 上游测试目录中嵌套的辅助参考实现（如 emio 的 `test/fuzzy/dragon4/rust_ref/`，Rust cdylib 用于交叉验证 dragon4 浮点格式化）不是项目主体：语言预检（lang_detect）会因全文件扫描命中 Cargo.toml 而误判 mixed，应按 R47"辅助工具不算主体"取顶层 manifest（CMakeLists.txt）与源码占比判定 (knowledge_ref: emio-rust-ref-auxiliary)

## 注意事项

- 上游 CMakeLists project() 的 VERSION 字段滞后为 0.2.0（tag 0.9.0 为权威版本），与库无关，无需处理
- 测试运行需可写 TMPDIR（/tmp 只读），环境恢复条件：挂载可写 /tmp 后 tmpfile 相关 3 用例即可通过
---

**编译结束**: 2026-09-03 04:16
**最终状态**: built
