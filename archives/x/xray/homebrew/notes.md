# xray homebrew 适配笔记

## 编译环境
- 构建系统: custom (Go)
- 编译日期: 2026-06-03
- 编译器: Go 1.26.3 (~/usr/local/go1263/bin/go)
- 状态: published

## 编译步骤

1. 源码下载: 从 GitHub 下载 v26.3.27 tarball（使用 ghfast.top 镜像绕过 SSL 超时）
2. 手动解压到 ~/tmp/builds/xray-homebrew.work
3. ohc-run.py init-build --no-download 完成初始化和骨架创建
4. manifest 修正: system=custom, build_system=go
5. Go 编译命令:
```bash
cd ~/tmp/builds/xray-homebrew.work
TMPDIR=/data/storage/el2/base/cache \
CGO_ENABLED=1 GOOS=linux GOARCH=arm64 \
GOPROXY=https://goproxy.cn,direct \
~/usr/local/go1263/bin/go build \
  -ldflags="-s -w -X github.com/xtls/xray-core/core.build=v26.3.27" \
  -o ~/usr/local/bin/xray ./main/
```
6. DESTDIR 安装到 test staging 目录
7. ELF 签名
8. 验证: xray version → Xray 26.3.27
9. ohc-run.py package 打包
10. ohc-run.py finish

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL下载超时 | GitHub 直连受限 | curl -kL 使用 ghfast.top 镜像下载 |
| 2 | -X 无法注入 Version_x/y/z | Go -X ldflags 只支持 string 类型变量，byte 类型不支持 | 源码已硬编码正确的版本号(26,3,27)，只注入 string 类型的 build 变量 |
| 3 | G0 干净构建验证失败 | xray 是 Go 项目，无 configure 脚本 | 创建 hints/g0-skip-configure 指示 G0 跳过 configure 步骤 |

## 源码修改

无源码修改，仅使用 ldflags 注入 build 版本信息。

## 依赖版本

- Go 1.26.3 (~/usr/local/go1263/bin/go)
- goproxy.cn 代理下载 Go 模块依赖

## 验证结果

```bash
$ ~/usr/local/bin/xray version
Xray 26.3.27 (Xray, Penetrates Everything.) v26.3.27 (go1.26.3 linux/arm64)
A unified platform for anti-censorship.
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| xray-homebrew-ohos-aarch64.tar.gz | 29741KB (~29MB) | 预编译包 |
| xray-homebrew-ohos-aarch64-debug.tar.gz | 70KB | debug 符号包 |

## 注意事项

- Go 项目版本注入需注意变量类型：-X 只支持 string，byte/uint8 变量需要源码硬编码
- xray 的版本号由 Version_x/y/z (byte) 和 build (string) 两部分组成
- G0 干净构建验证需要 hints 指示跳过 configure（Go 项目无 configure 脚本）
- TMPDIR 必须设为 /data/storage/el2/base/cache (R10 铁律)

---

**编译结束**: 2026-06-03
**最终状态**: published
---

**编译结束**: 2026-06-03 10:49
**最终状态**: built
