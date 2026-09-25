# cpp-smtpclient-library 1.1.14 适配笔记

## 编译环境
- 构建系统: cmake（CMakeLists.txt，C++14/17，依赖 OpenSSL）
- 编译日期: 2026-09-22
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤

```bash
# init-build（官方 tag v1.1.14，SHA-256 de525707…34883）
ohc-run.py init-build cpp-smtpclient-library 1.1.14 --url <官方 tar.gz>

# 探索编译（禁用 clang-tidy 后配置，链接 armv8 OpenSSL 静态库）
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
  -DCLANG_TIDY_EXE=CLANG_TIDY_EXE-NOTFOUND \
  -DOPENSSL_ROOT_DIR=<conan openssl/3.5.8.1 package_folder>
make -j1        # make jobserver FIFO 在 OHOS 被拒，须 -j1

# 上游测试（BUILD_TESTING=ON + googletest v1.17.0 本地源）
cmake -S . -B build-t -DBUILD_TESTING=ON -DCLANG_TIDY_EXE=CLANG_TIDY_EXE-NOTFOUND ...
make -j1 smtpclient_unittests
LD_LIBRARY_PATH=... ./bin/smtpclient_unittests   # 642/642 PASS

# Conan 交付
ohc-run.py conan-init cpp-smtpclient-library 1.1.14
ohc-run.py conan-verify cpp-smtpclient-library 1.1.14   # G0-G4 PASS
ohc-run.py finish cpp-smtpclient-library 1.1.14 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 配置后 make 报 `build.make:82: *** missing separator` | 上游 find_program(clang-tidy) 命中后，把含换行/分号的多行 --tidy 参数写入 build.make 配方行，换行未以 tab 起始 | conanfile.py `tc.cache_variables["CLANG_TIDY_EXE"]="CLANG_TIDY_EXE-NOTFOUND"`（必须 cache_variables，find_program 优先读 cache；variables 无效）→ E6401 |
| 2 | make jobserver mkfifo Operation not permitted | OHOS SELinux 禁止用户进程创建 FIFO | cmake.build(build_tool_args=["-j1"]) → 复用 E525/E074 |
| 3 | test_package find_package(cpp-smtpclient-library) 找不到 Config | 上游 CMake 导出名为 smtpclient（smtpclientConfig.cmake / smtpclient::smtpclient） | test_package/CMakeLists.txt 改 find_package(smtpclient) + target smtpclient::smtpclient；package_info 设 cmake_file_name/target_name |
| 4 | 空壳 test.c 不满足 R34 | 模板 test_package 仅打印字符串 | 重写 test.cpp 调用 MessageAddress/PlaintextMessage/Attachment 真实公开 API 并断言 |
| 5 | GitHub 直连不可达，googletest ExternalProject 克隆失败 | 网络受限 + ExternalProject 需 GIT_EXECUTABLE | 本地 googletest v1.17.0 git 仓库 + CMakeLists.txt.in 本地源（交付配方 BUILD_TESTING=OFF，不携带本地路径） |

## 源码修改

无提交补丁（patches: {}，patches_applied: []）。上游源码未修改；
clang-tidy 禁用与 -j1 均在 conanfile.py 配方内处理（本地运行上游测试用的
CMakeLists.txt.in 临时修改未进入交付）。

## 依赖版本

- openssl/3.5.8.1（ohpcd 制品仓，armv8 静态库）

## 验证结果

```bash
# 上游测试：56 套件 642 用例全部通过
[  PASSED  ] 642 tests.
# 鸿蒙专项测试：14 项断言全部 PASS（exit 0）
=== RESULT: ALL PASSED (0 failures) ===
# 消费者用例（安装产物 + 公开头文件）：CONSUMER OK（exit 0）
# conan-verify：G0-G4 全 PASS；finish W3：conan create passed，100% tests passed
```

## 注意事项

- 上游库名为 `smtpclient`（CMake PROJECT_NAME），非 cpp-smtpclient-library；
  conanfile.py package_info libs=["smtpclient"]、cmake_file_name="smtpclient"。
- 该库是 SMTP 客户端库（纯库，无 CLI），不需要 commands.json（R38 不适用）。
- 上游测试中 SMTP 网络类用例（SMTPClientBase 等）在本环境无网络服务器时仍
  以构造/错误码路径通过；gtest 全量 642/642 为实际运行结果。

**编译结束**: 2026-09-22
**最终状态**: built
