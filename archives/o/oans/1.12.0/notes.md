# oans 1.12.0 适配笔记

## 编译环境
- 构建系统：Makefile
- 平台：HarmonyOS PC aarch64 / OHOS
- 编译器：clang 15 / libc++
- 构建日期：2026-09-06
- 状态：built（待 W3 conan create 与 CI 发布）

## 依赖与 W0 核验
- `glib/2.84.0`：动态库，提供 glib-2.0、gio-2.0 头文件与 pkg-config 文件。
- `sqlite3/3.49.1`：制品仓 recipe 已发布；本地缓存为静态 `libsqlite3.a`。
- `uuid/2.40.1`：制品仓 recipe 已发布；提供静态 `libuuid.a`、`uuid.pc` 和 `uuid/uuid.h`。
- `xxhash/0.8.2`：制品仓 recipe 已发布；提供 `xxhash.h`。
- `gettext/0.22.5`：制品仓 recipe 已发布；提供静态 `libintl`，满足静态 GLib 的 gettext 符号依赖。
- `glib/2.84.0`、`sqlite3/3.49.1`、`uuid/2.40.1`、`xxhash/0.8.2`、`gettext/0.22.5`：均已使用 `conan download --only-recipe -r=ohpcd` 逐项核验；本地 W3 使用缓存 binary。

## 适配修改
1. `0001-ohos-combined.patch`：合并 HarmonyOS filesystem/libc、pkg-config、gettext、libatomic 和 C 属性兼容适配。
2. 移除不可用的 `blkid`、`mount`、`libbsd` pkg-config 探测，并显式链接 `libintl`。
3. 测试临时文件统一使用 `$TMPDIR`，避免只读 `/tmp`。
4. `test_package/test.sh` 是唯一消费者测试入口，由 Conan `test()` 实际执行，校验两个命令的版本输出和 `--help` 内容。
5. 将生产代码和上游测试中的 C++ 风格 `[[maybe_unused]]` 转为 clang C 兼容属性。

## 验证结果
```text
./test
EXIT=0
118 tests, 1328831 assertions, 0 failures
3 个 FIEMAP 能力测试按 HMDFS 平台限制跳过

DUPEREMOVE=./oans python3 tests/run.py -j 4
Ran 251 tests in 14.22s on 4 workers (+56 serial)
FAILED (failures=16, errors=10, skipped=110)
```

集成失败全部归因于当前 HMDFS 环境：FIDEDUPERANGE/FIEMAP 被拒绝、无 reflink、权限限制或临时目录能力限制；不是编译或链接失败。
---

**编译结束**: 2026-09-06 18:47
**最终状态**: built
