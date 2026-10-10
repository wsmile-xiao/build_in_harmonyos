# DRAFT-conan-cache-so-musl-eacces-static-closure

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-conan-cache-so-musl-eacces-static-closure.kv`
> 说明：该 kv 为文档式条目，本文档为其可读镜像。

---

## 适用场景

消费者（Rust -sys crate / 原生 dlopen / 直接 NEEDED）在运行时加载 conan 制品仓分发的 .so 报：

```
Error loading shared library libfontconfig.so.1: (needed by ./alacritty)
Error relocating ./alacritty: FcCharSetDestroy: symbol not found
Error relocating ./alacritty: FcPatternDestroy: symbol not found
...（数十行 Fc* 符号连锁）
```

或 Python 复现：

```
OSError: Error loading shared library .../libfontconfig.so.1: Permission denied
```

## 根因（受控 A/B/C/D 对照实验，2026-10-08 设备）

| 实验 | 内容 | 结果 |
|---|---|---|
| A | Harmonybrew Cellar 的 libfontconfig.so.1.16.0 | **加载成功**（CDLL + 二进制运行 rc=0） |
| B | conan 仓库 fontconfig/2.18.3 的 libfontconfig.so.1.17.0 拷贝到本地目录 | EACCES |
| C | chmod 755/777 | 依然 EACCES（排除权限位） |
| D | 交叉放置（conan .so 进 brew 目录 / brew .so 进 conan 目录） | 结果跟文件走不跟目录走 |

同目录、同权限位、同 SONAME、同架构、无 symbol versioning、GNU_STACK 一致——唯一差异是构建产物来源。musl loader 对 conan 缓存（hmdfs 路径上构建）的 ELF 返回 EACCES。ld-musl 报错形态有迷惑性：先报缺库，再连锁数十行 "symbol not found"，容易误判为符号不匹配。

## 解法（Rust GUI 件：Harmonybrew 静态归档闭包）

1. **选瓶**：fontconfig/freetype/expat/gettext/libpng/bzip2/zlib-ng-compat（libfontconfig.a 引用 XML_* / libintl_dgettext / FT_*；freetype.a 引用 png_/BZ2_/zlib——闭包必须一次配齐，缺 libintl.a 报 `undefined symbol: libintl_dgettext`）；
2. **收集**：解包后归集 7 个 .a 到 `build/fontconfig-closure/`；
3. **合成自包含 fontconfig.pc**（无 Requires，Libs 列全闭包依赖序）：
   ```
   Libs: -L${prefix} -lfontconfig -lexpat -lintl -lfreetype -lz -lbz2 -lpng16
   ```
4. **注入**：`PKG_CONFIG_PATH=<closure>/pkgconfig` + `RUSTFLAGS="-C linker=clang -L <closure>"`（链接搜索先到先得，闭包 .a 优先）；
5. freetype 本体对 Rust 侧由 freetype-sys 对 ohos target 自动 vendored 编译（build.rs 显式分支）。

**效果**（alacritty 0.17.0 实测）：产物 NEEDED 仅 `libc++_shared.so + libc.so`（/system/lib64 系统自带），消费者零 LD_LIBRARY_PATH，彻底消除 conan .so 的运行期 EACCES 风险。

## 兜底

纯 C/C++ conan 消费者（必须共享）可尝试拷贝到非 hmdfs 本地目录（实验 B 显示此路对 fontconfig 不通，需逐库实测）；或配方内 brew install + opt/lib 路径（alligator/alkimia GUI 件先例）。优先仍是静态闭包。

## 实证存档

probe_load.py（ctypes 四组对照）；build6.log（静态闭包 rc=0，NEEDED 仅 libc++_shared/libc）；build7.log（缺 libintl 最小闭包 undefined symbol 反证）。
