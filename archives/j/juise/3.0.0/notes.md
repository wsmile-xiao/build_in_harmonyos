# juise 3.0.0 适配笔记

## 编译环境
- 构建系统: autotools (configure + make, libtool 共享库)
- 编译日期: 2026-08-30
- 编译器: clang/clang++ (HNP /data/service/hnp/bin, OHOS aarch64)
- 状态: built（远端设备验证通过，test_package 4/4；pending CI upload → published）

## 编译步骤

设备端（ssh hm，`$HOME/ws/juise-3.0.0`）：

```bash
conan create archives/j/juise/3.0.0 \
  -pr:h=./ci/conan/profiles/ohos-aarch64 \
  -pr:b=./ci/conan/profiles/ohos-aarch64
```

关键 configure 参数（配方内）：
- `--prefix=/ --libdir=/lib --includedir=/include`
- `--with-libslax-prefix=... --with-libxslt-prefix=... --with-ssh2=...`
- `--with-libxml-prefix=... --with-libxml-include-prefix=<pkg>/include/libxml2 --with-libxml-libs-prefix=<pkg>/lib`
- `--disable-clira --disable-mixer --disable-debug --enable-shared --disable-static`
- `PKG_CONFIG_PATH=<generators_folder>:<5 依赖的 lib/pkgconfig>`（libssh2.pc Requires openssl）
- `CONFIG_SHELL=/bin/sh SHELL=/bin/sh CC=clang CXX=clang++`
- **必须注入 `PWD=<work>` 环境变量**，否则 conan 的 bash 包装器 getcwd 崩溃（见下）

产物：libjuise.so.0.0.0 + bin/juise + bin/juise-config + libexec/juise/juise-askpass + share/juise/import/*.slax

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-run bash 包装器 `getcwd: cannot access parent directories`，configure 无法确定工作目录 | OHOS 内核 getcwd(2) 在本目录返回 EPERM；bash 5.3 回退遍历根属主 0711 父目录链时无 read 权限；conan 子进程 `$PWD` 为空 | 配方 build() 注入 `os.environ["PWD"] = work`，bash 见 $PWD 与目录匹配即跳过 getcwd；configure/make 走 /bin/sh (mksh) 不受影响 |
| 2 | timestr.h 9 个语法错误 `__P` 未定义 | OHOS libc 无 glibc sys/cdefs.h | 补丁 0002：include 区后插标准 `__P` fallback |
| 3 | pid_lock.h `__BEGIN_DECLS` 未声明 | 同上 | 补丁 0003：插 `__BEGIN_DECLS/__END_DECLS` fallback |
| 4 | trace.h `u_int32_t` 未声明 | OHOS <sys/types.h> 有定义但缺 include | 补丁 0004：补 `#include <sys/types.h>` |
| 5 | extensions.c `_res` 未声明、`NBBY` 未定义 | OHOS 无全局 _res（resolv.h 仅 struct，libc.so 无符号）；NBBY 在 sys/param.h | 补丁 0005：补 `#include <sys/param.h>`；`_res` 段 `#ifndef __OHOS__` 包裹，`int addr_size` 移出守卫 |
| 6 | 链接失败 `ld.lld: error: unable to find library -lxml2` | conan libxml2 包的 xml2-config 硬编码构建期前缀 /usr/local；juise configure 裸调 `$XML_CONFIG --libs/--cflags` 不带 --prefix，LIBXML_LIBS 指向不存在的 /usr/local/lib | 配方传 `--with-libxml-include-prefix=<pkg>/include/libxml2` 与 `--with-libxml-libs-prefix=<pkg>/lib`（configure.ac 追加语义，conan 路径排在 -I/-L 首位） |
| 7 | 包内出现 `<pkg>/storage/Users/...` 泄漏目录 | install-exec-hook 用 `${DESTDIR}${SLAX_EXTDIR}` 注册 libslax 扩展，SLAX_EXTDIR 是 libslax 包的 cache 绝对路径 | 配方 package() 删除 package_folder 下 `storage/`（扩展注册属 libslax 运行时，不进 juise 制品） |
| 8 | patchelf 改写 RUNPATH 后 `Operation not permitted` | patchelf 重写 ELF 破坏 OHOS 平台执行校验 | 不做 patchelf；保留 libtool 构建目录 RUNPATH（conanrun 的 LD_LIBRARY_PATH 优先，无害） |

## 源码修改

5 个补丁（均已在干净 git 仓库 `git apply --check` 验证）：

- `patches/0001-config-guess-harmonyos.patch` — config.guess 识别 `*:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos`；config.sub 接受 `ohos*`/`linux-ohos*`
- `patches/0002-timestr-P-macro.patch` — timestr.h 定义 `__P` fallback
- `patches/0003-pidlock-begin-decls.patch` — pid_lock.h 定义 `__BEGIN_DECLS/__END_DECLS` fallback
- `patches/0004-trace-systypes.patch` — trace.h 补 `<sys/types.h>`
- `patches/0005-extensions-res-nbby.patch` — extensions.c 补 `<sys/param.h>`、`_res` 段 `__OHOS__` 守卫

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| libslax | 3.1.6 | slax-config、libslax/psu 运行时 |
| libxml2 | 2.15.3 | 注意其 xml2-config 前缀陷阱（见问题 6） |
| libxslt | 1.1.45.2 | |
| libssh2 | 1.11.1 | PKG_CHECK_MODULES 强制 |
| openssl | 3.5.6.1 | libssh2.pc Requires；AC_CHECK_LIB crypto |

## 验证结果

```bash
# 设备端 conan create 全链路
#   - configure: 通过
#   - make -j1:  通过（libjuise.la 链接成功）
#   - make install DESTDIR: 通过
#   - test_package 4/4 断言通过:
#     PASS: juise binary present and executable
#     PASS: juise --version reports 3.0.0
#     PASS: juise --help shows usage
#     PASS: libjuise shared library present

# 上游 make check：tests/ 仅占位（"Regression testing is not available (yet)"），无实际用例
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/juise | 主 CLI（libtool RUNPATH 指向构建目录 .libs，conanrun 环境正常加载） |
| bin/juise-config | 配置工具 |
| lib/libjuise.so.0.0.0 | 共享库（含 .so/.so.0 版本化别名） |
| libexec/juise/juise-askpass | askpass 工具（pkglibexec） |
| share/juise/import/*.slax | slax 导入库 |
| lib/pkgconfig/juise.pc | pkg-config 元数据 |

## 注意事项

1. **PWD 注入是硬要求**：删除会导致 bash 包装器 getcwd 崩溃、configure 无法确定工作目录（问题 1）。
2. **禁 LD_LIBRARY_PATH 注入**：会顶掉 lld 的 libxml2（clang 自带 RPATH），configure 编译测试报 "C compiler cannot create executables"。
3. **禁 patchelf 改二进制**：OHOS 拒绝执行被重写的 ELF（问题 8）。
4. 包内 `storage/` 泄漏已在 package() 清理；若上游 hook 行为变化需复核。
5. test_package 运行时依赖 conanrun 环境提供依赖库路径（libslax/libxml2 等），裸跑二进制会报缺库，属预期。
