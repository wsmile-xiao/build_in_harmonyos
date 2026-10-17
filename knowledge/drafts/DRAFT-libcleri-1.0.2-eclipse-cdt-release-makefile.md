# DRAFT: Eclipse-CDT makefile 工程适配（无 configure / Release/ 子目录构建）

- **Software**: libcleri 1.0.2（https://github.com/cesbit/libcleri，tag v1.0.2）
- **Date**: 2026-09-06
- **Status**: UNMATCHED — 待人工/AI 审核后 promote 为 E-entry
- **Knowledge decision**: new_draft（路径 B）

## 问题

libcleri 是 Eclipse-CDT managed-build 生成的 C 工程。tarball 根层只有 `src/`、`inc/`、
`test/`、`makefile.init`、`makefile.targets` 与 `Release/` 子目录，**没有根 makefile 与
configure**。bootstrap 阶段 `init-build` 的"嵌套源码检测"把 `Release/` 误判为源码根并
提升，导致 `.orig`/`.work` 缺少真正的 `src/*.c` —— 后续 `lang-preflight` 报
"无源文件可统计"，**误写 `env_unsupported` 终态**；`conan-init` 也按 autotools 生成
configure 模板，与实际 Eclipse makefile 工程不符。

## 根因

1. Eclipse-CDT managed-build 把可构建 makefile 放在 `Release/`（Eclipse 构建输出目录），
   `Release/subdir.mk` 引用 `../src/*.c`，即源文件在 tarball 根层 `src/`。
2. `init-build` 的嵌套源码提升逻辑见首个目录就抬升，未识别"首个目录仅含构建脚手架"，
   于是 `.orig`/`.work` 只剩 `Release/` 内容（makefile/objects.mk/sources.mk/subdir.mk）。
3. 误提升使源码统计为 0 → R47 语言预检按"无源文件"判定并写终态，属工具误判而非真实语言不匹配。

## 方案

1. 修复源码树：从 tarball 根层重建 `.orig`/`.work`（`tar -xzf <tarball> -C .orig --strip-components=1`，
   再 `cp -a` 到 `.work`），保留 `.tarball-sha256` 审计。
2. 用正确源码树重跑 `lang-preflight`（判定 c→cpp 兼容族，exit 0）。
3. 构建：`cd Release && make all CC=clang CFLAGS="-DNDEBUG -I../inc -I<dep_inc> -O3 ... -fPIC" LDFLAGS="-L<dep_lib>"`；
   libcleri 依赖 `-lpcre2-8`，需注入 pcre2 的 include/lib（来自 conan 依赖 cpp_info）。
4. conanfile.py 用 `layout()` 声明 `folders.source="." / build="."`，build() 里
   `self.run("make all ...", cwd="Release")`，package() 手工复制 `.so`（含版本化 SONAME 软链）
   与 `inc/cleri/*.h`。
5. 识别特征备忘：根目录无 makefile/configure、存在 `Release/` + `makefile.init` +
   `makefile.targets` + `objects.mk`/`sources.mk` 的工程即 Eclipse-CDT 型。

## 验证

- 重建后 `lang-preflight`：`detected_language=c`，源文件 50（c:50, bash:1），主体占比 100%。
- `cd Release && make all CC=clang` → exit 0，产出 `libcleri.so`（SONAME `libcleri.so.1`）。
- 上游测试 `test/test.sh`（15 个 test_* 目录，179 断言）→ exit 0。
- `conan-verify` G2（conan create + test_package）→ PASS，G3/G4/L2/L4/L5 全过。
- 日志与 SHA-256：见任务最终报告（upstream-test log、conan-create.log）。

## 适用边界

- **适用**：Eclipse-CDT managed-build 工程；凡根层无 configure/makefile、构建文件在
  `Release/`（或类似输出目录）、`subdir.mk` 引用相对 `../src/` 的 C/C++ 库。
- **不适用**：标准 autotools/cmake/meson 工程（嵌套源码提升行为正常）；纯源码根目录
  即构建目录的普通 makefile 工程（无嵌套误判）。

## 反例 / 限制

- 若 tarball 根层确实只有一个真实源码目录，init-build 的提升行为是正确的，不应绕过。
- 重建 `.orig`/`.work` 后必须重跑 lang-preflight 与基线指纹校验，不能沿用误判时的
  env_unsupported 终态（本次已通过正确源码树复跑覆盖）。
- Eclipse-CDT 工程的 `install` 目标（makefile.targets）写死 `/usr` 等系统路径，
  配方不得直接调用 `make install`，必须手工 package() 控制打包范围。

## 关联

- SONAME 版本化软链打包：等价命中 E274（create-soname-symlink），本任务配方
  `package()` 已按该条目实现 `libcleri.so.1`/`libcleri.so.1.0.2` 软链，走路径 A。
- 公共头文件传递依赖 include（`regex.h` 内 `#include <pcre2.h>`）：修复方向与 E216
  （explicit-link-aggregate-target）一致，test_package 显式 `find_package(pcre2)` +
  `target_link_libraries(pcre2::pcre2)`，走路径 A。