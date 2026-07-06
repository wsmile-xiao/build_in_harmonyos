# Vampire 5.0.1

## 软件信息

| 项目 | 值 |
|------|------|
| 名称 | vampire |
| 版本 | 5.0.1 |
| 描述 | 高性能一阶逻辑定理证明器 (High-performance theorem prover) |
| 许可证 | BSD-3-Clause |
| 主页 | https://github.com/vprover/vampire |
| 构建系统 | CMake |
| 语言 | C/C++ |
| 依赖 | 无（内嵌 CaDiCaL 2.1.3、Minisat） |

## 编译信息

| 项目 | 值 |
|------|------|
| 平台 | OpenHarmony ARM64 (aarch64) |
| 编译器 | Clang 15.0.4 |
| 构建类型 | Release |
| 静态链接 | 是 (BUILD_SHARED_LIBS=OFF) |
| 编译日期 | 2026-06-29 |
| 状态 | published |

## 编译命令

```bash
cd $BUILD_SRC_DIR
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=OFF
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 功能验证

```bash
# 版本
$ vampire --version
Vampire 5.0.1 (Release build, commit )
CaDiCaL: cadical-2.1.3

# 定理证明: 苏格拉底三段论
$ vampire socrates.p
% SZS status Theorem for vampire_socrates
% Refutation found. Thanks to Tanya!
```

## 文件清单

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (CMake 构建系统, R26 静态链接) |
| conandata.yml | Conan 数据文件 (源码 URL + sha256) |
| test_package/ | Conan 测试包 (L2 smoke test) |
| patches/ | 补丁目录 (空，无补丁) |
| reports/test-report.md | 测试报告 (含4项真实功能测试输出) |
| reports/test-execution.log | 原始测试执行日志 (终端输出) |
| reports/conan-verify-report.md | Conan 验证报告 (8道门禁全PASS) |
| reports/conan-create.log | conan create 完整日志 |
| reports/baseline.json | 产物基线 |
| manifest.yaml | 归档清单 |
| notes.md | 适配笔记 |

## Conan 引用

```
vampire/5.0.1
```
