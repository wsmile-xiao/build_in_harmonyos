# Go 1.21.13 编译笔记

## 编译状态

**状态**: published（已编译并发布）
**日期**: 2026-06-08

## 编译过程

### 1. Bootstrap 设置

使用已签名的 Go 1.24.3 作为 bootstrap 编译器：
```bash
export GOROOT_BOOTSTRAP=~/usr/local/go-1.24.3
export CGO_ENABLED=0
export TMPDIR=/data/storage/el2/base/cache
```

### 2. 源码编译

```bash
cd $BUILD_SRC_DIR/src
./make.bash
```

### 3. ELF 签名问题与解决

**问题**: Go 生成的二进制有非标准 ELF 格式（SHT_STRTAB string table 未 null-terminated），直接签名会失败。

**解决方案**:
1. 先用 `strip` 处理所有二进制，使其符合标准 ELF 格式
2. 然后用 `sign-elf` 签名

```bash
find $BUILD_SRC_DIR/bin -type f -exec strip {} \;
find $BUILD_SRC_DIR/pkg/tool -type f -exec strip {} \;
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf $BUILD_SRC_DIR/bin/*
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf $BUILD_SRC_DIR/pkg/tool/linux_arm64/*
```

### 4. 源码修改

修改了 `src/cmd/dist/buildtool.go` 和 `src/cmd/dist/build.go`，在构建步骤后自动调用签名：
- `signGoBootstrap()`: 签名 go_bootstrap
- `signToolchain()`: 签名 toolchain2 和 toolchain3 的所有工具

### 5. 验证

```bash
go version
# 输出: go version go1.21.13 linux/arm64
```

编译的 Hello World 程序在签名后可正常执行。

## 关键发现

1. **Go ELF 签名必须先 strip**: 这是 OpenHarmony 平台的特殊要求
2. **HMDFS 权限限制**: 需要设置 TMPDIR 到可写目录
3. **Go 自举编译**: 需要已签名的 bootstrap Go

## 质量门禁

- G0 干净构建验证: PASS
- G1 二进制完整性: PASS
- G2 功能可用性: PASS
- G3 可移植性: PASS（静态编译，无动态依赖）
- G4 档案完整性: PASS

## 产物

- 预编译包: `go-1.21.13-ohos-aarch64.tar.gz` (210MB)
- 安装路径: `~/usr/local/go-1.21.13`
- 签名二进制数: 21个（go, gofmt, 及 19 个工具链工具）