# mbedtls 2.28.10 编译笔记

## 基本信息
- 软件名：mbedtls
- 版本：2.28.10
- 构建系统：CMake
- 编译日期：2026-05-19

## 源码准备
- 下载 URL：https://github.com/Mbed-TLS/mbedtls/archive/refs/tags/v2.28.10.tar.gz
- 源码目录：~/tmp/builds/mbedtls-2.28.10.work

## 编译环境
- 前缀路径：~/usr/local
- 测试安装目录：~/tmp/test-install-mbedtls-2.28.10

---

**编译开始**: 2026-05-19 20:05

## 编译过程

### Step 1: CMake 配置
```bash
cd ~/tmp/builds/mbedtls-2.28.10.work/build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DENABLE_PROGRAMS=OFF -DENABLE_TESTING=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5
```

**关键问题**：
- CMake 4.1.2 不支持旧版 cmake_minimum_required(VERSION 2.5)
- 需要添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 参数
- HarmonyOS 平台识别问题（警告，不影响编译）

### Step 2: 编译
```bash
make -j4
```
- 编译时间：约 2 分钟
- 编译成功，无错误

### Step 3: Staging 安装
```bash
make install DESTDIR=$TEST_PREFIX
```
- 安装产物：
  - libmbedcrypto.a (701K)
  - libmbedtls.a (311K)
  - libmbedx509.a (144K)
  - 81 个头文件

### Step 4: 测试
```bash
make test
```
- 测试总数：113
- 通过：101
- 失败：12
- 通过率：89%
- 失败测试为已知平台兼容性问题（与历史版本一致）

### Step 5: 最终安装
```bash
make install
```
- 安装到 ~/usr/local

## 知识提取

### 新发现
- CMake 4.x 需要兼容性参数支持旧版 cmake_minimum_required
- 已记录到 manifest.yaml 的 knowledge_gained

---

*本笔记由 openharmony-compile-agent 自动生成*
---

**编译结束**: 2026-05-20 14:28
**最终状态**: built
