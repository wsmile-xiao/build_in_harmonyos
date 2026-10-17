# bytes 0.0.4 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-18
- 编译器: clang/clang++ (OHOS aarch64 profile)
- 状态: published

## 编译步骤

bytes 是 clibs 单文件 C99 库（bytes.c/bytes.h），上游 Makefile 无 configure、
无 make install 目标，仅提供 `make test`（编译并运行 test.c）。适配采用自定义配方：

1. `git worktree add -b feat/bytes-0.0.4 ... origin/main` 创建专用 worktree
2. `ohc-run.py init-build bytes 0.0.4 --url=https://github.com/clibs/bytes/archive/refs/tags/0.0.4.tar.gz`
   （仓库主页 URL 返回 HTML，改用官方 tag 归档 URL；sha256=1d8fa516d2e1c1607b40ee1e46c46b282be420d9aaa1d37d1f3e24bf5cbb1485）
3. `lang-preflight`：C 语言，与任务默认 cpp 属兼容族，通过
4. 上游测试：`make test` 在 work 目录实际运行，exit 0
5. conanfile.py 自定义构建：CC 编译 bytes.c -> libbytes.a（llvm-ar/ranlib 归档），
   安装 bytes.h + libbytes.a；R33 编译器取自 Conan conf，不依赖 shell 环境变量
6. test_package：消费者测试（test.c）+ 鸿蒙专项测试（ohos_specific_test.c），
   CMake 注册两个 ctest 用例
7. `conan-verify`：G0-G4 + L2/L4/L5 全通过，可标记 published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载返回 HTML | `https://github.com/clibs/bytes` 是仓库主页，非源码归档 | 改用官方 tag 归档 URL `.../archive/refs/tags/0.0.4.tar.gz` |
| 2 | 生成的配方是 Autotools 模板 | bytes 无 configure/autotools 构建系统 | 改写为自定义构建：直接编译 bytes.c 并归档为 libbytes.a |

## 源码修改

无补丁（patches/ 为空）。上游源码未修改。

## 依赖版本

无第三方依赖（requirements 为空）。

## 验证结果

```bash
# 上游测试（work 目录，实际运行）
make test          # exit 0，输出 "✓ ok"
# Conan 配方验证（8 道门禁）
ohc-run.py conan-verify bytes 0.0.4   # G1-G4/L2/L4/L5 全 PASS
```

### 上游测试完整枚举台账

| 入口 | 类型 | 是否独立上游用例 | 是否实际运行 | 结果 |
|------|------|------------------|--------------|------|
| test.c（test_string_to_bytes） | 用户测试源，断言式函数 | 是 | 是（make test） | 通过 |
| test.c（test_bytes_to_string） | 用户测试源，断言式函数 | 是 | 是（make test） | 通过 |
| test.c（main） | 测试入口 | 否（仅聚合两个测试函数） | - | - |
| bytes.c/bytes.h | 库源码（被测试目标） | 否 | - | - |
| Makefile `test` 目标 | 构建目标 | 否（测试构建入口） | - | - |
| .travis.yml | CI 配置（script: make test） | 否 | - | - |
| package.json | 包元数据 | 否 | - | - |
| History.md/Readme.md | 文档 | 否 | - | - |

上游独立测试用例总数：**2**（均为断言式函数，非框架 TEST_CASE，经 `make test` 单入口全量运行）
- 全量发现数：2
- 实际运行：2（同一 make test 进程内执行）
- 通过：2
- 全量通过率：2/2 = 100%（实际执行通过率同）

### 鸿蒙专项测试（新增用例）

`test_package/ohos_specific_test.c`：3 个测试函数（>4GB long long 边界换算、
asprintf 内存可释放性、gb 分支整除截断语义），经 conan create 内 ctest 实际编译运行并通过。
区别于上游 test.c（不重复计数）。

### 消费者验证（test_package/test.c）

仅经公开头文件 bytes.h 调用 string_to_bytes/bytes_to_string 并断言输出，
验证第三方消费者可编译、链接、调用并得到可观察结果。经 conan create 实际运行通过。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/b/bytes/0.0.4/conanfile.py | 自定义构建配方 |
| archives/b/bytes/0.0.4/conandata.yml | 官方源码 URL + sha256 |
| archives/b/bytes/0.0.4/test_package/ | 消费者测试 + 鸿蒙专项测试 |

## 注意事项

- bytes 无 CLI 产物（仅静态库 + 头文件），不创建 commands.json（R38 库类型）
- 上游 `asprintf` 依赖 OHOS libc 支持（GNU 扩展），实测可用
---

**编译结束**: 2026-09-18 21:35
**最终状态**: published
