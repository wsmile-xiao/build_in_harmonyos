# DRAFT-E572 — 已被依赖库删除的 *-config 探测脚本：迁移到 pkg-config（含消费方 .pc 陷阱）

## 场景

cube2font 1.5.1（Red Eclipse / Cube Engine 2 的 `src/shared/cube2font.c`，单文件工具）
在 OHOS 设备上用 conan 构建时的**第一条真实错误**：

```text
clang++ ... -c -o shared/cube2font.o shared/cube2font.c `freetype-config --cflags`
/bin/sh: freetype-config: inaccessible or not found
shared/cube2font.c:7:10: fatal error: 'ft2build.h' file not found
    7 | #include <ft2build.h>
make: *** [Makefile:235: shared/cube2font.o] Error 1
```

上游 `src/Makefile`（第 235、238 行）用反引号调用 `freetype-config` 取编译/链接参数；
该脚本自 FreeType 2.9.1（2018）起被上游删除，conan 的 freetype 依赖包里也没有
（`find <包> -name 'freetype-config*'` = 0 命中，包内连 `bin/` 目录都不存在）。

## 根因

1. **探测脚本世代更替**：`freetype-config` / `sdl-config` / `glib-config` 这代
   `*-config` 脚本已被 pkg-config 取代；宿主发行版常因兼容包残留，掩盖了问题，
   交叉编译（conan）环境第一次暴露。
2. **报错点错位**：真正 fatal 的是 `#include <ft2build.h>`，探测失败只在上一行留一句
   shell 的 "not found"，容易被误判成"头文件路径没配好"而去改依赖或加 `-I`。
3. **.pc 的 prefix 语义**：依赖包自带的 `.pc` 由打包时生成，prefix 是安装前缀
   （conan relocatable 布局下为 `/`）。把它直接放进 `PKG_CONFIG_PATH` 会得到
   `-I//include/freetype2 -L//lib -lfreetype` 这种指向根目录的死路径，编译**仍然失败**。

## 复现与实测证据（2026-09-11，OHOS 设备 aarch64）

```text
# 1) 依赖包内没有可包装的脚本
$ find <conan freetype 包>/ -name 'freetype-config*' | wc -l
0
$ ls <conan freetype 包>/bin
ls: .../p/freet3bc96d7306ba9/p/bin: No such file or directory

# 2) 依赖包自带 .pc 的 prefix 是安装前缀
$ head -4 <conan freetype 包>/lib/pkgconfig/freetype2.pc
prefix=/
exec_prefix=/
libdir=//lib
includedir=//include

# 3) 指向包内 .pc → 死路径
$ PKG_CONFIG_PATH=<conan freetype 包>/lib/pkgconfig pkg-config --cflags --libs freetype2
-I//include/freetype2 -L//lib -lfreetype
$ make cube2font ... CXXFLAGS="-I<zlib>/include"
shared/cube2font.c:7:10: fatal error: 'ft2build.h' file not found

# 4) 用消费方 PkgConfigDeps 生成的 .pc → 真实路径
$ PKG_CONFIG_PATH=<generators_folder> pkg-config --cflags --libs freetype2
-I<conan 缓存>/p/freet3bc96d7306ba9/p/include/freetype2 -I<...>/include -L<...>/lib -lfreetype
```

## 方案（cube2font 1.5.1 实证）

1. 补丁只改真正失败的两条规则（编译、链接），并加 `PKG_CONFIG?= pkg-config`：

   ```make
   +PKG_CONFIG?= pkg-config
   -	$(CXX) $(CXXFLAGS) -c -o $@ $< `freetype-config --cflags`
   +	$(CXX) $(CXXFLAGS) -c -o $@ $< `$(PKG_CONFIG) --cflags freetype2`
   -	$(CXX) $(CXXFLAGS) $(LDFLAGS) -o $@ $< `freetype-config --libs` -lz
   +	$(CXX) $(CXXFLAGS) $(LDFLAGS) -o $@ $< `$(PKG_CONFIG) --libs freetype2` -lz
   ```

   模块名 `freetype2` 取自 Conan 依赖包 cpp_info 的 `pkg_config_name` 属性
   （PkgConfigDeps 据此生成文件名）。
2. 配方 `generators = "PkgConfigDeps"`，build() 内 `os.environ["PKG_CONFIG_PATH"] = self.generators_folder`
   （PkgConfigDeps 的 .pc 指向依赖包在缓存中的真实目录）。
3. 配方侧仍需的依赖 flags（本例是静态 zlib 的 `-I`/`-L`）用同一 pkg-config 注入
   `CXXFLAGS`/`LDFLAGS`，不手写缓存路径。
4. 同类"必然失败的 shell 探测"（`PLATFORM= $(shell gcc -dumpmachine)`，无 gcc 时每次
   展开都打印 `gcc: No such file or directory`）在 make 命令行传值即可完全抑制：
   命令行变量优先于文件内赋值，无需改上游文件。
5. 结果：`conan create` 干净构建通过，test_package 两次真实转换共 40 项断言全过。

## 与既有条目的差异（可执行反证）

| 既有条目 | 其场景 | 与本条的差异（实测反证） |
|---|---|---|
| E433 `gpgme-config` | 包内**有** `gpgme-config`，但输出缺自身 include 目录 | 本条包内根本没有该脚本：`find <包> -name 'freetype-config*' \| wc -l` → `0`，`ls <包>/bin` → `No such file or directory`；包装不存在的脚本无意义 |
| E111 `krb5-config: inaccessible or not found` | Python 包编译期缺系统 C 开发库 | 本条不缺库（freetype 已在依赖图内并已安装），缺的是**过时的探测入口**；修复在构建脚本而非依赖清单 |
| DRAFT-pngnq-1.1-conan-libpng-config-wrapper | 包内**有** `libpng-config`，但 `prefix="/"` 输出不可用 → 自建 wrapper 前置 PATH | 本条包内无脚本可包装，官方替代口径是 pkg-config 模块（Debian 的 use-pkg-config.patch 即同一处替换）；同时本条把"依赖包自带 .pc 的 prefix 也是 `/`"这一同源陷阱补上：`PKG_CONFIG_PATH=<包>/lib/pkgconfig pkg-config --cflags freetype2` → `-I//include/freetype2`，编译复现同样的 `ft2build.h` 报错，必须改用消费方 PkgConfigDeps 的 .pc |
| E075 `pkg-config --cflags 空` | `C_INCLUDE_PATH` 让 pkg-config 过滤 `-I` | 本条是 shell 探测脚本不存在，与 C_INCLUDE_PATH 无关；反证：`unset C_INCLUDE_PATH` 后 `pkg-config --cflags freetype2` 输出正常，而 `freetype-config` 仍不存在 |

## 验证

- `conan-verify cube2font 1.5.1`：G1/G2/G3 PASS，G4 与 L2/L4/L5 工具跳过项按 workflow 第 7.2 节人工补测。
- test_package（真实转换）：单页 249 字符 → 1 张 256x256 PNG，19173/19173 字符框内像素全部有 ink；
  描边多页 249 字符 → 3 张 512x512 PNG，257964/258960 落在字符框内；计数 40/40。
- 产物：`bin/cube2font` sha256 `9c21a22d10322ceae203eda2b225ab89dc59e291845a45369631d7630c615391`，
  `DYN(PIE)` + `GNU_STACK RW` + `GNU_RELRO` + `BIND_NOW`，无 RPATH/RUNPATH。
