# infisical 0.18.2 适配笔记

## 编译环境
- 构建系统: go
- 编译日期: 2026-06-08
- 编译器: Go 1.26.4 (CGO_ENABLED=0)
- 状态: built

## 编译步骤

1. `git clone https://gitcode.com/Infisical/infisical.git --depth 1 --branch infisical-cli/v0.18.2` (SSL证书问题导致GitHub下载失败，使用gitcode镜像+git clone方式获取源码)
2. `cd cli && PATH=~/.harmonybrew/bin:$PATH GOPROXY=https://goproxy.cn,direct CGO_ENABLED=0 go build -ldflags="-s -w -X github.com/Infisical/infisical-merge/packages/util.CLI_VERSION=0.18.2" -o infisical .`
3. 手动 cp 到 staging 和 DEFAULT_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub tarball下载SSL失败 | 鸿蒙平台缺少GitHub的SSL证书 | 使用gitcode镜像git clone，然后创建本地tarball + file:// URL给init-build |
| 2 | init-build URL自动搜索失败 | infisical不在registry中 | 使用--url=file:///本地路径 传入预先创建的tarball |
| 3 | --version显示devel | 未注入版本ldflags | 使用 -ldflags "-X github.com/Infisical/infisical-merge/packages/util.CLI_VERSION=0.18.2" 注入版本 |

## 源码修改

无补丁，纯Go编译，不需要源码修改。

## 依赖版本

- Go 1.26.4 (harmonybrew)

## 验证结果

```bash
$ infisical --version
infisical version 0.18.2
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| infisical-0.18.2-ohos-aarch64.tar.gz | ~13M | 预编译包 |

## 注意事项

- infisical是Go项目，构建系统为go而非autotools，不支持configure/make标准流程
- 源码根目录是monorepo结构，CLI入口在cli/子目录
- 版本注入ldflags路径为: github.com/Infisical/infisical-merge/packages/util.CLI_VERSION
- gitcode镜像上infisical的tag格式为 infisical-cli/v0.18.2 而非 v0.18.2
---

**编译结束**: 2026-06-08 20:41
**最终状态**: built
