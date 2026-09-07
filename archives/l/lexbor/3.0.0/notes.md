# lexbor 3.0.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

lexbor 使用 CMake 构建，无外部依赖（纯 C 库）：

```bash
mkdir -p build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DCMAKE_BUILD_TYPE=Release
make -j1
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-lexbor-3.0.0
```

上游测试（LEXBOR_BUILD_TESTS=ON 构建 134 个测试可执行文件）：

```bash
cmake .. -DLEXBOR_BUILD_TESTS=ON -DCMAKE_BUILD_TYPE=Release
make -j1          # 构建全部测试目标（注意：本机需 -j1，make -j2 的 jobserver 在 HMDFS 上 mkfifo 受限）
ctest             # 需要先设置 LD_LIBRARY_PATH 指向 build 目录
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Python urllib 直连 GitHub 下载超时（Errno 110） | GitHub 直连 SSL/超时（同 2.6.0 历史踩坑） | `curl -k -L` 下载官方 tag tarball，init-build 用 `file://` URL |
| 2 | ctest 大量 "Error loading shared library" | 上游 CMake 用相对路径链接 libunit.so/liblexbor.so，本平台 musl 加载器按 CWD 解析相对 DT_NEEDED | 从各测试二进制所在目录运行，并为 CWD 下的相对 NEEDED 路径建符号链接；或 LD_LIBRARY_PATH 指向 build 目录 |
| 3 | make -j2 报 "jobserver mkfifo: Operation not permitted" | HMDFS 限制 mkfifo | 使用 `make -j1` |
| 4 | conan create test_package 链接报 lxb_dom_document_body undefined | test.c 用了错误的 DOM body API（lxb_dom_document_body 未在公开头文件声明） | 改用 `lxb_html_document_body_element(document)`（lexbor/html/interfaces/document.h） |
| 5 | W3 本地 CI 模拟 JC5 拦截 `archives/u/util-linux-login/2.42.2/.ci-trigger` | 该文件是 main 基线中其他库遗留的 tracked 空文件，本地 W3 在分支无 commit 时回退 full 整仓扫描误命中（属于无关历史基线，非本库缺陷） | 按 oh-executor 基线隔离规则：以仅含 lexbor 变更的 pr.diff 作为 junk_check 的临时 checker-input（JUNK_PR_DIFF），复验通过后无条件恢复（不修改、不提交、不删除该基线文件） |
| 6 | patchelf 改写 test 二进制 NEEDED 报 Operation not permitted | HMDFS 写保护 | 不使用 patchelf，改用符号链接 + 目录内运行方式 |

## 源码修改

无需修改源码，开箱即编译。conanfile.py 从 autotools 模板改写为 CMake 配方（lexbor 是 CMake 项目），conandata.yml 修正为官方 GitHub 源 URL 与真实 sha256。

## 依赖版本

- cmake 4.1.2
- clang 15.0.4
- make 4.4.1

## 验证结果

上游测试（LEXBOR_BUILD_TESTS=ON，ctest 注册 134 项）全部通过：
- 112 个测试直接通过
- 22 个数据驱动测试（html5lib/css/encoding/url）传入 test/files 数据后全部通过
- 代表性数据量：html5lib_tests 6806/6806、tree_builder 1786/1786、serialize_ext 204/204、encoding_html5lib 82/82、url parser 45 项 0 errors

Conan 验证（conan-verify G0-G4 + L2/L4/L5）全部 PASS；W3 本地 CI 模拟（build_and_test.sh）通过，.ci-result.json exit_code=0。

## 注意事项

- lexbor 纯 C 库、无依赖、无命令行工具（不需要 commands.json）
- 上游无 make check 目标，测试由 CMake LEXBOR_BUILD_TESTS 构建并经 ctest 运行（详见 test_package/MANIFEST.yml）
- 测试数据文件在源树 test/files/ 下，运行数据驱动测试需传入对应数据路径

**编译结束**: 2026-09-07 00:40
**最终状态**: built
