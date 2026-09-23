# unifdef 2.12 适配笔记

## 编译环境
- 构建系统: makefile（上游 2.12 为纯 POSIX Makefile，无 configure）
- 编译日期: 2026-09-17
- 编译器: clang 15（来自 conan profile `tools.build:compiler_executables.c`，设备上为 Harmonybrew OHOS SDK clang）
- 状态: built（conan-verify 全绿，CI release 合入 main 后 upload）

## 编译步骤
```bash
# 探索编译（模式 B）
cd $BUILD_SRC_DIR
make CC=<ohos-clang>                # 产出 unifdef（单文件 C 程序）
make CC=<ohos-clang> test           # 上游 90 例回归：本机 82/90（8 例宿主环境不兼容）
make CC=<ohos-clang> -j1            # 配方内构建命令（R9）

# conan 配方验证
python3 scripts/ohc-run.py conan-verify unifdef 2.12 --profile ohos-aarch64-device
# 内部 conan create 真实执行：
#   build(): make -j1 CC=<conf> + make test（白名单外失败即中止）
#   test_package: bash test_unifdef.sh → 12/12 断言通过（真实执行已安装二进制）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 if1-a~if5-a 共 5 例失败：`fatal error: 'stdio.h' file not found` | `unifdefall` 调用宿主 `cc -E` 预处理 `#include <stdio.h>`；OHOS SDK 交叉 clang 无默认 sysroot | 与 unifdef 本体无关的工具链环境差异；build() 以显式白名单容忍并在 MANIFEST/notes 逐项登记，白名单外失败一律中止构建 |
| 2 | multimissing/multinewline 失败：hunk 头范围与期望不符 | 期望输出内嵌 GNU diff -u 方言；OHOS 自带 toybox diff 对同一改动输出不同 hunk 范围（内容行一致） | 同上，登记为宿主 diff 方言差异（白名单） |
| 3 | outeperm 失败：期望 `Permission denied`，实际 `rmdir: Directory not empty` | HMDFS 不强制 chmod(2) 只读目录语义 | 同上，登记为文件系统语义差异（白名单） |
| 4 | 上游 `make install` 依赖 `install(1)` 且创建软链接 | CI worker PATH 不保证含 install(1)；HMDFS 软链接较脆弱 | `package()` 直接 `copy()` 到 bin/ 与 share/man/man1（unifdefall.1 以副本形式提供），`os.chmod` 0755 |
| 5 | init-build 将无 configure 的 Makefile 项目探测为 autotools，conan-init 模板不适用 | 探测启发式偏差 | 按 `templates/conanfile-makefile.py.tmpl` 与 `archives/n/nq/1.0` 先例手写纯 make 配方；manifest 的 build_system 记为 makefile |
| 6 | CI L2 smoke 以 `--version`/`--help` 探测二进制 | 上游 CLI 仅支持 `-V`/`-h`（`--version` 返回 2）；`-h` 返回 0 且打印 usage | L2 为非阻塞项：unifdef `--version/--help` 无法通过，但 test_package 已实测 `-V`/`-h` 语义；PR 中如实说明 |
| 7 | 上游 Makefile `version.sh::` 双冒号规则每次 make 都会执行 `scripts/reversion.sh` | POSIX/GNU make 对无前置依赖的双冒号规则总执行 | tarball 已含 version.h/version.sh，脚本在无 .git 时直接落到 `[ -f version.h ]` 分支不产生变化；构建日志中无害 |

## 源码修改

无平台宏、无补丁（R8：零 patch，`patches/` 为空 `{}`）。unifdef.c 为 ANSI C + POSIX err.h/getopt，未经修改即可在 OHOS aarch64 编译运行。

## 依赖版本

无（W0 依赖检查：`requires` 为空；纯 C 无第三方库，仅链接系统 libc）。

## 验证结果

```text
# 上游测试（make test / scripts/runtests.sh tests）：82/90 PASS
#   8 例宿主环境不兼容（白名单，逐项原因见 test_package/MANIFEST.yml）：
#     if1-a if2-a if3-a if4-a if5-a  （宿主 cc -E 无 sysroot，缺 libc 头）
#     multimissing multinewline       （GNU diff -u vs toybox diff 方言）
#     outeperm                        （HMDFS 不强制 chmod）
# test_package 功能测试（sh test_unifdef.sh）：12/12 PASS
1..12
ok - -V prints the unifdef-2.12 banner
ok - -h prints usage
ok - -DFOO keeps the #ifdef branch
ok - -UFOO keeps the #else branch
ok - exit status 1 when output changes
ok - exit status 0 when input is unchanged
ok - -s lists the control symbol FOO
ok - nested #ifndef kept with only OUTER defined
ok - nested #ifndef removed with OUTER and INNER defined
ok - -m modifies in place
ok - -M~ leaves a backup file
ok - unifdefall wrapper is installed and executable
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/unifdef | 主程序（arm64 ELF） |
| bin/unifdefall | 包装脚本（POSIX sh） |
| share/man/man1/unifdef.1 | man 手册 |
| share/man/man1/unifdefall.1 | man 手册（unifdef.1 副本，替代上游软链接） |

## 注意事项

- 产物为可执行命令，已在软件级 `archives/u/unifdef/commands.json` 声明（R38）。
- unifdef 的退出码是有语义的：0=输出与输入一致，1=输出有变化，2=错误；test_package 已覆盖 0/1 两种路径，脚本使用时需注意 `set -e` 下 rc=1 属正常结果。
- `unifdefall` 依赖宿主存在可用的 C 预处理器（`cc -E`）与 `sort`/`sed`；OHOS 设备上该包装脚本功能受限（与上游用例 if*-a 相同的根因），主程序 `unifdef` 不受影响。
- 上游测试全部保留（未改一例），白名单仅作用于构建脚本的环境容忍逻辑，CI 中若这些用例转为通过不受影响；白名单外任何失败都会使 `conan create` 失败。
---

**编译结束**: 2026-09-17 15:29
**最终状态**: built
