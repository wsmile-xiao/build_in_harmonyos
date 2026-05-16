# kustomize v5.8.1 编译笔记

## 编译信息
- **编译日期**: 2026-05-13
- **编译器**: go1.24.0 linux/arm64
- **平台**: HarmonyOS (OpenHarmony)
- **架构**: aarch64

## 编译过程

### 1. 源码获取
```bash
git clone --depth 1 --branch kustomize/v5.8.1 https://github.com/kubernetes-sigs/kustomize.git
```

### 2. 编译命令
```bash
CGO_ENABLED=0 go build -o ~/usr/local/bin/kustomize-new .
```

### 3. 遇到的问题

#### 问题: Go 链接器权限错误
**错误信息**:
```
link: mapping output file failed: permission denied
```

**原因**: HMDFS 文件系统对 Go 链接器的内存映射操作有限制。

**尝试的解决方案**:
1. ❌ 设置 TMPDIR/GOCACHE/GOTMPDIR 到不同目录
2. ❌ 使用外部链接器 `-linkmode=external`
3. ❌ 使用 `-buildmode=exe`
4. ✅ 首次编译成功（缓存复用）

**最终结果**: 
- 首次 `go build` 成功生成二进制
- 重新编译注入版本号失败（链接器权限）
- 版本号显示为 `v0.0.0-20260209161122-9790a1c3efd2` 而非 `v5.8.1`

### 4. 功能验证
所有核心功能正常:
- `kustomize version` ✅
- `kustomize help` ✅
- `kustomize build` ✅

### 5. ELF 签名
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf ~/usr/local/bin/kustomize-new
```
签名成功，二进制可在鸿蒙系统正常执行。

## 预编译包
- 路径: `archives/k/kustomize/5.8.1/packaging/kustomize-5.8.1-ohos-aarch64.tar.gz`
- 大小: 11M
- 内容: kustomize 二进制文件

## 已知限制

1. **版本号显示问题**: 由于 Go 链接器权限限制，无法通过 ldflags 注入版本号
2. **HMDFS 限制**: Go 链接器在 HMDFS 文件系统上有权限问题，是系统级限制
3. **功能完整性**: 版本号显示不影响核心功能使用

## 建议

对于 kustomize 这类 Go 项目，如果版本号显示很重要，建议:
1. 在 Linux 环境编译后移植
2. 或等待鸿蒙系统更新解除 HMDFS 限制
3. 或使用 Docker 容器编译

---
*编译者: OpenDesk Compile Agent*
*日期: 2026-05-13*