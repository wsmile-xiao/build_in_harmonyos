# unlzx 1.1 — HarmonyOS PC (aarch64) 适配笔记

- 上游：unlzx — decompresses LZX archives on multiple platforms
- 作者：Erik Meusel（v1.1, 03.04.01）；Aminet 上传者 David Tritscher
- 分发：https://aminet.net/misc/unix/unlzx.c.gz
  （说明文件 https://aminet.net/misc/unix/unlzx.c.readme）
- 版本：1.1（源码内 `static const unsigned char VERSION[]="$VER: unlzx 1.1 (03.4.01)";`
  ，gz 内文件时间戳 2001-04-03）
- 许可证：**上游未声明**（源码与 readme 通篇无版权/许可/再分发条款）。
  如实声明为 `license = "unknown"`，未臆测；详见 §1。
- 构建系统：**无**。分发包只有 `unlzx.c.gz` + `unlzx.c.readme` 两个文件，
  唯一的构建指示是源码顶部注释 `/* Compile with: gcc unlzx.c -ounlzx -O6 */`
- 依赖：**无**
- 包形态：`bin/unlzx`（应用包 → 软件级 commands.json，R38）
- 状态：**READY_FOR_HARMONY** —— WSL 侧已跑通完整 `conan create`（见 §6），
  HarmonyOS 真机 conan create 尚未执行

## 1. 许可证情况（需要评审注意）

上游**没有任何许可声明**：

```
$ grep -in "copyright\|licen\|GPL\|public domain\|freely\|permission" unlzx.c
（无输出；"free" 的命中全部是 free() 调用）
$ cat unlzx.c.readme
（只有 Short/Author/Uploader/Type/Version/Replaces/Requires/Architecture 元数据
  和一段功能说明，无任何许可条款）
```

这是 Amiga 时代 freeware 的常见状况。配方里以 `license = "unknown"` 如实申报
（仓库内 `archives/o/ostra/...` 先例相同），**没有**替上游选择 GPL/BSD 等
任何具体许可证。conandata 只引用 Aminet 官方 URL，仓库不分发源码本体。
是否可接受请评审判断。

## 2. 平台适配点（2 个补丁）

上游代码 1998 年写成、2001 年加了 stdin 支持，本身几乎完全是可移植 ANSI C，
只有两处需要处理：

### 2.1 缺失的系统头文件（`0001-unlzx-missing-includes.patch`）

`unlzx.c` 只 include 了 `<stdlib.h>` 和 `<stdio.h>`，但使用了：

| 函数/变量 | 需要 | 原状态 |
|---|---|---|
| `mkdir()`（`open_output()`，第 651 行） | `<sys/stat.h>` | 隐式声明 |
| `getopt()`、`optind`（`main()`，第 1228 行） | `<unistd.h>` | 隐式声明 |

隐式声明在旧编译器上只是警告，但 **GCC 14+ 默认把
`-Wimplicit-function-declaration` 升级为 error**，C23 更是正式删除该语法。
不补这两个头文件，在现代工具链上根本无法编译：

```
$ gcc -O2 -std=gnu17 -o unlzx unlzx.c
triangle.c 同类现象：
unlzx.c:651:5: error: implicit declaration of function 'mkdir' [-Wimplicit-function-declaration]
```

补上后连 `-Werror=implicit-function-declaration` 都能过（已实测）。

### 2.2 没有构建文件（`0002-add-GNUmakefile.patch`）

分发包里没有 makefile / configure / CMake，只有一句注释形式的编译指示。
补丁新增 `GNUmakefile`，把那一行翻译成 GNU make 规则，编译器与标志取自
Conan toolchain 环境（`$(CC)` / `$(CPPFLAGS)` / `$(CFLAGS)` / `$(LDFLAGS)`），
不写死 `gcc`（R33）。

> 补丁写法：新增文件用 `diff -u /dev/null b/GNUmakefile` 的 `/dev/null`
> 约定；用 `diff -N` 得到的 `--- a/GNUmakefile` 头会让 `patch -p1` 停下来
> 询问 `File to patch:`，在非交互构建里就是失败。

## 3. 上游测试清点（R51 三步法第 1 步）

| 项 | 值 | 依据 |
|---|---|---|
| `upstream_test_targets` | **0** | 分发包只有 2 个文件，无任何构建/测试目标 |
| `upstream_test_files` | **0** | 无测试源文件、无测试数据 |
| `upstream_case_total` | **0** | 上游不提供用例。**确认的 0**，不是 UNKNOWN |

因此本 PR 不申报上游通过率，改为提供**真实归档往返**验证（见 §4）。

## 4. WSL 侧已完成的可验证证据（无 Harmony PC）

### 4.1 补丁 apply + 构建
```
$ patch -p1 --batch -i patches/0001-unlzx-missing-includes.patch   # OK
$ patch -p1 --batch -i patches/0002-add-GNUmakefile.patch          # OK
$ make CC=gcc CFLAGS="-O2 -std=gnu17 -Werror=implicit-function-declaration"
  31216  unlzx       # 仅剩上游固有的 -Wformat 警告（见 §5）
```

### 4.2 构造 LZX 归档并往返（关键验证）
`test_package/conanfile.py` 里的生成器按 LZX 规范现场构造归档。踩坑记录：

- **多字节字段是小端**。源码末尾结构注释原文写着
  `FUCKED UP LITTLE ENDIAN SHIT`。第一版生成器按大端写，
  `unlzx` 立即报 `CRC: Archive_Header` 并退出 1（已实测复现）；
  改成小端后 header CRC 通过。
- **CRC 算法 = 标准 CRC-32**（表首项 `0x00000000, 0x77073096, 0xEE0E612C`），
  与 Python `zlib.crc32` 的增量语义逐位一致。用 `unlzx` 自身的 `crc_calc()`
  写了个对照程序，两边对同一输入都得出 `0xE190CC6E`，确认无误。
- 头 CRC 覆盖范围：`crc_calc(header@31B，CRC 字段先置 0)` →
  再 `crc_calc(filename)` → 再 `crc_calc(comment)`，链式累积。

实测：
```
$ unlzx -v good.lzx
Unpacked   Packed Time     Date        Attrib   Name
      36       36 00:00:00  0-jan-1970 -------- "hello.txt"
      36       36 1 file                                    rc=0

$ unlzx -x good.lzx
Storing "hello.txt"... crc good                             rc=0
$ cmp hello.txt <payload>       → 一致

$ unlzx -v bad.lzx              # 故意破坏 header CRC
CRC: Archive_Header                                        rc≠0
```

## 5. 观察到的上游缺陷（不修，仅记录）

`view_archive()` 用 `%ld` 打印 `unsigned int`（共 14 处，如
`printf("%8ld ", unpack_size)`）。这在 LP64 上是格式串与实参类型不匹配，
属未定义行为。只影响 `-v` 的表格数字显示，**不影响解包路径**（`-x` 完全
不经过这些代码），因此本配方不修改它，test_package 也刻意不依赖那些数字
（只断言成员名出现）。真机结果若与预期不符，这里是第一嫌疑点。

## 6. 补充：WSL 侧完整 `conan create` 实测（本机原生 Linux profile）

在独立 `CONAN_HOME` 上真跑完整 `conan create`，暴露并修复了一个纯静态检查
抓不到的问题：

| 现象 | 根因 | 修法 |
|---|---|---|
| `make: *** No targets specified and no makefile found` | `Autotools.make()` 把 make 跑在 **build 目录**（`basic_layout` 下 ≠ 源码目录），而 GNUmakefile 在源码目录 | 改为 `self.run("make -j1", cwd=self.source_folder)`。同一探针配方证实：`AutotoolsToolchain` 生成的 `CFLAGS/CPPFLAGS/LDFLAGS` 对 `self.run` 生效，`CC` 则由 profile 的 `tools.build:compiler_executables` 提供（OHOS profile 已设置，指向 worker 的 clang） |

最终本机 `conan create` 结果：

```
unlzx/1.1: Sources correctly downloaded from https://aminet.net/misc/unix/unlzx.c.gz
unlzx/1.1: Uncompressing unlzx.c.gz to .        ← Conan 直接支持裸 .gz 源
unlzx/1.1: RUN: make -j1
unlzx/1.1: Package created
test package: RUN: unlzx -v good.lzx > view.log 2>&1
test package: RUN: unlzx -x good.lzx > extract.log 2>&1
test package: RUN: unlzx -v bad.lzx > corrupt.log 2>&1 || echo REFUSED >> corrupt.log
→ 无异常，test_package 四项断言全过
```

> 另注：`unlzx` 是 `application` 类型，Conan 会把它的 `bin/` 注入构建环境，
> 所以 test() 里可以直接用裸命令名 `unlzx`（库包则不行，见 triangle 的
> test_package 为何改用绝对路径）。

## 7. 待真机验证内容（READY_FOR_HARMONY 清单）

1. `conan create`（clang 15 / aarch64-ohos）：补 `<sys/stat.h>`/`<unistd.h>`
   后能否编译（clang 15 默认 gnu17，上游代码是 C89 风格，预期可以）
2. test_package 的 LZX 往返四项断言（构造归档用的是 Python，与目标平台无关，
   因此这一项理论上与 x86_64 结果一致）
3. `-v` 输出中 `%ld` 格式串在 aarch64 上是否打印出正确数字（见 §5；本配方
   的断言不依赖它）
4. 软件级 commands.json 是否被 CI L0k 接受
