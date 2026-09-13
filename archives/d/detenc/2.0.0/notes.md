# detenc 2.0.0 适配笔记

## 基本信息
- 上游: https://github.com/reevoo/detenc （tag v2.0.0）
- 许可证: MIT（tarball 内 COPYING）
- 构建系统: 纯 Makefile（根 Makefile + src/Makefile，无 configure/cmake）
- 编译器: /data/service/hnp/bin/clang（OHOS aarch64）
- 状态: built（上游测试全量通过）

## 上游结构与产物
- `src/`：4 个 C 源文件（detenc.c、libdetenc.c、one_byte_detector.c、utf8_detector.c），
  仅依赖 stdio/string/unistd；零第三方依赖，无平台探测、无特殊 syscall。
- `src/usage.inc` 由 `sed 's/^/"/;s/$$/\\n"/' < usage.txt` 生成（toybox sed 兼容）。
- 产物：单二进制 `bin/detenc`。
- `test/`：Ruby minitest 套件，根 Makefile `check` 目标 = 构建 + `cd test && rake test`；
  测试经 `../bin/detenc -q <tempfile>` 驱动（7 个 test_*.rb + test_helper.rb，rake pattern test_*.rb 全量加载 8 个文件）。

## 编译与测试要点

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `CC = gcc` 无法用环境变量覆盖 | Makefile 内赋值优先于环境变量（make 命令行变量才优先于 Makefile 赋值） | build() 以命令行变量 `CC="{cc}"` 传 clang（cc 取自 `tools.build:compiler_executables`，R33） |
| 2 | 上游 CFLAGS 仅 `-Wall` | 上游默认无优化 | 命令行补 `CFLAGS="-Wall -O2"`；产物为可执行文件，无需 -fPIC |
| 3 | 测试文件 `MiniTest::Test` 报 `uninitialized constant MiniTest (NameError)` | minitest 5.x 移除了 `MiniTest` 兼容别名（设备 ruby 3.4.5 内置 minitest 5.25.4） | 补丁 0001 将 7 个 test_*.rb 中的 `MiniTest::Test` 改为 `Minitest::Test`（同 Alpine APKBUILD 思路） |
| 4 | Ruby Tempfile 需可写 TMPDIR | OHOS /tmp 只读（E002） | build() 中 `TMPDIR=<conan build 目录> make check ...` |

## 上游测试结果（设备实跑）

```
$ make check CC=clang CFLAGS="-Wall -O2" -j1
...（rake test）
Finished in 7.29s, 5.89 runs/s, 45.79 assertions/s.

43 runs, 334 assertions, 0 failures, 0 errors, 0 skips
```

- 口径：上游 minitest 全量（rake test 扫描全部 test_*.rb），无 skip/disable。
- 未打补丁时的失败证据：`test_bom_detection.rb:3: uninitialized constant MiniTest (NameError)`。

## test_package 冒烟
- `detenc -v` → `detenc: version 2.0.0`
- 检测断言（复用上游 test/inputs 样本）：
  - ASCII 样本 → US-ASCII
  - latin1.txt（`H\xe2ll\xf6`）→ ISO-8859-15
  - utf16be.txt → UTF-16BE
  - utf16le.txt → UTF-16LE
  - utf8bom.txt → UTF-8

## 验证结果
- `detenc -v`：`detenc: version 2.0.0`
- `detenc -q` 对上游 4 个输入文件的检测结果与上游测试期望一致。
