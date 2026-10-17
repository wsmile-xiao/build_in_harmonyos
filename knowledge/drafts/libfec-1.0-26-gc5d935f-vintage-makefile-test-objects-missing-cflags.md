# 老式手写 makefile：测试对象规则不带 $(CFLAGS) → srcdir 构建找不到 config.h

- **软件**: libfec 1.0-26-gc5d935f（泛化到手写 makefile 项目）
- **阶段**: build（make test）
- **severity**: 3
- **状态**: DRAFT

## 现象

```
vtest27.c:2:10: fatal error: 'config.h' file not found
make: *** [makefile:82: vtest27.o] Error 1
```

库本体（libfec.a）与构建期工具已全部编过，**只在 `make test` 阶段**报错。

## 根因

1990s 手写 makefile 的库对象规则链在 CFLAGS 里带 `-I.`，configure 生成在
**build 目录**的 config.h 可被解析；但**测试程序**的对象规则被作者写成
极简形式 `gcc -g -c $<`，不带 `$(CFLAGS)`：

- 源码树内构建时 cwd == 源码目录，config.h 就在手边，问题被掩盖；
- Conan 以 srcdir/builddir 分离构建（basic_layout）时，config.h 只在 build
  目录，测试对象经 VPATH 找到 .c 后以**源目录**为 include 起点 → 找不到。

## 修复

给测试对象规则补 `$(CFLAGS)`（独立补丁，单一职责）：

```diff
-	$(CC) -g -c $<
+	$(CC) $(CFLAGS) -g -c $<
```

`-I.` 指向 build 目录即解析 config.h；-fPIC/-Wall/-O2 对测试对象无害。
若上游还硬编码 `gcc`，需配套 gcc→`$(CC)` 补丁（见 libfec 0003）。

## 证据

libfec 1.0-26-gc5d935f 真机（frp-tip.com:56267）：

- create-5：libfec.a、gen_ccsds 构建期代码生成全过；make test 阶段
  vtest27/29/39/615 四处 `config.h file not found`；
- 0004 补丁（commit `2122567ceb`）后 create-8 全绿：rstest 228×OK、
  vtest 全部 exit 0、test_package 19/19。
