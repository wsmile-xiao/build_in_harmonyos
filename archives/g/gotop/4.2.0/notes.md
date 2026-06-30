# gotop 4.2.0 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-05-26}
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

**编译开始**: 2026-05-26

### 构建方式
- Go语言项目，使用 `go build ./cmd/gotop`
- 无 Makefile，无 configure 脚本
- 构建命令: `CGO_ENABLED=0 go build -ldflags="-X main.Version=4.2.0 -X main.BuildDate=2026-05-26" -o gotop ./cmd/gotop`

### 关键问题及解决

#### 问题1: GitHub下载超时
- 现象: init-build下载GitHub tarball超时
- 解决: 使用 codeload.github.com 下载（该域名可访问）

#### 问题2: Go链接器HMDFS mmap失败
- 现象: `go build` 链接阶段报错 "mapping output file failed: permission denied"
- 原因: Go链接器使用mmap写入输出文件，HMDFS不支持mmap写操作
- 解决: 将TMPDIR、GOTMPDIR、GOCACHE设置为 `/data/storage/el2/base/haps/entry/files/`（hmfs文件系统支持mmap），并在此路径输出二进制
- 影响: 所有Go项目编译均需注意此问题

#### 问题3: gotop配置文件查找路径异常
- 玠象: 运行gotop -V时出现 "failed to parse config file" 错误
- 原因: configdir包在OpenHarmony上查找路径异常
- 解决: 使用 -C 参数指定配置文件路径可正常运行
- 状态: 不阻塞编译，但用户首次运行可能需要创建 ~/.config/gotop/gotop.conf
---

**编译结束**: 2026-05-26 11:43
**最终状态**: built
