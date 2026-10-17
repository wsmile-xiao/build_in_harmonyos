# nvi 1.81.6 适配笔记

## 编译环境
- 构建系统: autotools（configure 在源码 dist/ 子目录，out-of-source 构建于 build.unix）
- 编译日期: 2026-09-08
- 编译器: clang/clang++ (OHOS aarch64, armv8)
- 状态: built（conan-verify 通过，未提 PR，PR 由主编负责）

## 编译步骤
1. 下载源码：https://mirrors.ocf.berkeley.edu/debian/pool/main/n/nvi/nvi_1.81.6.orig.tar.gz
   sha256=8bc348889159a34cf268f80720b26f459dbd723b5616107d36739d007e4c978d
2. 打 config.guess/config.sub ohos 补丁（patches/0001-dist-config.guess.patch，strip=1）
3. configure（在源码树 build.unix 目录，VPATH 指向 dist/）：
   ```
   ../dist/configure --prefix=$DEFAULT_PREFIX --with-db_type=bundled \
     vi_cv_path_preserve=$HOME/tmp/vi.recover \
     CPPFLAGS="-I<ncurses>/include -I<db>/include" \
     LDFLAGS="-L<ncurses>/lib -L<db>/lib"
   ```
   - 依赖注入用 build_folder 私有 prefix（R49），禁止 /usr/local
4. make -j1（HMDFS jobserver 限制）
5. make install：必须传 ln=<wrapper> 覆盖 vi→ex/view 硬链接
   （wrapper: `#!/bin/sh exec /usr/bin/ln -s "$@"`，HMDFS 硬链接报 Operation not permitted）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 不识别 HarmonyOS | 2007 年 autoconf 无 ohos triplet | patches/0001-dist-config.guess.patch 增加 aarch64-unknown-linux-ohos |
| 2 | make install vi→ex/view 硬链接失败 | HMDFS 不支持硬链接（Operation not permitted） | configure/make 传 ln=<wrapper>，wrapper 内 exec /usr/bin/ln -s |
| 3 | nvi 无 --version | nvi 是 ex/vi 实现，不提供 --version 选项 | 测试用 `vi -e -s` + stdin ex 命令驱动（printf 's/.../wq'） |
| 4 | vi 运行需 terminfo | ncurses 静态链接但运行期需 TERMINFO 环境变量 | test 用 env="conanrun" 注入 ncurses runenv（TERMINFO 指向 share/terminfo） |
| 5 | configure 在 dist/ 子目录 | nvi 源码结构特殊（configure 不在根） | autotools.configure(build_script_folder="dist")，同 berkeley-db/4.8.30 配方 |

## 源码修改
- patches/0001-dist-config.guess.patch：dist/config.guess 增加 HarmonyOS 识别（aarch64-unknown-linux-ohos）
- patches/0002-dist-config.sub.patch：dist/config.sub 增加 ohos-linux 三元组
- conanfile.py build() 动态修改 dist/configure：config.status 临时目录 umask 077→002（E114 类，refresh-patch 将 configure 判为 generated 无法出补丁文件）

## 依赖版本
- berkeley-db/4.8.30（configure 检测 db_create，静态 libdb.a，制品仓已发布）
- ncurses/6.6（静态 wide-char libncursesw.a，制品仓已发布）

## 验证结果
```bash
# 运行验证（探索阶段实测成功）
printf 's/nvi/nvi-ok/\nwq\n' | TERM=dumb vi -e -s file
# 产物：bin/vi bin/ex bin/view lib/libvi.so.0.0.0 lib/libvi.a share/man share/vi/catalog
# vi NEEDED 仅 libvi.so.0 + libc.so（ncurses/db 静态并入）
# make check: nvi 无 TESTS，exit 0
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | 最终版配方（Autotools + 依赖注入 + ln wrapper + configure umask 动态补丁） |
| conandata.yml | 源码 URL + sha256 + patches 声明 |
| patches/0001-dist-config.guess.patch | dist/config.guess ohos 支持 |
| patches/0002-dist-config.sub.patch | dist/config.sub ohos 支持 |
| test_package/ | conanfile.py + test.sh（实质运行 vi 二进制，R34） |
| commands.json（软件级） | name=nvi, type=tool, commands=[vi,ex,view] |

## 注意事项
- HMDFS 硬链接限制必须传 ln=wrapper（软链接规则 R5）
- HMDFS jobserver 限制：make 用 -j1
- vi_cv_path_preserve 用 build_folder 私有路径（R49），不用固定系统临时目录
- TERMINFO 环境变量指向 ncurses 包 share/terminfo 才能运行 vi
---

**编译结束**: 2026-09-08 04:06
**最终状态**: built
