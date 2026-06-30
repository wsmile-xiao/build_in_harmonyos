# skalibs 2.14.5.1 适配笔记

## 编译环境
- 构建系统: autotools（skalibs 自定义 configure，非标准 GNU autotools）
- 编译日期: 2026-06-09/10
- 编译器: clang 15.0.4 (OHOS SDK aarch64)
- 目标架构: aarch64-unknown-linux-ohos
- 状态: built → 待升级为 published

## 编译步骤

1. **下载源码**: skarnet.org 原始URL连接被重置(Errno 104)，改用 GitHub API tarball URL
   ```
   curl -L -o skalibs-2.14.5.1.tar.gz https://api.github.com/repos/skarnet/skalibs/tarball/refs/tags/v2.14.5.1
   ```
   注意: tarball 内目录名为 `skarnet-skalibs-6b1d07c/`（而非标准 `skalibs-2.14.5.1/`），init-build 已正确处理

2. **初始化构建**: `python3 ohc-run.py init-build skalibs 2.14.5.1 --url=...`
3. **configure**: `sh configure --prefix=/storage/Users/currentUser/usr/local`
   - 注意: skalibs 的 configure 是自定义脚本，不是标准 autotools
   - 交叉编译需额外参数: `--with-sysdep-devurandom=yes`
4. **make**: `make -j1`（~98秒完成，894个 .c 文件编译）
   - 初次自动编译的 make 因 jobserver mkfifo Operation not permitted 失败，RC=2
   - 手动运行 `make -j1` 成功
5. **make install DESTDIR**: `make install DESTDIR=$TEST_PREFIX` — 成功安装 100 个文件
6. **make install**: 安装到 `/storage/Users/currentUser/usr/local` — 成功
7. **sign-elf**: 对 libskarnet.so.2.14.5.1 緻加 ELF 签名
8. **verify-build**: G1-G4 全部 PASS
9. **package**: 打包生成 skalibs-2.14.5.1-ohos-aarch64.tar.gz (2.3MB)
10. **finish**: 档案关闭为 built（因 G0 初始失败降级，后续 clean-verify 已通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码下载失败 | skarnet.org 连接被重置(Errno 104)，Savannah/GNU mirrors 404 | 使用 GitHub API tarball URL: `https://api.github.com/repos/skarnet/skalibs/tarball/refs/tags/v2.14.5.1` |
| 2 | make HANDOFF (RC=2) | 自动编译脚本运行 make 时 jobserver mkfifo Operation not permitted | 手动运行 `make -j1`，成功完成 |
| 3 | G0 configure 失败 | skalibs 自定义 configure 在交叉编译时无法自动检测 `/dev/urandom` sysdep | 在 manifest configure_options 中添加 `--with-sysdep-devurandom=yes` |
| 4 | G4 manifest 缺少 build_system | G4 检查要求顶级字段 `build_system:`，但 manifest 只有嵌套 `build.system:` | 在 manifest.yaml 添加顶级 `build_system: autotools` 字段 |
| 5 | 预扫描风险警告 | pthread_cancel 在 musl/OHOS 不可用; ppoll 不可用 | 编译无实际错误，skalibs 代码已有条件编译处理 |

## 源码修改
无补丁，无需修改源码。所有编译成功无需任何源码修改。

## 依赖版本
- 无外部依赖（skalibs 是基础库）
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18)
- 目标: aarch64-unknown-linux-ohos

- musl libc (OHOS 系统 libc)

## 验证结果
详见 reports/test-report.md — 18项测试全部通过 (100%)

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| skalibs-2.14.5.1-ohos-aarch64.tar.gz | 2405KB | 预编译包（共享库+静态库+头文件+sysdeps） |
| skalibs-2.14.5.1-ohos-aarch64-debug.tar.gz | 416KB | 调试符号包 |

## 注意事项
1. skalibs 使用自定义 configure 脚本（非标准 GNU autotools），交叉编译需 `--with-sysdep-devurandom=yes`
2. skarnet.org 原始下载 URL 在此平台不可用，需使用 GitHub tarball 替代
3. tarball 内目录名非标准（`skarnet-skalibs-6b1d07c/`），init-build 已处理
4. env_get 函数已废弃，建议使用 env_get2
5. bitarray_peek 是宏定义而非函数
6. SHA256Schedule 是自定义结构体名（不是常见的 SHA256_CTX）
7. 此库为 skarnet.org 基础库，后续 execline/s6arnet/s6 等依赖此库

---
**编译结束**: 2026-06-10
**最终状态**: built（待升级为 published）
---

**编译结束**: 2026-06-10 10:55
**最终状态**: published
