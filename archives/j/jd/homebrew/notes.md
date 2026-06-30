# jd homebrew 适配笔记

## 编译环境
- 构建系统: custom (Go)
- 编译日期: 2026-06-03
- 编译器: Go 1.26.3 (~/usr/local/go1263/bin/go)
- 状态: built

## 编译步骤

1. 下载源码: v2.5.0.tar.gz (2.2MB, via ghproxy.net mirror, SSL证书问题无法直连GitHub)
2. init-build: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build jd homebrew --url=file://... --no-download`
3. 修正manifest: system=custom, build_system=go
4. Go编译:
   ```
   cd ~/tmp/builds/jd-homebrew.work
   CGO_ENABLED=1 GOOS=linux GOARCH=arm64 GOPROXY=https://goproxy.cn,direct \
     ~/usr/local/go1263/bin/go build -ldflags="-s -w" -o jd ./v2/jd/main.go
   ```
5. DESTDIR安装: `cp jd $TEST_PREFIX/$DEFAULT_PREFIX/bin/jd` (R20铁律)
6. 本地安装: `cp jd $DEFAULT_PREFIX/bin/jd`
7. ELF签名: `python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf $DEFAULT_PREFIX/bin/jd`
8. 验证: `~/usr/local/bin/jd --version` → jd version 2.5.0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL下载失败 | 鸿蒙平台SSL证书问题，无法直连github.com | 使用ghproxy.net镜像下载，再用file:// URL + --no-download |
| 2 | 版本注入(ldflags -X) | jd v2/jd/main.go中version是const而非var | const="2.5.0"已硬编码正确版本，无需ldflags注入 |
| 3 | R10 TMPDIR | /tmp只读(E002) | TMPDIR=/data/storage/el2/base/cache |

## 源码修改

无源码修改，无需补丁。

## 依赖版本

- Go 1.26.3 (~/usr/local/go1263/bin/go)
- 无额外编译依赖 (纯Go项目，无C库依赖)

## 验证结果

```bash
$ ~/usr/local/bin/jd --version
jd version 2.5.0

$ file ~/usr/local/bin/jd
ELF executable, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), stripped

$ ls -la ~/usr/local/bin/jd
-rwxrwx--- 1 20001006 file_manager 6739840 2026-06-03 10:30 jd
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ~/usr/local/bin/jd | 6.74MB (stripped+signed) | ELF aarch64 binary |

## 注意事项

- jd是Go项目，入口为 `./v2/jd/main.go`（不是根目录的main.go）
- version是const而非var，无法用ldflags -X注入，但源码已硬编码正确版本号"2.5.0"
- Homebrew formula确认: `system "go", "build", *std_go_args(ldflags: "-s -w"), "./v2/jd/main.go"`
- go.mod指定go 1.24.0，但Go 1.26.3向下兼容可正常编译

---

**编译结束**: 2026-06-03 10:30
**最终状态**: built
---

**编译结束**: 2026-06-03 17:10
**最终状态**: built
