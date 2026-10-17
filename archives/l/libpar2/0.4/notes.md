# libpar2 0.4 适配笔记

## 编译环境
- 构建系统: autotools（自带 configure 脚本，无需 autoreconf）
- 编译日期: 2026-09-14
- 编译器: clang/clang++ 15 (aarch64-linux-ohos, libc++, C++11)
- 状态: built

## 关键决策

### 语言纠正：C → C++
认领信息标注语言为 C，实际源码全部为 `.cpp`（libpar2.cpp、par2cmdline.cpp 等 30+
文件），configure.ac 使用 `AC_PROG_CXX` / `AC_LANG_CPLUSPLUS`，`lib_LTLIBRARIES =
libpar2.la` 是 C++ 共享库。按实际语言适配。

### AC_CHECK_LIB(stdc++) 绕过（本库最大坑）
OHOS 工具链只有 libc++，没有 libstdc++。configure.ac 中的
`AC_CHECK_LIB(stdc++, main,,AC_MSG_ERROR(You need libstdc++))` 在 OHOS 上必然失败。
处理分两步：
1. 注入 autoconf 缓存变量 `ac_cv_lib_stdcpp_main=yes` 跳过链接探测。
   ⚠️ 变量名是 **ac_cv_lib_stdcpp_main**（autoconf 将 '+' 映射为 'p'），
   不是网上常见的 `ac_cv_lib_stdcpp__main`（双下划线版会不生效）。
2. patch configure（0002）：探测成功分支仍会执行 `LIBS="-lstdc++ $LIBS"`，
   最终链接 libpar2.la 时带 -lstdc++ 依然失败。必须把该注入行删除。
   Makefile.am 的 `LDADD = -lstdc++ $(SIGC_LIBS)` 不影响库目标
   （库链接只用 `$(libpar2_la_LIBADD) $(LIBS)`），无需改动。

### config.sub 补丁（0001）
libpar2 自带的 config.sub（2013 年版）既不认识 aarch64 CPU，也不认识
linux-ohos OS。`--host=aarch64-linux-ohos` 直接 canonicalize 失败。补丁三处：
- KERNEL-OS 组合列表加 `linux-ohos*`
- CPU 列表加 `aarch64`
- OS 列表加 `-linux-ohos*`

### 三元组与依赖发现
- AutotoolsToolchain 不自动注入 OHOS 三元组，显式传
  `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`。
- configure.ac 用 `PKG_CHECK_MODULES(SIGC, sigc++-2.0)` 找 libsigc++，
  依赖 libsigc/2.10.8 的 package_info 声明了 pkg_config_name=sigc++-2.0，
  用 PkgConfigDeps 生成 .pc 并注入 `PKG_CONFIG_PATH=<generators_folder>`。
- conftest 链接 libsigc 共享库后要运行产物，OHOS loader 无默认搜索路径，
  build 环境注入依赖 libdir 的 LD_LIBRARY_PATH（与 aaphoto/libthai 同模式）。

### 老代码 C++11
2003 年代代码在 profile 默认 cppstd=17 下可能不兼容，显式
`tc.cxxflags.append("-std=c++11")`（nixpkgs 对 clang 同样加
`CXXFLAGS="-std=c++11"`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | AC_CHECK_LIB(stdc++) 链接探测失败 | OHOS 只有 libc++ 无 libstdc++ | 注入缓存变量 `ac_cv_lib_stdcpp_main=yes` |
| 2 | configure 通过后链接仍带 -lstdc++ 失败 | 探测成功分支 `LIBS="-lstdc++ $LIBS"` | patch configure 删除该注入行（0002） |
| 3 | `--host=aarch64-linux-ohos` 报 unrecognized | config.sub 无 aarch64/ohos 支持 | patch config.sub 三处（0001） |
| 4 | PKG_CHECK_MODULES 找不到 sigc++-2.0 | .pc 在 generators_folder 但 PKG_CONFIG_PATH 未指向 | configure_args 注入 PKG_CONFIG_PATH |
| 5 | conftest 运行报加载共享库失败 | OHOS loader 无 conan 缓存库搜索路径 | build 环境注入 LD_LIBRARY_PATH |
| 6 | 老代码 clang 15 编译兼容性 | 2003 年代码 + 默认 cppstd=17 | -std=c++11 |

## 源码修改

2 个补丁（见 conandata.yml）：
- `0001-config.sub-ohos.patch`：config.sub 支持 aarch64 + linux-ohos
- `0002-configure-libstdcxx.patch`：删除 configure 中 -lstdc++ 的 LIBS 注入

## 依赖版本

| 依赖 | 版本 | 制品仓 | 说明 |
|------|------|--------|------|
| libsigc | 2.10.8 | ✅ ohpcd 已发布 | sigc++-2.0 pkg-config，meson 构建 |

## 验证结果

```bash
# test_package 消费者测试（上游无测试，自补）
./test_libpar2
<按实际运行结果填写>
```

产物：`lib/libpar2.so`（+ soname 软链）、`include/libpar2/*.h`、
`lib/libpar2/include/config.h`、`licenses/COPYING`。

## 注意事项

- 上游 configure.ac 元数据版本写死 0.2（AC_INIT/AM_INIT_AUTOMAKE 未随 0.4 更新），
  不影响构建，仅 soname/元数据层面。
- 上游仓库 Parchive/libpar2 已于 2025-04-28 归档（read-only），源码包在 launchpad。
- 库名链接名是 `par2`（libpar2.la → -lpar2），package_info 的 cpp_info.libs 用 `par2`。
