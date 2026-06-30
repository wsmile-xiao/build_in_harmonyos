# xmlsec1 1.3.11 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-20
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build xmlsec1 1.3.11 --url=http://www.aleksey.com/xmlsec/download/xmlsec1-1.3.11.tar.gz`
2. 配置: `./configure --prefix=$HOME/usr/local --with-libxslt=/data/service/hnp/libxslt.org/libxslt_1.1.39 --with-openssl=$HOME/usr/local`
3. 编译: `make -j2`
4. 安装: `make install DESTDIR=$TEST_PREFIX`
5. 打包: `python3 $SKILL_ROOT/scripts/ohc-run.py package xmlsec1 1.3.11`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HTTPS下载失败 | 网络限制 | 使用 HTTP 协议下载 |
| 2 | config.guess无法识别HarmonyOS | 缺少平台识别 | 应用 patch-autotools-ohos.pl 补丁生成 0001/0002 补丁 |
| 3 | libtool .la文件路径错误 | 交叉编译路径问题 | 修改libtool脚本使用修复的.la文件 |
| 4 | config.status临时目录权限 | /tmp 只读 | 使用 ~/tmp/config_status_tmp |

## 源码修改

8 个补丁文件：
- 0001-config.guess.patch - HarmonyOS 平台识别
- 0002-config.sub.patch - ohos-linux triplet 支持
- 0003-xmlsec1-config.patch - 路径修复
- 0004-xmlsec1-gnutls.pc.patch - pkg-config 路径
- 0005-xmlsec1-nss.pc.patch - pkg-config 路径
- 0006-xmlsec1-openssl.pc.patch - pkg-config 路径
- 0007-xmlsec1.pc.patch - pkg-config 路径
- 0008-xmlsec1Conf.sh.patch - 配置脚本路径

## 依赖版本
- libxml2 2.11.9（已安装）
- libxslt 1.1.39（系统预装）
- openssl 1.1.1w（已安装）

## 验证结果
预编译包已生成，包含：
- bin/xmlsec1
- bin/xmlsec1-config
- include/xmlsec1/
- lib/libxmlsec1.so

## 平台限制
musl 动态链接器不支持 RUNPATH，用户需设置：
```bash
export LD_LIBRARY_PATH="$HOME/usr/local/lib:/data/service/hnp/libxslt.org/libxslt_1.1.39/lib:$LD_LIBRARY_PATH"
xmlsec1 --version
```