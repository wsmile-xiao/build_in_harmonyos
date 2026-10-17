# osv-scanner 2.1.0 适配笔记

## 编译环境
- 构建系统: custom (Go 项目，使用 go build)
- 编译日期: 2026-07-02
- 编译器: clang/clang++ (仅用于Go工具链签名验证)
- Go 版本: go1.24.4 linux/arm64
- Go module: github.com/google/osv-scanner/v2
- 状态: built (conan-verify 8道门禁全部PASS)

## 编译步骤

### 1. 环境准备
```bash
export GOROOT="/storage/Users/currentUser/usr/local/go"
export PATH="/storage/Users/currentUser/tmp/go_bin:$PATH"
export GOPATH="$HOME/go"
export GOPROXY="https://goproxy.cn,direct"
export TMPDIR="$HOME/tmp"
export GOCACHE="$HOME/tmp/go-cache"
export GOTMPDIR="$HOME/tmp/go-tmp"
export GOOS=linux
export GOARCH=arm64
export CGO_ENABLED=0
```

### 2. 签名 Go 内部工具
Go 工具链的内部工具（compile, link, asm 等）位于 GOROOT/pkg/tool/linux_arm64/，
这些工具未签名，无法在 OHOS 上执行。需要用 binary-sign-tool 签名所有工具：
```bash
TOOLDIR="$GOROOT/pkg/tool/linux_arm64"
for tool in compile link asm buildid cgo cover fix nm objdump pack preprofile test2json trace addr2line covdata doc pprof; do
    /data/service/hnp/bin/binary-sign-tool sign -inFile "$TOOLDIR/$tool" -outFile "/tmp/$tool-signed" -selfSign 1 -signAlg SHA256withECDSA
    cp "/tmp/$tool-signed" "$TOOLDIR/$tool"
done
```

### 3. 创建 toolexec 包装器（关键 OHOS 适配）
Go 链接器使用 `fallocate()` 系统调用预分配输出文件空间。
HMDFS/tmpfs 文件系统不支持 fallocate，返回 EACCES (Permission denied)。
Go 链接器只忽略 ENOTSUP/EPERM，不忽略 EACCES，导致链接失败。

解决方案：创建 toolexec 包装器，拦截链接工具调用，将输出重定向到 /dev/shm
（/dev/shm 支持 fallocate），链接完成后再复制回原路径。

包装器位于 `$HOME/tmp/toolexec_wrapper.sh`。

### 4. 下载依赖
```bash
cd /storage/Users/currentUser/tmp/builds/osv-scanner-2.1.0.work/
go mod download
```

### 5. 编译二进制
```bash
# 编译 osv-scanner
go build -toolexec $HOME/tmp/toolexec_wrapper.sh -o osv-scanner ./cmd/osv-scanner/

# 编译 osv-reporter
go build -toolexec $HOME/tmp/toolexec_wrapper.sh -o osv-reporter ./cmd/osv-reporter/
```

### 6. 签名编译后的二进制
```bash
/data/service/hnp/bin/binary-sign-tool sign -inFile osv-scanner -outFile osv-scanner-signed -selfSign 1 -signAlg SHA256withECDSA
rm -f osv-scanner && mv osv-scanner-signed osv-scanner && chmod +x osv-scanner

/data/service/hnp/bin/binary-sign-tool sign -inFile osv-reporter -outFile osv-reporter-signed -selfSign 1 -signAlg SHA256withECDSA
rm -f osv-reporter && mv osv-reporter-signed osv-reporter && chmod +x osv-reporter
```

### 7. Staging 安装
```bash
TEST_PREFIX="/storage/Users/currentUser/tmp/staging/osv-scanner"
mkdir -p "$TEST_PREFIX/bin"
cp osv-scanner osv-reporter "$TEST_PREFIX/bin/"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go内部工具无法执行 (Permission denied) | GOROOT/pkg/tool/ 下的二进制未签名 | 用 binary-sign-tool 签名所有内部工具 |
| 2 | Go链接器失败 "mapping output file failed: permission denied" | fallocate() 在 HMDFS/tmpfs 上返回 EACCES，Go链接器不忽略此错误码 | 创建 toolexec 包装器，将链接器输出重定向到 /dev/shm |
| 3 | LD_PRELOAD 不生效 | Go 的 syscall.Fallocate 直接使用系统调用，不经过 libc | 改用 toolexec 包装器方案 |
| 4 | Conan self.run() env 参数错误 | Conan 2.x 要求 env 是列表 ['KEY=VALUE'] 而非字典 | 将 env 字典转换为列表格式 |
| 5 | Conan package() 未复制二进制 | basic_layout 中 self.build_folder 指向子目录，二进制在 self.source_folder | 改用 self.source_folder 作为 copy() 的 src |
| 6 | test_package 执行失败 'deps_cpp_info' | Conan 2.x 移除了 deps_cpp_info 属性 | 改用 self.dependencies[name].package_folder |

## 源码修改

无补丁。源码未修改，所有适配通过环境变量和工具链包装器完成。

## 依赖版本

- Go: go1.24.4 linux/arm64 (已签名)
- binary-sign-tool: OHOS SDK 26.0.0.18
- Conan: 2.29.1 (OHOS 适配版)
- clang: 15.0.4

## 验证结果

```bash
$ ./osv-scanner --version
osv-scanner version: 2.1.0
commit: n/a
built at: n/a

$ ./osv-reporter --version
osv-scanner version: 2.1.0
commit: n/a
built at: n/a
```

Conan-verify 8道门禁结果：
- G0: PASS (预构建风险评估)
- G1: PASS (配方完整性)
- G2: PASS (conan create 干净构建)
- G3: PASS (系统同名库隔离 R26)
- G4: PASS (产物完整性)
- L2: PASS (smoke test)
- L4: PASS (安全扫描 checksec)
- L5: PASS (产物基线 SHA256)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| osv-scanner | ~61.6 MB | 已签名 Go 二进制 (osv-scanner 主程序) |
| osv-reporter | ~49.2 MB | 已签名 Go 二进制 (osv-reporter 报告工具) |

## 注意事项

1. **Go 工具链签名**: GOROOT/pkg/tool/linux_arm64/ 下的所有工具必须签名才能执行。
   如果 Go 工具链被重新安装或更新，需要重新签名这些工具。

2. **toolexec 包装器**: $HOME/tmp/toolexec_wrapper.sh 是 OHOS 上的 Go 编译必需品。
   如果该文件丢失，Go 编译将失败（链接器 fallocate 错误）。
   该文件需要在 PATH 中可执行，且 shebang 必须指向 OHOS 上的 bash 路径。

3. **二进制签名**: 所有编译出的 Go 二进制必须用 binary-sign-tool 签名才能执行。
   conanfile.py 的 build() 方法已包含自动签名步骤。

4. **CGO_ENABLED=0**: 纯 Go 编译，避免 C 依赖。如果未来需要 CGO，
   需要额外配置 C 编译器和交叉编译环境。

---

## 功能测试

**测试日期**: 2026-07-02
**测试结论**: ✅ 通过 — 软件可在鸿蒙平台上正常使用

### 测试覆盖

| 类别 | 测试数 | 通过 | 失败 |
|------|--------|------|------|
| 基础功能 (--version/--help) | 5 | 5 | 0 |
| 在线扫描 (npm/Maven/Go) | 5 | 5 | 0 |
| 输出格式 (table/JSON/Markdown/SARIF/CycloneDX/SPDX/HTML) | 8 | 8 | 0 |
| 错误处理 | 4 | 4 | 0 |
| 其他功能 (verbosity/fix/递归) | 3 | 3 | 0 |
| osv-reporter | 3 | 3 | 0 |
| **合计** | **28** | **28** | **0** |

### 关键测试结果

1. **在线漏洞扫描**: 成功访问 OSV API (api.osv.dev)，发现 lodash 4.17.20 的 5 个漏洞 (CVSS 5.3-8.1)、log4j-core 2.14.0 的 7 个漏洞 (CVSS 最高 10.0)、Go stdlib 1.21.99 的 48 个漏洞
2. **多生态支持**: npm (package-lock.json)、Maven (pom.xml)、Go (go.mod) 均正常扫描
3. **所有输出格式正常**: table/JSON/Markdown/SARIF/CycloneDX 1.5/SPDX 2.3/HTML 全部通过
4. **文件输出**: --output 参数正常写入文件
5. **错误处理**: 退出码语义清晰 (127=文件错误, 128=参数错误, 1=发现漏洞)

### 已知限制

| 限制 | 影响 | 说明 |
|------|------|------|
| Go call analysis 不可用 | 🟡 低 | Go 不在默认 PATH 中，call analysis 为可选功能，不影响核心扫描 |
| 离线模式需预下载数据库 | 🟡 低 | 需先执行 --download-offline-databases |
| fix 命令需完整格式 lockfile | 🟡 低 | 简化测试数据缺少 root node，实际项目完整 lockfile 不受影响 |

详细测试报告: `reports/functional-test-report.md`

---

**编译结束**: 2026-07-02 15:37
**功能测试结束**: 2026-07-02 16:06
**最终状态**: built (conan-verify 全部 PASS，功能测试 28/28 PASS，未执行 CI upload)
