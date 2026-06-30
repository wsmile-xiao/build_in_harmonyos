# docker-machine homebrew 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-06-03}
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

**编译开始**: 2026-06-03 (minimal build from source)

**构建方案**: 从源码编译（最小化版本）

- docker-machine 项目已归档（archived），最后版本 v0.16.2
- GitHub 完全不可访问，源码通过 Go 模块代理（goproxy.cn）下载
- 预编译二进制尝试下载成功（ghfast.top 镜像），但 ELF 签名失败（.shstrtab 非 null terminated）
- 最终采用最小化源码编译方案：仅保留 `generic` 和 `none` 驱动，剔除所有不兼容的云驱动（amazonec2, azure, digitalocean, exoscale, google, openstack, rackspace, softlayer, virtualbox, vmwarefusion, vmwarevcloudair, vmwarevsphere, hyperv）
- 依赖适配：codegangsta/cli → urfave/cli, docker/docker/pkg/term → golang.org/x/term, mcndockerclient/dockerclient → stub, swarm → stub

**版本注入**: `-ldflags="-s -w" -X github.com/docker/machine/version.GitCommit=v0.16.2-ohos`

**Go 编译**: `CGO_ENABLED=1 GOOS=linux GOARCH=arm64 GOPROXY=https://goproxy.cn,direct ~/usr/local/go1263/bin/go build -ldflags="-s -w -X version.GitCommit=v0.16.2-ohos" -o docker-machine ./cmd/docker-machine`

**TMPDIR**: `/data/storage/el2/base/cache`

**ELF 签名**: ✅ 成功（binary-sign-tool sign -inFile -outFile -selfSign 1）

**验证**: `docker-machine version 0.16.2, build v0.16.2-ohos`

**编译结束**: 2026-06-03
**最终状态**: published（最小化编译版本）
---

**编译结束**: 2026-06-03 11:31
**最终状态**: published
