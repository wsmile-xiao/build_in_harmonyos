# golang-migrate homebrew — 适配笔记

## 编译信息

- **软件**: golang-migrate
- **版本**: homebrew (v4.19.1)
- **构建系统**: Go (custom)
- **日期**: 2026-06-03

## 编译过程

### Step 1: init-build
- 下载源码: https://codeload.github.com/golang-migrate/migrate/tar.gz/refs/tags/v4.19.1
- SSL 下载失败（github.com），改用 codeload.github.com 成功
- 解压到 ~/tmp/builds/golang-migrate-homebrew.work

### Step 2: Go 编译
- 设置环境: CGO_ENABLED=1, GOOS=linux, GOARCH=arm64, GOPROXY=https://goproxy.cn,direct
- 编译命令: ~/usr/local/go1263/bin/go build -ldflags="-s -w -X main.Version=v4.19.1" -tags "postgres mysql sqlite sqlite3 file" -o migrate ./cmd/migrate/
- 版本注入: -X main.Version=v4.19.1（cmd/migrate/version.go 中 var Version = "dev"）
- 编译耗时约 160 秒（含依赖下载）

### Step 3: 安装与验证
- DESTDIR 模式: make install DESTDIR=$TEST_PREFIX（R20）
- 本地安装: cp migrate ~/usr/local/bin/migrate
- 版本验证: migrate --version → v4.19.1 ✅

### Step 4: 打包与签名
- ELF 签名: ohc-run.py sign-elf ✅
- 预编译包: golang-migrate-homebrew-ohos-aarch64.tar.gz (9959KB)
- 质量门禁: G1-G4 PASS

## 关键发现

1. **SSL 下载**: github.com 的 SSL 下载失败，需改用 codeload.github.com
2. **版本注入**: 变量名为 `Version`（大写 V），ldflags 用 `-X main.Version=v4.19.1`
3. **Go 版本**: Go 1.26.3 支持 CGO_ENABLED=1 的 arm64 交叉编译
4. **构建标签**: postgres mysql sqlite sqlite3 file 为常用驱动组合
5. **G0 门禁**: Go 项目无 configure 脚本，G0 clean-verify 不适用

## 铁律遵循

- R10: 使用 $TMPDIR（非 /tmp，只读）
- R20: DESTDIR 模式（--prefix=$DEFAULT_PREFIX + DESTDIR=$TEST_PREFIX）
- R19: 使用 ohc-run.py package 打包（非手动 tar）
- R17: 知识先草稿
---

**编译结束**: 2026-06-03 10:35
**最终状态**: built
