# hubble v1.17.2 适配笔记

## 编译环境
- 构建系统: Go (go1.26.4)
- 编译日期: 2026-06-08
- 编译器: Go (CGO_ENABLED=0)
- 状态: published

## 编译步骤

1. 获取源码: `git clone --depth 1 --branch v1.17.2 https://gitcode.com/cilium/hubble.git` (GitHub无法直达，用gitcode镜像)
2. 编译: `cd $BUILD_SRC_DIR && PATH=~/.harmonybrew/bin:$PATH CGO_ENABLED=0 GOPROXY=https://goproxy.cn,direct go build -ldflags="-s -w" -o hubble .`
3. 安装到 staging: `cp hubble $TEST_PREFIX/$DEFAULT_PREFIX/bin/`
4. 本地安装: `cp hubble $DEFAULT_PREFIX/bin/`
5. 打包: `ohc-run.py package hubble v1.17.2`

## 遇到的问题与解决方案

| # | 问题 | 因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub下载SSL失败 | 鸿蒙平台SSL证书问题 | 使用gitcode.com镜像git clone替代 |
| 2 | gh.idayer.com/ghfast.top镜像返回HTML | 镜像不支持tar.gz下载 | 改用git clone方式获取源码 |
| 3 | hubble --version报错 | hubble使用subcommand而非flag | 用`hubble version`替代`hubble --version` |

## 源码修改

无源码修改，纯Go项目直接编译成功。

## 依赖版本

- go/1.26.4 (harmonybrew)

## 验证结果

```bash
$ hubble version
hubble  compiled with go1.26.4 on linux/arm64

$ file hubble
ELF executable, 64-bit LSB arm64, static, BuildID=..., stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| hubble-v1.17.2-ohos-aarch64.tar.gz | 89114KB (~87MB) | 预编译包(含ELF签名) |
| hubble-v1.17.2-ohos-aarch64-debug.tar.gz | 77KB | 调试符号包 |

## 注意事项

- hubble是纯Go项目，CGO_ENABLED=0确保静态编译，无外部库依赖
- 版本查询使用`hubble version`(subcommand)，不支持`--version` flag
- 源码获取需使用中国镜像(gitcode.com)，GitHub直连不可用
---

**编译结束**: 2026-06-08 18:39
**最终状态**: built
