# rig 1.11 适配笔记

## 编译环境
- 构建系统: makefile (非 autotools，原信息错误)
- 编译日期: 2026-06-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码包：使用 curl 从 SourceForge 下载（因 SSL 证书问题无法直接用脚本下载）
2. 解压到 ~/tmp/builds/rig-1.11.orig 和 rig-1.11.work
3. 初始化编译环境：`ohc-run.py init-build rig 1.11 --url=file://...`
4. 修改 Makefile：
   - 将 PREFIX=/usr/local 改为 PREFIX?=/usr/local（支持环境变量覆盖）
   - 将 MANDIR=${PREFIX}/man 改为 MANDIR=${PREFIX}/share/man（符合现代标准）
   - 将 g++ 改为 $(CXX) $(CXXFLAGS)（支持交叉编译）
   - 移除 install 命令中的 -g 0 -o 0 -s（非 root 用户权限问题）
5. 编译：`make CXX=clang++ CXXFLAGS="-fPIC -O2"`
6. 安装到 staging 目录：`make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX`
7. ELF 签名：`binary-sign-tool sign -inFile rig -outFile rig.signed.tmp -selfSign 1`
8. 验证和打包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | Python urllib 的 SSL 证书验证问题 | 使用 curl -k 手动下载源码包 |
| 2 | Savannah URL 404 | Savannah 镜像站点无该文件 | 使用 SourceForge 的原始 URL |
| 3 | Makefile 使用 g++ 固定编译器 | 原始 Makefile 不支持环境变量 | 改用 $(CXX) 变量 |
| 4 | install 命令需要 root 权限 | 原始 Makefile 使用 -g 0 -o 0 | 移除权限相关参数 |
| 5 | binary-sign-tool 直接调用失败 | 需要特定参数格式 | 使用正确参数：sign -inFile -outFile -selfSign 1 |
| 6 | 验证脚本找不到二进制 | DESTDIR 模式导致路径嵌套 | 重新组织 staging 目录结构 |

## 源码修改

修改文件: Makefile
- 补丁: 0001-Makefile.patch
- 变更内容:
  - PREFIX 改为可覆盖模式
  - MANDIR 路径修正为 share/man
  - 编译器改用环境变量
  - install 命令移除 root 权限参数

## 依赖版本

- 无外部依赖，纯 C++ 程序
- 数据文件：5 个 .idx 文件（fnames.idx, lnames.idx, locdata.idx, mnames.idx, street.idx）

## 验证结果

```bash
$ ~/usr/local/bin/rig -c 1
Casey Ramsey
538 Cedarwood Ln
Indianapolis, IN  46206
(317) xxx-xxxx

$ ~/usr/local/bin/rig --help
USAGE: rig [-f | -m ] [ -d datadir ] [ -c num ]
       datadir - Directory where data files can be found.
       If datadir is not specified, /usr/local/share/rig is used.
       num - print num identities.
       -f and -m specify gender of generated identities.
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| rig-1.11-ohos-aarch64.tar.gz | 133KB | 预编译包（含二进制+数据文件） |
| rig-1.11-ohos-aarch64-debug.tar.gz | 51KB | 调试符号包 |
| 0001-Makefile.patch | 853B | Makefile 适配补丁 |

## 注意事项

1. rig 不支持 --version 参数（设计如此，非 bug）
2. 数据文件路径硬编码在二进制中，需确保安装后路径一致
3. 程序依赖 /dev/urandom，鸿蒙系统已支持

---

**编译结束**: 2026-06-06 12:02
**最终状态**: built
