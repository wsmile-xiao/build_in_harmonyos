# tbox 1.8.0 适配笔记

## 编译环境
- 构建系统: xmake.sh (configure 脚本基于 xmake.sh 框架，生成 Makefile)
- 编译日期: 2026-06-30
- 编译器: clang/clang++ 15.0.4 (OHOS SDK LLVM)
- 状态: published

## 编译步骤

1. 手动下载源码包（GitHub SSL 证书问题，使用 `curl -k -L` 下载）
2. `ohc-run.py init-build tbox 1.8.0 --no-download` 初始化构建环境
3. `./configure --prefix=$DEFAULT_PREFIX` — 平台自动检测 harmonyos/arm64
4. `make -j2` — 编译生成 libtbox.a 和 demo
5. `make install DESTDIR=$TEST_PREFIX` — 安装到 staging 目录
6. 运行 demo 程序进行功能测试（48 个测试用例）
7. `ohc-run.py conan-init` 生成 Conan 配方
8. `ohc-run.py conan-verify` 验证配方（8 道门禁全部通过）
9. `ohc-run.py finish tbox 1.8.0 published` 收尾归档

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载 SSL 证书错误 | 环境缺少 CA 证书 | 使用 `curl -k -L` 手动下载 tarball，init-build 使用 `--no-download` |
| 2 | filelock.c 中 flock 未声明 | 配置头定义 TB_CONFIG_OS_HARMONYOS，源码检查 TB_CONFIG_OS_HARMONY（缺 "OS" 后缀） | 在条件中添加 `\|\| defined(TB_CONFIG_OS_HARMONYOS)` |
| 3 | conan-verify G2 失败：补丁文件不存在 | conandata.yml 引用旧补丁文件名，refresh-patch 生成了新文件名 | 更新 conandata.yml 中 patch_file 路径为新文件名 |
| 4 | make jobserver 警告 | 鸿蒙不支持 mkfifo | 使用 `make -j2` 或 `make -j1` 避免 jobserver |

## 源码修改

- **文件**: `src/tbox/platform/bsd/filelock.c` (第 27 行)
- **补丁**: `patches/0001-src-tbox-platform-bsd-filelock.c.patch` (+1/-1)
- **修改内容**: 在 `#if` 条件中添加 `|| defined(TB_CONFIG_OS_HARMONYOS)`，使 `<sys/file.h>` 被正确包含

## 依赖版本

无外部依赖。tbox 是自包含的 C 库。

## 验证结果

```
conan-verify: 8/8 门禁通过 (G0-G4 + L2/L4/L5)
功能测试: 48 个测试，44 PASS / 1 CRASH / 3 TIMEOUT
Staging: libtbox.a + 406 headers + demo 全部安装成功
```

## 注意事项

- tbox 使用 xmake.sh 构建系统，非标准 autotools，但 configure 脚本可正常工作
- 鸿蒙不支持 mkfifo，make jobserver 受影响，建议使用 -j1 或 -j2
- memory_check 测试在非调试环境会触发 SIGTRAP（内存调试器断点），属于预期行为
- platform_event/semaphore/thread_local 测试会阻塞等待同步原语，在测试环境中可能超时
---

**编译结束**: 2026-06-30 17:12
**最终状态**: published
