# step 25.08.3-r0 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-06-02}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}
---

**编译开始**: 2026-06-02 11:29 CST

## 编译过程

1. **init-build**: 使用 Go 模块代理下载源码 (goproxy.cn)，源码来自 smallstep/cli Go module v0.28.3
2. **Go 编译**: `CGO_ENABLED=1 GOOS=linux GOARCH=arm64 go build -ldflags="-w -X main.Version=0.28.3 -X main.BuildTime=2026-06-02" ./cmd/step`
3. **DESTDIR 安装**: 手动 cp 到 `$TEST_PREFIX/$DEFAULT_PREFIX/bin/step` (Go 项目无 make install)
4. **ELF 签名**: `ohc-run.py sign-elf` 对 DESTDIR 和本地安装的二进制签名
5. **预编译包**: `ohc-run.py package` → `step-25.08.3-r0-ohos-aarch64.tar.gz` (34MB)
6. **本地验证**: `step version` → "Smallstep CLI/0.28.3 (linux/arm64)" ✅

## 特殊处理

- **Go 项目**: 无 configure/make/make install 传统流程，直接 `go build` 产出单一二进制
- **manifest 修正**: `build_system: go` (初始为 autotools，需修正为 go)
- **GitHub 下载超时**: 通过 goproxy.cn Go 模块代理下载源码替代
- **ldflags**: 设置 `main.Version=0.28.3` 和 `main.BuildTime=2026-06-02` 确保版本信息正确
- **make check 跳过**: Smallstep CLI 集成测试需要 CA 服务和网络，当前环境无法运行
---

**编译结束**: 2026-06-02 11:59
**最终状态**: published
