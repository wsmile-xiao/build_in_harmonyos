# libm17n-flt 1.8.6 适配笔记

## 定位
- 上游 m17n-lib 1.8.6（savannah 官方 tarball），m17n 字体布局表库
- 构建系统: autotools（configure.ac），同一 tarball 产出 libm17n-flt / libm17n-core / libm17n
- 本包以 libm17n-flt 命名，随包安装三库（FLT 依赖 core/m17n）

## 编译环境
- 构建系统: autotools（官方 release tarball 含预生成 configure）
- 编译器: clang/clang++（OHOS aarch64）
- 状态: built（conan create 全流程通过，消费者 11 codings）

## 构建要点
- 显式 `--build/--host=aarch64-unknown-linux-ohos`（config.guess 无法识别 HarmonyOS）
- `--disable-nls`：跳过内置 gettext intl 子目录（`lock.h` 的 `#pragma weak pthread_cancel` 在 OHOS musl 无该符号致编译失败）
- `--disable-gui --without-libotf --without-fontconfig --without-gd`：禁用可选重依赖（X11/OTF/freetype/fontconfig）
- 0001 patch：configure config.status 临时目录 `umask 077→022`（OHOS 沙箱 0700 目录不可写，librrd 先例）

## 测试
- 上游无自动化测试套件（无 make check 目标）
- test_package 消费者 4 断言：m17n_init + m17n_init_flt + mconv_list_codings（11 codings）+ m17n_fini_flt + m17n_fini 生命周期 roundtrip

## 遇到的问题与解决方案
| # | 问题 | 解决方案 |
|---|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 显式 --build/--host=aarch64-unknown-linux-ohos |
| 2 | 内置 gettext intl 编译失败（pthread_cancel） | --disable-nls 跳过 |
| 3 | config.status 临时目录 Permission denied | 0001 patch：umask 077→022 |
| 4 | 链接 undefined symbol | 符号三库分散，package_info libs 三者全链（flt/core/m17n） |
| 5 | mconv_list_codings(NULL) 段错误 | 消费者用例传合法 MSymbol** 缓冲 |
| 6 | M17N_INIT() 宏编译失败 | 直接用四个生命周期函数（不依赖 merror_code/MERROR_NONE） |

## 验证
- 本地 `conan create . --profile=ohos-aarch64`：`test_m17n_flt: OK (m17n init/flt/list/fini roundtrip, 11 codings)`
