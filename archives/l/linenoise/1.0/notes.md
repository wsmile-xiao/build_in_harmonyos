# linenoise 1.0 适配笔记

## 编译环境
- 构建系统: cmake（配方内嵌 CMakeLists.txt 覆盖；上游 1.0 Makefile 仅含 example 目标）
- 编译日期: 2026-09-02
- 编译器: clang 15.0.4 (aarch64-linux-ohos)
- 状态: built

## 编译步骤

1. 上游源码：https://github.com/antirez/linenoise/archive/refs/tags/1.0.tar.gz（官方 GitHub，tag 1.0）
2. `make`：上游 Makefile 编译 linenoise_example（example.c），验证上游样例可编译
3. 库构建：`clang -Wall -W -Os -fPIC -c linenoise.c -o linenoise.o && llvm-ar rcs liblinenoise.a linenoise.o`，同时生成 `liblinenoise.so`
4. 配方：上游无 configure/install 目标，conanfile.py 内嵌 CMakeLists.txt（仅库目标，省略 RUNTIME DESTINATION 满足 R38）经 conan create 干净构建验证（G2 PASS）
5. test_package：消费者 API 冒烟测试（linenoiseHistorySetMaxLen / Add / Save / Load），conan create 内 CTest 1/1 通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 GitHub archive 超时 | 本设备 urllib 直连 github.com archive 通道超时 | codeload.github.com 通道可下载，预放置 tarball 到 $TMPDIR/builds/ 后 init-build 跳过下载 |
| 2 | W3 本地 CI 的 junk_check 误扫整仓 | 分支未提交任何改动时 origin/main...HEAD diff 为空，junk_check 回退 full 模式误报其他库既有基线垃圾（flatcv/goaccess/lsof 等） | 提交本库改动使 diff 非空，junk_check 进入 incremental 模式只查本 PR 文件；真实 CI 使用 pr.diff 只查 PR 文件 |
| 3 | /tmp 只读 | OHOS 平台 /tmp 只读（E002） | 使用 $TMPDIR（$HOME/tmp） |

## 源码修改

无补丁（1.0 适配无需修改上游源码/测试）。

## 依赖版本

- 无外部依赖（单文件 C 库，仅依赖 libc）

## 验证结果

```bash
# 上游 make（样例编译）
make
# → linenoise_example 编译成功

# conan create（干净构建 + test_package CTest）
conan create archives/l/linenoise/1.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing --user=ohpcd --channel=stable
# → "linenoise 1.0 API test: OK"，Test Passed (1/1)

# 消费者静态链接 staging 验证
clang -I $TEST_PREFIX/include ln-staging-test.c $TEST_PREFIX/lib/liblinenoise.a -o ln-staging-test && ./ln-staging-test
# → staging link OK
```

## 交付物

无打包产物（纯库配方，conan create 生成制品）。

## 注意事项

- linenoise 1.0 tag 无独立测试程序（2.0 才新增 linenoise-test.c），上游示例不计为独立用例
- linenoise API 成功返回 1、失败返回 0，与常规约定相反，断言方向需反转
- conandata.yml 保持官方 GitHub URL（R39），CI 自动注入镜像 fallback（本地 conan-verify 经 ghfast 镜像验证通过）
---

**编译结束**: 2026-09-02 02:15
**最终状态**: built
