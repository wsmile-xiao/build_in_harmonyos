# sl 5.02-r1 编译笔记

## 软件简介
sl (Steam Locomotive) 是一个经典的终端火车动画命令，当用户误输入 `sl` (而不是 `ls`) 时会显示一个动画火车。

## 编译过程

### 源码获取
- 来源: GitHub (mtoyoda/sl)
- URL: https://github.com/mtoyoda/sl/archive/5.02.tar.gz
- Savannah SSL证书问题，改用GitHub下载

### 构建系统
- **类型**: 简单Makefile（非autotools）
- 原始Makefile使用 `CC=gcc`, `CFLAGS=-O`, `-lncurses`
- 需修改为: `CC=clang`, 添加include/lib路径, `-lncursesw -ltinfo`

### 依赖处理
- **ncurses**: 从cmd-pkgs预编译包获取 (ncurses/6.4)
  - 已安装: libncursesw.a (静态库, wide-char版本)
  - 已安装: libtinfo.a (terminfo库)
  - 注意: 预编译包中只有ncursesw(wide-char版本), 不提供libncurses.a
  - 需使用 `-lncursesw -ltinfo` 而非 `-lncurses`

### Makefile修改 (补丁: 0001-makefile-ohos-clang.patch)
- `CC=gcc` → `CC=clang`
- `CFLAGS=-O` → `CFLAGS=-fPIC -O2 -I$(DEFAULT_PREFIX)/include`
- 新增 `LDFLAGS=-L$(DEFAULT_PREFIX)/lib`
- `-lncurses` → `-lncursesw -ltinfo`
- 新增 `install` target: `DESTDIR=$(DEFAULT_PREFIX)/bin/sl`
- 新增 `clean` target

### 编译命令
```bash
cd $BUILD_SRC_DIR
make
```

### 安装
- `make install DESTDIR=$TEST_PREFIX` → staging验证
- `make install` → 本地安装到 $DEFAULT_PREFIX

### 验证
- 二进制执行正常 (因非真实终端环境显示 "Error opening terminal")
- verify-build: PASS (G1 PASS, G2 PASS-warn, G3 PASS-warn, G4 PASS)

### 预编译包
- sl-5.02-r1-ohos-aarch64.tar.gz (309KB)
- 包含: bin/sl (ELF签名, stripped)

## 编译日期
2026-06-04
---

**编译结束**: 2026-08-23 00:28
**最终状态**: built

## Conan Adaptation (2026-08-22)
- Conan recipe (conanfile.py) generated and verified
- test_package with test_sl.py smoke test
- commands.json declared (R38)
- W3 local CI simulation passed
- W4 pre-PR audit passed
<!-- PR created via ohc-run.py submit -->
