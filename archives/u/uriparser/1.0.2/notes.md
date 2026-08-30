# uriparser 1.0.2 适配笔记

## 编译环境
- 构建系统: cmake（直接 cmake，不使用 configure wrapper）
- 编译日期: 2026-08-28
- 编译器: clang 15.0.4 / clang++（OHOS aarch64，profile: ci/conan/profiles/ohos-aarch64）
- 状态: built（本地 conan-verify 全门禁通过；无远端授权，未 CI 上传）

## 源码身份
- 官方仓库: https://github.com/uriparser/uriparser
- 不可变 tag: `uriparser-1.0.2`（tag 对象 25ee58092e02e12de01653e6c8a84041a9298442，GitHub API 实测一致）
- 官方发布包: https://github.com/uriparser/uriparser/releases/download/uriparser-1.0.2/uriparser-1.0.2.tar.bz2
- 实际 SHA-256: dd2e4843f43de6f5aedf430e530f1e2d159eba8ca4d64c2787af1c20f707a9e4（下载实测，写入 conandata.yml）

## 编译步骤
1. W0 依赖预检：`conan list "uriparser/*" -r=ohpcd` → 0 配方（libkml 1.3.0 恢复依赖缺口确认）；gtest/1.17.0 已在 ohpcd；uriparser 本身无运行时依赖。
2. init-build uriparser 1.0.2 --url https://github.com/uriparser/uriparser --tar tar.bz2（EXPECTED_SHA256 校验通过，基线 113 文件，环境检查通过）。
3. conan-init → 生成骨架；随后 AI 重写为 CMake 配方（见下）。
4. conan-verify 全门禁（G0-G4 + L2/L4/L5）→ **Verdict PASS**。

## 配方要点（conanfile.py）
- CMake 项目：`-DURIPARSER_BUILD_DOCS=OFF -DURIPARSER_BUILD_TESTS=OFF -DURIPARSER_BUILD_FUZZERS=OFF -DURIPARSER_BUILD_TOOLS=ON -DURIPARSER_BUILD_CHAR=ON -DURIPARSER_BUILD_WCHAR_T=ON -DURIPARSER_ENABLE_INSTALL=ON`。
- `BUILD_SHARED_LIBS` 跟随 options.shared（默认 static）；liburiparser 非系统同名库，动态/静态均可，消费者由 Conan 管理。
- cpp_info.libs = ["uriparser"]；CMakeDeps 消费目标 uriparser::uriparser（与上游安装包同名）。
- 无 requires（自包含 C 库）；产出库 + `uriparse` 命令行工具（软件级 commands.json 已声明，R38）。
- 无补丁：全部通过 CMake 选项完成 OHOS 适配。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure wrapper 无法执行 | uriparser 的 configure 是 bash 专用 cmake wrapper（`[[ =~ ]]`、`type -P` 等），OHOS /bin/sh 不兼容 | 直接 CMake 构建，绕开 wrapper（历史 liburiparser 笔记同结论） |
| 2 | test_package 首次 G2 失败 | test.c 先调 `uriToStringA(NULL,...)` 取长度，而公开 API 内部 charsRequired 传 NULL，恒返回 URI_ERROR_NULL | 改用固定缓冲 + maxChars 重组 |
| 3 | 上游测试套件编译失败 | 上游 CMakeLists 对测试强制 C++11，ohpcd 仅有 gtest/1.17.0（要求 C++17） | 测试执行阶段（$TMPDIR 副本）提升 C++17；交付配方 URIPARSER_BUILD_TESTS=OFF 不受影响 |
| 4 | conan-verify 镜像注入 | E017：GitHub 直连可能不稳，conan-verify 自动 ghfast 镜像 + 回滚 | 自动处理，回滚后 sha256 校验一致 |

## 依赖版本
- gtest/1.17.0（仅上游测试执行阶段消费，非包依赖）
- 构建工具：cmake 4.1.2 / make 4.4.1 / clang 15.0.4（系统自带）

## 验证结果
```bash
# conan-verify（含 conan create + 消费者 test_package）
python3 scripts/ohc-run.py conan-verify uriparser 1.0.2   # Verdict PASS

# 上游测试套件（独立执行：URIPARSER_BUILD_TESTS=ON + gtest/1.17.0）
ctest --test-dir build/uriparser-tests                      # 1/1 Passed, 100%
./build/uriparser-tests/testrunner                          # 412 tests from 35 suites: [PASSED] 412

# 日志
# - archives/u/uriparser/1.0.2/reports/conan-verify-report.md
# - archives/u/uriparser/1.0.2/reports/conan-create.log
```

## 注意事项
- 本任务无远端授权（analysis_approved_remote_ci=false）：未 commit/push/PR、未写 Conan remote、未触发远端 CI。
- finish W3 未能派发：外部执行通道 ohpc_compile_worker(127.0.0.1:18082) 全会话不可达（连接被拒）；且历史多次任务已证实 W3 全仓 JC3 会被无关基线 archives/g/goaccess/1.10.2/ncurses-headers.tar.gz 拦截——均属外部阻塞，需分析端下发后续轮次。
- 历史 archives/l/liburiparser/1.0.2/ 仅为旧记录（无配方/无校验和证据），本任务未复制或沿用；全新适配于 archives/u/uriparser/1.0.2/。
---

**编译结束**: 2026-08-29 11:54
**最终状态**: built
