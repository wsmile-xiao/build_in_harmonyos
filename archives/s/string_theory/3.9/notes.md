# string_theory 3.9 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE 库）
- 编译日期: 2026-09-02
- 编译器: clang/clang++ 15.0.4（/data/service/hnp/bin，aarch64-unknown-linux-ohos）
- 状态: published

## 编译步骤

```bash
# 1. 源码获取（官方 GitHub tag 3.9）
curl -fL -o string_theory-3.9.tar.gz https://github.com/zrax/string_theory/archive/refs/tags/3.9.tar.gz
sha256sum string_theory-3.9.tar.gz   # 9bb0a9697319964479f813d9c61e3c5a1f57f7e8a5bc6db14cba7489addc3f49

# 2. 探索性编译（OHOS 工具链，生成 st_config.h，验证编译）
cmake -DST_BUILD_TESTS=OFF -DCMAKE_SYSTEM_NAME=Linux ${BUILD_SRC_DIR}

# 3. 上游测试套件（gtest 从 GitHub FetchContent，CI 禁连；本地用缓存 gtest 源码构建运行）
cmake -DST_BUILD_TESTS=ON -DFETCHCONTENT_SOURCE_DIR_GTEST=<本地gtest源> ${BUILD_SRC_DIR}
cmake --build . --target st_gtests && ./test/st_gtests   # Debug 112/112 过，Release 111/112

# 4. 配方与验证
python3 scripts/ohc-run.py conan-verify string_theory 3.9   # G1-G4 全过
python3 scripts/ohc-run.py finish string_theory 3.9 published  # W3 local CI 通过

# 5. 鸿蒙专项测试（OHOS 工具链直接编译运行）
/data/service/hnp/bin/clang++ -std=c++17 -I <build>/include -I <src>/include -o harmonyos_special_test harmonyos_special_test.cpp
./harmonyos_special_test   # ALL PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | W3/finish 本地 CI 被 junk_check 阻塞（`JC_RESULT=fail / blocked_by_JC`） | 分支零提交时 `git diff origin/main...HEAD` 为空，junk_check 退化 full 模式整仓扫描，误命中 main 基线中**其他库**已提交的 goaccess tarball、scudo-malloc 隐藏标记等基线噪声 | 生成仅含本 PR 文件的 pr.diff，junk_check 以 prdiff 模式只校验本 PR 交付文件；清理 conan-verify 镜像注入残留的 `conandata.yml.ghfast-bak/.orig`；基线文件原样未动 |
| 2 | conan-init 生成 autotools 模板错误 | init_build 按 URL 猜测构建系统为 autotools，实际为 CMake header-only | 重写为 package_type=header-library + CMakeToolchain 配方（参考 E321/E322/E470） |
| 3 | test_package 编译失败（`operator<<` 不支持 ST::string、`to_int` 返回 int 非指针） | 模板生成 test.c 空壳 + 对 API 签名误用 | 重写为真实 C++ 消费者测试：用 `c_str()` 输出、`conversion_result` 重载判断转换状态 |
| 4 | 上游测试 Release(-O2) 下 `char_buffer.self_assign` SIGSEGV | 上游 `operator=(buffer&&)` 自移动时重叠 memcpy（UB），copy 赋值有 `this==&copy` 保护而 move 赋值无 | 上游缺陷，记录台账如实回报；conan recipe ST_BUILD_TESTS=OFF 不受影响 |
| 5 | `/tmp` 只读 | 平台限制（SKILL §7 E002） | 日志等临时目录用 `$HOME/tmp` |

## 源码修改

无（header-only 库，无需补丁；patches/ 为空）

## 依赖版本

- 无第三方运行时依赖（header-only）
- 上游测试框架: googletest v1.15.2（仅测试用，FetchContent）

## 验证结果

```bash
# conan-verify: G0/G1/G2/G3/G4 + L2/L4/L5 全过
# W3 local CI: setup.sh + build_and_test.sh 通过，.ci-result.json exit_code=0
# test_package: CTest 1/1 Passed（0.02 sec）
# 上游测试: Debug 112/112 = 100%；Release 111/112 = 99.1%（self_assign 上游 UB 崩溃）
# 鸿蒙专项测试: harmonyos_special_test ALL PASS（ELF arm64 ohos 原生运行）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake header-only 配方（package_type=header-library） |
| conandata.yml | 官方 GitHub URL + SHA-256 9bb0a969... |
| test_package/ | C++ 消费者测试（真实调用 ST API） |
| reports/ | conan-verify-report / test-report / upstream-test-ledger / knowledge_candidate_ledger |

## 注意事项

- 上游 string_theory 3.9 char_buffer self-move 存在 UB（Release -O2 崩溃），属上游缺陷；使用方避免 `sbuf = std::move(sbuf)` 自移动已是规避
- header-only 库 CI 禁 GitHub 时需在配方禁用上游测试（ST_BUILD_TESTS=OFF），消费者验证由 test_package 承担（W3 与 CI 同源一致）
- junk_check 在零提交分支会退化 full 模式，W3 前须准备 pr.diff 或先提交（与 CI prdiff 模式对齐）

---

**编译结束**: 2026-09-02 23:10
**最终状态**: published
**知识路径**: A（复用既有知识 E321/E322/E470 + DRAFT-dr_mp3 基线噪声隔离），详见 reports/knowledge_candidate_ledger.md