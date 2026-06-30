# alsa-lib 1.2.12 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-22
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 安装依赖：automake 1.17, libtool 2.4.7（预编译包）
2. 运行 autoreconf 生成 configure 文件
3. Configure: `./configure --prefix=/storage/Users/currentUser/usr/local`
4. 编译：`make -j2`
5. 安装：`make install DESTDIR=/storage/Users/currentUser/tmp/test-install-alsa-lib-1.2.12`
6. 打包：生成预编译包 alsa-lib-1.2.12-ohos-aarch64.tar.gz

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 文件不存在 | 源码是 GitHub tarball，缺少 autotools 生成文件 | 安装 automake/libtool 后运行 autoreconf -fi |
| 2 | versionsort64 未定义 | musl libc 不支持 versionsort64 函数 | 修改 src/conf.c 和 src/ucm/parser.c，使用 alphasort64 替代 |
| 3 | clean-verify G0 失败 | OHOS SDK 链接器依赖 libxml2.so.16，隔离环境无法找到 | 添加 bootstrap 补丁（保存 configure 和 Makefile.in） |

## 源码修改

生成 2 个补丁文件：
- 0001-src-conf.c.patch：修改 src/conf.c，添加 `!defined(__OHOS__)` 条件，使用 alphasort64
- 0002-src-ucm-parser.c.patch：修改 src/ucm/parser.c，添加 `!defined(__OHOS__)` 条件，使用 alphasort64

## 依赖版本

- automake 1.17（预编译包）
- libtool 2.4.7（预编译包）
- clang 15.0.4（OHOS SDK）

## 验证结果

```bash
# 本地安装验证
ls ~/usr/local/lib/libasound.so*
# 输出：libasound.so -> libasound.so.2.0.0, libasound.so.2 -> libasound.so.2.0.0

# pkg-config 验证
pkg-config --modversion alsa
# 输出：1.2.12
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| alsa-lib-1.2.12-ohos-aarch64.tar.gz | 4.4MB | 预编译包（包含 libasound.so, libatopology.so, aserver, 配置文件等） |

## 注意事项

1. OHOS 平台使用 musl libc，不支持 versionsort64，需要替换为 alphasort64
2. GitHub tarball 不包含 autotools 生成文件，需要运行 autoreconf
3. G0 clean-verify 因环境依赖问题需要特殊处理（bootstrap 补丁）

---
**编译结束**: 2026-05-22 17:30
**最终状态**: published
---

**编译结束**: 2026-05-22 16:56
**最终状态**: built
