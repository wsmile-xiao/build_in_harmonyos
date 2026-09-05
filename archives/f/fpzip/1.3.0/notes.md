# fpzip 1.3.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang/clang++ 15.0.4 (aarch64-linux-ohos, Conan profile ohos-aarch64)
- 状态: built

## 编译步骤

1. Bootstrap: `ohc-run.py init-build fpzip 1.3.0 --url=https://github.com/LLNL/fpzip/archive/refs/tags/1.3.0.tar.gz`
   - 官方 tag 为 `1.3.0`（无 `v` 前缀），init-build 用 `v1.3.0` 拼 URL 会 404 → HTML，须显式传入正确 tag 的 tarball URL。
   - tarball SHA-256: 248df7d84259e3feaa4c4797956b2a77c3fcd734e8f8fdc51ce171dcf4f0136c（GitHub API tags 核对 commit 4a539c06…）
2. 语言预检: `ohc-run.py lang-preflight fpzip 1.3.0` → cpp/cpp 匹配（CMake，17 源文件 cpp:16/c:1，主体 94%）
3. Adapt（HOST 隔离构建）: `cmake -B build-ohos -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DFPZIP_FP=FPZIP_FP_SAFE` → `cmake --build` exit 0 → `ctest -V` 1/1 Passed（float/double 多精度压缩-解压-校验全过）
4. Staging: `DESTDIR=$TEST_PREFIX cmake --install`，产物 include/fpzip.h、lib/libfpzip.so、cmake/fpzip/*。上游仅安装库与头文件（utils/fpzipcmd 无 install 规则），属库类型，无需 commands.json（R38）
5. 配方: `conan-init` 生成后改写为 CMake 驱动（conan.tools.cmake），test_package 改为 C++ 项目
6. 验证: `conan-verify` G0-G4/L2/L4/L5 全 PASS；`finish` W3 本地 CI（setup.sh + build_and_test.sh）通过，状态 built

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载返回 HTML | fpzip 官方 tag 为 `1.3.0`，工具按 `v1.3.0` 拼 GitHub URL 404 | 显式传 `--url=.../archive/refs/tags/1.3.0.tar.gz`，API 核对 tag commit |
| 2 | CMake configure 报 "Compatibility with CMake < 3.5 has been removed" | 上游 `cmake_minimum_required(3.1)` 与 CMake 4.x 不兼容 | 配方 generate() 以 `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"` 传入（-D 通道，toolchain variables 不生效） |
| 3 | conan create 链接失败 undefined symbol: operator new/__cxa_* | test_package 声明纯 C 项目，链接 C++ 静态库缺 C++ 运行时 | test_package 改 `project(... CXX)` + test.c→test.cpp + malloc 显式转换 |
| 4 | W3 build_and_test.sh JC 拦截 | 其他库（embree/flatcv/libmorton/goaccess/captagent/lsof/scudo-malloc/stb_image）9 个已跟踪垃圾文件属 main 历史基线，不在本库允许范围 | 按 oh-executor 基线规则：临时 `git rm --cached` 隔离（记录 blob/sha256）→ W3 复验通过 → `git add -f` 无条件恢复，恢复后与 HEAD 零 diff |

## 源码修改

无补丁（0 patches）。纯配方层适配，不改上游源码。

## 依赖版本

无外部依赖（requirements 为空）。

## 验证结果

```bash
# 上游测试（Adapt 阶段）
cmake --build . --config Release -j2   # exit 0
ctest -V                               # 1/1 Passed, all tests passed
# Conan 验证（conan-verify）
conan create ... -pr:h=ohos-aarch64 --build=missing   # G2 PASS，test_package 往返校验 OK
# W3 本地 CI
setup.sh 通过; build_and_test.sh 通过（JC/L0-L5 全绿，.ci-result.json exit_code=0）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 驱动配方（shared 选项、CMAKE_POLICY_VERSION_MINIMUM、FPZIP_FP_SAFE） |
| conandata.yml | 官方 tag 1.3.0 tarball + SHA-256 |
| test_package/ | C++ 消费者测试（16x8x4 double 往返压缩-解压校验）+ MANIFEST.yml |
| reports/test-report.md | 上游 ctest 与消费者测试报告 |

## 注意事项

- CMake >= 4 环境下必须传 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（cache 变量），否则 configure 直接失败。
- fpzip 上游 install 不安装 fpzipcmd 命令行工具，无需 commands.json。
- 官方 tag 无 `v` 前缀；上游来源 https://github.com/LLNL/fpzip（LLNL）。
