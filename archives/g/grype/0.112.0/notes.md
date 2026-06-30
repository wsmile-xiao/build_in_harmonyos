# grype 0.112.0 适配笔记

## 编译环境
- 构建系统: Go (容器镜像漏洞扫描器)
- 编译日期: 2026-05-26
- 编译器: 预编译二进制（Go gc compiler, go1.26.2）
- 状态: built

## 编译步骤

由于 HarmonyOS HMDFS 平台限制，Go linker 无法在 HMDFS 上完成编译（fallocate syscall 返回 EACCES，W^X mmap 政策限制）。因此采用官方预编译二进制方式部署：

1. 从 GitHub Releases 下载 `grype_0.112.0_linux_arm64.tar.gz`（通过 gh-proxy.com 镜像）
2. 提取 grype 二进制文件
3. 使用 `ohc sign-elf` 签名（添加 .codesign section）
4. 复制到 staging 目录并验证

```bash
# 下载预编译二进制
wget -O ~/tmp/grype-prebuilt.tar.gz "https://gh-proxy.com/https://github.com/anchore/grype/releases/download/v0.112.0/grype_0.112.0_linux_arm64.tar.gz"
tar -xzf ~/tmp/grype-prebuilt.tar.gz -C ~/tmp/

# 签名
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf ~/tmp/grype

# 安装到 staging
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp ~/tmp/grype $TEST_PREFIX/$DEFAULT_PREFIX/bin/grype
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf $TEST_PREFIX/$DEFAULT_PREFIX/bin/grype

# 验证
$DEFAULT_PREFIX/bin/grype version
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go linker "mapping output file failed: permission denied" | HMDFS 的 fallocate syscall 返回 EACCES；W^X mmap 政策禁止同时写入和执行 | 使用官方预编译二进制代替源码编译 |
| 2 | HMDFS 上新创建的 ELF 二进制无法执行 | HMDFS 自动添加 security.isolate SELinux 属性 | 使用 ohc sign-elf 添加 .codesign section |
| 3 | GitHub 直连超时 | 网络限制 | 使用 gh-proxy.com 镜像下载 |
| 4 | Go 依赖下载超时 | proxy.golang.org 不可达 | 使用 GOPROXY=https://goproxy.cn |

## 源码修改

无源码修改。使用官方预编译二进制部署。

## 依赖版本

- grype 0.112.0 (预编译二进制, Go 1.26.2)
- ohc sign-elf (binary-sign-tool -selfSign 1)

## 验证结果

```bash
$DEFAULT_PREFIX/bin/grype version
Application:         grype
Version:             0.112.0
BuildDate:           2026-05-01T18:57:12Z
GitCommit:           244f2a10a5668078fcf771454bbd832b3a5b9e8a
GitDescription:      v0.112.0
Platform:            linux/arm64
GoVersion:           go1.26.2
Compiler:            gc
Syft Version:        v1.44.0
Supported DB schema: 6
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| grype-0.112.0-ohos-aarch64.tar.gz | ~76MB | grype 二进制预编译包 |
| grype-0.112.0-ohos-aarch64-debug.tar.gz | - | 调试符号包 |

## 注意事项

1. Go 项目在 HMDFS 平台无法源码编译，这是平台限制而非软件适配问题
2. 与 syft、skopeo 等 Go 项目面临相同的 linker 限制
3. 部署使用官方预编译二进制 + ohc sign-elf 签名方案
4. 预编译二进制为官方发布版本，未经源码修改
---

**编译结束**: 2026-05-26 22:29
**最终状态**: built
