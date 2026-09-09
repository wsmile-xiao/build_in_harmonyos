# libmad 0.15.1b 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-27
- 编译器: clang / clang++
- 状态: built

## 编译步骤

1. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
2. source() 从 Debian 官方镜像获取 `libmad_0.15.1b.orig.tar.gz`（SHA-256: `bbfac3ed6bfbc2823d3775ebb931087371e142bb0e9bb1bee51a76a6e0078690`），strip_root 解包。
3. build() 中内联修补：config.guess/config.sub 增加 HarmonyOS 识别；configure 剔除 clang 不支持的 GCC 优化 flag；修复 HMDFS mktemp；mad.h 修正 aarch64 定点位宽。
4. `./configure --enable-static --disable-shared` + `make -j1`。
5. `make install` 打包，产出静态库 `libmad.a` 与头文件 `mad.h`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 无法识别主机平台 | config.guess/config.sub 过旧，无 HarmonyOS/ohos 分支 | 在 config.guess 增加 `*:HarmonyOS:*:*` 分支，config.sub 增加 `ohos*`、`linux-ohos*` 规范名 |
| 2 | clang 编译报未知选项 | configure 追加 GCC 专属 flag（-fforce-mem、-fexpensive-optimizations 等） | configure 内剔除这些 flag |
| 3 | config.status 生成时 mktemp 失败 | HMDFS 文件系统下 `mktemp -d -q` 行为受限 | 替换为固定临时目录 `./conftmp; mkdir -p $tmp` |
| 4 | 解码输出异常/位宽错误 | mad.h 默认 FPM_INTEL + SIZEOF_LONG=4，aarch64 定点乘法溢出 | mad.h 改为 FPM_DEFAULT、SIZEOF_LONG=8 |

## 源码修改

无外部补丁文件，全部为 conanfile.py 内联 `replace_in_file` 修改（见 conanfile.py `_patch_config_guess/_patch_configure/_patch_mad_h`）。

## 依赖版本

- 无第三方运行时依赖（纯 C 库）。

## 验证结果

- 消费者 test_package 编译链接成功，运行通过：`mad_version` 字符串可读、`mad_decoder_init/finish`、`mad_header_init/finish` 可调用。
- 上游 `make check` 无注册测试入口（发布包未附带测试程序/fixture）。

## 交付物

| 文件 | 说明 |
|------|------|
| libmad.a | OHOS PC aarch64 静态库 |
| mad.h | 安装头文件 |

## 注意事项

- 官方发布源为 SourceForge；本配方使用 Debian 官方镜像的同源 tarball（内容一致，SHA-256 已核验）。
- mad.h 的 FPM/SIZEOF_LONG 修补对 aarch64 定点解码正确性至关重要，不可省略。
---

**编译结束**: 2026-09-07 00:54
**最终状态**: built
