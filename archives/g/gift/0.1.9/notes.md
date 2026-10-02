# gift 0.1.9 适配笔记

## 编译环境
- 构建系统: autotools（2002 年 automake 1.6 / autoconf 2.53 / libtool 1.4）
- 编译日期: 2026-09-24 ~ 09-25
- 编译器: clang 15.0.4（ohos-sdk llvm）/ c++ = clang++
- 依赖: expat/2.8.4、libuuid/2.42.2（conan full_deploy）；perl 5.42.0（hnp）
- 状态: built（conan create + test_package 全部通过）

## 编译步骤

1. W1: conan full_deploy 拉取 expat/libuuid 依赖；下载 GNU 官方 tarball 并核验 sha256。
2. 补丁 config.guess/config.sub（识别 `aarch64-unknown-linux-ohos`）。
3. 补丁 configure：mktemp→mkdir、ac_max_sed_lines=100000、sed 由管道改文件交接。
4. `./configure --host=aarch64-unknown-linux-ohos CPPFLAGS/LDFLAGS 指向依赖`，
   configure 自动生成 39 个 Makefile，并经 gift-check-perl-config.pl 取得
   PERL_LD_ADD（-Wl,-E + libperl 链接参数）。
5. 串行 `make`（HMDFS 无 jobserver mkfifo，禁 -j）：产出 GIFTServer/gift 等
   5 个程序 + 9 个共享库 + FeatureExtraction 工具。
6. `make install DESTDIR=...` 验证布局：bin/（5 程序 + 24 个 perl 脚本）、
   lib/（9 库 × .so.0.0.0/.so.0/.so/.a/.la）、include/libGIFT*/、share/*.mrml。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 阶段 `mktemp: Invalid argument`，无法生成 config.status | HMDFS setgid tmpdir 上 mktemp 以 0700 建目录被拒 | 补丁 configure：mktemp -d → mkdir 生成式目录名 |
| 2 | 39 个 Makefile 中大半变量空缺（sed 交接损坏），make 大量 undefined | toybox sed 处理超长管道时写后读损坏（HMDFS 管道怪癖 + sed 缓冲上限） | 补丁 ac_max_sed_lines=100000 并改为 sed 文件交接；另装 GNU sed 4.10 加固 |
| 3 | config.guess 报 Unrecognized host | 2002 年脚本无 aarch64/musl 概念 | 引入新 config.guess/config.sub 并保留 ohos LIBC 检测 |
| 4 | perl 5.42 下 `__libcpp_is_integral<char>` 重定义错误 | libGIFTQuPerl/cc/xs_init.cc `#define bool char` 与 libc++ 内部冲突 | 删除该宏定义（C++ 编译器 bool 即 bool） |
| 5 | iostream.h 不存在、流到 bool 隐式转换报错、in-class 限定/this->/make_pair/cassert 等大量 C++17 报错 | 1998-2002 年代码 + 现代 clang | 0002 补丁统一修复 30 个文件（详见 patches） |
| 6 | perl.h 宏污染（如 `_\_ attr` 冲突）| perl.h 与 GIFT 头同时展开 | 冲突点 `#undef` 相应宏 |
| 7 | libMRML.so 只 NEEDED libc 却引用 `_ZdlPv`/`XML_*` | libtool 1.4 `-nostdlib` 链接 shared 时不记录 C++ 运行时与非直接依赖 | 不在源码修（Linux/glibc 下游由最终二进制补齐可工作）；本地验证用手动 relink 使 NEEDED 闭包完整 |
| 8 | libGIFTQuPerl 不能链 -lperl | libperl.a 非 PIC，无法进 -shared | 保持上游设计：Perl_* 留给最终二进制 `-Wl,-E` 导出解析 |
| 9 | gift 二进制无法在设备 exec（NEEDED 搜索失败）| 鸿蒙 musl 加载器忽略 LD_LIBRARY_PATH/RUNPATH，DT_NEEDED(soname) 只搜 /system/lib64 等只读目录 | 验证策略改为：dlopen 探针（绝对路径加载）+ 链接期符号闭包探针（test_package）双通道 |
| 10 | patchelf 修改过的 ELF 被 exec/dlopen 拒绝 | 平台信任机制仅接受工具链直出产物 | 放弃 patchelf 方案，用带桩符号的探针变体验证加载机制 |

## 源码修改

- `patches/0001-ohos-build-scripts.patch`：config.guess、config.sub、configure
  （mktemp→mkdir、sed 上限+文件交接）、gift-check-perl-config.pl（perl 5.42 兼容）。
- `patches/0002-cxx-compiler-fixes.patch`：30 个 C++ 文件的编译期修复
  （in-class 限定、this->、显式 (bool) 流转换、make_pair 模板参数、cassert、
  ::bind、reinterpret_cast、perl.h 宏 undef、CAcPerl size_type、K&R main 补 int 等）。

## 依赖版本

- expat/2.8.4（conan，ohpcd 远端）
- libuuid/2.42.2（conan，ohpcd 远端，仅静态 .a）
- perl 5.42.0（hnp /data/service/hnp/perl.org/perl_5.42.0）

## 验证结果

```bash
# 1) 全量构建（串行）通过
make -j1   # exit 0；GIFTServer/gift + 9 个 libGIFT*/libMRML .so

# 2) 链接期符号闭包：最终二进制与全部 9 库 + expat/libperl 全符号解析
#    （ld.lld 链接 gift：0 undefined symbols）

# 3) 设备 dlopen 探针（绝对路径 + 桩符号变体）：9/9 库加载成功
dlopen libMRML.so                    -> OK
dlopen libGIFTQuInvertedFile.so      -> OK
dlopen libGIFTQuHierarchy.so         -> OK
dlopen libGIFTAcInvertedFile.so      -> OK
dlopen libGIFTAcHierarchy.so         -> OK
dlopen libGIFTAcDistanceMatrix.so    -> OK
dlopen libGIFTAcURL2FTS.so           -> OK
dlopen libGIFTQuPerl.so              -> OK
dlopen libGIFTAcPerl.so              -> OK

# 4) conan create + test_package（链接探针 + 包完整性断言）全部通过
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/gift | ~200KB | MRML 图像检索服务端（daemon） |
| bin/gift-generate-inverted-file 等 4 个 | — | 倒排文件构建/处理工具 |
| lib/libMRML.so.0.3.0 | ~4.6MB | MRML 协议核心库 |
| lib/libGIFT{Qu,Ac}*.so.0.0.0（8 个） | 0.3~0.9MB | 查询/访问器库组 |
| bin/*.pl、bin/*.pm（24 个） | — | Perl 客户端/管理脚本 |
| share/*.mrml（3 个） | — | 运行时配置数据 |

## 注意事项

- **必须串行 make**：HMDFS 不支持 jobserver 的 mkfifo（`make -j` 必败）。
- **禁止 LD_LIBRARY_PATH 思维**：鸿蒙 musl 加载器只搜只读系统目录；包内 so 的
  exec/运行时解析依赖 DT_NEEDED 闭包完整与安装到系统路径。二进制冒烟在设备上
  以 dlopen/链接探针代替 `gift --help`。
- gift 服务端运行时还需 FeatureExtraction 工具与图像数据集，属部署问题而非编译问题。
- libGIFTQuBayesian 是 header-only，不产库文件。
---

**编译结束**: 2026-09-25 12:06
**最终状态**: built
