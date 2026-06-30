# icon 9.5.25a 适配笔记

## 编译环境
- 构建系统: custom（Icon自有构建系统，使用 make Configure name=linux）
- 编译日期: 2026-06-16
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `make Pure` 清理旧编译产物
2. `make Configure name=linux` 配置为linux平台（NoGraphics模式）
3. 修改 Makedefs: CC=gcc→CC=clang, CFLAGS=-O→CFLAGS=-fPIC -O2 -D_MUSL
4. 修改 src/h/define.h: 添加 #define _MUSL 1
5. `make All` 编译（Icont/Ilib/Ibin）
6. 编译过程中对 icont/iconx 进行 ELF 签名（否则 Ilib 编译失败：Operation not permitted）
7. `make Install dest=$TEST_PREFIX/$DEFAULT_PREFIX` 安装到 staging 目录
8. 手动拷贝文件到 $DEFAULT_PREFIX 模拟用户部署

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | icont/iconx 无法执行 (Operation not permitted) | HarmonyOS ELF签名机制，未签名二进制不可执行 | 使用 ohc-run.py sign-elf 对 icont/iconx 签名后继续编译 |
| 2 | fpoll.c 中 __freadahead 未声明 | musl libc 中 __freadahead 函数存在但未在 stdio_ext.h 中声明 | 添加 size_t __freadahead(FILE *f); 声明 |
| 3 | mklib.sh 无法识别 HarmonyOS 平台 | uname -s 返回 HarmonyOS，不在 mklib.sh 的 case 列表中 | 在 Linux*|*BSD*|GNU*|Haiku* 后添加 |HarmonyOS* |
| 4 | make Install dest=$TEST_PREFIX/$DEFAULT_PREFIX 失败 | 父目录不存在且目录已存在时 Install 拒绝创建 | 先创建父目录，再运行 make Install |

## 源码修改

| 补丁 | 文件 | 修改内容 |
|------|------|----------|
| 0001-Makedefs.patch | Makedefs | CC=gcc→clang, CFLAGS=-O→-fPIC -O2 -D_MUSL |
| 0002-ipl-cfuncs-fpoll.c.patch | ipl/cfuncs/fpoll.c | 添加 __freadahead 声明 |
| 0003-ipl-cfuncs-mklib.sh.patch | ipl/cfuncs/mklib.sh | 添加 HarmonyOS* 平台模式 |
| 0004-src-h-define.h.patch | src/h/define.h | 添加 #define _MUSL 1 |

## 依赖版本

- 无外部依赖（C语言，仅使用系统库 libm/libdl/libpthread）

## 验证结果

### 版本号
```bash
$ /storage/Users/currentUser/usr/local/bin/icon -V
Icon Version 9.5.25a, September 7, 2025  (linux 32/64, Jun 16 2026)
```

### Hello World
```bash
$ echo 'procedure main(); write("Hello from Icon!"); end' > hello.icn
$ icont hello.icn && ./hello
Hello from Icon!
```

### 数学运算
```bash
$ echo 'procedure main(); write(2+3); write(sqrt(2.0)); end' > math.icn
$ icont math.icn && ./math
5
1.414213562
```

### 字符串操作
```bash
$ echo 'procedure main(); s := "Hello World"; write(s[2:5]); write(reverse(s)); end' > str.icn
$ icont str.icn && ./str
ell
dlroW olleH
```

### 协程 (co-expression)
```bash
$ echo 'procedure main(); co := create 1 to 5; while x := @co do write(x); end' > coexpr.icn
$ icont coexpr.icn && ./coexpr
1
2
3
4
5
```

### 检测特性
```
Features: UNIX, ASCII, co-expressions, dynamic loading, external values, keyboard functions, large integers, pipes, system function
```

### make Test 结果
- 总测试数: 99
- 通过: 98
- 失败: 1 (ilib — 仅因 /tmp 只读导致 directory 函数返回空值，已知 E002 限制)

## 对话记录

### Phase 2: 配置
- `make Pure` 清理 → `make Configure name=linux` → 手动修改 Makedefs (CC=clang, CFLAGS=-fPIC -O2 -D_MUSL) 和 define.h (#define _MUSL 1)
- fpoll.c 和 mklib.sh 已在之前编译中修改，保留在 work 目录中

### Phase 3: 编译
- `make All` 成功编译 Icont/Ilib/Ibin
- icont/iconx 需 ELF 签名才能执行 Ilib 编译
- 签名工具: `ohc-run.py sign-elf bin/icont bin/iconx src/rtt/rtt`

### Phase 4: 安装
- `make Install dest=$TEST_PREFIX/$DEFAULT_PREFIX` — 需预先创建父目录
- staging 目录包含: bin/(icon,icont,iconx,libcfunc.so), lib/(392 .u1/.u2 + icall.h), doc/, man/

### Phase 5: 测试
- `make Test` — 99 项测试，98 通过，1 失败 (ilib)
- ilib 失败原因: directory() 检测 /tmp 时返回空值 (HarmonyOS /tmp 只读 E002)

### Phase 6: 打包
- `ohc-run.py package icon 9.5.25a` — 生成 icon-9.5.25a-ohos-aarch64.tar.gz (5.9MB)
- 本地安装验证通过

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| icon-9.5.25a-ohos-aarch64.tar.gz | 6203KB | 预编译包 |

## 注意事项

- Icon使用自有构建系统（非autotools/cmake），配置方式为 make Configure name=linux
- 需在编译Ilib前对 icont/iconx 二进制进行ELF签名
- 无图形支持（NoGraphics配置）
- make Install不支持标准DESTDIR模式，需手动适配
---

**编译结束**: 2026-06-16 03:21
**最终状态**: built
