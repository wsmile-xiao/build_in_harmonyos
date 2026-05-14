# chicken — HarmonyOS aarch64 预编译包

CHICKEN 是一个 Scheme-to-C 编译器，支持 R5RS Scheme 标准，提供高效的编译和解释能力。

## 快速安装

### 方式 1: 直接解压
```bash
tar xzf chicken-5.4.0-ohos-aarch64.tar.gz -C ~/usr/local
```

### 方式 2: 使用安装脚本
```bash
# 从软件目录安装（会自动下载）
sh install.sh 5.4.0

# 或从本地归档安装
cd archives/c/chicken/5.4.0/packaging
sh install-chicken-5.4.0.sh ~/usr/local
```

### 验证安装
```bash
$ chicken --version
CHICKEN Version 5.4.0 (rev 1a1d1495)
```

## 可用版本

| 版本 | 状态 | 补丁数 | 包大小 | 发布日期 |
|------|------|--------|--------|----------|
| 5.4.0 | partial | 0 | 22 MB | 2026-04-29 |

## 5.4.0 版本详情

### 预编译包

| 文件 | 大小 | 说明 |
|------|------|------|
| chicken-5.4.0-ohos-aarch64.tar.gz | 22 MB | 主包 |
| chicken-5.4.0-ohos-aarch64-debug.tar.gz | 2.6 MB | 调试符号 |
| install-chicken-5.4.0.sh | 1.4 KB | 安装脚本 |

### 包内容

#### 二进制文件 (bin/)
| 文件 | 大小 | 说明 |
|------|------|------|
| chicken | 2.7 MB | Scheme-to-C 编译器 |
| csi | 231 KB | 交互式解释器 |
| csc | 240 KB | 编译器驱动 |
| chicken-install | 772 KB | egg 包管理器 |
| chicken-uninstall | 96 KB | egg 卸载工具 |
| chicken-status | 121 KB | egg 状态查询 |
| chicken-profile | 84 KB | 性能分析工具 |
| chicken-do | 23 KB | 构建辅助工具 |
| feathers | 1.9 KB | 调试器前端 |

#### 库文件 (lib/)
| 文件 | 大小 | 说明 |
|------|------|------|
| libchicken.so.11 | 4.0 MB | 动态库 |
| libchicken.a | 7.5 MB | 静态库 |
| chicken/11/*.import.so | - | 44 个模块导入库 |
| chicken/11/types.db | - | 类型数据库 |

#### 头文件 (include/chicken/)
- chicken.h
- chicken-config.h

#### 文档 (share/chicken/)
- doc/README, LICENSE, DEPRECATED
- manual/*.html (HTML 手册)
- man/man1/*.1 (手册页)

### 编译信息

| 项目 | 值 |
|------|-----|
| 构建系统 | autotools (自定义 Makefile) |
| 编译参数 | PLATFORM=linux |
| 编译器 | gcc (clang 15.0.4) |
| 优化选项 | -Os -fomit-frame-pointer |
| 目标平台 | ohos-aarch64 |
| 质量门禁 | PASS (G1-G4) |
| 补丁数 | 0 |
| 编译状态 | partial |

### 测试结果

| 测试类型 | 结果 | 说明 |
|---------|------|------|
| 编译测试 | PASS | 编译成功 |
| 功能测试 | PASS | 核心功能正常 |
| posix 测试 | PARTIAL | 1 个失败 |
| 总测试数 | 6377+ | 6376+ 通过 |

**posix 测试失败说明**:
- 失败测试: file-permissions
- 原因: 鸿蒙 SELinux 限制
- 影响: 不影响核心编译功能
- 状态: partial

### 已知限制

1. **文件权限**: posix file-permissions 测试失败（SELinux）
2. **并行编译**: 不支持 make -j
3. **编译时间**: 约 200 秒

## 环境要求

- **平台**: HarmonyOS/OpenHarmony aarch64
- **PATH**: `~/usr/local/bin`
- **库路径**: `~/usr/local/lib`

## 使用示例

### 编译 Scheme 文件
```bash
# 直接编译
csc hello.scm -o hello

# 或先转 C 再编译
chicken hello.scm -output-file hello.c
gcc hello.c -lchicken -o hello
```

### 交互式解释器
```bash
csi
#;1> (define (square x) (* x x))
#;2> (square 5)
25
```

### 安装 egg
```bash
chicken-install srfi-1
chicken-status
```

## 相关链接

- 官网: https://call-cc.org
- 文档: https://wiki.call-cc.org/manual
- Eggs: https://wiki.call-cc.org/eggs

---
*维护: openharmony-compile-agent*