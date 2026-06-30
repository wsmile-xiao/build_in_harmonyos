# libmaa 1.5.1 适配笔记

## 编译环境
- 构建系统: mkc (mk-configure, NetBSD 风格 bmake 构建系统) — **非标准 autotools**
- 编译日期: 2026-06-10
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 目标架构: aarch64 (OpenHarmony)
- 状态: published

## 编译步骤

libmaa 1.5.1 使用 mk-configure (mkc) 构建系统，其 Makefile 使用 `.include <mkc.lib.mk>` 和 `.include <mkc.subprj.mk>`，需要 bmake/mkc 工具。OpenHarmony 上没有 bmake/mkc，因此采用手动编译方式。

### 步骤 1: 初始化构建
```bash
SKILL_ROOT="/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent"
python3 $SKILL_ROOT/scripts/ohc-run.py init-build libmaa 1.5.1 \
  --url=https://downloads.sourceforge.net/project/dict/libmaa/libmaa-1.5.1/libmaa-1.5.1.tar.gz
```
结果: ✅ 成功。源码下载到 ~/tmp/builds/libmaa-1.5.1.work

### 步骤 2: 尝试自动构建（失败）
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py build libmaa 1.5.1
```
结果: ❌ 失败。脚本检测构建系统为 "makefile"（因为源码目录有 Makefile），跳过 configure 步骤。make 在 Step4 失败，错误为 `Makefile:8: *** missing separator. Stop.` — mkc 的 `.include <mkc.subprj.mk>` 语法不兼容 GNU make。

### 步骤 3: 手动编译（核心步骤）

#### 3.1 生成 arggram.c
```bash
cd ~/tmp/builds/libmaa-1.5.1.work/maa
awk -f arggram2c < arggram.txt > arggram.c
```

#### 3.2 编译所有 .o 文件（24 个源文件）
```bash
CFLAGS="-fPIC -O2 -DSIZEOF_LONG=8 -DSIZEOF_VOID_P=8 \
  -DHAVE_HEADER_SYS_RESOURCE_H=1 -DHAVE_HEADER_ALLOCA_H=1 \
  -DMAA_MAJOR=4 -DMAA_MINOR=1 -DMAA_TEENY=0 -I. -I.."

SRCFILES="xmalloc.c hash.c set.c stack.c list.c error.c memory.c string.c \
  debug.c flags.c maa.c prime.c bit.c timer.c arg.c pr.c sl.c \
  base64.c base26.c source.c parse-concrete.c text.c log.c arggram.c"

for f in $SRCFILES; do
    clang $CFLAGS -c $f -o ${f%.c}.o
done
```
结果: ✅ 24 个 .o 文件全部编译成功

#### 3.3 创建库文件
```bash
# 静态库
llvm-ar rcs libmaa.a *.o           # 170,334 bytes, 24 个 .o

# 共享库 (版本号来自 Makefile.common: MAA_MAJOR=4, MAA_MINOR=1)
clang -shared -fPIC -O2 $CFLAGS *.o -o libmaa.so.4.1  # 104,768 bytes

# 符号链接
rm -f libmaa.so libmaa.so.4
ln -s libmaa.so.4.1 libmaa.so
ln -s libmaa.so.4.1 libmaa.so.4
```

#### 3.4 DESTDIR staging 安装 (R20)
```bash
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/lib
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/include
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/lib/pkgconfig

cp libmaa.a $TEST_PREFIX/$DEFAULT_PREFIX/lib/
cp libmaa.so.4.1 $TEST_PREFIX/$DEFAULT_PREFIX/lib/
cd $TEST_PREFIX/$DEFAULT_PREFIX/lib/
ln -s libmaa.so.4.1 libmaa.so
ln -s libmaa.so.4.1 libmaa.so.4

cp maa.h $TEST_PREFIX/$DEFAULT_PREFIX/include/
cp libmaa.pc $TEST_PREFIX/$DEFAULT_PREFIX/lib/pkgconfig/
```

#### 3.5 本地安装（模拟用户部署）
```bash
cp libmaa.a $DEFAULT_PREFIX/lib/
cp libmaa.so.4.1 $DEFAULT_PREFIX/lib/
ln -s libmaa.so.4.1 $DEFAULT_PREFIX/lib/libmaa.so
ln -s libmaa.so.4.1 $DEFAULT_PREFIX/lib/libmaa.so.4
cp maa.h $DEFAULT_PREFIX/include/
cp libmaa.pc $DEFAULT_PREFIX/lib/pkgconfig/
```

### 步骤 4: 测试与验证

详见 reports/test-report.md，以下为关键结果：

```bash
# 自定义综合验证程序
LD_LIBRARY_PATH=$DEFAULT_PREFIX/lib ~/tmp/test_libmaa
libmaa version: 4.1.0
hash test: hello -> world
list length: 2
All tests passed!
```

### 步骤 5: 打包
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package libmaa 1.5.1
```
结果: ✅ libmaa-1.5.1-ohos-aarch64.tar.gz (683KB)

### 步骤 6: 收尾
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finish libmaa 1.5.1 published
```
结果: ⚠️ 部分完成。G1-G4 全通过，G0 失败（mkc 项目无 configure 脚本）

---

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ohc-run.py build 检测为 makefile 系统，跳过 configure 步骤，make 失败 ("missing separator") | 源码目录有 mkc 风格 Makefile，脚本识别为纯 makefile 项目；mkc 的 `.include <mkc.subprj.mk>` 语法不兼容 GNU make | 改为手动编译模式：逐文件用 clang 编译 |
| 2 | bit.c 编译失败：`use of undeclared identifier 'SIZEOF_LONG'` | mkc 构建系统通过 MKC_CHECK_SIZEOF 在 configure 步骤定义 SIZEOF_LONG 宏，手动编译时未定义 | 添加 `-DSIZEOF_LONG=8`（aarch64 上 sizeof(long)=8，经实测确认） |
| 3 | timer.c 编译失败：`field has incomplete type 'struct rusage'` + `undeclared identifier 'getrusage/RUSAGE_SELF'` | maaP.h 条件包含 `<sys/resource.h>`（需 `HAVE_HEADER_SYS_RESOURCE_H=1` 宏），mkc 未生成此宏 | 添加 `-DHAVE_HEADER_SYS_RESOURCE_H=1`。经单独编译测试确认 OpenHarmony **有** sys/resource.h |
| 4 | 验证测试崩溃：`tim_stop: Internal error / No timer: total` | 测试程序未调用 `maa_init()`（maa_init 会调用 `tim_start("total")` 启动内部计时器） | 测试程序中先调用 `maa_init(argv[0])` |
| 5 | G0 干净构建验证失败：`configure failed (exit 127)` | clean-verify 在原始 tarball 上运行 `./configure`，mkc 项目无 configure 脚本 | 已记录为 mkc 构建系统固有限制（创建 E105 知识草稿） |

---

## 对话记录

### 对话 1: 初始化与首次构建尝试

**时间**: 2026-06-10 00:54

1. 加载编译技能 (openharmony-compile-agent)
2. 执行 `ohc-run.py init-build libmaa 1.5.1 --url=...` → ✅ 成功
3. 执行 `ohc-run.py build libmaa 1.5.1` → ❌ 失败
   - 脚本检测构建系统为 "makefile"，跳过 configure
   - Step4 make 失败: `Makefile:8: *** missing separator. Stop.`
   - 输出 HANDOFF: EXIT_REASON=make_failed, KNOWLEDGE_HIT=E002
4. 读取 HANDOFF，发现实际构建系统是 mk-configure (mkc)，不是 autotools

### 对话 2: 手动编译与修复

**时间**: 2026-06-10 00:57-01:00

1. 分析源码目录结构：发现 `.include <mkc.lib.mk>` / `<mkc.subprj.mk>` 语法
2. 检查平台特性：
   - sizeof(long) = 8 ✅
   - sys/resource.h 可用 ✅
   - alloca.h 可用 ✅
3. 生成 arggram.c: `awk -f arggram2c < arggram.txt > arggram.c`
4. 首次编译：bit.c 失败 (SIZEOF_LONG 未定义)、timer.c 失败 (rusage 未声明)
5. 添加宏定义后重编译：24 个 .o 文件全部成功 ✅
6. 创建 libmaa.a (170KB) 和 libmaa.so.4.1 (105KB) ✅
7. DESTDIR staging 安装 ✅

### 对话 3: 测试验证与打包

**时间**: 2026-06-10 01:00-01:07

1. 编译运行 basics/list/stack/hash/string/set 测试
2. 发现验证测试崩溃（未调用 maa_init），修复后全通过 ✅
3. verify-build → G1-G4 全 PASS，G0 FAIL（mkc 限制）✅
4. package → libmaa-1.5.1-ohos-aarch64.tar.gz (683KB) ✅
5. 本地安装验证 → `All tests passed!` ✅
6. finish → published 状态，G0 失败为已知 mkc 限制
7. 创建 E105 知识草稿（mk-configure 构建系统适配模式）

---

## 源码修改

**无源码修改**。所有适配通过编译宏定义（CFLAGS）完成，符合 R8 "源码四不准则"。

关键宏定义列表：
- `-DSIZEOF_LONG=8` (bit.c 位计数，aarch64 平台)
- `-DSIZEOF_VOID_P=8` (指针大小)
- `-DHAVE_HEADER_SYS_RESOURCE_H=1` (timer.c 定时器功能)
- `-DHAVE_HEADER_ALLOCA_H=1` (maaP.h alloca 支持)
- `-DMAA_MAJOR=4 -DMAA_MINOR=1 -DMAA_TEENY=0` (版本号)
- `-fPIC -O2` (位置无关代码 + 优化)

---

## 依赖版本

无外部依赖。libmaa 仅依赖 libc。

---

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmaa.a | 170,334 bytes | 静态库 (24 个 .o) |
| libmaa.so.4.1 | 104,768 bytes (原始) / 165,632 bytes (打包) | 共享库 (含签名段) |
| libmaa.so | → libmaa.so.4.1 | 共享库链接 |
| libmaa.so.4 | → libmaa.so.4.1 | 共享库版本链接 |
| maa.h | 24,505 bytes (609 行) | 公共头文件 |
| libmaa.pc | 272 bytes | pkg-config 文件 |

预编译包: `libmaa-1.5.1-ohos-aarch64.tar.gz` (699,520 bytes / 683KB)
调试包: `libmaa-1.5.1-ohos-aarch64-debug.tar.gz` (155,179 bytes)

---

## 注意事项

- libmaa 使用 mk-configure (mkc) 构建系统，**不是 autotools**，需手动编译
- 必须定义 `SIZEOF_LONG=8`、`HAVE_HEADER_SYS_RESOURCE_H=1` 等宏（aarch64 平台）
- 使用库时**必须**先调用 `maa_init()`，最后调用 `maa_shutdown()`
- arggram.c 需要由 arggram.txt 通过 awk arggram2c 脚本生成
- mkc 项目 G0 干净构建验证必然失败（无 configure 脚本），需手动验证替代
- 共享库仅依赖 libc.so，无其他运行时依赖