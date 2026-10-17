# DRAFT: 纯 Makefile 上游把 CLI 工具链到自身 .so 上——拆 tools 包后工具加载期 127

> Contributor: username- | Status: DRAFT | Created: 2026-09-17
> 来源: libfreeaptx-tools 0.2.2 适配（上游只有一份手写 Makefile，没有 configure / CMake / Meson）

## 症状

`conan create` 全绿，`make install` 也把两个工具装进了 `bin/`。但真机一跑：

```
$ bin/freeaptxenc --version
CANNOT LINK EXECUTABLE "bin/freeaptxenc": library "libfreeaptx.so.0" not found
$ echo $?
127
```

`--help` 同样答不出来。构建日志里**没有任何错误**，`make` 退出码 0，
`bin/` 里的文件也在——典型的"构建成功、产物不可用"。

## 根因

上游 Makefile 用"工具依赖库文件"的隐式规则把两者绑在一起：

```make
UTILITIES  = $(NAME)enc $(NAME)dec
LIBNAME    = lib$(NAME).so

$(UTILITIES): $(LIBNAME)
.o: .c
	$(CC) $(CFLAGS) -c -o $@ $<
$(LIBNAME): $(SOURCES) $(HEADERS)
	$(CC) $(CFLAGS) -fPIC -shared -o $@ $^
```

于是工具的链接命令实际是

```
$(CC) ... -o freeaptxenc freeaptxenc.o $(LIBNAME)
```

产物带 `DT_NEEDED libfreeaptx.so.0`，而且没有 RUNPATH。库包与本包按
"同一文件只能有一个属主"的规则把 `lib/` 删掉之后，这个 `DT_NEEDED`
就没人满足了。

一条命令即可判定（不需要真机）：

```sh
readelf -d bin/freeaptxenc | grep NEEDED
# 出错形态: Shared library: [libfreeaptx.so.0]
# 正确形态: Shared library: [libc.so]
```

## 顺带踩到的三个坑

同一份 Makefile 还有三处会让"照抄上游构建步骤"的适配失败：

1. **静态目标是空壳。** 上游声明了
   `STATIC_UTILITIES = $(NAME)enc.static $(NAME)dec.static` 和
   `.SUFFIXES: .o .c .static`，但**没有 `.c.static:` 规则**，
   所以 `make freeaptxenc.static` 报 `No rule to make target`。
   看到 `.static` 目标就去依赖它，是这条路上最容易踩的空档。

2. **`CFLAGS = -W -Wall -O3` 是普通赋值**，会盖掉环境变量。交叉编译时
   在 `configure`/环境里注入 `-fPIC` 是无效的，必须用 **make 命令行变量**
   （命令行赋值优先级最高）：

   ```sh
   make -j1 CC=<cc> CFLAGS="-W -Wall -O3 -fPIC"
   ```

   漏掉 `-fPIC` 的后果不是警告而是链接期
   `R_AARCH64_ADR_PREL_PG_HI21` 之类重定位错误。

3. **聚合安装目标会把库、头文件、`.pc` 一起装进 tools 包**。上游
   `default:` 与 `install:` 都包含 `$(LIBNAME)` / `$(HEADERS)`，
   拆分包时必须一并收窄，否则两个归档互相覆盖。

## 修复

补丁 0001 把工具的链接规则改成吃源文件，产物自包含：

```make
$(NAME)enc: freeaptxenc.o $(SOURCES)
	$(CC) $(CFLAGS) $(CPPFLAGS) $(LDFLAGS) -I. -o $@ $@.o $(SOURCES)
```

并把 `default` 收窄为 `$(UTILITIES) $(HEADERS)`、`install` 只装 `bin/`。
补丁 0002 补 `-V/--version`（上游 `-h/--help` 与未知选项一律 `return 1`，
平台 L2 冒烟必然判失败）。

## 验证

```
$ readelf -d bin/freeaptxenc | grep NEEDED
 0x0000000000000001 (NEEDED)   Shared library: [libc.so]
$ bin/freeaptxenc --version; echo $?
freeaptxenc 0.2.2
0
$ 4800 字节 24bit 立体声 PCM | freeaptxenc | freeaptxdec
长度回到 4800 字节，平均绝对误差 2898（约 0.03% 满量程）
```