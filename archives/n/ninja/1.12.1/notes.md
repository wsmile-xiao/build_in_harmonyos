# ninja 1.12.1 — 适配笔记

> 档案创建时间: 2026-04-25 00:00:00
> 最后更新: 2026-08-07
> Conan 适配: 2026-08-07

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | ninja |
| 版本 | 1.12.1 |
| 状态 | ✅ built (conan-verify PASS) |
| 构建系统 | cmake |
| 源码路径 | https://github.com/ninja-build/ninja/archive/refs/tags/v1.12.1.tar.gz |
| 补丁数 | 1 |

## 二、编译阶段

### Phase 1: 环境准备
- [x] ohc-run.py init-build 完成
- [x] 源码下载解压 (git clone from GitHub)

### Phase 2: 编译 (CMake)
- [x] cmake 配置完成 (-DBUILD_TESTING=OFF)
- [x] make 编译完成 (ninja binary)
- [x] make install 完成 (staging dir)
- [x] ninja --version 返回 1.12.1

### Phase 3: 测试验证
- [x] ninja_syntax_test.py: 21 tests PASS
- [x] smoke test: ninja --version OK

### Phase 4: Conan 配方
- [x] conan-init 生成 conanfile.py + conandata.yml + test_package/
- [x] conan-verify G1-G4 + L2/L4/L5 全部 PASS
- [x] W3 本地 CI 模拟 PASS

## 三、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| src/inline.sh | shebang #!/bin/sh → #!/data/service/hnp/bin/bash | patch | 0001-src-inline.sh.patch |

## 四、Conan 配方要点
- package_type = "application" (ninja 是命令行工具)
- BUILD_TESTING=OFF 避免 CMake FetchContent 下载 Google Test (GitHub 不可达)
- test_package 使用完整路径调用 ninja 二进制 (R34 合规)

## 五、结束记录
- **最终状态**: built (conan-verify PASS, W3 CI PASS)
- **结束时间**: 2026-08-07 05:48
