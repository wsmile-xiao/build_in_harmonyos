# wmrack 1.4 适配笔记

## 编译环境
- 构建系统: autotools（GNU Autoconf 2.61 生成，configure.in 手工维护）
- 编译日期: 2026-09-27
- 编译器: clang/clang++（ohos-sdk 26.0.0.18 native llvm，clang 15）
- 状态: built

## 编译步骤

1. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
   - 配方内 `build()` 依次执行：应用 2 个 portability 补丁 → 恢复 autotools 脚本可执行位（E490）→ 放宽 configure 临时目录 umask（E114/E011）→ `./configure --prefix=<pkg> --x-includes=<libx11>/include --x-libraries=<libx11>/lib --host=aarch64-linux-ohos` → `make -j1 standart.style wmrack`（E074 强制单线程）→ `make -j1 install`（prefix 直指 package_folder，Makefile 不支持 DESTDIR）
2. 关键点：`AC_PATH_X` 在交叉编译下探测不到 Conan 包内的 X11，必须用 `--x-includes/--x-libraries` 显式注入；Makefile 生成的链接行不含 `$(LDFLAGS)`，`-L` 搜索路径须经 `LIBS` 变量注入（`AutotoolsDeps.environment` 追加）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: WMRack needs X Windows!!!` | AC_PATH_X 无法探测 Conan 包内 X11 | `--x-includes/--x-libraries` 显式指向 libx11 包（ref: kic 2.4c 先例） |
| 2 | `ld.lld: unable to find library -lXpm/-lXext` | Makefile 链接行不含 -L 搜索路径 | `LIBS` 注入依赖包 libdir |
| 3 | `time()` 隐式声明返回 int，arm64 64 位 time_t 截断 | wmrack.c 缺 `<time.h>` | 补丁 0001 补 include |
| 4 | `%02d`/`%s` varargs 传结构体/指针数组（UB） | wmrack.c 对 TrackInfo/sscanf 用法错误 | 补丁 0001 传 `.num` 字段与 `char[]` |
| 5 | `-Wformat-security` 告警 | `fprintf(stderr, buffer)` 非字面格式串 | 补丁 0002 改为 `fprintf(stderr, "%s", buffer)` |
| 6 | configure 临时目录不可写（`drwx--S---`） | `umask 077 && mktemp -d` 在 HMDFS 上产生 setgid 目录（E114/E011） | build() 内将两处 `umask 077` 改写为 `umask 022` |
| 7 | autotools 脚本可执行位丢失 | HMDFS 适配路径保留内容不保留 mode（E490） | build() 内对 configure/install-sh 幂等 chmod +x 并自校验 |

## 源码修改

- `patches/0001-wmrack.c.patch`：补 `#include <time.h>`；`static flash` 补 `int`；`sprintf %02d` 改传 `TrackInfo.num`；`sscanf %s` 改传 `char[]`
- `patches/0002-xpmicon.c.patch`：`fprintf(stderr, buffer)` → `fprintf(stderr, "%s", buffer)`

## 依赖版本

- libx11/6.4.0（直接依赖，X11 核心库）
- libxpm/3.5.17（XPM 图标加载）
- libxext/6.4.0.1（X11 Shape 扩展）
- xorgproto/2025.1（X11 头文件：Xfuncproto.h 等）
- 传递依赖：libxcb/1.16、libxau/1.0.11、libxdmcp/1.1.5、xtrans/1.6.0

## 验证结果

```bash
# conan-verify 全门禁通过（G0-G4 + L2/L4/L5）
$ python3 scripts/ohc-run.py conan-verify wmrack 1.4   # Verdict: PASS
# 消费者用例（test_package/test.sh，7 组约 19 断言）
$ bash test.sh
OK: AArch64 ELF64 executable (96704 bytes)
OK: DT_NEEDED -> libX11.so.6 / libXpm.so.4 / libXext.so.6
OK: compiled-in default (grey) style -> "296 11 4 1"
OK: --help banner + usage, exit status 1
OK: reached the mixer stage — Xpm/X11/Xext chain resolved
ALL CONSUMER TESTS PASSED
# 上游无自动化测试（无 tests/、无 AC_CONFIG_TESTDIR、Makefile 无 check/test），已清点记录
```

## 注意事项

- wmrack 是 Window Maker dock applet，运行需 X server；OHOS 无 X server，消费者用例以"运行至设备探测阶段"验证动态链完整性
- Makefile 不支持 DESTDIR（R20），conanfile 以 `--prefix=<package_folder>` 直接安装
- `make -j1`（E074）；默认构建目标含 `standart.style`（XPM/ 符号链接，编译期写死 grey.style 几何参数）
---
**编译结束**: 2026-09-27 17:38
**最终状态**: built

### 对话 #1
- **日期**: 2026-09-27
- **内容**: 完成源码核验（官方 SourceForge 源，sha256 复算一致）、OHOS 交叉编译适配（X11 探测补偿、LIBS 注入、E490/E114/E074 三项平台修复、2 个 portability 补丁）、真实构建与 conan create、上游测试清点（无自动化测试）、7 组鸿蒙消费者用例、conan-verify 全门禁与 finish 管线。提交前只读审计发现 4 项阻塞（JC full 模式误报、.ci-result.json 缺失、G0 环境问题、留档日志被覆盖），经 commit 后增量验证与本地环境修正全部闭环。
- **结论**: wmrack 1.4 适配完成，状态 built，等待平台 CI 验证。
---

**编译结束**: 2026-09-27 17:49
**最终状态**: built
