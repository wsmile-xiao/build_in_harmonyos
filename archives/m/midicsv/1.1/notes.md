# midicsv 1.1 适配笔记

## 编译环境
- 构建系统: makefile（简单Makefile，非autotools）
- 编译日期: 2026-06-11
- 编译器: clang/clang++
- 状态: published

## 编译步骤

midicsv 使用简单 Makefile（非 autotools），无 configure 脚本。直接修改 Makefile 后编译：

```bash
# 1. 加载构建上下文
source .build-context-midicsv-1.1

# 2. 进入源码目录
cd $BUILD_SRC_DIR

# 3. 修改 Makefile 适配 OpenHarmony（详见补丁 0001-Makefile-ohos-adapt.patch）
#    - CC = gcc → clang
#    - INSTALL = ginstall（OpenHarmony 无 GNU install）
#    - CFLAGS += -fPIC -O2
#    - DESTDIR ?= （添加 DESTDIR 支持）
#    - INSTALL_DEST → $DEFAULT_PREFIX
#    - TMPDIR ?=（/tmp 只读，R10 铁律）
#    - /tmp → $(TMPDIR)（R10）
#    - install → $(INSTALL)，添加 $(DESTDIR) 前缀

# 4. 编译
make clean
make -j1

# 5. DESTDIR 安装
make install DESTDIR=$TEST_PREFIX

# 6. 测试
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL下载失败 | fourmilab.ch SSL证书验证失败，HarmonyOS缺CA证书 | 手动 curl 下载 tarball，init-build 检测已存在则跳过 |
| 2 | CC=gcc不可用 | HarmonyOS使用clang而非gcc | Makefile中CC改为clang |
| 3 | `install`命令不存在 | HarmonyOS无GNU install命令 | 使用ginstall（GNU coreutils安装）替代，Makefile添加INSTALL=ginstall |
| 4 | Makefile无DESTDIR支持 | 原始Makefile直接安装到INSTALL_DEST | 添加DESTDIR ?=变量，install目标路径加$(DESTDIR)前缀 |
| 5 | /tmp只读(R10) | HarmonyOS /tmp为只读文件系统 | Makefile添加TMPDIR ?=，所有/tmp改为$(TMPDIR) |
| 6 | midicsv不支持--version | 老式CLI程序，不支持GNU风格长选项 | G2门禁警告，实际功能正常（make check通过） |
| 7 | manifest缺少build_system字段 | G4检查顶级build_system字段 | 添加顶级build_system: makefile |

## 源码修改

补丁文件：`0001-Makefile-ohos-adapt.patch`

修改文件：Makefile

修改内容摘要：
1. `CC = gcc` → `CC = clang`
2. 新增 `INSTALL = ginstall`
3. `CFLAGS = -g -Wall` → `CFLAGS = -g -Wall -fPIC -O2`
4. 新增 `DESTDIR ?=`
5. `INSTALL_DEST = /usr/local` → `INSTALL_DEST = $DEFAULT_PREFIX`
6. 新增 `TMPDIR ?= $TMPDIR`
7. `/tmp` → `$(TMPDIR)`（check/pipetest/torture目标）
8. `install` → `$(INSTALL)`（install目标）
9. `$(INSTALL_DEST)` → `$(DESTDIR)$(INSTALL_DEST)`（install目标）

## 依赖版本

midicsv无外部依赖，仅依赖libc。

- libc: musl（ld-musl-aarch64.so.1）

## 验证结果

### make check 测试

```
$ make check
All tests passed.
```

### 功能验证（MIDI往返转换测试）

```
$ ./midicsv test.mid $TMPDIR/verify-test.csv
midicsv转换：成功

$ ./csvmidi $TMPDIR/verify-test.csv $TMPDIR/verify-test.mid
csvmidi转换：成功

$ ./midicsv $TMPDIR/verify-test.mid $TMPDIR/verify-test2.csv
midicsv回转：成功

$ cmp -s test.mid $TMPDIR/verify-test.mid
MIDI文件对比：一致（回转完整）

$ diff -q $TMPDIR/verify-test.csv $TMPDIR/verify-test2.csv
CSV文件对比：一致（回转完整）
```

### 二进制信息

```
midicsv: ELF64 PIE aarch64, 动态链接 libc.so, 43KB（strip后）
csvmidi: ELF64 PIE aarch64, 动态链接 libc.so, 84KB（strip后）
```

### Staging验证

- 二进制文件数：2（midicsv, csvmidi）
- man pages：3（midicsv.1, csvmidi.1, midicsv.5）
- R7安全弹窗检查：通过（二进制可直接执行）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| midicsv-1.1-ohos-aarch64.tar.gz | 185KB | 预编译包（含2二进制+3man page） |
| midicsv-1.1-ohos-aarch64-debug.tar.gz | 110KB | 含调试符号的预编译包 |
| 0001-Makefile-ohos-adapt.patch | ~3KB | Makefile适配补丁 |

## 注意事项

1. midicsv不支持`--version`，G2门禁会给出⚠️警告，但实际功能完全正常
2. INSTALL_DEST硬编码了$DEFAULT_PREFIX路径，这是Makefile项目的固有特性（非autotools的动态配置）
3. 补丁中INSTALL_DEST包含绝对路径，不同环境下需调整
---

**编译结束**: 2026-06-11 15:02
**最终状态**: published
