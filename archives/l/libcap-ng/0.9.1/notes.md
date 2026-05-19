# libcap-ng 0.9.1 编译记录

## 构建信息
- **日期**: 2026-05-16
- **平台**: 鸿蒙系统 aarch64 (HongMeng Kernel 1.12.0)
- **编译器**: gcc（系统编译器）
- **源码**: https://github.com/stevegrubb/libcap-ng/archive/refs/tags/v0.9.1.tar.gz

## 编译过程

### 第一步：获取源码
- 从 GitHub 仓库下载 v0.9.1.tar.gz
- Git 仓库不包含完整的 autotools 配置脚本

### 第二步：构建环境设置
- 设置环境变量（SKILL_ROOT、BUILD_SRC_DIR 等）
- 手动创建 config.h，包含鸿蒙系统特定定义

### 第三步：构建系统问题解决

#### 问题 1：缺少 autotools 辅助文件
- **问题描述**: configure 脚本需要 install-sh、config.guess、config.sub
- **解决方案**: 从 automake 安装目录复制

#### 问题 2：config.guess 系统识别失败
- **问题描述**: config.guess 无法识别鸿蒙系统类型
- **错误信息**: `./config.guess: unable to guess system type`
- **尝试修复**: 指定 `--build=aarch64-linux-gnu --host=aarch64-linux-gnu`

#### 问题 3：configure 脚本不完整
- **问题描述**: configure 包含未展开的宏（AM_INIT_AUTOMAKE、LT_INIT、PKG_PROG_PKG_CONFIG）
- **错误信息**: `./configure[2564]: AM_INIT_AUTOMAKE: inaccessible or not found`
- **根本原因**: Git 仓库的 configure 脚本未完全生成

#### 最终解决方案：手动 Makefile
- 创建 Makefile.manual 绕过 autotools 问题
- 手动编译所有组件

### 第四步：编译
```bash
make -f Makefile.manual
```

**构建产物：**
- libcap-ng.so.0.0.1 (51,584 字节)
- libcap-ng.a (42,240 字节)
- libdrop_ambient.so.0.0.0 (18,688 字节)
- pscap、filecap、netcap、captest 实用工具

### 第五步：测试
- **lib_test**: 通过（退出码 0）
- **thread_test**: 通过（退出码 0）
- 所有测试成功执行

### 第六步：安装
- 安装到 staging 目录（DESTDIR 模式）
- 创建预编译包：libcap-ng-0.9.1-ohos-aarch64.tar.gz
- 验证本地安装

## 使用的编译器标志
- `-fPIC -DPIC` - 位置无关代码
- `-W -Wall -Wshadow -Wundef` - 警告标志
- `-D_GNU_SOURCE` - GNU 扩展
- `-Wl,-z,relro` - RELRO 安全加固

## 使用的依赖
- pthread（用于 thread_test）
- Linux 内核头文件（linux/capability.h）

## 已知问题和解决方案

1. **Autotools configure 无法工作**
   - 创建手动 Makefile
   - 手动定义 config.h

2. **缺少辅助文件**
   - 从现有 automake 安装复制

3. **系统类型无法识别**
   - 手动指定 build/host（aarch64-linux-gnu）

## 创建/修改的文件
- config.h（创建）
- Makefile.manual（创建）

## 验证结果
- 库文件正确安装
- 头文件正确安装
- 实用工具功能正常
- 测试通过

## 编译总结
libcap-ng 0.9.1 在鸿蒙系统上成功编译。由于 autotools 配置脚本与鸿蒙系统不兼容，采用了手动 Makefile 方式构建。所有组件编译成功，测试通过，质量门禁检查通过。

