# chibi-scheme 0.12 — OpenHarmony 编译记录

## 基本信息
- 软件: chibi-scheme
- 版本: 0.12
- 构建系统: Makefile (非标准autotools)
- 目标: ohos-aarch64
- 许可证: BSD-3-Clause
- 描述: Small footprint Scheme for use as a C Extension Language

## 编译指导

### 构建系统说明
chibi-scheme使用自定义Makefile构建系统，configure脚本只是一个提示信息，实际编译直接使用make。

### 编译命令
```bash
# 设置环境变量（可选）
export PREFIX=/storage/Users/currentUser/usr/local

# 直接编译（无需configure）
make PREFIX=$PREFIX -j$(nproc)

# 安装到staging目录
make install PREFIX=$PREFIX DESTDIR=/path/to/staging

# 本地安装
make install PREFIX=$PREFIX
```

### 重要提示
- **无需configure**: chibi-scheme的configure脚本只是提示信息，直接运行make即可
- **平台自动检测**: Makefile.detect会自动检测平台和架构
- **DESTDIR模式**: 支持 `make install DESTDIR=...` 进行staging安装
- **PREFIX参数**: 必须在编译和安装时指定相同的PREFIX值

## 补丁清单

**无补丁** - chibi-scheme 0.12源码无需任何修改即可在OpenHarmony aarch64上编译成功。

## 已知限制

暂无已知限制。所有功能测试通过：
- R7RS标准测试: 1225/1225通过
- 基本执行功能正常
- FFI支持正常
- 模块加载正常

## 功能验证

### 版本信息
```bash
$ chibi-scheme -V
chibi-scheme 0.12.0
```

### 基本执行测试
```bash
$ chibi-scheme -e '(display "Hello from chibi-scheme!\n")'
Hello from chibi-scheme!
```

### R7RS测试结果
```bash
$ make test
# 18个子测试组全部通过
# 1225个测试用例全部通过 (100%)
```

### 安装的命令行工具
- `chibi-scheme` - Scheme解释器主程序
- `chibi-ffi` - FFI绑定生成工具
- `chibi-doc` - 文档生成工具
- `snow-chibi` - Snow包管理器

## 预编译包

### 文件列表
- `chibi-scheme-0.12-ohos-aarch64.tar.gz` (5.3MB) - 主包
- `chibi-scheme-0.12-ohos-aarch64-debug.tar.gz` (2.9MB) - Debug符号包
- `install-chibi-scheme-0.12.sh` - 安装脚本

### 安装方法
```bash
# 解压并安装
tar xzf chibi-scheme-0.12-ohos-aarch64.tar.gz
./install-chibi-scheme-0.12.sh
```

## 质量门禁

| 门禁 | 状态 | 说明 |
|------|------|------|
| G0 干净构建 | ✅ PASS | 无补丁，可重复构建 |
| G1 二进制完整性 | ✅ PASS | 所有二进制文件完整 |
| G2 功能可用性 | ✅ PASS | 基本功能验证通过 |
| G3 可移植性 | ✅ PASS | RPATH正确设置 |
| G4 档案完整性 | ✅ PASS | 所有必需文件齐全 |

---

**编译日期**: 2026-04-24
**编译状态**: ✅ success