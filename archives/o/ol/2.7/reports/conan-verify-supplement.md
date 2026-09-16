# ol 2.7 — conan-verify 人工补测（G4 / L2 / L4 / L5）

`conan-verify` 在 `--user=ohpcd --channel=stable` 形态下解析 package_id 失败，G4 报
「⚠️ 无法找到程序包 ID」、L2/L4/L5 报「⏭️ 跳过（无 cache 路径）」，而报告仍打印
`✅ PASS`（工具文案缺陷，以跳过行为准）。本文件按「先取产物清单、再实测消费者」
口径补齐这四项证据。**包目录用 glob 定位**（分片目录名 `p/b/<名前缀><hash>` 每轮
清缓存重建都换名，写死目录名下一轮即不可复核）。

```sh
PKG=$(ls -d "${CONAN_HOME:-$HOME/.conan2}"/p/*/ol*/p | head -1)
```

## G4：产物清单 ↔ `package_info()`

- 命令：`find "$PKG" -type f | sed "s|$PKG/||" | sort`
- 结果：**282 个文件**（含 conan 元数据 `conaninfo.txt`/`conanmanifest.txt` 两个）
  - `bin/`：2（`ol`、`olvm`）↔ `cpp_info.bindirs = ["bin"]`
  - `lib/`：1 个共享库（`libol.so`，带 `DT_SONAME=libol.so`）+ 273 个 `lib/ol/**`
    （Ol 标准库 `.scm`/`.lisp`、`repl` fasl、`Gtk/README.md` 等上游随包数据）
    ↔ `cpp_info.libdirs = ["lib"]`
  - `include/ol/`：2（`ol.h`、`vm.h`）↔ `cpp_info.includedirs = ["include"]`、
    `cpp_info.libs = ["ol"]`
  - `share/man/man1/ol.1.gz`：1
  - `licenses/LICENSE`：1
- 即 280 个交付产物 + 2 个 conan 元数据，无多余目录、无缺失目录。

## L2：平台功能实测（真实命令）

| 命令 | 输出（首行） | 退出码 |
|------|--------------|--------|
| `"$PKG/bin/ol" --version` | `ol (Otus Lisp) 2.7` | 0 |
| `"$PKG/bin/olvm" --version` | `olvm (Otus Lisp Virtual Machine) 2.7` | 0 |
| `OL_HOME="$PKG/lib/ol" "$PKG/bin/ol" consumer.scm` | `42` | 0 |

`consumer.scm` 内容为 `(import (owl math))` + `(print (* 6 7))`，即同时覆盖
「解释器可执行」与「运行期经 `OL_HOME` 找到包内标准库」。`bin/olvm` 是上游
`strip` 后重新签名的可执行文件（未重签前实测 rc=126 `Operation not permitted`）。

## L4：静态安全属性（`llvm-readelf -h -lW -dW`）

| 产物 | Type | GNU_STACK | GNU_RELRO | BIND_NOW | `.codesign` | DT_SONAME |
|------|------|-----------|-----------|----------|-------------|-----------|
| `bin/ol` | DYN (PIE) | RW（NX） | 存在（partial） | 无 | 1 个段 | —（可执行文件） |
| `bin/olvm` | DYN (PIE) | RW（NX） | 存在（partial） | 无 | 1 个段 | —（可执行文件） |
| `lib/libol.so` | DYN | RW（NX） | 存在（partial） | 无 | 1 个段 | `libol.so` |

PIE + NX + RELRO 均满足；`BIND_NOW`（full RELRO）由上游链接参数决定，不构成本包缺陷。
`lib/libol.so` 的 `DT_SONAME=libol.so` 由补丁 `0001-GNUmakefile.patch` 添加，
`bin/` 下两个可执行文件带有效 `.codesign`（鸿蒙内核要求）。

## L5：产物 sha256 基线与跨轮可复现性

同提交、不同缓存目录的两次独立构建（第二次为复现性探针，recipe 仅把 `build()` 末尾的
上游测试调用换成 no-op，`build()`/`package()` 的编译与打包代码逐字节相同，
**两份都带同一个 SONAME 补丁**）：

| 产物 | 两轮 sha256 |
|------|-------------|
| `bin/ol` | `b6b512d36028b655c3474210b59072eeea29ae1e624c01e256f33eb2f01c459c` |
| `bin/olvm` | `977d9acea6c4efe374821b394707c6d93ba2616602c803285c738056d445a6c3` |
| `lib/libol.so` | `43be8686bb423079374d0be9c7aaf07497c5d470d967a511a2ed6a4c65489771` |
| `include/ol/ol.h` | `023f010d1473668c2f0a9aaf9a05c22ecb3903cc0a1cea9ae62cdeef69642242` |
| `include/ol/vm.h` | `c619e475bd747932f68b62aea17996f1ccaf49dc15c9093649b83b9e58044a3f` |
| `share/man/man1/ol.1.gz` | `3a9987ee1b1f7dfa33e03f9b03bbdce93bc940fcb287330f8b49b5d7a94a5f71` |
| `licenses/LICENSE` | `55b59ad136116d632354d8921fb9023aeacbda3345c7ae3ff8516d95ff97f38a` |

- 交付产物清单逐文件 `diff` 无差异：两轮均为 **280 个文件**。
- 包内容聚合（排除 `conaninfo.txt`/`conanmanifest.txt`，命令在包目录内用相对路径）：
  两轮均为 `19358458ce1fdd468f84194715d4c4fe21f413eead873ff7434e00cc54afd09e`：

  ```sh
  cd "$PKG" && find . -type f ! -name conaninfo.txt ! -name conanmanifest.txt \
    | sed 's|^\./||' | sort | xargs sha256sum | sha256sum
  ```

- 第四次独立构建（把上游测试改为四组并行编排后重建，cache 已清空）产物与上表
  仍逐字节相同（聚合 `19358458…afd09e`、280 文件）——编排只改变测试执行顺序/并行度，
  不改变任何制品字节。
- 第三次独立构建（修 `conanfile.py` 的解析/签名/license 后重建，cache 已清空）产物与上表
  逐字节相同：包内容聚合仍为 `19358458ce1fdd468f84194715d4c4fe21f413eead873ff7434e00cc54afd09e`，
  交付产物清单仍为 280 文件——说明该轮改动只影响申报与校验逻辑，不改变任何制品字节。
- 采信轮 `make check` 汇总行为
  `rc=0 group_rcs={'language-tests': 0, 'rosettacode-tests': 0, 'ffi-tests': 0, 'check-reference': 0} groups=5 test_rows=211 result_rows=210 fail_rows=0 ok_cells=210 unrun=['tests/fasl-binary.bin']`
  （并行编排后配方汇总行新增 `group_rcs`，逐组 RC 全部为 0；旧串行编排的同口径汇总为
  `rc=0 groups=5 test_rows=211 result_rows=210 fail_rows=0 ok_cells=210 unrun=['tests/fasl-binary.bin']`）
  （测试名行 211 / 结果行 210，未执行的 1 例即上游默认不执行的 `tests/fasl-binary.bin`）。
- 复现性探针的那份 recipe 修订已从本地缓存删除（`conan remove
  "ol/2.7@ohpcd/stable#<probe-rrev>" -c`），缓存中只保留采信轮修订；本表数据来自
  删除前的实测比对。

## 上游测试编排（不减少覆盖）

**最终编排（第二版：独立源码树副本 + HAVE_* 预置）**

第一版「同一棵树里四组并发」在 CI #46152 上暴露出并发竞态：`group_rcs={'ffi-tests': 2}`、
`groups=3`、`test_rows=195`（ffi 组在打印自己的分组头之前就以 make rc=2 退出），
四个并发 make 实例共享 `tmp/`、`ol`/`olvm`、`tests/ffi/src.inc` 等中间产物。
最终版改为：**每组复制一份已构建的源码树副本**（`../ol-test-<group>`），在副本里并行执行，
从根上消除共享状态；同时在命令行预置 `HAVE_SOCKETS/HAVE_DLOPEN/HAVE_SECCOMP/HAVE_MEMFD_CREATE=1`
（`configure.mk` 用 `?=`，预置后每次子 make 省掉 5 次 clang 特性探测）。
配方在任一组 RC 非零时会把该组日志尾部打到 stdout，便于 CI 日志直接定位。

**计时证据（本机设备，编排改动前后各测一次）**：

- 串行 `make check`（改动前）：设备实测约 25-30 分钟（`finish` 内嵌 W3 的完整轮 12:21→12:56）；
  CI #45856（worker CI-020）上 `conan create` 到 3600s 上限仍未跑完（日志尾
  `[fail] ol/2.7 — conan create TIMED OUT after 3600s`，此时 `make release` 四目标已全部构建成功）。
- 同一棵树四组并行（第一版）：`$HOME/tmp/ol-2.7/perf/p-*.log` 实测四组同时跑完约 9-10 分钟
  （language 61 ok / rosetta 112 ok / ffi 16 ok / reference 21 ok，0 fail）。
- 独立副本并行 + HAVE_* 预置（最终版）：采信轮 `conan-verify` 整轮（构建 + 420 次用例执行 +
  test_package）实测约 5.5 分钟（20:56:39→21:02:19），汇总行 `rc=0`、四组 RC 全 0、
  `test_rows=211 result_rows=210 fail_rows=0`。


上游 `make check` 由四个分组构成。串行执行在 CI worker 上超过 `conan create` 的 3600s 上限
（CI #45856 实测 `conan create TIMED OUT after 3600s`，此时 `make release` four 目标已全部构建成功）。
配方改为：先串行 `make olvm-binaries` 建两个 olvm 变体，再四组并行
（`language-tests` / `rosettacode-tests` / `ffi-tests` / `check-reference`，各组自身仍 `-j1`），
逐组落盘后按固定顺序拼接为 `upstream-check.log`。**用例集合与串行 `make check` 完全一致**
（不抽样、不减 debug/release 变体），设备墙钟由约 25-30 分钟降到约 10 分钟。

## W3 质量门禁（SONAME）

`finish` 内嵌的本地 CI 模拟（`ci/conan/build_and_test.sh`，`--build=ol/*` 强制重建）
另有 `conan-verify` 不执行的 L5a SONAME 门禁。加 `0001-GNUmakefile.patch` 之前实测
`[fail] L5a: libol.so 缺少 DT_SONAME`（`L5_RESULT=fail: soname_gate_failed`）；
补 `-Wl,-soname,libol.so` 后该门禁通过，`llvm-readelf -dW libol.so` 见
`SONAME Library soname: [libol.so]`。

## 结论

- 上游测试：清点 211 例、实际运行 210/210（100%），逐字日志见 `reports/upstream-check-log.md`；
  `tests/fasl-binary.bin` 属上游默认不执行（`extras/check.mk` 的 `%.bin.ok` 规则被注释、`tmp/check.log` 无记录），单列不冒充通过。
- 消费者验证：3/3（100%）——`test_package` 的 `embed_test`（C 消费者，`<ol/ol.h>`
  嵌入 API 5 断言）、`harness.scm`（`bin/ol` 解释器 7 断言）、`olvm --version`。
- 四项自动跳过项（G4/L2/L4/L5）已按上表全部人工补齐：G4 产物完整、
  L2 真实可运行、L4 安全属性与 SONAME 达标、L5 两轮逐字节可复现。
