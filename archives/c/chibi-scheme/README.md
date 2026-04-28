# chibi-scheme — OpenHarmony 预编译包

## 基本信息
- 软件: chibi-scheme
- 描述: Small footprint Scheme for use as a C Extension Language
- 许可证: BSD-3-Clause
- 目标平台: ohos-aarch64

## 可用版本

| 版本 | 状态 | 补丁数 | 测试通过率 | 包大小 |
|------|------|--------|------------|--------|
| 0.12 | ✅ success | 0 | 100% (1225/1225) | 5.3MB |

## 快速安装

### 方法1: 使用安装脚本
```bash
curl -fsSL <url>/install.sh | sh -s -- 0.12
```

### 方法2: 手动安装
```bash
tar xzf chibi-scheme-0.12-ohos-aarch64.tar.gz -C ~/usr/local
cd ~/usr/local && sh install-chibi-scheme-0.12.sh
```

## 编译指导

### 构建系统说明
chibi-scheme使用自定义Makefile构建系统，configure脚本只是提示信息，直接使用make编译。

### 编译命令
```bash
make PREFIX=/storage/Users/currentUser/usr/local
make install PREFIX=/storage/Users/currentUser/usr/local DESTDIR=/path/to/staging
```

### 重要提示
- **无需configure**: 直接运行make即可
- **无需补丁**: 源码无需任何修改
- **平台自动检测**: Makefile.detect自动检测平台

## 补丁清单

**无补丁** - 所有版本在OpenHarmony aarch64上编译均无需修改源码。

## 已知限制

暂无已知限制。所有功能测试通过。

## 功能验证

### 基本执行测试
```bash
$ chibi-scheme -e '(display "Hello from chibi-scheme!\n")'
Hello from chibi-scheme!
```

### 安装的命令行工具
- `chibi-scheme` - Scheme解释器主程序
- `chibi-ffi` - FFI绑定生成工具
- `chibi-doc` - 文档生成工具
- `snow-chibi` - Snow包管理器

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- ~/usr/local/bin 在 PATH 中

---

**最新编译**: 2026-04-24
**维护者**: openharmony-compile-agent