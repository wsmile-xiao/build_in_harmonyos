# dbmate 2.33.0 编译笔记

## 基本信息
- **软件**: dbmate — Go database migration tool
- **版本**: 2.33.0
- **源码**: https://github.com/amacneil/dbmate (tag v2.33.0)
- **编译日期**: 2026-08-06

## 编译环境
- **Go 版本**: 1.26.5 (arm64 linux, via Harmonybrew)
- **CGO**: 启用 (CGO_ENABLED=1)，支持 SQLite 驱动
- **CC**: clang (HarmonyOS NDK toolchain)
- **构建标签**: netgo,osusergo,sqlite_omit_load_extension,sqlite_fts5,sqlite_json
- **链接标志**: -s -extldflags -static (静态链接)

## 编译过程

### Step 1: 获取源码
从 GitHub 下载 dbmate v2.33.0 tarball (SHA256: e7b57143c9ee436e9373e19420e752fef7a0b03807fe381bf7d039c7b9d2f6d6)。

### Step 2: 依赖下载
`go mod download` 通过 goproxy.cn 成功下载所有依赖。

### Step 3: 编译
使用 Go 1.26.5 + CGO_ENABLED=1 编译，包含 SQLite 驱动（go-sqlite3 的 C 代码用 clang 编译）。

**关键问题与解决**:
- E166 (Go linker mmap fails on HMDFS): 将 GOCACHE、GOTMPDIR 和链接器输出路由到 ext2 分区 (/data/storage/el2/base/haps/entry/files/dbmate-2.33.0/)
- E128 (ELF signing): 构建产物通过 binary-sign-tool 签名
- E077 (chmod semantics on HMDFS): 签名后 chmod 0o755 恢复 owner x bit

### Step 4: 验证
- 二进制已签名（ELF签名），可正常执行
- `dbmate --version` 输出: `dbmate version 2.33.0`
- 产物大小: ~31MB (strip 后)

### Step 5: Conan 适配
创建了完整的 Conan 配方 (conanfile.py + conandata.yml + test_package/)，基于 cloudfoundry-cli 和 tlsx 的 Go 项目适配模式。

## 知识提取
- **L3 本版**: Go 工具编译使用 CGO_ENABLED=1 + 静态链接，SQLite 驱动用 clang 编译
- **L2 模式**: Go 项目在 HarmonyOS 上需要 ext2 分区用于链接器输出（E166），ELF 签名（E128）
- **L1 平台**: Go 1.26.5 via Harmonybrew 可正常执行（已签名）
---

**编译结束**: 2026-08-06 06:30
**最终状态**: built
