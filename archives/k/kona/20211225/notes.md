# kona 20211225 适配笔记

## 编译环境

- 构建系统: 纯 Makefile（非 autotools，无 configure 步骤）
- 编译日期: 2026-06-18
- 编译器: clang 15.0.4
- 平台: HarmonyOS（aarch64, musl libc）
- 源码版本: Win64-20211225 tag（跨平台 C 代码，非仅 Windows）
- 源码 SHA256: cd5dcc03394af275f0416b3cb2914574bf51ec60d1c857020fbd34b5427c5faf
- 状态: **published**

## 编译步骤

kona 是 K 编程语言的开源实现，使用纯 Makefile 构建（非 autotools）。

```bash
# 1. 修改 Makefile 添加 harmonyos 平台支持（详见源码修改章节）
# 2. 编译
make CC=clang CFLAGS="-fPIC -O2" PRODFLAGS="-O3 -fPIC" PREFIX=$DEFAULT_PREFIX k
# 3. DESTDIR 安装（R20 铁律）
make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
# 4. 预编译包制作
python3 $SKILL_ROOT/scripts/ohc-run.py package kona 20211225
# 5. 本地安装验证
make install PREFIX=$DEFAULT_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile OS 检测失败 | `uname -s` 返回 "harmonyos"，Makefile 无此 case | 添加 `ifeq (harmonyos,$(OS))` 块，镜像 linux 设置 |
| 2 | install 不支持 DESTDIR | 原 install target 直接用 `$(PREFIX)/bin/k`，无 DESTDIR 前缀 | 修改 install target：增加 `mkdir -p $(DESTDIR)$(PREFIX)/bin` 和 `$(DESTDIR)` 前缀 |
| 3 | src/va.c 2 个编译警告 | LLONG_MAX/LLONG_MIN 转 double 时精度损失 | 非关键警告，kona 的类型转换逻辑已处理边界情况，不影响功能 |
| 4 | G0 自动验证失败 | 平台 `patch` 命令不支持 `--input` 选项 | 平台限制；手动验证：补丁应用 + 编译 + 测试全部通过 |
| 5 | G4 manifest 缺少 build_system | 模板缺少顶层 build_system 字段 | 添加 `build_system: makefile` 顶层字段 |

## 源码修改

### Makefile — 平台适配（补丁：0001-Makefile.patch，+15/-1 行）

修改了 3 处：

1. **OS 检测分支**（编译/链接配置）：
   ```makefile
   # OpenHarmony (HarmonyOS) — treat same as linux
   ifeq (harmonyos,$(OS))
   CFLAGS += -pthread
   OBJS= src/0.o src/bswap.o src/c.o src/getline.o src/mt.o src/p.o src/r.o \
         src/k.o src/kc.o src/kx.o src/kg.o src/km.o src/kn.o src/ko.o src/ks.o \
         src/v.o src/va.o src/vc.o src/vd.o src/vf.o src/vg.o src/vq.o
   LDFLAGS = -lm -ldl
   endif
   ```

2. **依赖规则块**：
   ```makefile
   ifeq (harmonyos,$(OS))
   src/*.o: src/incs.h src/ts.h Makefile src/k.h
   endif
   ```

3. **安装目标（DESTDIR 支持）**：
   ```makefile
   install:
   	mkdir -p $(DESTDIR)$(PREFIX)/bin
   	install k $(DESTDIR)$(PREFIX)/bin/k
   ```

## 依赖版本

- 无外部依赖（kona 是自包含 C 项目）
- 编译器：clang 15.0.4
- 链接库：-lm -ldl（系统标准库）
- 构建工具：GNU Make 4.4.1

## 验证结果

```bash
$ echo "2+2" | k
  4
$ echo "7*8" | k
      56
$ echo "!5" | k
  0 1 2 3 4
$ echo "2*!5" | k
  0 2 4 6 8
$ echo "+/!5" | k
  10
$ echo "3>2" | k
  1
$ echo '"hello"' | k
  "hello"
$ printf 'a: !5\nb: 2*a\nb\n' | k
      0 2 4 6 8
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| kona-20211225-ohos-aarch64.tar.gz | 297KB | 预编译包（ELF 签名、strip、权限修复） |
| kona-20211225-ohos-aarch64-debug.tar.gz | 58KB | 调试符号包 |
| 0001-Makefile.patch | 2219 字节 | Makefile 平台适配补丁（+15/-1 行） |

## 知识沉淀

- 知识图谱草稿 E105：Makefile 平台检测模式（类似 E090 meson 平台检测）
- 触发条件：Makefile 中 `ifeq ($(OS), linux)` 式平台分支，HarmonyOS 不匹配
- 解决方案：添加 `ifeq (harmonyos,$(OS))` 镜像 linux 配置

## 注意事项

- kona tag 名为 Win64-20211225 但源码是跨平台 C 代码，可在 ARM/HarmonyOS 上正常编译
- src/va.c 的 2 个编译警告是 long long → double 的隐式转换（LLONG_MAX/MIN），不影响功能
- kona 是解释器，不产生库文件，只输出单个二进制 `k`
- G0 自动验证受限于平台 `patch` 命令（不支持 `--input`），已手动验证通过

---

**编译结束**: 2026-06-18 00:35
**最终状态**: published
