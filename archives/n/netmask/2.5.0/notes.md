# netmask 2.5.0 适配笔记（2.4.4 → 2.5.0 版本升级）

## 编译环境
- 构建系统: autotools（官方 release dist tarball：configure/Makefile.in/config.h.in 预生成）
- 编译日期: 2026-09-04
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos，本机 native，build=host=OHOS）
- 依赖: check/0.15.2（制品仓 ohpcd，OHOS armv8 binary 实测可下载）
- profile: ci/conan/profiles/ohos-aarch64（os=OHOS / arch=armv8 / clang 15）

## 版本升级决策（相对 2.4.4）
| 项 | 2.4.4 | 2.5.0 | 影响 |
|---|---|---|---|
| 上游 tag | v2.4.4 (29a9c239) | v2.5.0 (01b7a4dc, 2025-07-27) | release notes: patricia tree 内部重写、遍历 API、--octal bug 修复 |
| 源码形态 | Debian orig（无 configure） | GitHub release dist（含 configure，sha256 5975a37f…实测） | 免 automake 自举；source URL 换官方 release 资产 |
| 第三方依赖 | 无 | **check (libcheck) 硬依赖** | configure.ac PKG_CHECK_MODULES([CHECK],[check])；2.4.4 曾记录"禁升级"即因此（现 check/0.15.2 已发布，可升级） |
| 测试 | 26 check | **34 check**（新增 IPv6 6 项 + file_input + coverage1 + v4_edge） | test_package fixtures 26→34，逐条复刻 |
| config.guess | 不触发（无 canonical） | 触发（AX_CODE_COVERAGE） | 本机/CI uname=HarmonyOS 无法 guess → --build=aarch64-linux-ohos |

## 真实编译过程（2026-09-04 宿主探索 + conan 流程设计）
```bash
# 源码：官方 release 资产经 ghfast.top 镜像下载，sha256 实测 == 5975a37f…2f4c73
#   https://github.com/tlby/netmask/releases/download/v2.5.0/netmask-2.5.0.tar.gz

# ① E114 修补：dist configure 内嵌 `(umask 077 && mktemp -d "./confXXXXXX")`，
#    HMDFS 下 config.status 报 Permission denied → 全量去掉 `umask 077 && `
# ② configure（in-source；check.pc 需在 PKG_CONFIG_PATH；config.guess 认不出
#    HarmonyOS → 显式 --build）
#    CC=clang PKG_CONFIG_PATH=<check.pc dir> ./configure --build=aarch64-linux-ohos \
#        --prefix=/ MAKEINFO=true     # exit 0；check 0.15.2 命中、syslog/strerror/strtoul yes
# ③ 链接（静态，产物自包含）
#    make -j1 CHECK_LIBS=<check 包>/lib/libcheck.a   # exit 0；ldd 无 libcheck.so NEEDED
# ④ 上游测试
#    make check LOG_COMPILER=/data/service/hnp/bin/bash  # 34/34 ok（首次动态链接
#        libcheck.so 时需 LD_LIBRARY_PATH；静态链接后无需，直接 34/34 通过）
# ⑤ 冒烟
#    ./netmask -v → netmask, version 2.5.0
#    ./netmask 192.168.0.1/255.255.255.0 → 192.168.0.0/24
```

## 关键坑与处置（新增/变更相对 2.4.4）
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `cannot guess build type` | 2.5.0 configure 触发 config.guess，`uname -s=HarmonyOS` 不在识别表 | `./configure --build=aarch64-linux-ohos`（config.sub 支持该 triplet；本机/CI 均 build=host=OHOS，与 profile 一致） |
| 2 | PKG_CHECK_MODULES 找不到 check | 需要 check.pc 在 pkg-config 搜索路径 | generate() PkgConfigDeps 生成指向真实包目录的 .pc；configure 前 `export PKG_CONFIG_PATH=<generators_folder>` |
| 3 | 链接 `-lcheck` 报 unable to find library / 产物 NEEDED libcheck.so | check 0.15.2 包内自带 check.pc 的 prefix 指向构建临时目录 b/...（包配方缺陷）；动态 .so 被链接进 netmask，运行时缺库 | make 时 `CHECK_LIBS=<check 包>/lib/libcheck.a` 覆写为静态归档绝对路径 → 无 NEEDED，产物自包含 |
| 4 | E114 umask 077（同上） | dist configure 由 autoconf 生成，内嵌 umask 077 建临时目录 | `_drop_umask_077`：全量去掉 `umask 077 && ` |
| 5 | test-driver kernel-exec testscript 被拒 | HMDFS + conan 构建子进程无法 exec 文本 shebang（E046 变体，同 2.4.4） | `make check LOG_COMPILER=/data/service/hnp/bin/bash` |
| 6 | makeinfo 缺失 | 无 texinfo | configure `MAKEINFO=true` 固化（同 2.4.4） |

## 源码修改
- 无 patches/（conandata patches 为空）。configure 内 umask 077 为 autoconf 通用生成逻辑，
  build() 运行时去掉（同 2.4.4 先例），非上游源文件差异、不涉平台宏。

## 依赖版本
- requires: check/0.15.2（制品仓 ohpcd；configure/link 需要；源码未 include check.h）
- build-time: 官方 dist 无需 tool_requires；pkg-config 由 profile buildenv 的
  /data/service/hnp/bin/pkg-config 提供（与 2.4.4 用 hnp bash 同理）
- 运行时: 无（静态链接 libcheck.a 且无符号引用 → 自包含）

## 验证结果
```bash
# make check = ./testscript（34 个 check）—— 34 ok / 0 not ok
# test_package test.sh 复刻 34 个 check（编号 1-34），preflight `-v` 含 2.5.0
# 冒烟：./netmask -v → netmask, version 2.5.0
```

## 注意事项
1. **本版本首次适配不造后缀**（2.5.0；R37 无历史发布）。
2. **版本红线更新**：2.4.4 笔记中"2.4.5+ 引入 libcheck 禁升级"的限制随本版本解除——
   前提是 check/0.15.2 已发布（W0 实测通过）。后续升级仍需先确认依赖已发布（R36）。
3. **构建必须 in-source**：testscript 相对路径引用 ./netmask 与 tests/；conanfile 不设
   分离 build（同 2.4.4）。
4. W2 原子性：本 PR 仅动 archives/n/netmask/ 目录下 2.5.0 相关（+软件级版本索引）。
   遗留的 archives/l/libXext 脏改动（历史遗留）未触碰。

## 2.4.4 → 2.5.0 升级提交说明
- 本适配配方/笔记位于: archives/n/netmask/2.5.0/（分支 feat/netmask-2.5.0）
- 升级任务交付的独立升级 manifest 记录位于分支 chore/netmask-2.5.0 的归档外路径
  （archives/n/netmask-2.5.0/manifest.json，按任务方指定放置；与本 conan 配方分属两分支，
  避免仓库 JC6 单软件原子性冲突）
- 软件级 manifest versions 已登记 2.5.0
---

**编译结束**: 2026-09-04 18:33
**最终状态**: built
