# source-to-image v1.6.1 编译笔记

## 编译信息
- **编译日期**: 2026-05-28
- **编译器**: go1.25.8 linux/arm64
- **平台**: HarmonyOS (OpenHarmony) aarch64
- **构建系统**: go (Go module project with vendor directory)
- **CGO_ENABLED**: 0 (static binary)

## 编译过程

### 1. 源码获取
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build source-to-image 1.6.1 \
  --url=https://github.com/openshift/source-to-image/archive/refs/tags/v1.6.1.tar.gz
```

### 2. 编译命令
```bash
# Go linker mmap fails on HMDFS filesystem, must use /data directory for output
export PATH="$HOME/usr/local/go/bin:$PATH"
export CGO_ENABLED=0
export GOCACHE="/data/storage/el2/base/haps/entry/files/go-build"
export GOTMPDIR="/data/storage/el2/base/haps/entry/files/tmp-go"

go build -mod vendor -tags "exclude_graphdriver_btrfs" \
  -o /data/storage/el2/base/haps/entry/files/s2i ./cmd/s2i/
```

### 3. 遇到的问题

#### 问题1: CGO_ENABLED=1 导致 btrfs 头文件缺失
**错误信息**: `fatal error: 'btrfs/version.h' file not found`
**解决方案**: 设置 `CGO_ENABLED=0`（与上游 Makefile 一致）

#### 问题2: Go 链接器 mmap 权限错误
**错误信息**: `link: mapping output file failed: permission denied`
**根因**: HMDFS 文件系统不支持 Go 链接器所需的 mmap 操作
**解决方案**: 将输出二进制和 GOTMPDIR 设置到 /data/storage 目录（支持 mmap）

#### 问题3: 版本号注入失败
**问题**: 无法通过 ldflags 注入版本号（因链接器限制）
**结果**: `s2i version` 显示 "unknown" 而非 "1.6.1"
**影响**: 功能完整，仅版本号显示不正确

#### 问题4: make check 测试二进制需要 ELF 签名
**问题**: Go 测试二进制在 HMDFS 上无法直接执行
**解决方案**: 将测试二进制编译到 /data 目录，ELF 签名后手动执行

### 4. make check 结果
- pkg/util: PASS
- pkg/scripts: PASS
- pkg/util/fs: PASS
- pkg/util/status: PASS
- pkg/tar: FAIL（chmod/chown 在 HMDFS 上不生效，E046 平台限制）
- Docker/集成测试: 跳过（需要 Docker 运行时）

### 5. 安装
```bash
# 手动安装到 DEFAULT_PREFIX
cp /data/storage/el2/base/haps/entry/files/s2i $DEFAULT_PREFIX/bin/s2i
cp $DEFAULT_PREFIX/bin/s2i $DEFAULT_PREFIX/bin/sti  # sti 是 s2i 的兼容别名
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf $DEFAULT_PREFIX/bin/s2i
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf $DEFAULT_PREFIX/bin/sti
```

### 6. 功能验证
```bash
$ s2i version          # 输出: s2i unknown（版本号限制）
$ s2i --help           # 输出正常帮助信息
$ s2i build --help     # 输出正常
$ sti version          # 输出: s2i unknown (deprecated warning)
```

## 无源码修改
本项目无需修改任何源码文件，所有编译通过环境变量和构建参数解决：
- `CGO_ENABLED=0`
- `-mod vendor`
- `-tags exclude_graphdriver_btrfs`
- 输出路径使用 /data 目录（避开 HMDFS mmap 限制）

## 已知限制
1. **版本号**: s2i version 显示 "unknown"（ldflags 无法注入）
2. **HMDFS**: Go 链接器在 HMDFS 上有 mmap 限制，需要输出到 /data
3. **chmod**: tar 包测试因 HMDFS chmod 限制失败（E046）

---
*编译者: OpenDesk Compile Agent*
*日期: 2026-05-28*
---

**编译结束**: 2026-05-28 11:40
**最终状态**: built
