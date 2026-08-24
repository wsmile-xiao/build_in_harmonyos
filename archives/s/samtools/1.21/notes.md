# samtools 1.21 适配笔记

## 编译环境
- 构建系统: autotools (configure bypassed, manual config.mk/config.h generation)
- 编译日期: 2026-08-22
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载 samtools-1.21.tar.bz2 源码包 (SHA256: 05724b083a6b6f0305fcae5243a056cc36cf826309c3cb9347a6b89ee3fc5ada)
2. 通过 Conan 安装 zlib、bzip2、ncurses、curl、OpenSSL 和 liblzma 依赖
3. 从 ncurses/6.6 Conan 包获取头文件与静态库
4. 从 Conan profile 读取 CC，并据其工具目录选择 AR/RANLIB，显式传入 samtools 与 bundled htslib 构建
5. 手动生成 config.mk (绕过 configure, 因 HMDFS config.status 临时目录权限问题)
6. 手动生成 config.h
7. make -j1 编译
8. `package()` 将主程序、辅助工具和 man page 复制到 Conan package_folder
9. 运行 Conan test_package 验证打包后的 `samtools --version`、SAM/BAM 转换、排序、索引、统计和 FASTA 提取
10. 通过 `LD_LIBRARY_PATH` 验证 OHOS 动态加载器可以解析 Conan 提供的 libcurl、OpenSSL、zlib、bzip2 和 liblzma

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure config.status Permission denied | HMDFS tmpfs 对 mktemp -d 创建的目录内文件写入受限 | 手动生成 config.mk/config.h, 绕过 configure |
| 2 | htslib Makefile 使用默认 gcc/ar/ranlib | 源码默认工具链不匹配 Conan profile | 从 `tools.build:compiler_executables` 读取 CC，并显式传入 AR/RANLIB |
| 3 | ncurses 头文件缺失 | cmd-pkgs ncurses 6.4 未包含 curses.h | 从 ncurses 6.6 conan build 目录提取头文件 |
| 4 | lzma.h 缺失 | liblzma 未声明为 Conan 依赖 | 显式依赖已发布的 liblzma/5.8.1 |
| 5 | 链接时找不到 -lssl/-lcrypto | OpenSSL 仅作为 curl 的传递依赖，库目录未注入 samtools 链接参数 | 显式依赖 openssl/3.5.6.1 并注入其 include/lib 目录 |
| 6 | GitHub release 下载过慢 | release-assets 下载链路在本机多次超时 | 使用提供同一官方 tarball 和 SHA256 的 openSUSE 权威镜像 |

## 依赖版本

- zlib/1.3.1.1 (Conan)
- bzip2/1.0.8 (Conan)
- ncurses/6.6 (Conan)
- curl/8.15.0 (Conan)
- liblzma/5.8.1 (Conan)
- openssl/3.5.6.1 (Conan)

## 验证结果

```
samtools 1.21
Using htslib 1.21
Features: build=Makefile curses=yes
conan create: PASS (打包后的 samtools --version 返回 0 且版本为 1.21)
conan-verify: PASS (all gates G0-G4, L2/L4/L5)
```

## 注意事项

- samtools 是 CLI 工具 (package_type=application), 非库
- 配方中需要 commands.json 声明可执行文件 (R38)
- generate() 校验 Conan profile 提供 Clang C 编译器；CC/AR/RANLIB 从 Conan 配置推导并通过 make 命令行传递
---

**编译结束**: 2026-08-23 09:00
**最终状态**: built and fully tested

## 完整测试结果

上游源码包含 samtools 与 bundled htslib 测试。使用 Conan Clang 工具链和依赖库运行：

```text
make check
Number of tests:
    total            .. 951
    passed           .. 920
    failed           .. 0
    expected failure .. 31
    unexpected pass  .. 0
UPSTREAM_CHECK_RC=0
```

按上游 Harness 语义，951/951（100%）完成且没有 unexpected failure；若只计算无 expected-failure 标记的直接通过项，则为 920/951（96.74%）。31 项是上游明确标记的 expected failure，不是 OpenHarmony 适配失败。

## OHOS 专项消费者测试

`test_package/test_samtools.c` 包含 10 项独立断言，全部通过（10/10，100%）：版本、帮助、SAM 读取、SAM 转 BAM、记录计数、排序、索引、flagstat、quickcheck 和 FASTA 区间提取。临时文件使用 `TMPDIR`，不写入 OHOS 只读 `/tmp`。

另外，`package_info()` 通过 `VirtualRunEnv` 暴露所有 Conan 依赖的 `libdirs`，解决 OHOS 动态加载器解析 `libcurl.so` 等 htslib 运行时依赖的问题。
