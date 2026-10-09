# mailto 1.3.2 适配笔记

## 上游信息

- 上游：Andreas Ley 的 WWW Mail Gateway（Apache 软件基金会 1999 年发布）
- 功能：解析 HTTP 表单（或 URL 参数），把字段拼装成 MIME 邮件，调用本机 sendmail 投递
- 设计背景：1999 年"WWW 上匿名发信"不可取，因此附带访问控制文件 `mailto.conf`，
  规定哪些人可通过网关发信
- 形态：2 个 .c（`mailto.c` 18KB + `util.c` 2.4KB）+ 2 个消息头（英/德）
- 主页：<https://www.apache.org/distware/mailto/>
- 作者署名（实测 `-v` 输出）：`(c) 1994-1998 by Andreas Ley (Andreas.Ley@rz.uni-karlsruhe.de)`

## 源码获取

```
http://deb.debian.org/debian/pool/main/m/mailto/mailto_1.3.2.orig.tar.gz
sha256 = 74050d4dae4b3f32ba9f5069251394887b6f044f8c68ef49a0e350876d0d1c99
```

## 构建路线：直驱 clang，不跑上游 Makefile

上游 Makefile 一共只有这几个目标：

```make
CC=gcc
mailto: $(OBJECTS)
	$(CC) $(CFLAGS) $(OBJECTS) -o $@

install: all
	test -d $(BINDIR) || mkdir -p $(BINDIR)
	$(INSTALL_PROGRAM) mailto $(BINDIR)

INSTALL = bsdinst            # ← BSD 专有
BINDIR = /usr/machine/etc/httpd/cgi-bin   # ← 写死的绝对路径
```

两个结论：

1. **`all` 目标就是裸的 `$(CC) $(CFLAGS) *.o -o mailto`**，没有 configure、没有
   自动依赖探测、没有可选模块逻辑 —— 与本仓���已合入的 `prctl` / `snooze` 同类，
   在 conanfile 里直接驱动 clang 即可，不必也不宜在交叉环境调用 make。
2. **`install` 目标不可用**：`bsdinst` 是 BSD 的 install 实现，OHOS 没有；
   `BINDIR` 又写死成 `/usr/machine/etc/httpd/cgi-bin` 这个 Apache 1.3 时代路径。
   本包只做 build/package，`package()` 用 `copy()` 自行决定落点：
   `bin/mailto` + `share/doc/mailto/{README,ChangeLog,INSTALL}` + `etc/mailto.conf`。

## ⚠ 唯一的适配点：`getline` 符号冲突

这是本包最容易踩、也是唯一需要 patch 的地方。

`util.c` 里定义了一个 1999 年风格的行读取辅助函数：

```c
int getline(char *s, int n, FILE *f) {   /* s[0..n-1]，遇 CR/LF 折叠，返回 feof */
```

而 POSIX.1-2008 把 `getline` 收进了标准库，OHOS sysroot 的 `<stdio.h>` 里有：

```c
ssize_t getline(char **restrict, size_t *restrict, FILE *restrict);
```

两者签名完全不同，交叉编译时**默认可见性**下直接报：

```
util.c:96:5: error: conflicting types for 'getline'
        int getline(char *s, int n, FILE *f) {
C:/ohos-tc/sysroot/usr/include/stdio.h:155:9: note: previous declaration is here
ssize_t getline(char **__restrict, size_t *__restrict, FILE *__restrict);
```

### 处置：重命名，不删不改行为

`patches/0001-rename-getline-to-avoid-posix-sysroot-clash.patch` 把符号改成
`mailto_getline`，**函数体一字不动**。

为什么不用删掉这个函数、或者用 `-Dgetline=...` 宏绕过：

- **删函数**：会改变上游源码语义，且 patch 变成"减法"，评审难以判断是否影响了行为。
- **`-Dgetline=mailto_getline`**：实测**行不通**。函数**定义处**的标识符也会被宏替换，
  于是 sysroot 的声明同样变成 `mailto_getline`，冲突只是换了个名字继续报。
  （错误信息实测：`error: conflicting types for 'mailto_getline'`。）
- 排查后还确认：这个函数在 `util.c` 里**只有定义、没有内部调用**，`mailto.c` 也从未
  引用它（上游没提供 `util.h`，`util.c` 的四个函数 `getword` / `rind` / `getline` /
  `send_fd` 全是无调用点的遗留辅助代码）。所以重命名后不存在任何需要同步的调用点。

## 编译告警说明

`mailto.c` 用 `-Wall` 会有 12 条告警，全部来自 1999 年的 gnu89 代码风格：

| 类别 | 数量 | 说明 |
|---|---|---|
| `-Wformat` / `-Wformat-extra-args` | 3 + 3 | printf 的 format 串与实参类型不完全一致 |
| `-Wformat-security` | 2 | format 串来自非常量 |
| `-Wcomment` | 1 | 块注释里嵌套了 `/* */`（`NEED_STRERROR` 那段） |
| `-Wdangling-else` / `-Wparentheses` | 1 + 1 | `while (ptr=strchr(...))` 这类老写法 |

这些都不影响正确性（CGI 工具、输出内容固定、且测试用例断言的是确定的输出文本），
因此配方统一用 `-w` 静默，避免 CI 日志被 12 行历史遗留告警淹没。**不启用 `-Werror`。**

## 验证方式（CI 零网络、零 MTA）

`mailto` 是 CGI 程序，没有库 API 可链接，消费者用例只能按"CGI 程序的真实调用方式"
验证。关键在于**裸调用**（不设任何 CGI 环境变量）会走 `QUERY_STRING` 为空的默认分支，
直接吐出一份完整的默认表单：

```
Content-type: text/html

<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">
<!-- mailto v1.3.2 (c) 1994-1998 by Andreas Ley (...) -->
<HTML>
<HEAD>
<TITLE>WWW Mail Gateway</TITLE>
...
```

这给了三条确定性断言（全部基于源码写死文本，不依赖网络、不调用 sendmail）：

| 用例 | 断言 |
|---|---|
| `-v` | 输出含 `mailto v1.3.2` 与 `Andreas Ley` |
| `-h` | 输出含 `Usage:` 与 `[-h] [-v]` |
| 裸调用 | 输出含 `Content-type: text/html` 与 `WWW Mail Gateway` |
| `-Z`（非法选项） | 输出含 `unrecognized option` 与 `Usage:` |

**本地实测**：qemu-aarch64-static + OHOS sysroot 下 **17 项断言全部通过**。

> 教训：断言必须来自**实测输出**。最初按源码里的注释块写了 `Version 1.3.2`，
> 真机跑出来其实是 `mailto v1.3.2`（那段 `** Version 1.3.2 - 2.3.1999` 是
> C 注释，不会被打印）。已按实测输出改正。

## 排查中踩的连锁坑

### 坑 1：conandata.yml 的 `patches` 格式写错 → 补丁被静默跳过（并踩中 L0f）

初版把 `patches` 写成 **dict-by-filename**（key 为补丁文件名）：

```yaml
# ❌ 错误写法
patches:
  0001-rename-getline-to-avoid-posix-sysroot-clash.patch:
    patch_file: "patches/0001-rename-getline-to-avoid-posix-sysroot-clash.patch"
```

Conan 2.x 的 `apply_conandata_patches()` 按 `self.version` 查找
（`patches.get(version)`），key 是文件名时取到**空列表** → 补丁被**静默跳过、
不报任何错**。现象是「补丁明明写了却没生效，编译错误仍是原来的
`conflicting types`」。

当时的误判是「`apply_conandata_patches()` 在本环境下失效」，于是绕道改成手工
`self.run("patch -p1 --batch -i ...")`。本地确实编过了，但 **CI 门禁 L0f 专门校验
conandata 的 patches 格式**，直接拦截：

```
[fail] L0f: conandata.yml patches format wrong — key '0001-...patch' is a filename, not a version
       Use list format (recommended):
         patches:
           - patch_file: "patches/0001-...patch"
             patch_description: "..."
             patch_type: "portability"
L0_RESULT=fail: gate failed: bad_patch_format
L1_RESULT=skip: blocked_by_L0
```

已按 `docs/ADAPTATION_GUIDE.md` 第 7 节改为**列表格式**（含 `patch_file` /
`patch_description` / `patch_type`），配方内改回标准的
`apply_conandata_patches(self)`。

> **教训**：工具「静默失败」比「报错」危险得多。遇到"配置了却没生效"，
> 第一反应应该是怀疑**配置的格式/语义**，而不是先怀疑工具坏了 ——
> 本次正是这个误判把一个格式问题伪装成了环境问题。

### 坑 2：手写 unified diff 的 `@@` 行数不准 → `patch` 报 malformed 且不生效

手写 patch 头 `@@ -93,7 +93,20 @@` 时，只要实际增删行数对不上，GNU patch 会报
`patch: **** malformed patch at line 17: ...`。改用
`difflib.unified_diff(..., n=3)` 从真实原文**自动生成**，不再手写行数。

另：改完配方必须 `conan remove "mailto/1.3.2:*" -c` 清缓存，否则 conan 会复用旧
build 目录里的**未打补丁**源码，看起来"改了没效果"。

## 交付物

```
archives/m/mailto/1.3.2/
├── conanfile.py              配方（直驱 clang + apply_conandata_patches）
├── conandata.yml             源 URL + sha256 + patches 列表格式
├── manifest.yaml             适配要点/依赖/patch 记录
├── notes.md                  本文
├── patches/
│   └── 0001-rename-getline-to-avoid-posix-sysroot-clash.patch
└── test_package/
    ├── CMakeLists.txt
    ├── conanfile.py
    ├── MANIFEST.yml
    └── test_mailto.c         消费者用例（17 项断言）
```
