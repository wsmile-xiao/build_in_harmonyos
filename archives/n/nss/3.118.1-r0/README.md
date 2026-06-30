# NSS 3.118.1-r0 编译归档

## 软件介绍

**Network Security Services (NSS)** 是 Mozilla 开发的一组开源库，用于支持跨平台的安全通信应用程序开发。NSS 提供了完整的加密库实现，支持 SSL/TLS 协议、S/MIME、PKCS#11、PKIX 等标准。

### 主要组件

- **NSPR (Netscape Portable Runtime)**: 平台抽象层，提供线程、内存、I/O 等基础功能
- **SSL/TLS 库**: 实现安全套接字层和传输层安全协议
- **证书处理库**: X.509 证书解析、验证和管理
- **加密库**: 对称加密、非对称加密、哈希算法等
- **PKCS#11 接口**: 硬件令牌和智能卡支持

### 主要应用

- Mozilla Firefox 浏览器
- Thunderbird 邮件客户端
- Apache HTTP Server (mod_nss)
- 各种需要安全通信的开源项目

### 版本信息

- **NSS 版本**: 3.118.1
- **发布标签**: NSS_3_118_1_RTM
- **NSPR 版本**: 4.37
- **源码包**: nss-3.118.1-with-nspr-4.37.tar.gz (约 75MB)

## 编译进展

### 当前状态: **构建中** (Building)

#### ✅ NSPR 4.37 - 编译成功

**编译时间**: 2026-05-25  
**编译方法**: configure + make  
**关键修改**: 设置 `TMPDIR=/data/storage/el2/base/cache`

**编译产物** (已安装到 `~/usr/local/`):

| 库文件 | 类型 | 大小 |
|--------|------|------|
| libnspr4.so | 共享库 | 268KB |
| libnspr4.a | 静态库 | 424KB |
| libplc4.so | 共享库 | 35KB |
| libplc4.a | 静态库 | 25KB |
| libplds4.so | 共享库 | 26KB |
| libplds4.a | 静态库 | 9KB |

**头文件位置**: `~/usr/local/include/nspr/`

#### ⏳ NSS 3.118.1 - 编译进行中

**当前阶段**: 配置文件准备完成

**已完成任务**:
1. ✅ 创建 `HarmonyOS.mk` 配置文件
   - 基于 Linux.mk 适配 OpenHarmony
   - 配置 clang 编译器
   - 设置 aarch64 架构支持
   - 定义编译标志和链接选项

2. ✅ 修改 `arch.mk` 添加 HarmonyOS 平台识别
   - OS_ARCH = HarmonyOS
   - OS_RELEASE = 1.12
   - KERNEL = HarmonyOS

3. ✅ 修改 `config.mk` 添加 HarmonyOS 到目标平台列表

**待完成任务**:
1. ⏳ 批量修改 `lib/*/manifest.mn` 添加 `REQUIRES = nspr`
   - 需要修改多个子目录的 manifest.mn 文件
   - 添加 NSPR 依赖声明

2. ⏳ 编译 NSS 核心库
   - 使用 gyp-ninja 或 make 构建系统
   - 需要 NSPR 头文件路径配置

3. ⏳ 编译 NSS 工具程序
   - certutil, pk12util, modutil 等工具
   - 验证工具功能

4. ⏳ 运行测试验证
   - 单元测试
   - 集成测试
   - 功能验证

### 关键问题和解决方案

#### 1. OpenHarmony HMDFS 临时目录权限限制

**问题描述**:  
OpenHarmony 的 HMDFS 文件系统对临时目录权限有限制，导致 configure 脚本无法在默认位置创建临时文件。

**解决方案**:
```bash
export TMPDIR=/data/storage/el2/base/cache
```

**补丁文件**: `patches/0002-config-status-tmpdir.patch`

#### 2. config.guess 和 config.sub 不识别 HarmonyOS

**问题描述**:  
Autoconf 的 config.guess 和 config.sub 脚本无法识别 HarmonyOS 平台。

**解决方案**:  
创建快速修复脚本，返回 `aarch64-unknown-linux-ohos`。

**补丁文件**: `patches/0001-nspr-config-guess-ohos.patch`

#### 3. NSS 需要 HarmonyOS 平台配置

**问题描述**:  
NSS 使用 coreconf 构建系统，需要平台特定的配置文件。

**解决方案**:  
创建 `HarmonyOS.mk` 配置文件，适配 OpenHarmony 编译工具链。

**补丁文件**: `patches/0003-nss-harmonyos-config.patch`

## 补丁文件说明

### 0001-nspr-config-guess-ohos.patch
- **目标**: NSPR config.guess 和 config.sub
- **作用**: 添加 HarmonyOS/OpenHarmony 平台识别
- **状态**: 已创建

### 0002-config-status-tmpdir.patch
- **目标**: NSPR config.status 脚本
- **作用**: 支持 TMPDIR 环境变量，解决临时目录权限问题
- **状态**: 已创建

### 0003-nss-harmonyos-config.patch
- **目标**: NSS coreconf 配置文件
- **作用**: 添加 HarmonyOS 平台配置支持
- **文件**:
  - `HarmonyOS.mk` - 平台编译配置
  - `arch.mk` - 平台识别
  - `config.mk` - 目标平台列表
- **状态**: 已创建

## 后续工作建议

### 短期任务 (优先级: 高)

1. **完成 manifest.mn 批量修改**
   ```bash
   # 查找所有需要修改的 manifest.mn 文件
   find nss/lib -name manifest.mn
   
   # 为每个文件添加 REQUIRES = nspr
   for file in nss/lib/*/manifest.mn; do
     echo "REQUIRES = nspr" >> "$file"
   done
   ```

2. **编译 NSS 库**
   ```bash
   export TMPDIR=/data/storage/el2/base/cache
   export NSPR_INCLUDE_DIR=~/usr/local/include/nspr
   export NSPR_LIB_DIR=~/usr/local/lib
   make nss_build_all
   ```

3. **验证编译产物**
   - 检查库文件依赖关系
   - 运行基础功能测试
   - 确认符号导出正确

### 中期任务

1. **整理归档产物**
   - 复制编译产物到归档目录
   - 更新 manifest.yaml 状态
   - 创建编译报告

2. **集成测试**
   - 与依赖库的兼容性测试
   - OpenSSL 互操作性测试
   - 性能基准测试

3. **文档完善**
   - 编译指南
   - 使用说明
   - API 文档

### 长期目标

1. **上游贡献**
   - 提交 HarmonyOS 支持补丁到 NSS 项目
   - 参与社区讨论和代码审查

2. **持续维护**
   - 跟踪 NSS 上游更新
   - 维护 HarmonyOS 适配补丁
   - 定期重建和测试

## 依赖关系

```
NSS 3.118.1
├── NSPR 4.37 ✅ (已编译)
│   ├── pthread
│   └── dl
├── SQLite3 (可选，系统自带)
├── zlib (可选，已安装)
└── OpenSSL (可选，已安装)
```

## 构建环境

- **操作系统**: OpenHarmony 1.12
- **内核**: HarmonyOS Kernel
- **架构**: aarch64 (ARM64)
- **编译器**: Clang 15.0.4
- **工具链**: LLVM (lld, llvm-ar, llvm-ranlib)
- **构建系统**: gyp-ninja / make

## 参考链接

- [NSS 官方网站](https://developer.mozilla.org/en-US/docs/Mozilla/Projects/NSS)
- [NSS 源码仓库](https://hg.mozilla.org/projects/nss)
- [NSPR 文档](https://developer.mozilla.org/en-US/docs/Mozilla/Projects/NSPR)
- [NSS 3.118.1 发布说明](https://www.mozilla.org/en-US/security/advisories/)

## 更新历史

- **2026-05-25**: 创建归档目录，记录编译进展
- **2026-05-25**: NSPR 4.37 编译成功
- **2026-05-25**: 创建 HarmonyOS 配置文件和补丁
- **当前**: 等待完成 NSS manifest.mn 批量修改

---

**注意**: 本归档为部分产物，NSS 编译尚未完成。完成编译后，将补充库文件、工具程序和头文件等产物。