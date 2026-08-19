# lttoolbox 3.7.6 — 构建笔记

## 背景

apertium-core 3.9.12 的 `configure.ac:71` 声明：
```
PKG_CHECK_MODULES(LTTOOLBOX, [lttoolbox >= 3.7.2])
```
制品仓 ohpcd remote 和本地 cache 均无 lttoolbox，这是 apertium-core 的 P0 阻塞依赖。

## 版本选择

| 版本 | 构建系统 | 满足 >=3.7.2 | 选择 |
|------|----------|-------------|------|
| 3.7.6 | autotools | ✅ | ✅ **本配方** |
| 3.8.0+ | CMake | ✅ | ✗ 依赖链更重（需 CMake + ICU + Boost + utfcpp + Python） |

lttoolbox 3.7.6 是最后一个基于 autotools 的稳定版本（`configure.ac` + `Makefile.am` + `autogen.sh`）。
3.8.0 起上游迁移到 CMake（`CMakeLists.txt`）。本配方参照 libiconv 的 autotools 模式构建。

## 上游 release

- GitHub: https://github.com/apertium/lttoolbox/releases/tag/v3.7.6
- 源码 URL: `https://github.com/apertium/lttoolbox/archive/refs/tags/v3.7.6.tar.gz`
- SHA256: `06cae70c8a0c93a358b84f95e287009ca4d7e732e05b782ac27156bc8ded4762`

## 构建系统

autotools（configure.ac + Makefile.am + autogen.sh）。

**关键**：release tarball 不含预生成 `configure` 脚本，必须在 build 阶段执行 `autoreconf -fi` 生成。
`autogen.sh` 本身会调用 `autoreconf -fi && ./configure`，但我们只需 autoreconf 部分。

## 依赖

| 依赖 | Conan ref | 来源 | 说明 |
|------|-----------|------|------|
| libxml2 | `libxml2/2.15.3.1` | ohpcd/stable | XML 解析（dix 字典格式） |
| ICU | `icu4c/77` | ohpcd remote | Unicode 支持（icu-i18n, icu-io, icu-uc） |
| Boost | `boost/1.91.0` | ohpcd remote | C++ 库（configure.ac 未直接要求，但 lttoolbox 3.7.6 头文件引用 sorted_vector.hpp） |
| utfcpp | `utf8cpp/4.1.1` | ohpcd remote | UTF-8 编解码（configure.ac: AC_CHECK_HEADER utf8.h） |
| pthread | system | — | POSIX 线程（AX_PTHREAD） |

### 依赖路径注入

configure.ac 使用 `PKG_CHECK_MODULES` 检测 libxml2 和 ICU，这依赖系统 pkg-config。
在 Conan 交叉构建环境下，我们通过 `CPPFLAGS`/`LDFLAGS` 直接注入依赖的 include/lib 路径，
绕过系统 pkg-config 查找。

## 构建产物

- `lib/liblttoolbox.a` — 静态库（R26: 静态避免污染 /lib）
- `bin/lt-comp` — 编译字典到二进制 letter transducer
- `bin/lt-proc` — 处理文本（lexical string processing）
- `bin/lt-print` — 打印 transducer 内容（ATT 格式）
- `bin/lt-expand` — 展开 transducer
- `bin/lt-trim` — 裁剪 transducer
- `bin/lt-compose` — 组合 transducer
- `bin/lt-append` — 追加 transducer
- `bin/lt-paradigm` — 范式操作
- `bin/lt-tmxcomp` / `bin/lt-tmxproc` — TMX 编译/处理
- `bin/lt-invert` / `bin/lt-restrict` / `bin/lt-apply-acx`
- `include/lttoolbox/*.h` — 头文件
- `share/lttoolbox/` — DTD/RNG schema 文件

## OHOS 适配

- autotools `config.guess`/`config.sub` 可能不识别 OHOS triplet。
  Conan OHOS 适配版 conan 会自动处理 triplet 映射（os=OHOS → linux-ohos）。
  如遇 config.guess 不识别问题，需补丁（参照 libiconv E007 补丁模式）。
- `configure.ac` 使用 `AC_CANONICAL_HOST` 探测 host triplet。
- `--build` 和 `--host` 由 Conan AutotoolsToolchain 自动设置。

## 测试

test_package/ 包含一个 C++ 程序，调用 lttoolbox API（Transducer/Alphabet 类）
验证库可链接且头文件可包含。

## 教训参考

- acf-lib-lua5.3 教训：依赖解析需裸版本 ref，创建后需不带 --user/--channel 重新导出。
- libiconv autotools 模式：静态构建、CPPFLAGS/LDFLAGS 注入、patch-autotools-ohos。
