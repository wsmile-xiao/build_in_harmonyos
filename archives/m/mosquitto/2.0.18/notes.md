# mosquitto 2.0.18 — 编译进度

> 档案创建时间: 2026-08-07
> 最后更新: 2026-08-07
> 状态: built (conan-verify passed, W3 CI passed)

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | mosquitto |
| 版本 | 2.0.18 |
| 状态 | ✅ success |
| 构建系统 | cmake |
| 源码路径 | https://mosquitto.org/files/source/mosquitto-2.0.18.tar.gz |

## 二、编译阶段

### Phase 1: 环境准备
- [x] init-build 完成 / 源码下载解压

### Phase 2: 编译（cmake + make）
- [x] cmake configure 完成
- [x] make 编译完成
- [x] make install 完成

### Phase 2.5: Conan 配方生成与验证
- [x] conan-init 生成 conanfile.py + conandata.yml + test_package/
- [x] conan-verify 全部通过 (G0-G4 + L2/L4/L5)

### Phase 3: 测试验证
- [x] conan create test_package 通过
- [x] test_mosquitto 调用 mosquitto_lib_init/version/new/destroy API

### Phase 4: 归档收尾
- [x] 补丁生成（refresh-patch --auto）
- [x] manifest.yaml 更新
- [x] W3 本地 CI 模拟通过
- [x] 归档关闭

## 三、平台修复

### 修复 1: CMakeLists.txt
- 问题: cmake_minimum_required(VERSION 3.1) 不兼容 CMake 4.x
- 修复: bump 到 3.5
- 补丁: patches/0001-CMakeLists.txt.patch

### 修复 2: config.h
- 问题: HarmonyOS 不实现 pthread_cancel/pthread_testcancel (与 Android Bionic 相同)
- 修复: 添加 __OHOS__ 守卫，不定义 HAVE_PTHREAD_CANCEL
- 补丁: patches/0002-config.h.patch

## 四、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| CMakeLists.txt | CMake 4.x 兼容性 | 修改 cmake_minimum_required | ✅ 0001-CMakeLists.txt.patch |
| config.h | HarmonyOS pthread_cancel 缺失 | 添加 __OHOS__ 守卫 | ✅ 0002-config.h.patch |

## 结束记录
- **最终状态**: built (conan-verify passed, W3 CI passed, W4 audit passed)
- **结束时间**: 2026-08-07
- **编译结束**: 2026-08-07
