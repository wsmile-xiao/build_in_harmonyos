# portable-libyaml 0.2.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-08
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

### CMake 构建（成功）

1. 下载源码包：libyaml 0.2.5 (从 GitHub)
2. cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=ON
3. make -j2
4. make install DESTDIR=staging（staging 验证）
5. make install（安装到本地）

### Autotools 构建（历史失败，不再使用）

受 E046 SELinux 限制阻塞，configure 阶段失败。使用 CMake 构建系统替代。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x 兼容性 | cmake_minimum_required(VERSION 3.0) 在 CMake 4.x 中被移除 | 设置 CMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 2 | config.status 权限拒绝 (历史) | SELinux/文件系统限制（E046） | 使用 CMake 构建系统替代 autotools |
| 3 | Conan CMakeDeps target 名 | 生成 target 为 yaml 而非 yaml::yaml | test_package CMakeLists.txt 使用 yaml 而非 yaml::yaml |

## 验证结果

```bash
# CMake 构建产物
$ ls ~/usr/local/lib/libyaml.a
142472 bytes

$ ls ~/usr/local/include/yaml.h
54439 bytes

# CTest 结果
1/2 Test #1: version ........................   Passed
2/2 Test #2: reader .........................   Passed
100% tests passed

# 功能验证
$ clang test_yaml.c -lyaml -o test_yaml
$ ./test_yaml
libyaml test: OK
```

## Conan 配方

- conanfile.py: CMake 构建系统，静态库
- conandata.yml: 源码 URL + SHA256
- test_package/: 使用 yaml_parser API 的实质性测试
- Conan 验证: G0-G4 + L2/L4/L5 全部通过

---

**编译结束**: 2026-08-08 00:46
**最终状态**: built
