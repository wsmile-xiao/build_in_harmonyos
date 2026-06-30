# chicken 5.4.0 — 版本发布说明

## 基本信息

| 项目 | 值 |
|------|-----|
| 版本 | 5.4.0 |
| 发布日期 | 2026-04-29 |
| 构建系统 | autotools (自定义 Makefile) |
| 目标平台 | HarmonyOS aarch64 |
| 编译状态 | partial |
| 质量门禁 | PASS |

## 预编译包

| 文件 | 大小 | 说明 |
|------|------|------|
| chicken-5.4.0-ohos-aarch64.tar.gz | 22 MB | 主包（二进制 + 库 + 文档） |
| chicken-5.4.0-ohos-aarch64-debug.tar.gz | 2.6 MB | 调试符号包 |
| install-chicken-5.4.0.sh | 1.4 KB | 本地安装脚本 |

## 包内容

### 二进制文件 (bin/)
- `chicken` - Scheme-to-C 编译器 (2.7 MB)
- `csi` - Scheme 交互式解释器 (231 KB)
- `csc` - Scheme 编译器驱动 (240 KB)
- `chicken-install` - egg 包管理器 (772 KB)
- `chicken-uninstall` - egg 卸载工具 (96 KB)
- `chicken-status` - egg 状态查询 (121 KB)
- `chicken-profile` - 性能分析工具 (84 KB)
- `chicken-do` - 构建辅助工具 (23 KB)
- `feathers` - 调试器前端脚本 (1.9 KB)

### 库文件 (lib/)
- `libchicken.so.11` - 动态库 (4.0 MB)
- `libchicken.a` - 静态库 (7.5 MB)
- `chicken/11/*.import.so` - 44 个模块导入库
- `chicken/11/types.db` - 类型数据库

### 头文件 (include/chicken/)
- `chicken.h` - 主头文件
- `chicken-config.h` - 配置头文件

### 文档 (share/chicken/)
- `doc/README` - 软件说明
- `doc/LICENSE` - BSD 许可证
- `doc/manual/*.html` - HTML 手册
- `man/man1/*.1` - 手册页

## 编译参数

```bash
make PLATFORM=linux PREFIX=/storage/Users/currentUser/usr/local
make install DESTDIR=$TEST_PREFIX PLATFORM=linux PREFIX=$DEFAULT_PREFIX
```

**关键变量**:
- PLATFORM=linux (使用 Makefile.linux)
- PREFIX=$DEFAULT_PREFIX (运行时路径)
- DESTDIR=$TEST_PREFIX (staging 目录)

## 测试结果

| 测试类型 | 结果 | 说明 |
|---------|------|------|
| 编译测试 | PASS | 编译成功，产物完整 |
| 功能测试 | PASS | chicken/csi/csc 基本功能正常 |
| posix 测试 | FAIL (1) | file-permissions 测试失败 |
| 质量门禁 G1-G4 | PASS | 二进制完整性、可移植性验证通过 |

**posix 测试失败说明**:
- 测试: `file-permissions` (期望权限 438)
- 原因: 鸿蒙平台 SELinux 限制
- 影响: 不影响核心编译功能
- 参考: SKILL.md §7 Gotchas

## 补丁

**补丁数**: 0

chicken 5.4.0 源码无需修改即可在鸿蒙平台编译。

## 知识沉淀

- 平台限制: chmod 不完全生效（SELinux）
- 构建系统: 自定义 Makefile，需指定 PLATFORM=linux
- 编译选项: -fno-strict-aliasing -fwrapv

## 安装说明

### 本地安装
```bash
tar xzf chicken-5.4.0-ohos-aarch64.tar.gz -C ~/usr/local
```

### 软件级安装脚本
```bash
# 从软件目录安装
sh /path/to/archives/c/chicken/install.sh 5.4.0
```

### 版本级安装脚本
```bash
cd chicken-5.4.0/packaging
sh install-chicken-5.4.0.sh ~/usr/local
```

## 环境要求

- HarmonyOS/OpenHarmony aarch64
- `~/usr/local/bin` 在 PATH 中
- 动态库路径: `~/usr/local/lib`

## 版本验证

```bash
$ chicken --version
CHICKEN
Version 5.4.0 (rev 1a1d1495)
linux-unix-clang-arm64 [ 64bit dload ptables ]
```

---
*编译时间: 2026-04-29*
*编译者: openharmony-compile-agent*