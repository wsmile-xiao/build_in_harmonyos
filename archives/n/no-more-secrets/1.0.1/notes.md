# no-more-secrets 1.0.1 — 适配笔记

## 软件信息
- 上游: https://github.com/bartobri/no-more-secrets（官方 tag `v1.0.1`）
- 语言: C（GPL-3.0-or-later）
- 构建系统: 纯 GNU Make（无 configure）
- 产物: `nms`、`sneakers` 两个命令行工具 + man 页（man6）

## 适配决策
1. **选 ncurses 实现**：上游提供无依赖的 ANSI/VT100 版（`make nms`）与
   ncurses 版（`make all-ncurses`，链接 `-lncursesw`）。主流发行版打包
   均采用 ncurses 版，终端兼容性更好；本配方以 Conan 依赖方式引用已发布
   的 `ncurses/6.6`（静态 `libncursesw.a`，头文件位于 include/ 根，
   `<ncurses.h>` 直接可用）。
2. **patch 0001-Makefile.patch**：上游 `-ncurses` 链接目标只有
   `$(CC) $(CFLAGS)`，无法传入 `-L<依赖libdir>`（交叉工具链必需）。
   补丁在 `nms-ncurses`/`sneakers-ncurses` 两条链接行加入 `$(LDFLAGS)`。
   通用构建增强，不含平台宏（`guard: none`）。
3. **in-source 构建**：上游 Makefile 无 VPATH，无法 out-of-source；
   配方 layout 设 `folders.source = folders.build = "."`。
4. **不走 `make install`**：OHOS 构建沙箱缺少可用的 GNU coreutils
   `install`（/bin/install 权限受限）；package() 直接 conan copy
   `bin/nms`、`bin/sneakers`、man6 页与 LICENSE。

## 编译命令（等价于配方 build()）
```sh
make -j1 CC=clang CFLAGS="-fPIC -O2 -I<ncurses include>" \
     LDFLAGS="-L<ncurses lib>" all-ncurses
```

## 验证
- `nms -v` → `nms version 1.0.1`（非交互干净退出）
- `sneakers` 需交互 TTY；非 tty 下提示后退出，仅做存在性/可执行校验
- 上游无测试套件；test_package 用 test.sh 冒烟验证上述两点

## 关键命令
- conan create: 见 conanfile.py（requirement ncurses/6.6）
---

**编译结束**: 2026-09-03 13:03
**最终状态**: built
