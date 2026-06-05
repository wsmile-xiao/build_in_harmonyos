# tenv 4.12.2 适配笔记

## 编译环境
- 构建系统: Go
- 编译日期: 2026-05-19
- 编译器: clang/clang++ (用于 Go 工具链签名)
- 状态: built

## 编译步骤

### 1. 获取源码
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build tenv 4.12.2 --url=https://github.com/tofuutils/tenv/tarball/v4.12.2
```

源码来自 GitHub: https://github.com/tofuutils/tenv/tarball/v4.12.2

### 2. 安装 Go 工具链

由于 Go 官方预编译包需要 ELF 签名才能在 HarmonyOS 上运行，采用以下方法：

1. 下载 Go 1.25.0 预编译包（linux-arm64）：
   ```bash
   curl -fsSL https://mirrors.aliyun.com/golang/go1.25.0.linux-arm64.tar.gz -o $TMPDIR/go1.25.0.linux-arm64.tar.gz
   tar xzf go1.25.0.linux-arm64.tar.gz
   mv go ~/usr/local/
   ```

2. 对 Go 工具链进行 ELF 签名：
   ```bash
   # 签名 go 和 gofmt
   /data/service/hnp/bin/binary-sign-tool sign -selfSign 1 -inFile go -outFile go-signed -signAlg SHA256withECDSA
   /data/service/hnp/bin/binary-sign-tool sign -selfSign 1 -inFile gofmt -outFile gofmt-signed -signAlg SHA256withECDSA
   
   # 签名 Go 工具链（compile、link、asm 等）
   cd ~/usr/local/go/pkg/tool/linux_arm64
   for tool in asm cgo compile cover link preprofile vet; do
     /data/service/hnp/bin/binary-sign-tool sign -selfSign 1 -inFile $tool -outFile $tool-signed -signAlg SHA256withECDSA
     mv $tool-signed $tool
     chmod +x $tool
   done
   ```

3. 验证 Go 可用：
   ```bash
   export PATH=~/usr/local/go/bin:$PATH
   go version
   # 输出: go version go1.25.0 linux/arm64
   ```

### 3. 编译 tenv

使用 Go 构建系统：
```bash
export PATH=~/usr/local/go/bin:$PATH
export GOPROXY=https://goproxy.cn,direct
export GOPATH=~/tmp/go-cache
export GOCACHE=~/tmp/go-cache/build-cache
cd /data/storage/el2/base/cache/builds/tenv-4.12.2.work
make build
```

编译生成 6 个二进制文件：
- tenv (19M)
- tofu (2.5M)
- terraform (2.5M)
- terragrunt (2.5M)
- terramate (2.5M)
- atmos (2.5M)

### 4. 签名编译产物

对所有编译出的二进制文件进行 ELF 签名：
```bash
cd build
for bin in atmos tenv terraform terragrunt terramate tofu; do
  /data/service/hnp/bin/binary-sign-tool sign -selfSign 1 -inFile $bin -outFile $bin-signed -signAlg SHA256withECDSA
  mv $bin-signed $bin
  chmod +x $bin
done
```

### 5. Staging 安装

```bash
source .build-context-tenv-4.12.2
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp -a build/* $TEST_PREFIX/$DEFAULT_PREFIX/bin/
```

### 6. 本地安装验证

```bash
cp -a build/* ~/usr/local/bin/
~/usr/local/bin/tenv version
# 输出: tenv version dev
~/usr/local/bin/tenv help
```

### 7. 创建预编译包

```bash
cd $TEST_PREFIX/$DEFAULT_PREFIX
tar czf $ARCHIVE_DIR/packaging/tenv-4.12.2-ohos-aarch64.tar.gz bin/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah URL 404 | tenv 不在 Savannah 发布 | 从 GitHub releases 获取源码 |
| 2 | Go 工具链无法运行 | ELF 未签名导致权限拒绝 | 使用 binary-sign-tool self-sign 签名 |
| 3 | Go 无法访问 proxy.golang.org | 网络限制 | 设置 GOPROXY=https://goproxy.cn,direct |
| 4 | Go compile 工具无法运行 | Go 工具链文件也需要 ELF 签名 | 签名所有 Go 工具链文件（asm、compile、link 等） |

## 源码修改

无源码修改，tenv 编译无需补丁。

## 依赖版本

- go: 1.25.0 (预编译包，需要 ELF 签名)
- Go 依赖包: 通过 GOPROXY=https://goproxy.cn,direct 自动下载

## 验证结果

```bash
# 二进制文件签名验证
for f in tenv tofu terraform terragrunt terramate atmos; do
  readelf -S $f | grep .codesign
done
# 所有 6 个文件都有 .codesign section

# 功能验证
~/usr/local/bin/tenv version
# 输出: tenv version dev

~/usr/local/bin/tenv --help
# 显示完整帮助信息

~/usr/local/bin/tenv tofu --help
# 显示 tofu 子命令帮助

~/usr/local/bin/tenv tf --help
# 显示 terraform 子命令帮助
```

## ELF 签名覆盖率

- 总二进制文件数: 6
- 已签名文件数: 6
- 签名覆盖率: 100%

所有二进制文件都有 .codesign section，符合 HarmonyOS 可执行要求。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tenv-4.12.2-ohos-aarch64.tar.gz | 32M | 预编译包，包含所有 6 个二进制文件 |

## Go 工具链安装说明

Go 工具链已安装到 ~/usr/local/go，需要将其打包为预编译包供后续 Go 项目使用：

- 位置: ~/usr/local/go
- 版本: 1.25.0
- 状态: 已签名，可运行
- 包含工具: go, gofmt, 以及 pkg/tool/linux_arm64/* 工具链

建议：将 Go 工具链打包为独立预编译包（go-1.25.0-ohos-aarch64.tar.gz），供其他 Go 项目编译使用。

## 注意事项

1. **ELF 签名是关键**: Go 工具链的所有可执行文件都需要 ELF 签名才能在 HarmonyOS 上运行
2. **GOPROXY 必须设置**: 默认代理无法访问，必须使用国内镜像
3. **无传统 configure**: Go 项目使用 go build，不需要 configure 步骤
4. **静态链接**: Go 编译产物是静态链接的 ELF 文件，不依赖动态库
5. **质量门禁适配**: verify-build 脚本需要适配 Go 项目，当前无法正确识别 Go 构建系统
---

**编译结束**: 2026-05-19 20:16
**最终状态**: built
