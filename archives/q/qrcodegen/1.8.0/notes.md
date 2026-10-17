# qrcodegen 1.8.0 适配笔记（C++ implementation, Project Nayuki）

## 编译环境
- 构建系统: cmake（source() 内联生成 CMakeLists.txt，上游仅提供 Makefile）
- 编译日期: 2026-09-12
- 编译器: clang 15 / clang++（OHOS SDK）
- 状态: published

## 编译步骤

1. `conan create archives/q/qrcodegen/1.8.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
2. source() 阶段：下载官方 tarball（sha256 2ec0a4d33d6f521c942eeaf473d42d5fe139abcfa57d2beffe10c5cf7d34ae60），strip_root 后将 cpp/ 子目录内容提升到源码根（tarball 是多语言实现合集：c/、cpp/、java/、python/、rust/ 等；本包为 **C++ 实现**，与已归档的 libqrcodegen C 实现同上游不同语言绑定）
3. source() 阶段：内联生成 CMakeLists.txt（add_library qrcodegen qrcodegen.cpp + install 头文件与库），C++11 标准
4. build() 阶段：CMake configure + build，产物 libqrcodegen.a（默认静态）
5. test_package：消费者探针直接用 clang++ 编译 + `-static-libstdc++` 静态链 libc++，链接 libqrcodegen.a 真实调用 API

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test 阶段报 `Error relocating ./test_qrcodegen: _ZTISt12length_error: symbol not found` 等大量 libc++ 符号缺失 | OHOS 上 C++ 探针动态链接 libc++_shared.so，conanrun 环境 LD_LIBRARY_PATH 不含 SDK libc++ 目录 | test_package 沿用 argp-standalone 先例：`-static-libstdc++` 把 libc++ 静态链进探针，运行期只依赖系统 libc.so |
| 2 | G1 门禁要求 conanfile.py 含 `apply_conandata_patches` 调用 | conan-init 生成模板骨架时按门禁清单校验 | build() 内加 `apply_conandata_patches(self)`（无补丁时为 no-op）并恢复 `export_conandata_patches` |
| 3 | init-build 嵌套源码自动提升到 c/（C 实现） | tarball 含 c/ 与 cpp/ 两个实现，自动检测取了 c/ | source() 手动处理：提升 cpp/ 到根（与 libqrcodegen C 版归档的 c/ 提升逻辑同构） |

## 源码修改

无补丁。源码零修改，仅通过 source() 内联生成的 CMakeLists.txt 接入构建（上游 Makefile 不安装头文件/库，无 install 目标）。

## 依赖版本

零外部依赖（纯 C++11 单文件库）。

## 验证结果

```bash
$ conan create ... （ohos-aarch64 profile）
...
qrcodegen consumer test: ALL PASSED
Package 'qrcodegen/1.8.0@ohpcd/stable' created
```

- G1-G4 + L2/L4/L5 全部 PASS（conan-verify 8 道门禁）
- 消费者测试 12 项断言全过（encodeText numeric/text、encodeBinary、QrSegment 中级 API、版本/尺寸公式、查找图形/时序线模块断言、纠错级别单调性）

## 测试说明（N 口径）

- 上游 C++ 实现（cpp/ 子目录）**无测试套件**：无测试目标、无测试源文件（C 实现才有 qrcodegen-test.c 521 用例，C++ 实现没有）——N=0，PR 正文按模板如实申报并附豁免说明
- 适配后补全消费者测试：test_package/test.cpp 12 项断言（见 test_package/MANIFEST.yml）

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（CMake 流程 + cpp/ 提升 + 内联 CMakeLists） |
| conandata.yml | 官方源 URL + sha256 + 镜像 fallback |
| test_package/ | 消费者测试（12 断言，-static-libstdc++ 模式） |
| manifest.yaml / notes.md | AI 元数据 |

## 注意事项

- 本包与 archives/l/libqrcodegen/1.8.0（C 实现）同上游不同语言绑定，互不冲突
- OHOS 下 C++ 消费者测试必须 -static-libstdc++（见问题 1），下游包写 test_package 时同样适用
---

**编译结束**: 2026-09-12 13:18
**最终状态**: built
