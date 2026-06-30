# libmxml 4.0.4 编译适配笔记

## 编译环境

| 项目 | 内容 |
|------|------|
| 软件 | libmxml (Mini-XML) |
| 版本 | 4.0.4 |
| 构建系统 | autotools (configure/make) |
| 编译器 | clang 15.0.4 |
| 平台 | HarmonyOS aarch64 (HongMeng Kernel 1.12.0) |
| 编译日期 | 2026-06-18 |
| 状态 | published |

---

## 编译步骤

### Step 1: init-build 初始化

```
python3 $SKILL_ROOT/scripts/ohc-run.py init-build libmxml 4.0.4 \
  --url=https://github.com/michaelrsweet/mxml/releases/download/v4.0.4/mxml-4.0.4.tar.gz
```

初始化结果：下载/解压成功，69 个源文件，无依赖缺失。

### Step 2: configure（修复后）

```bash
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX
```

**关键 configure 输出**:
```
checking build system type... aarch64-unknown-linux-gnu
checking host system type... aarch64-unknown-linux-gnu
checking for gcc... clang
checking whether the C compiler works... yes
checking for pthread.h... yes
checking for pthread_create using -lpthread... yes
configure: Installing static libraries...
checking for OS-specific compiler options... -D__USE_MISC -D_GNU_SOURCE -Wl,-z,relro,-z,now
configure: creating ./config.status
config.status: creating Makefile
config.status: creating mxml4.pc
config.status: creating config.h
```

### Step 3: make 编译

```bash
make -j2
```

**编译输出**:
```
Compiling mxml-attr.c
Compiling mxml-file.c
Compiling mxml-get.c
Compiling mxml-index.c
Compiling mxml-node.c
Compiling mxml-options.c
Compiling mxml-search.c
Compiling mxml-set.c
Compiling mxml-private.c
Compiling testmxml.c
Creating libmxml4.so.2...
Creating libmxml4.a...
Linking testmxml...
```

### Step 4: make install DESTDIR（R20 暂存安装）

```bash
make install DESTDIR=$TEST_PREFIX
```

**安装输出**:
```
Installing libmxml4.so to $TEST_PREFIX/$PREFIX/lib...
Installing libmxml4.a to $TEST_PREFIX/$PREFIX/lib...
Installing documentation in $TEST_PREFIX/$PREFIX/share/doc/mxml4...
Installing header files in $TEST_PREFIX/$PREFIX/include/libmxml4...
Installing pkgconfig files in $TEST_PREFIX/$PREFIX/lib/pkgconfig...
Installing man pages in $TEST_PREFIX/$PREFIX/share/man...
```

### Step 5: make test

```
Testing library...
Stdio file test passed!
String test passed!
File descriptor test passed!
```

### Step 6: make install（本地安装）

```bash
make install
```
将库安装到 `$DEFAULT_PREFIX`（~/usr/local），模拟用户部署状态。

---

## 遇到的问题与解决方案

### 问题 1: config.guess 无法识别 HarmonyOS

**错误现象**:
```
checking build system type... ./config.guess[1733]: can't create
  /storage/Users/currentUser/tmp/cgAT7pxv/dummy.c: Permission denied
./config.guess: unable to guess system type
configure: error: cannot guess build type; you must specify one
```

**根因分析**:
1. `uname -s` 返回 `HarmonyOS`，而 config.guess（版本 2023-08-22）的 case 语句中没有 `HarmonyOS` 的匹配项
2. config.guess 在设置 CC_FOR_BUILD 时使用 `umask 077 && mktemp -d` 创建临时目录，在 HMDFS 上生成的目录权限为 `drwx--S---`，导致即使目录所有者也无法在其中创建文件（Permission denied）

**解决方案（R23 平台检测优先）**:

修改 config.guess 两处：
1. 将所有 `umask 077` 替换为 `umask 000`（修复 HMDFS 写权限问题）
2. 在 `UNAME_SYSTEM` 赋值后添加 `HarmonyOS→Linux` 映射

```bash
# config.guess 修复
sed -i 's/umask 077/umask 000/g' config.guess
sed -i '/UNAME_SYSTEM=`(uname -s)/a [ "$UNAME_SYSTEM" = "HarmonyOS" ] \&\& UNAME_SYSTEM=Linux' config.guess
```

### 问题 2: config.status 也受 umask 077 影响

**错误现象**:
```
./config.status[714]: can't create ./confYxE2uo/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**根因**: configure 脚本生成的 config.status 也包含 `umask 077`，同样受 HMDFS 权限限制。

**解决方案**: 将 configure 中的 `umask 077` 也改为 `umask 000`：

```bash
sed -i 's/umask 077/umask 000/g' configure
```

### 问题 3: 无 make check 目标

mxml 使用 `make test` 而非标准的 `make check`。`make test` 包含 3 项 I/O 测试，全部通过。

---

## 源码修改

| 文件 | 修改内容 | 补丁文件 |
|------|----------|----------|
| config.guess | 1. `umask 077` → `umask 000`（3处）；2. 添加 `[ "$UNAME_SYSTEM" = "HarmonyOS" ] && UNAME_SYSTEM=Linux`；3. case 语句添加 `\|HarmonyOS` | 0001-config.guess.patch |
| configure | `umask 077` → `umask 000`（2处） | 0002-configure.patch |

所有修改均为平台适配，不影响代码逻辑。

---

## 依赖版本

无外部依赖。libmxml 是独立的 Mini-XML 库，仅依赖标准 C 库和 pthread。

---

## 验证结果

| 验证项 | 命令 | 结果 |
|--------|------|------|
| 单元测试 | `make test` | 3/3 通过 |
| XML 解析 | `./testmxml test.xml` | 正确解析复杂 XML |
| 链接测试 | `clang -o test test.c -lmxml4 && ./test` | PASS |
| pkg-config | `pkg-config --modversion mxml4` | 4.0.4 |
| ELF 类型 | `file libmxml4.so.2` | aarch64 ELF |
| 符号表 | `llvm-nm libmxml4.a \| grep -c "T "` | 101 个导出符号 |

---

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `libmxml-4.0.4-ohos-aarch64.tar.gz` | 1.9MB | 预编译包（含 .so/.a/头文件/pkgconfig/man） |
| `libmxml-4.0.4-ohos-aarch64-debug.tar.gz` | 212KB | 调试符号包 |
| `0001-config.guess.patch` | 2.2KB | config.guess HarmonyOS 适配补丁 |
| `0002-configure.patch` | 887B | configure umask 修复补丁 |

---

## 注意事项

1. **libmxml 4.x API 变化**: mxmlSaveString 的签名与旧版不同，需要传入 `mxml_options_t *` 参数
2. **安装路径**: 库文件在 `$PREFIX/lib/libmxml4.*`，头文件在 `$PREFIX/include/libmxml4/mxml.h`
3. **pkgconfig 名称**: `mxml4`（不是 `mxml`）
4. **无命令行工具**: libmxml 是纯库，不安装可执行文件
5. **umask 问题通用性**: 此 umask 077 问题是平台级问题（L1），所有使用 autotools 的软件都可能遇到

---

**编译结束**: 2026-06-18 00:04
**最终状态**: published
