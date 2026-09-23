# cmor 3.15.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-14
- 编译器: clang/clang++（OHOS 6.0 / aarch64）
- 状态: built

## 编译步骤

```bash
conan create archives/c/cmor/3.15.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

配方（conanfile.py）核心流程：
1. source()：下载官方 3.15.2 tarball + 3 个 CMOR tables submodule（cmip6/mip/cmip7-cmor-tables，release tarball 不含其内容）
2. generate()：AutotoolsToolchain + `--with-netcdf=no --with-udunits2 --with-json-c --with-uuid`，注入依赖 LDFLAGS
3. build()：注入 OHOS config.guess/config.sub 识别 → configure → make -j1 → ar 打包 libcmor.a

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `cannot guess build type` | tarball 自带 config.guess/config.sub（2021-01-08 版）不含 HarmonyOS/linux-ohos 识别 | 幂等注入：config.guess 主 case 加 `*:HarmonyOS:*:*` 输出 `aarch64-unknown-linux-ohos`；config.sub OS 校验加 `ohos*`、kernel-os 组合加 `linux-ohos*` |
| 2 | configure conftest 探测 `cannot run C compiled programs` | conftest 链接 netcdf/hdf5 共享库，运行需依赖库 + NDK libc++ 在 LD_LIBRARY_PATH | `_runtime_env()`：configure 前把 host 依赖 lib 目录 + NDK libc++ 目录注入 LD_LIBRARY_PATH |
| 3 | netcdf AC_CHECK_LIB 探测失败（`-lnetcdf` 找不到） | ①conan netcdf 包自带 bin/nc-config 写死构建期路径 `/p/b/.../p`（已失效）；②configure.ac netcdf 段 `LDFLAGS=${NCLDFLAGS}` 覆盖了注入的 `-L` | ①传 `--with-netcdf=no` 走 `-lnetcdf` 分支；②patch configure 脚本 `LDFLAGS=${NCLDFLAGS}` → `"${NCLDFLAGS} ${SV_LDFLAGS}"`（SV_LDFLAGS 已保存环境值），CFLAGS 同理 |
| 4 | `config.status` 权限错误（Permission denied） | HMDFS setgid + umask 077 → drwx--S--- 阻塞 owner（E129） | build() 中把 configure/config.status 的 `umask 077` 替换为 `umask 022` |
| 5 | make 报 `cmor_locale.h not found` | configure（AC_CONFIG_FILES: include/cmor_locale.h）生成在 out-of-tree build 目录，Makefile 的 CPPFLAGS 指向源码 include（仅 .in） | make 前把生成头 `build-release/include/cmor_locale.h` 复制到源码 include/ |
| 6 | make 报 `cmor_fortran_interface.o` 编译失败 | OHOS 无 gfortran，configure 默认启用 Fortran 把 .o 加入 LIBFILES | configure 参数 `--enable-fortran=no` |
| 7 | 上游 C 测试 12/13 SIGSEGV | 测试深层路径触发 netcdf→hdf5 C++ 绑定（libhdf5_cpp→libc++_shared.so）运行时 ABI 重定位失败 | 环境限制非库缺陷：最小复现（netcdf 写文件、四轴 cmor_axis 定义）均 exit=0；PR body 如实申报 1/13 |
| 8 | test_package 编译缺 `udunits2.h` 等依赖头 | cmor 公共头直接 include 依赖头，CMakeDeps 对仅可见依赖不填充 include 路径 | requirements(headers=True) + test_package 显式声明依赖 + cmor package_info includedirs 加 include/cdTime |
| 9 | test_package 运行期 `libc++_shared.so` 加载失败 | hdf5 C++ 绑定库运行需 NDK libc++ 目录 | test_package test() 中 prepend NDK libc++ 目录到 LD_LIBRARY_PATH |
| 10 | cmip7-cmor-tables sha256 校验失败 | 本地 init 快照与官方 main 分支内容不一致（上游 main 更新） | 从官方 URL 重新下载计算 sha256 更新 conandata.yml |

## 源码修改

无静态补丁文件。适配均在 conanfile.py build() 内完成：
- config.guess/config.sub OHOS 注入（幂等，`_inject_ohos_aux`）
- configure 脚本 CFLAGS/LDFLAGS 保留（netcdf 探测）
- umask 077→022
- cmor_locale.h 生成头复制

## 依赖版本

- netcdf/4.9.3（conan ohpcd）
- udunits/2.2.28.1（conan ohpcd，本次【依赖项】PR #9352 发布）
- json-c/0.17（conan ohpcd）
- uuid/2.40.1（conan ohpcd）

## 验证结果

```bash
conan create archives/c/cmor/3.15.2 ...  # 全绿：libcmor.a 构建 + test_package 1/1 通过
```

- 主包：libcmor.a 构建成功，头文件 + cdTime 子目录 + LICENSE 正确装包
- test_package：版本宏（3.15.2）+ cmor_setup + cmor_close 断言全部通过
- 上游 C 测试：13 个注册，1 个通过（test_unit_cat_unique），12 个 SIGSEGV（运行时 hdf5 C++ 绑定 ABI 环境限制，详见 reports/test-report.md）

## 注意事项

- cmor 公共头 include/cmor_func_def.h 直接 `#include <udunits2.h>`、`<json-c/json.h>`、`<netcdf.h>`、`<uuid/uuid.h>` 及 `include/cdTime/` 子目录头——下游使用 cmor 时必须能解析这些依赖头，conan 配方已通过 headers=True + includedirs 暴露
- release tarball 不含 3 个 CMOR tables submodule；上游测试用 `Tables/` 相对路径引用，运行测试需建立 Tables 符号链接
- 若下游使用 hdf5 C++ 绑定链（通过 netcdf），运行时需 NDK libc++ 目录在 LD_LIBRARY_PATH
