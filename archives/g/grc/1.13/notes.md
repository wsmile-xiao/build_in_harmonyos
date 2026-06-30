# grc 1.13 适配笔记

## 编译环境
- 构建系统: custom (Python 脚本工具，使用 install.sh 安装)
- 编译日期: 2026-06-21
- 编译器: N/A (纯 Python 脚本)
- 状态: published

## 编译步骤

grc 是纯 Python 脚本工具，无需编译。使用自带的 install.sh 脚本安装。

1. 从 GitHub 获取源码：https://github.com/garabik/grc/archive/refs/tags/v1.13.tar.gz
2. 解压源码
3. 使用 install.sh 安装到 staging 目录：
   ```bash
   sh install.sh $TEST_PREFIX/$DEFAULT_PREFIX $TEST_PREFIX
   ```
   - PREFIX=$TEST_PREFIX/$DEFAULT_PREFIX (bin/share 目录)
   - ETCPREFIX=$TEST_PREFIX (etc 目录)
4. 验证 grc --version 和 grcat 可执行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub API SSL 证书问题 | 平台 curl 缺少 CA 证书 | 使用 codeload.github.com 直接下载 tar.gz |
| 2 | init-build 无法自动搜索 URL | grc 不在 registry 中 | 使用 --url=file:// 指定本地 tarball |

## 源码修改

无源码修改，grc 是纯 Python 脚本，开箱即用。

## 依赖版本

- python3: 3.14.5 (已预装)

## 验证结果

```bash
$ python3 $TEST_PREFIX/$DEFAULT_PREFIX/bin/grc --version
Generic Colouriser 1.13

$ python3 $TEST_PREFIX/$DEFAULT_PREFIX/bin/grcat
You are not supposed to call grcat directly, but the usage is: grcat conffile
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| grc | 5188 B | 主程序 Python 脚本 |
| grcat | 10849 B | 配色器 Python 脚本 |
| colourfiles/conf.* | ~80 个文件 | 各命令的配色配置文件 |
| grc.conf | 4051 B | 主配置文件 |

## 注意事项

- grc 是纯 Python 脚本工具，无需编译，无 ELF 二进制文件
- 使用 install.sh 安装，参数1为 PREFIX，参数2为 ETCPREFIX
- 无 setup.py，无 Makefile
- 运行时依赖 Python 3 解释器
---

**编译结束**: 2026-06-21 15:23
**最终状态**: published
