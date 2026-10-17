# pgdbf 0.6.2 适配笔记

## 编译环境
- 构建系统: autotools (2012 configure + Makefile.in，无需 autoreconf)
- 编译日期: 2026-09-04
- 编译器: clang 15.0.4 (OHOS SDK, target aarch64-unknown-linux-ohos)
- profile: ci/conan/profiles/ohos-aarch64 (os=OHOS, arch=armv8, build=host)
- 状态: built（conan-verify 通过，未上传制品）

## 编译步骤

conan create 等价步骤（在 BUILD_SRC_DIR 手工复现验证）：
1. `./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu --prefix=<prefix>`
2. `make -j1`
3. `make install DESTDIR=<stage>`
4. 功能验证：用样例 dBase III 文件跑 `pgdbf`，检查生成 SQL；`pgdbf -s LATIN1` 验证 iconv。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type; you must specify one` | 上游 config.guess(2012) 无法识别 `uname -s=HarmonyOS`/HongMeng Kernel | recipe generate() 显式传 `--build/--host=aarch64-unknown-linux-gnu`（config.sub 2012 已支持该 triplet；同 a52dec 先例） |
| 2 | configure/config.status 写私有临时目录 confXXXXXX 时 Permission denied / could not setup config files machinery | hmdfs 下 `(umask 077 && mktemp -d)` 建出 `drwx--S---` 不可写目录 | recipe build() 内将 configure 文本 `umask 077`→`umask 022`（同 ssmtp/abnfgen 先例，本地验证过该两行替换） |
| 3 | test_package 中 `grep 'Caf.*\t42'` 匹配失败 | conan test 环境使用 /system/bin/grep(toybox)，UTF-8 模式下 `.` 不跨非 UTF-8 字节 0xE9 | 测试断言改为 ASCII-safe：默认输出只断言 `^Caf`，内容断言放到 `-s LATIN1` 的合法 UTF-8 输出上 |

## 源码修改

无 patches（patches/ 为空）。两处平台适配均在 recipe 内完成：
- conanfile.py generate(): --build/--host triplet
- conanfile.py build(): _patch_configure_umask()（umask 077→022）

## 依赖版本

无外部依赖（仅 libc/iconv，由 OHOS SDK sysroot 提供，configure 检测 HAVE_ICONV=1）。

## 验证结果

- `conan create`（含 test_package）: 通过
- `ohc-run.py conan-verify`: 通过（G0-G4 + L2/L4/L5 全 PASS）
- 上游自动化测试: 无（make check 为空转，见 test_package/MANIFEST.yml）
- 功能断言: 3 项通过（CREATE TABLE / 数据行 / iconv LATIN1→UTF-8 "Café"）

## 交付物

| 文件 | 说明 |
|------|------|
| bin/pgdbf | ELF aarch64 可执行（动态链接 ld-musl-aarch64） |
| share/man/man1/pgdbf.1 | man page |
| share/doc/pgdbf/README | README |

## 注意事项

- license 为 GPL-3.0-or-later（usage 帮助文本声明 GPLv3+）。
- 命令行工具 → 软件级已建 commands.json (type=tool)。
- conan test 运行环境 grep 为 toybox，测试脚本断言需避免跨非 UTF-8 字节正则。
---

**编译结束**: 2026-09-04 10:35
**最终状态**: built
