# icecast 2.4.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-08
- 编译器: clang/clang++ (OHOS aarch64)
- 状态: built

## 编译步骤

1. `init-build icecast 2.4.4`（源码来自 https://downloads.xiph.org/releases/icecast/icecast-2.4.4.tar.gz，SHA256 49b5979f9f614140b6a38046154203ee28218d8fc549888596a683ad604e4d44）
2. `build icecast 2.4.4`（VPATH 构建于 icecast-2.4.4-build/）：
   - configure：首次失败 RC=1，根因缺少 GNU sed/coreutils（toybox sed 与配置脚本不兼容），自动安装 sed 4.9 + coreutils 9.10 后成功
   - make：首次失败 RC=2，同样原因，自动重试成功后完成
   - make install（DESTDIR 模式）：产出 bin=1（icecast 可执行文件）+ share/icecast 资源（web/admin XSLT、配置文件模板、文档）
   - make check：无 `check` target（icecast autotools 未集成测试，仅 src/avl/test.c、src/log/test.c、src/net/test_resolver.c 未挂接）
   - Staging 验证：探索编译阶段未设置 RPATH，运行 `--version` 找不到 conan 缓存中的 libcurl/libvorbis/libogg/libxml2；设置 LD_LIBRARY_PATH 后 `icecast --version` 正常输出 "Icecast 2.4.4"。conan create 阶段由 conan 管理依赖路径，不受此影响。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure/make 失败 (RC=1/2) | 系统 sed 为 toybox，无法处理 autoconf 配置脚本 | 安装 GNU sed 4.9 + coreutils 9.10（cmd-pkgs），PATH 前置 $HOME/usr/local/bin |
| 2 | make check 无目标 | icecast Makefile 未定义 check target，测试程序未挂接 | 记录为平台/上游限制，跳过（不阻塞） |
| 3 | staging 验证 --version 失败 | 探索编译产物未设 RPATH，运行时找不到依赖库 | LD_LIBRARY_PATH 指向 conan 缓存后验证通过；conan 配方由 conan create 管理依赖 |

## 源码修改

无（探索阶段未修改源码）

## 依赖版本

- curl/8.15.0
- libogg/1.3.6
- libvorbis/1.3.7
- libxml2/2.15.3
- libxslt/1.1.45.1
- openssl/3.5.6.1
- zlib/1.3.1.1

## 验证结果

```bash
# 探索阶段：LD_LIBRARY_PATH 指向 conan 依赖库后
$ ./icecast --version
Icecast 2.4.4
```

## 注意事项

- icecast 为命令行流媒体服务器（tool 类型），需在软件级归档声明 commands.json（R38）
- 运行依赖 libcurl/libvorbis/libogg/libxml2/libxslt，全部来自制品仓
- 源码硬编码 /etc/mime.types（PSCAN-PATH-001，medium），configure 可用 --sysconfdir 控制，但 icecast 2.4.4 使用 /etc/icecast.xml 作为默认配置路径
---

**编译结束**: 2026-08-08 13:19
**最终状态**: built

## clean-verify 环境限制说明

- clean-verify 脚本在 /storage/Users/currentUser/tmp/ 下解压源码直接跑 configure 时，
  shell getcwd 报 "cannot access parent directories"（HMDFS 文件系统限制），G0 以环境原因失败。
- 该失败为环境限制而非配方缺陷：同一 configure 在 conan-verify G2（conan create 干净构建）
  中已成功通过，6 个补丁全部应用、配置、编译、打包、test_package 功能测试全部 PASS。
- 配方正确性以 conan-verify G2 结果为准。

## 2026-08-09 CI 编译失败修复（PR #4730）

- CI 上 `configure` 检测 `xsltSaveResultToString` 为 no（`HAVE_XSLTSAVERESULTTOSTRING` 未定义），
  `src/xslt.c` 的回退实现（`#ifndef HAVE_XSLTSAVERESULTTOSTRING`）被编译，其中直接访问
  `buf->buffer->use/content`、`buf->conv->use/content` 内部字段；libxml2 2.12+ 已将
  `xmlBuf` 结构体不透明化（tree.h 仅前向声明 `struct _xmlBuf`），导致 4 处
  "incomplete definition of type 'struct _xmlBuf'" 编译错误。
- 修复：新增 `0006-src-xslt.c-libxml2-xmlbuf-api.patch`，改用 libxml2 公开 API
  `xmlBufUse()` / `xmlBufContent()`（libxml2 ≥2.9.0 可用，兼容新老版本）。
- 验证：本地模拟 CI 场景（不定义 HAVE_XSLTSAVERESULTTOSTRING）clang -fsyntax-only 通过；
  本地 conan create --build=icecast/2.4.4 强制重建，6 补丁全部应用，test_package ALL TESTS PASSED。
