# squashfs-tools-ng 1.3.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-05 (首次), 2026-08-27 (conan 适配), 2026-09-18 (CI 修复重验)
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 源码获取: GitHub archive tarball (v1.3.2 tag)
   - 注意: tarball 不含预生成 configure, 需 autoreconf -fi
2. autoreconf: 需要 automake/1.18 + libtool/2.5.4.1 (tool_requires)
   - ACLOCAL_PATH 需包含 libtool 的 share/aclocal 和系统 pkg-config 的 pkg.m4
3. configure: --build=aarch64-unknown-linux-gnu --disable-maintainer-mode
   - PKG_CHECK_MODULES 通过预设置 CFLAGS/LIBS 环境变量绕过
   - 所有压缩器启用: gzip, xz, lz4, zstd, bzip2, lzo
4. make -j1 (OHOS 限制: 多线程 make 的 jobserver mkfifo 不支持)
5. make check (上游测试套件, 67 项)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tarball 无 configure | GitHub archive 不含生成文件 | tool_requires automake/libtool, build() 中 autoreconf -fi |
| 2 | autoreconf 缺 m4 宏 | LT_INIT 需要 libtool.m4, PKG_PROG_PKG_CONFIG 需要 pkg.m4 | ACLOCAL_PATH 注入 libtool 和 pkg-config 的 aclocal 目录 |
| 3 | PKG_CHECK_MODULES 失败 | conan 依赖不提供 .pc 文件 | 预设置 <DEP>_CFLAGS/<DEP>_LIBS 环境变量绕过 pkg-config |
| 4 | config.status 权限拒绝 | HMFS 下 umask 077 + mktemp -d 创建不可访问目录 | mktemp wrapper (exit 1) + config.status 临时目录替换为可写路径 |
| 5 | make 重新运行 autotools | maintainer-mode 默认启用 | --disable-maintainer-mode |
| 6 | make check 12 项 xfrm/table/xattr 测试 exit 127 | zstd/1.5.6 制品仓包仅提供动态库 libzstd.so.1, 测试二进制运行时无 LD_LIBRARY_PATH | generate() 中将所有依赖 libdirs 注入 LD_LIBRARY_PATH |
| 7 | 工具脱离 conanrun 环境执行 exit 127 (L2 平台冒烟失败) | 交付工具 NEEDED libzstd.so.1 (动态链入 zstd), 系统无此库 | 升级 zstd/1.5.7.1 (首个含 libzstd.a 的版本), 复制 libzstd.a 到私有目录作为唯一 -L 搜索路径静态链入; 注意: libtool 会把 -Wl,-Bstatic/-Bdynamic 对前置重排使其失效, 绝对路径 .a 会被嵌套进 libsquashfs.a (ld.lld 报 neither ET_REL), 私有目录方案两者皆避开 |

## 源码修改

无源码补丁 (patches_applied 为空)。所有适配通过 conanfile.py 代码内处理:
- umask 修复: _fix_config_status() 方法在 configure 后修改 config.status
- mktemp 修复: generate() 创建 mktemp wrapper 强制 fallback
- LD_LIBRARY_PATH 修复: generate() 注入全部依赖 libdirs

## 依赖版本

- zlib/1.3.1 (静态, R26 系统同名库)
- xz/5.6.2 (liblzma)
- lz4/1.10.0
- zstd/1.5.7.1 (静态链入 libzstd.a — 1.5.6/1.5.7 仅含 .so, 工具动态依赖会导致脱离 conan 环境不可执行)
- bzip2/1.0.8
- lzo2/2.10
- readline/8.3
- ncurses/6.6 (readline terminfo 依赖: tgetstr/tgetflag)
- automake/1.18 (tool_requires)
- libtool/2.5.4.1 (tool_requires)

## 上游测试清点与实测 (R51)

- 上游 tests/ 目录: 67 项注册测试 (make check)
- 实测环境: 本机 HarmonyOS 设备, conan create + ohos-aarch64 profile
- 实测结果: **67/67 PASS, 0 FAIL, 0 SKIP** (第二轮, 修复 LD_LIBRARY_PATH 后)
- 首轮曾 55/67 (12 项 exit 127: libzstd.so.1 运行时缺失), 修复后全绿
- test_package: 5 个 CLI 工具 --version + gensquashfs/rdsquashfs round-trip + tar interop (tar2sqfs/sqfs2tar) + sqfsdiff, 共 12 项断言全过

## 验证结果

```bash
# conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -r=ohpcd --build=missing
# make check: # TOTAL: 67 / # PASS: 67 / # SKIP: 0 / # XFAIL: 0 / # FAIL: 0
# test_package: All tests passed (5 tools --version + round-trip)
```
---

**编译结束**: 2026-09-19 00:02
**最终状态**: built
