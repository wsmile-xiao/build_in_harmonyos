# ezstream 1.0.2 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos 交叉)
- 状态: built

## 软件简介
ezstream 是 Xiph.Org 的 Icecast 流媒体源客户端命令行工具：读取本地音频文件
（或外部程序输出），可选地经外部解码/编码器转码，通过 libshout 推送到
Icecast 服务器。纯 C 实现（355KB），产物为 3 个可执行文件：
`ezstream`（主程序）、`ezstream-cfgmigrate`（v0.x 配置迁移工具）、
`ezstream-file.sh`（单文件推送脚本）。

## 依赖结构（configure.ac 实测）
| 依赖 | 探测宏 | 性质 | 制品仓状态 |
|------|--------|------|-----------|
| libshout | AX_CHECK_LIBSHOUT | REQUIRED (AC_MSG_ERROR) | libshout/2.4.6 ✅ |
| libxml2 | AX_CHECK_LIBXML2 | REQUIRED (AC_MSG_ERROR) | libxml2/2.15.3 ✅ |
| libtag_c | AX_CHECK_TAGLIB_C | REQUIRED (AC_MSG_ERROR) | taglib/1.13.1（PR #8267，C bindings）|
| check | PKG_CHECK_MODULES | 测试专用（test_requires）| check/0.15.2 ✅ |

注意：taglib/2.3（制品仓现有）**不带 C bindings**（BUILD_BINDINGS=False），
ezstream 需要 taglib/1.13.1（BUILD_BINDINGS=ON 产出 libtag_c.a +
include/taglib/tag_c.h，即 PR #8267）。依赖引用用无 channel 的
`taglib/1.13.1`（CI 的 conan create/upload 均不带 --user/--channel）。

## 编译步骤

```bash
# 1. 官方 tarball 解压 + 打 config.guess/sub 补丁（2023-08-22 版，识别 ohos）
# 2. 依赖环境：conan PkgConfigDeps 生成 shout/libxml-2.0/taglib_c 等 .pc
#    + shout.pc 别名（conan 生成 libshout.pc，上游探测名是 shout）
# 3. configure（关键环境/参数）：
TAGLIB_CPPFLAGS="-I<taglib_pkg>/include" \
LIBSHOUT_LIBS="-lshout -lspeex -lvorbisenc -lvorbisfile -lvorbis -logg -lssl -lcrypto -ldl -lpthread -lm" \
./configure --prefix=<prefix> \
    --enable-static --disable-shared \
    --with-taglib-includes=<taglib_pkg>/include/taglib
# 4. make -j8 → 全绿
# 5. make check → 14/14 PASS（check 框架单测）
# 6. 二进制验证：ezstream -V / -h、ezstream-cfgmigrate -h
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: libtag_c is missing | tag_c.h 在 include/taglib/ 子目录，探测宏找 <tag_c.h> 找不到；且 taglib/2.3 无 C bindings | 用 taglib/1.13.1；--with-taglib-includes 指向 include/taglib（探测用），TAGLIB_CPPFLAGS 指向 include 根（源码 <taglib/tag_c.h> 用） |
| 2 | make check 14/14 FAIL（exit 127 找不到 .so）| 测试二进制动态链接 conan 依赖的 .so，LD_LIBRARY_PATH 未含包缓存目录 | 补 LD_LIBRARY_PATH=<各依赖包>/lib 后 14/14 PASS |
| 3 | 链接失败：cannot find '//lib/libspeex.la' | libshout/2.4.6 包内 libshout.la 的 dependency_libs 记录了构建期 prefix='/'，configure 的 pkg-config --static 展开把它带进 libezstream.la | LIBSHOUT_LIBS 环境变量（AX_CHECK_LIBSHOUT 的 AC_ARG_VAR）显式传最终静态链接行，绕过 .la 展开 |
| 4 | config.guess 报 Invalid configuration | 上游 2016-10-02 版 config.guess/sub 不识别 ohos | 补丁替换为 2023-08-22(config.guess)/2023-09-19(config.sub) 版 |
| 5 | W3 本地 CI：test_package 4 断言中 2 失败（minimal.xml/bad.xml 报 world readable+writeable，连接断言拿不到输出）| 上游 cfg_file_check()（src/cfg.c）对 S_IWOTH 致命拒绝、S_IROTH 告警；HMDFS 检出文件默认 0666 两位置位（Linux CI 为 0644 无此问题）| test_ezstream.sh 将 XML 复制到 mktemp 私有目录并 chmod 0600 后再喂给被测二进制（HMDFS chmod 可生效，实测 0600 稳定不回弹）；Linux CI 上该复制为无害 no-op |

## 源码修改
- patches/0001-config.guess-sub-2023-08-22-for-ohos.patch：
  build-aux/config.guess、build-aux/config.sub 整体替换（GNU config 官方新版，
  原生支持 ohos）。无其他源码修改——ezstream 纯 C + POSIX，无需 __OHOS__ 守卫。

## 依赖版本
- libshout/2.4.6（连带 libogg/1.3.6、libvorbis/1.3.7、speex/1.2.1、openssl/3.5.6.1）
- libxml2/2.15.3
- taglib/1.13.1（连带 zlib/1.3.1）
- check/0.15.2（仅测试）

## 验证结果

```bash
$ ./src/ezstream -V
ezstream version 1.0.2
$ make check
# TOTAL: 14  PASS: 14  (LD_LIBRARY_PATH 补齐后)
$ ./src/ezstream -c examples/ezstream-minimal.xml
ezstream[...]: examples/ezstream-minimal.xml: world readable
ezstream[...]: stream: default: connect: [127.0.0.1]:8000: error -2: Couldn't connect
ezstream[...]: initial server connection failed
# ↑ 配置解析→流建立→连接尝试 全管线贯通（无服务器环境预期失败）
$ ./src/ezstream -c bad.xml
bad.xml:2: parser error : Premature end of data in tag broken line 1
# ↑ libxml2 错误路径正常
```

## test_package 设计（R34 实质测试）
ezstream 是 CLI 应用，测试直接执行被测包二进制：
1. `ezstream -V` → 断言版本横幅含 "1.0.2"
2. `ezstream -c ezstream-minimal.xml` → 断言输出含 "Couldn't connect"
   （证明 XML 解析、配置结构、libshout 连接逻辑真实执行）
3. `ezstream -c bad.xml`（SCRATCH 私有目录 0600 生成）→ 断言 libxml2 parser error
4. `ezstream-cfgmigrate -h` → 断言用法横幅
---

**编译结束**: 2026-09-09 11:56
**最终状态**: built
