# xmill 0.8 适配笔记

| 项 | 值 |
|---|---|
| 目标库 / 版本 | `xmill` / `0.8`（请求值，见「版本口径」） |
| 上游工程 | AT&T Labs Research **XMill**（XML 压缩器，Hartmut Liefke / Dan Suciu，1999） |
| 可达上游 | https://github.com/jungsagacity/xmill （唯一分支 `master`，无 tag；源码内含 AT&T 版权头） |
| 源码 sha256 | `9b9677de8f64a2ecbd345778175db3d8eab4b017460c83f05051e7584bb397a4` |
| 语言（R47） | `cpp`（`lang-preflight` → `task=cpp, detected=cpp`，源文件 67 个，主体占比 76%） |
| 构建系统 | 上游**无**（只有 MSVC `xmill.sln` + `xmill/xmill.vcproj`）→ 补丁新增 cmake |
| 强制第三方依赖 | `zlib/1.3.2`（W0 可消费，见下） |
| 编译环境 | HarmonyOS / aarch64 / clang 15.0.4 (target `aarch64-unknown-linux-ohos`) / libc++ / cppstd 17 |
| 状态 | **built**（conan create + conan-verify 全绿，未 upload） |

---

## 0. 版本口径（重要，留证）

**请求版本 `0.8` 没有任何上游证据。**

1. `xmill` 不是任何发行版/语言生态的包：Debian `sources.debian.org/api/src/xmill/` → 404、
   `packages.debian.org` 无结果、snapshot 无源包；Fedora / AUR / Alpine / Arch / opam /
   pkgsrc / rpmfind / ConanCenter / npm / crates.io / Hackage / PyPI / NuGet / Maven / Homebrew
   全部无 `xmill`（完整日志见 `.dep-analysis/xmill_0.8/logs/`，同批对照 `xmille` 正常命中，
   说明不是查询方法问题）。
2. 唯一同名可达上游工程为 AT&T XMill；其源码自述版本是 **`XMill 0.7 (30 Nov 99)`**
   （`xmill/src/Options.cpp:459`）。AT&T 官方发布站点
   `www.research.att.com/sw/tools/xmill/` 已下线，`archive.org` / `web.archive.org` 实测 rc=28 超时，
   故 0.8 无任何可达证据。
3. 可达上游仓库只有 `master` 一个分支（GitHub API `/branches` 只有 master，`/tags` 为空）。

**处理方式**：目录与 Conan 包名沿用请求版本 `0.8`，源码锁定镜像 `master` 快照的 sha256
（移动分支必须锁 hash 才能复现）。本文件与 README/manifest 均显式标注“上游自述 0.7”的差异，
不把 0.7 冒充成 0.8。

---

## 1. W0 依赖可消费性核验（R35：一律 `conan download`）

| 探测 | 原始输出（关键行） | rc | 判定 | 日志 |
|---|---|---|---|---|
| 对照组（不存在包） | `ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]` | 1 | 远端无此 ref | `logs/W0_00_control.log` |
| **`zlib/1.3.2` 配方** | `Downloading recipe 'zlib/1.3.2#73f9291b…'` / `Download completed in 0s` | **0** | **可消费** | `logs/W0_10_zlib_1.3.2_recipe.log` |
| **`zlib/1.3.2` 二进制** | `Package installed`（`os:OHOS arch:armv8 compiler:clang 15`） | **0** | **可消费** | `logs/W0_11_zlib_1.3.2_binary.log` |
| `bzip2/1.0.8`（可选面） | `Downloading recipe 'bzip2/1.0.8#3b49a968…'` | 0 | 可消费（默认构建面不需要） | `logs/W0_20_bzip2_1.0.8_recipe.log` |

结论：唯一强制依赖 zlib **已发布且可消费**，`R36` 依赖阻塞不成立；本包 `--build=missing`
未用于依赖（conan create/verify 日志中 zlib 均为 `Already installed! (Cache)`）。

上游依赖形态：zlib 不是以 Conan 依赖声明，而是**树内 vendored**（`xmill/zlib/*`，`zlib.h:40`
自述 `1.1.3`），通过 `#include "../zlib/zlib.h"`（`ZLib.cpp` 里是 `"..\zlib\zlib.h"`）使用。
适配改为消费 `zlib/1.3.2`（补丁 0002/0008），不再编译 vendored 副本。

---

## 2. 源码与上游测试入口核验

```
$ curl -sSL -o jungsagacity-master.tar.gz https://codeload.github.com/jungsagacity/xmill/tar.gz/refs/heads/master
http=200 size=282030   curl_rc=0
$ sha256sum jungsagacity-master.tar.gz
9b9677de8f64a2ecbd345778175db3d8eab4b017460c83f05051e7584bb397a4
$ tar tzf ... | wc -l
88

# 等价 URL 交叉验证（conan get() 需要 .tar.gz 后缀）
$ curl -sSL -o alt-master.tar.gz https://github.com/jungsagacity/xmill/archive/refs/heads/master.tar.gz
http=200 size=282030
$ sha256sum alt-master.tar.gz
9b9677de…4bb397a4      # 与 codeload 直链逐字节一致
```

上游**没有自动化测试套件**（真实核验，非推断）：

```
$ find . \( -iname '*test*' -o -iname '*spec*' \)        → 空
$ grep -rn "ctest|BUILD_TESTING|add_test|pytest|TEST("  → 空
$ find . -iname 'Makefile*' -o -iname 'CMakeLists.txt' -o -iname 'configure*' -o -iname 'meson.build'
  xmill.sln
  xmill/xmill.vcproj          # 只有 MSVC 工程
$ grep -n "int main" xmill/src/Main.cpp
  265:int main(int argc,char **argv)
```

唯一的“上游样例”是随包数据：`xmill/sprot1_2.xml`（12,891,059 B，SWISS-PROT XML）与
对应的压缩件 `xmill/sprot1_2.xmi`（34,392 B）。真实测试入口就是 CLI 本身。

---

## 3. 真实构建：首个错误 → 根因 → 修复 → 重新验证

### 3.1 预检（语法普查，非“构建首错”）

上游是 1999 年的 MSVC 代码，直接以 `-std=c++17` 编译前先做一次语法普查，命中 4 类：

| # | 位置 | 错误 | 根因 | 修复 |
|---|---|---|---|---|
| 1 | `XMLOutput.hpp:195` | `error: ISO C++17 does not allow 'register' storage class specifier` | C++17 删除了 `register` | 删除 `register`（补丁 0007） |
| 2 | `Output.hpp` 非 WIN32 分支 | `error: unknown type name 'FILE'` / `use of undeclared identifier 'stdout'/'fopen'` | 上游把 `<stdio.h>` 只放在 `#else`（WIN32）分支，POSIX 分支只包 `<unistd.h>` | POSIX 分支补 `<stdio.h>`（补丁 0006） |
| 3 | `ZLib.cpp:39` | `fatal error: '..\zlib\zlib.h' file not found` | 反斜杠在 POSIX 上不是路径分隔符 | 改 `<zlib.h>` + 消费 Conan zlib（补丁 0008） |
| 4 | `Main.cpp:394/610` | `cannot initialize a parameter of type 'char *' with an rvalue of type 'const char *'` | `(no_output==0) ? destfile : ""` 三元表达式合成类型是 `const char*` | 显式 `(char *)""`（补丁 0009） |

（普查命令与原始输出：`logs/10-syntax-cxx17.log`，26 处 error 归为上表 4 类。）

### 3.2 首个真实构建错误（链接期）

```
$ cmake --build . -j2
[ 98%] Linking CXX executable xmill
[100%] Linking CXX executable xdemill
ld.lld: error: undefined symbol: errno
>>> referenced by Main.cpp
>>>               CMakeFiles/xmill.dir/xmill/src/Main.cpp.obj:(XMLParse::ParseDOCTYPE())
>>> referenced by Main.cpp
>>>               CMakeFiles/xmill.dir/xmill/src/Main.cpp.obj:(CFile::ReadBlock(char*, unsigned int))
>>> referenced 11 more times
clang-15: error: linker command failed with exit code 1
make[2]: *** [CMakeFiles/xmill.dir/build.make:470: xmill] Error 1
rc=2                       # 日志 logs/14-cmake-build-1.log（首次）→ 13-cmake-build-1.log
```

**根因**：`xmill/src/File.hpp:43` 手写 `extern int errno;`。MSVC CRT 有全局 `errno` 符号，
但 POSIX/musl 的 `errno` 是宏（`(*__errno_location())`），没有同名全局符号 → 链接失败。

**修复**（补丁 0003）：删除手写声明，改 `#include <errno.h>`（`errno` 的 2 处使用
`File.hpp:116,118` 自动走 libc 宏）。

**重新验证**：`cmake --build . -j2` → `rc=0`，产出 `xmill`(264,704 B) / `xdemill`(260,608 B)，
`ELF 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)`（`logs/14-cmake-build-2.log`）。

### 3.3 运行期错误 #1：`xdemill` SIGSEGV（rc=139）

压缩正确（下一节），但解压必崩：

```
$ xdemill tiny.xmi ; echo $?
139                        # 128+11 = SIGSEGV，输出文件 0 字节
```

`gdb` 不可用（`ptrace: Permission denied`，SELinux），改用**插桩副本**二分定位
（不动主源码，`evidence/tmp/dbgsrc*`）。逐步收敛：

```
T bh enter → T bh uncompressor built → T fh enter → T fh magic ok → T fh output init ok
→ T fh pathexpr loaded → T bh fileheader done → T bh cutoff=48 → T bh memset ok
→ T bh cont loaded → T bh labeldict loaded → T bh contmem allocated
→ T man small conts: blocknum=4 blockarray=0x5983eb8498
→ T  it 0 size=12
→ T   alloc size=12 buf=0x5983e553c0 curptr=0x83e553c0 bufsize=48      ← 指针被截断
→ T   smallcont size=12 dataptr=0x83e553c0                             ← 已失效
```

`buf=0x5983e553c0` 但 `curptr=0x83e553c0`（只剩低 32 位）。首个 `fprintf` 前的最后一步是
`compressman.UncompressSmallGlobalData()` → `EnumCompress` 的解压初始化调用 `WordAlignMemBlock()`：

```c
inline void WordAlignMemBlock()      // MemMan.hpp:131（修复前）
{
   memoryalloc_curptr =
      (unsigned char *)(((unsigned long)memoryalloc_curptr+3)&0xFFFFFFFCL);
}
```

**根因**：`0xFFFFFFFC` 是 32 位字面量掩码。1999 年的 Win32 上指针就是 32 位，写成字面量没问题；
在 LP64（OHOS aarch64）上它把 64 位指针**截断**，之后所有容器数据指针都指向未映射内存 →
`memcpy` 段错误。

**修复**（补丁 0005）：改为按指针宽度取掩码 `&~(unsigned long)3`。

**重新验证**（`logs/25-…`）：

```
$ xdemill rt.xmi && cmp rt.xml sprot1_2.xml  → IDENTICAL rc=0
$ xdemill up.xmi && cmp up.xml sprot1_2.xml  → IDENTICAL rc=0
b98e10f243b863bf…  rt.xml / up.xml / sprot1_2.xml   # 三者 sha256 相同
```

### 3.4 运行期错误 #2：`xmill -v` SIGSEGV（rc=139）

```
$ xmill -v tiny.xml ; echo $?
139                        # 只打印到 "   Structure:      11 ==> Small..." 就崩
```

继续插桩定位到第二个容器块（普通路径字典块），崩点在
`CompressContainerBlock::CompressLargeContainers()` 里**仅 verbose 才执行**的
`pathdictnode->PrintInfo()`：

```
T man call block=0x5afdca7330
T PI this=0x5afdca7310 parent=0x5afdca71c0 ccblock=0x5afdca7330 rexpr=0x5afdc6bf10 labelid=32772
T PI regexpr done
T PI label 32772        ← 崩在这
```

**根因**（`LabelDict.hpp:499`）：

```c
void PrintLabel(TLabelID labelid)
{
   ...
   len=LookupCompressLabel(labelid,&ptr);       // 压缩字典（有效）
   len=LookupLabel(labelid,&ptr,&isattrib);     // 解压字典 —— labeldictlist
   ...
}

unsigned long LookupLabel(TLabelID labelid,char **ptr,unsigned char *isattrib)
{
   UncompressLabelDict *labeldict=labeldictlist;
   while(labelid>=labeldict->labelnum)          // labeldictlist 在压缩器里是 NULL
   ...
}
```

`labeldictlist` 只在 `LabelDict::Load()`（解压路径）里构建，压缩器里恒为 NULL →
`NULL->labelnum` 空指针解引用。凡是压缩器侧的标签打印（`xmill -v`、`PathTree`/`VRegExpr`/`FSMEdge`
的打印路径）都会崩。

**修复**（补丁 0004）：有解压字典时用它，否则用压缩字典（同名同长），并顺带删掉那行被覆盖的
冗余 `LookupCompressLabel` 调用。

**重新验证**：`xmill -v tiny.xml` → `rc=0`，输出结构/空白/特殊容器统计与
`//# <- @id`、`//# <- title` 等路径表达式（`logs/35-cmake-build-4.log` 后的实测输出）。

> 已知上游瑕疵（未修，非崩溃）：`Options.cpp:PrintUsage()` 的用法文本宣传 `-h`，但
> `InterpretOptionString()` 没有 `'h'` 分支 → `xmill -h` 报 `Invalid option '-h'` 并以 255 退出。
> 这是“文档有、实现无”的缺失功能，不属于移植适配范围，故不在补丁里自造实现。

### 3.5 集成错误：`find_package(ZLIB)` 命中宿主的动态 zlib

第一次 `conan create` 的 test_package 中，**鸿蒙特有用例 T3 直接把它拦了下来**：

```
[FAIL] [OHOS] T3 no runtime libz.so dependency (static zlib)
$ readelf -d <pkg>/bin/xmill | grep NEEDED
  (NEEDED)  Shared library: [libz.so.1]      ← 不该有
$ grep ZLIB_DIR <build>/CMakeCache.txt
ZLIB_DIR:PATH=/storage/Users/currentUser/.harmonybrew/lib/cmake/ZLIB
```

**根因**：配方 `generate()` 只生成了 `CMakeToolchain`，**没有 `CMakeDeps`** → 构建目录里没有
Conan 生成的 `ZLIBConfig.cmake`，`find_package(ZLIB REQUIRED)` 便命中了宿主 harmonybrew 的 zlib
（动态库）。编译器不报错，只有运行期依赖检查能发现。

**修复**：`generate()` 里补 `CMakeDeps(self).generate()`。

**重新验证**：`conan create` rc=0；`readelf -d` 只剩 `libc++_shared.so` / `libc.so`；
test_package 7/7 PASS（`logs/44-conan-create.log`）。

### 3.6 补丁管线问题（手动模式，R13）

`refresh-patch --auto` 只成功生成 8 个补丁，两个必须手工处理：

1. **`Main.cpp`（0009）**：工具用 `read_text(encoding="utf-8", errors="replace")` 读源文件，
   上游 `Main.cpp` 含 GBK 字节（`//0:压缩`、`//HandleSingleFile("f:\\sprot1_1.xmi",1)` 两行注释），
   被替换成 U+FFFD 后写回补丁 → `patch --dry-run` 失败。
   → 用字节级 `diff -u` 生成，`patch --dry-run -p1` 通过（rc=0）。
2. **`CMakeLists.txt`（0001）**：新增文件一开始没被 `edit-tracker` 记录（`track-edit add` 登记后
   才纳入）；且 conan 的 `apply_conandata_patches` 要求新增文件补丁的头部是 `--- /dev/null`，
   工具生成的 `--- a/CMakeLists.txt` 会被判 `source/target file does not exist`。
   → 用 `diff -u --label /dev/null --label b/CMakeLists.txt /dev/null <work>/CMakeLists.txt` 重新生成。

另外：`filemgr-editFile` 写回时会剥离行尾空白，导致补丁里混入 10 处与适配无关的空白变更；
已逐行还原（`File.hpp` 1 处、`LabelDict.hpp` 5 处、`XMLOutput.hpp` 1 处、`ZLib.cpp` 3 处），
使 9 个补丁只包含真实改动。

**全量验证**：把 9 个补丁按序应用到 `xmill-0.8.orig` 的干净副本，与 `xmill-0.8.work`
**逐字节一致**（`diff -r` rc=0），`CMakeLists.txt` 亦一致。

### 3.7 conan create 过程中的另外两个坑（已修）

1. `get()` 依据 URL 后缀选解包器：codeload 的 `…/tar.gz/refs/heads/master` 没有后缀，
   被当成 zip → `BadZipFile: File is not a zip file`。
   → 改用 `https://github.com/jungsagacity/xmill/archive/refs/heads/master.tar.gz`
   （302 到 codeload，实测 sha256 完全一致）。
2. 首次 `conan create` 报
   `CMakePresets.json was not found in …/generators folder` → `generate()` 缺失（已补）。

---

## 4. 上游样例与 CLI 端到端测试

完整测试脚本：`<workspace>/xmill-0.8-evidence/run-upstream-tests.sh`
原始日志：`<workspace>/xmill-0.8-evidence/logs/36-upstream-tests-final.log`

| # | 用例 | 命令 | 结果 |
|---|------|------|------|
| T1 | 压缩上游样例 | `xmill sprot1_2.xml` | PASS rc=0 |
| T1b | **与上游自带压缩件逐字节一致** | `sha256(sprot1_2.xmi)` | PASS `f6e1a0ffc0f2b8f0…` |
| T2 | 解压自产 .xmi | `xdemill ours.xmi` | PASS rc=0 |
| T2b | 还原原始 XML | `sha256(ours.xml)` | PASS `b98e10f243b863bf…` |
| T3 | 解压上游自带 .xmi | `xdemill up.xmi` | PASS rc=0 |
| T3b | 还原原始 XML | `sha256(up.xml)` | PASS `b98e10f243b863bf…` |
| T4/T4b/T4c | `-w` 保空白字节级往返 | `xmill -w` + `xdemill` + `cmp` | PASS |
| T5 | 压缩级别 `-1…-9` | 9 级各自往返 + `cmp` | PASS 9/9 |
| T6 | `-v -m 2` | `xmill -v -m 2` | PASS rc=0 |
| T7 | `-c` 写标准输出 | `xmill -c > out` | PASS 154 B |
| T8 | `-i` 选项文件 | `xmill -i opt.txt` | PASS rc=0 |
| T9 | `-p` 路径表达式 | `xmill -p /catalog` | PASS rc=0 |
| T10/T10b/T10c | `-d` 删源 / `-f` 覆盖 | `xmill -d` / `-f` | PASS |
| T11/T11b | 无参打印 usage(rc=1) / 非法选项拒绝(rc=255) | | PASS |
| T12 | **[OHOS]** 二进制形态 | `e_machine=0x00B7` + `interp=/lib/ld-musl-aarch64.so.1` | PASS |

**汇总：20/20 PASS，0 FAIL，0 SKIP。** 上游唯一样例 `sprot1_2.xml` 与其压缩件 `sprot1_2.xmi`
均已实际使用，无漏测。

> 语义说明：XMill 默认会**重排无意义空白**（`Options.cpp` 里默认 `usedosnewline=0`、
  解压时 `output.Init(XMLINTENT_SPACES,0,1)` 做缩进），因此默认模式下字节级不等价是**上游设计行为**；
  需要字节级等价时用 `-w`（保空白）—— T4 即验证该路径。sprot1_2.xml 本身无冗余空白，故默认模式也字节级一致。

---

## 5. conan create / conan-verify / test_package

```
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<同>
rc=0                                    # logs/44-conan-create.log
test_package: pass=7 fail=0 skip=0      # 含 2 项鸿蒙特有断言（T2 ELF 形态 / T3 无 libz.so）

$ ohc-run.py conan-verify xmill 0.8
G0 ✅(命中 E092) / G1 ✅ / G2 ✅ / G3 ✅ / G4 ✅ / L2·L4·L5 跳过（可执行包无 cache 路径）
✅ 配方验证通过: xmill 0.8 → 可标记 status: published
```

安全基线（`L4` 在本环境因 G4 取不到包 ID 而跳过，故手工补证）：

```
$ readelf -h  bin/xmill → Type: DYN (Position-Independent Executable file)   # PIE
$ readelf -lW bin/xmill → GNU_RELRO … R    /  GNU_STACK … RW                 # 全 RELRO + NX
$ readelf -d  bin/xmill → (FLAGS) BIND_NOW / (FLAGS_1) NOW PIE               # now binding
```

`G0` 命中知识条目 `E092`（CMake 不识别 HarmonyOS 目标平台）并给出“改用 `CMAKE_SYSTEM_NAME=Linux`”
的建议。本包**未采纳**：实际构建只需 CMake 生成 Makefile，不依赖平台模块；实测 configure 仅打印
`System is unknown to cmake, create: Platform/HarmonyOS`（警告），G2 全绿，产物也已验证为
`os=OHOS / aarch64 / musl`。强行改写 `CMAKE_SYSTEM_NAME` 反而会破坏 Conan 工具链的 settings 一致性。

---

## 6. 依赖版本

| 依赖 | 版本 | 类型 | 证据 |
|------|------|------|------|
| zlib | `1.3.2`（上游 vendored 为 1.1.3，不 pin） | 强制第三方 | `logs/W0_10/11_*`；`readelf -d` 确认静态链入，无 `libz.so.1` 运行期依赖 |
| bzip2 | `1.0.8` | 可选（`-DUSE_BZIP` 才启用） | `logs/W0_20_*`；本包未启用 |
| libc / POSIX | 工具链 sysroot | 系统 | clang 15 target `aarch64-unknown-linux-ohos` |

---

## 7. 交付物

| 文件 | 大小 | sha256（前 16） |
|------|------|------------------|
| `bin/xmill` | 264,704 B | `8795bb2bf6b0be0…` |
| `bin/xdemill` | 260,608 B | `072d0395d111d9c…` |

---

## 8. 注意事项

1. **别用默认模式做字节级比对**：默认会重排空白，用 `-w`。
2. **`-h` 上游未实现**（用法文本里有、解析器里没有），会以 255 退出；这是上游瑕疵，未修改。
3. 上游只有 MSVC 工程，本包的 `CMakeLists.txt` 是**适配新增物**（补丁 0001），不是上游文件。
4. `xmill` 的设计是“结构感知压缩”，对**很小的 XML** 会出现压缩后体积**大于**原文件的情况
   （header/结构表固定开销）；这是算法特性，不是缺陷。
5. 许可证为 AT&T 专有（仅非商业研究用途），分发前请确认合规。
---

**编译结束**: 2026-10-01 17:13
**最终状态**: built
