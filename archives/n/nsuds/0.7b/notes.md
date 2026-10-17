# nsuds 0.7b 适配笔记

上游版本 **0.7B**（`AC_INIT([nsuds], [0.7B])`），Conan 版本号按 Conan 2 全小写
引用约束归一化为 **0.7b**；二进制 `--version` 仍输出 `nsuds version 0.7B`。

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am；git 快照无预生成 configure）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4（OHOS 原生 / aarch64）
- 状态: built

## 编译步骤

```
# 探索编译（ohc-run 模式 B，工作目录 $BUILD_SRC_DIR）
autoreconf --install --verbose        # git 快照无 configure，需自举（automake 1.18）
sed -i 's/umask 077/umask 000/g' configure   # E114: HMDFS mktemp 临时目录不可写
CPPFLAGS=-I<ncurses>/include LDFLAGS="-L<libncurses alias> -L<ncurses>/lib" \
CFLAGS="-fPIC -O2 -fcommon" \
  ./configure --prefix=/ --disable-setgid
make -j2
make install DESTDIR=<stage>
```

Conan 配方（archives/n/nsuds/0.7b/conanfile.py）执行等价流程：
`autoreconf` → 修 configure umask → `configure --prefix=/ --disable-setgid`
→ `make -j1` → `make install`（`--build=missing`，test_package 同步跑通）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Conan 2 拒绝 `nsuds/0.7B` 引用（全小写约束） | Conan 2 recipe ref 需小写 | Conan 版本用 `0.7b`（上游 0.7B 归一化），README/notes 说明 |
| 2 | `codeload.github.com/.../<sha>` 无扩展名 → `BadZipFile` | conan get() 按 URL basename 判压缩格式 | source() 显式 `filename="nsuds-0.7b.tar.gz"` |
| 3 | 链接期 `duplicate symbol: level_data / showmarks` | 老 C 代码头文件内 tentative definition；clang≥11 默认 -fno-common | CFLAGS 追加 `-fcommon`（恢复 -fcommon 行为） |
| 4 | `make install` 失败 `chgrp: No such file or directory` | OHOS(toybox) 无 chgrp、无 games 组；Makefile.am install-*hook 无条件 chgrp | conandata patch `0001-remove-chgrp-install-hooks.patch` 删除两处 chgrp（并 `--disable-setgid`） |
| 5 | `config.status: can't create ./confXXXX/subs1.awk: Permission denied` | HMDFS 下 `umask 077 && mktemp -d` 产生不可写 drwx--S--- 目录（E114） | autoreconf 后 `sed -i 's/umask 077/umask 000/g' configure`（configure 生成 config.status 时继承） |
| 6 | ncurses 6.6 包只有 `libncursesw.a`，configure 探测 `-lncurses` 失败 | ncurses widec 静态包不产 libncurses.a | build 目录私有 `libncurses.a -> libncursesw.a` 别名（绝不触碰 /lib /lib64，R26） |
| 7 | automake/aclocal 缺失 | OHOS 基础镜像无 automake（E178） | `tool_requires("automake/1.18")`（afuse 同款做法） |

## 源码修改

- `patches/0001-remove-chgrp-install-hooks.patch`：删除 src/Makefile.am
  `install-exec-hook` 与 `install-data-hook` 中 `chgrp games ...` 两行
  （OHOS 无 chgrp 二进制/games 组；setgid 通过 --disable-setgid 关闭）。

## 依赖版本

- ncurses/6.6（Conan 依赖，静态 wide-char 包 `--without-shared`，R26 系统同名库隔离）
- automake/1.18（仅构建期 tool_requires，用于 autoreconf 自举）

## 验证结果

```bash
# W3 本地 CI 模拟（setup.sh + build_and_test.sh）：exit_code=0
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
#   → 编译通过；test_package test() 真实执行通过
# 打包产物内 nsuds 二进制非交互 CLI：
./bin/nsuds --version   # nsuds version 0.7B  (exit 0)
./bin/nsuds --help      # Usage: nsuds [OPTIONS]... (exit 0)
./bin/nsuds -v / -h     # 同上
# 上游 make check：无 TESTS，no-op（exit 0）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 完整配方（autoreconf+静态 ncurses 适配） |
| conandata.yml | 官方源 + sha256 + patch 声明 |
| patches/0001-remove-chgrp-install-hooks.patch | chgrp hook 移除补丁 |
| test_package/ | conanfile.py + test.sh + MANIFEST.yml（实质执行二进制 CLI） |
| commands.json | 软件级 R38 tool 声明（bin/nsuds, --help/-h/--version/-v） |

## 注意事项

- nsuds 是纯交互式 ncurses 游戏，本身无可自动化上游测试；`make check` 为 no-op。
  可验证的非交互 CLI（--version/-v/--help/-h，均在任何 ncurses 初始化前 exit 0）
  已由 test_package 实质执行并断言输出。
- 编译期内 bake 的 HELPDIR/SCOREDIR 为 `--prefix=/` 派生绝对路径
  （/share/doc/nsuds-0.7B/ 与 /var/games/nsuds/），属 autotools+DESTDIR 打包固有行为。
- 上游版本 0.7B 的 Conan 引用记为 0.7b（见上），PR/分支仍按任务约定用 0.7B。
---

**编译结束**: 2026-09-03 23:52
**最终状态**: published
