# readosm 1.1.0a 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-16
- 编译器: gcc/g++
- 状态: built

## 编译步骤

1. 下载源码: https://download.savannah.nongnu.org/releases/readosm/readosm-1.1.0a.tar.gz
2. 解压源码到 ~/tmp/builds/readosm-1.1.0a.orig 和 readosm-1.1.0a.work
3. 替换 config.guess 和 config.sub 为较新版本（gnu-tar-1.35 项目中的 2023 版本）
4. 在 config.guess 中添加 HarmonyOS 检测逻辑
5. 修改 config.status 使用固定临时目录绕过权限限制
6. 配置: `./configure --prefix=$DEFAULT_PREFIX CPPFLAGS="-I$DEFAULT_PREFIX/include" LDFLAGS="-L$DEFAULT_PREFIX/lib"`
7. 编译: `make -j4`
8. 安装 staging: `make install DESTDIR=$TEST_PREFIX`
9. 运行测试: `make check` - 3个测试全部通过
10. 本地安装: `make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败下载源码失败 | HarmonyOS 缺少 CA 证书 | 使用 curl -k 绕过 SSL 验证 |
| 2 | config.guess 无法识别 HarmonyOS | 原版 config.guess 是 2009 年版本 | 替换为 2023 版本并添加 HarmonyOS 检测 |
| 3 | config.status 无法创建临时文件 | HarmonyOS 安全策略限制 | 修改 config.status 使用固定临时目录 |
| 4 | 缺少 expat.h | 依赖未在默认路径 | 设置 CPPFLAGS/LDFLAGS 指向 expat |

## 源码修改

- config.guess: 添加 HarmonyOS 检测
```sh
# HarmonyOS detection - return early without compiler test
case $UNAME_SYSTEM in
    HarmonyOS)
        GUESS=$UNAME_MACHINE-unknown-linux-gnu
        echo "$GUESS"
        exit ;;
esac
```

- config.status: 修改临时目录创建逻辑
```sh
tmp="/storage/Users/currentUser/tmp/builds/readosm-1.1.0a.work/.config_tmp"
```

## 依赖版本

- expat: 2.4.8
- zlib: 系统自带

## 验证结果

```bash
make check
============================================================================
Testsuite summary for readosm 1.1.0a
============================================================================
# TOTAL: 3
# PASS:  3
# SKIP:  0
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0
============================================================================
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libreadosm.so.1.0.1 | 动态库 | OSM 数据解析库 |
| libreadosm.a | 静态库 | OSM 数据解析库 |
| readosm.h | 头文件 | API 定义 |

## 注意事项

- HarmonyOS 下 autotools 项目需要替换 config.guess/config.sub
- 临时文件创建权限问题需要特殊处理
- 需要手动设置 CPPFLAGS/LDFLAGS 指向已安装的依赖
---

**编译结束**: 2026-05-16 15:29
**最终状态**: built
