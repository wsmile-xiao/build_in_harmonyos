# tdb 1.4.15 适配笔记

## 编译环境

- 构建系统: Samba waf（wafsamba；`configure` + `Makefile` 包装，内部调用 `buildtools/bin/waf`）
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4（OHOS SDK，aarch64-linux-ohos / musl）
- 驱动: python3 3.14.7（waf 需要；`configure` 包装脚本读取 `$PYTHON`）
- 状态: built（conan-verify 通过，未 upload）

## 编译步骤

```sh
# 1) 解包后进入源码目录（conan source() 已 strip_root）
export PYTHON=python3

# 2) 配置（本包禁用可选 python 绑定；理由见下）
./configure --prefix=<package_folder> --disable-python

# 3) 构建（并行度取 conan tools.build:jobs，默认 2）
make -j2

# 4) 上游测试（conanfile.py build() 内嵌执行）
make test

# 5) 安装（waf install 到 package_folder）
make install
```

`make test`（waf `testonly`）实际执行内容：2 个 shell 集成测试
（`test_tdbbackup.sh`、`test_tdbdump.sh`）→ 37 个 TAP 单元测试
（`wscript` 的 `tdb1_unit_tests` 列表）→ `tdbtorture` 多进程压力测试。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./configure` 在 `Checking for HAVE_SECURE_MKSTEMP` 处直接中断（`The configuration failed`） | `lib/replace/wscript` 的 mkstemp 运行探针硬编码 `/tmp/test.XXXXXX` 并断言文件权限为 0600；鸿蒙 `/tmp` 只读（E002），且 HMDFS 将文件权限归一化为 0640（chmod 不生效，E046），探针**必然失败**，而上游在该检查上标了 `mandatory=True`（源码注释 "lets see if we get a mandatory failure for this one"） | 补丁 0001：`mandatory=True` → `mandatory=False`。检查仍会运行并如实报告 `not found`，lib/replace 自动编译内置 mkstemp 替代实现（`REPLACE_MKSTEMP`） |
| 2 | 默认（启用 python 绑定）时 `configure` 在 `Testing pyembed configuration` 处中断 | `python3-config --cflags --libs --ldflags --embed` 输出含 `-lintl`，而 OHOS/musl 无 libintl（`Checking for library intl : no`），pyembed 探针链接失败（`ld.lld: unable to find library -lintl`）；waf 的该探针为 fatal | 本包定位为纯 C 库，使用官方 `--disable-python` 关闭可选绑定（并避免包与构建机 python ABI 耦合） |
| 3 | `--disable-python` 后 `make test` 仍然失败（`Python test failed: PYTHONPATH=bin/python python3 python/tests/simple.py`） | `SAMBA_CHECK_PYTHON` 即使在 `--disable-python` 下仍会把 `python3` 记入 `python_interpreters`，`testonly` 无条件调用 `RUN_PYTHON_TESTS`，而 pytdb 未构建导致 `import tdb` 失败 | 补丁 0002：`wscript` 的 `testonly` 在 `env.disable_python` 时显式跳过 python 测试并打印原因（C 测试全部保留运行） |
| 4 | robust mutex 相关 | musl 未实现 `pthread_mutexattr_setrobust`（未声明），`lib/replace` 的 `HAVE_PTHREAD_MUTEXATTR_SETROBUST` 检测为否 | 无需补丁：`wscript` 自动跳过 `USE_TDB_MUTEX_LOCKING`；37 个单测（含 mutex 系列）在无 robust mutex 模式下全部通过 |

### 已排除的尝试（如实记录）

- 将探针临时目录从 `/tmp` 改为构建目录：仍因 HMDFS 权限归一化（0640 ≠ 0600）失败；
  探针的语义是"系统 mkstemp 是否安全（0600）"，在 HMDFS 上不可满足，故采
  非致命 + 内置替代实现，而非放宽断言。
- 启用 python 绑定并以 `LD_LIBRARY_PATH` 补 libpython 路径：pyembed 失败主因是
  `-lintl` 不存在（链接期），非运行时库路径问题，故放弃该路线。

## 源码修改（补丁）

| 补丁 | 修改 | 说明 |
|------|------|------|
| `0001-lib-replace-wscript.patch` | `lib/replace/wscript` 的 mkstemp 探针 `mandatory=True`→`False` | 鸿蒙 `/tmp` 只读 + HMDFS 权限归一化；探针结果如实为 not found，改用内置 mkstemp |
| `0002-wscript.patch` | `wscript` 的 `testonly` 增加 `env.disable_python` 守卫 | `--disable-python` 时不再误跑 `python/tests/simple.py`（45 项 pytdb 绑定测试） |

未修改任何上游测试**用例**；补丁不引入平台宏（无 `__OHOS__`），无绝对路径。

## 依赖版本

- 无外部库依赖（`lib/replace`、`third_party/waf` 均内置于源码包）

## 发现与知识

✅ wafsamba 的 mandatory 运行探针（`HAVE_SECURE_MKSTEMP`）在 /tmp 只读（E002）与 HMDFS 权限归一化 0640（E046）下必失败，应改非致命并走 lib/replace 内置替代实现（对应补丁 0001；不得放宽断言或硬编码设备路径）

✅ musl 未实现 robust mutex（E192）：lib/replace 自动探测关闭 `USE_TDB_MUTEX_LOCKING`，无需补丁；37 个单测（含 mutex 系列）在降级模式下全部通过

✅ `--disable-python` 时上游 wscript 仍会把 python3 记入 `python_interpreters` 并误跑 `python/tests/simple.py`，需要 testonly 守卫（对应补丁 0002；C 测试全部保留运行）

✅ 平台 `python3-config --embed` 输出携带不存在的 `-lintl`，pyembed 探针无法链接；纯 C 包以官方 `--disable-python` 规避（E339 为 waf 版本核对项，本包内置 waf 2.1.6 未触发）

## 验证结果

```sh
$ ./configure --prefix=... --disable-python   # rc=0
$ make -j2                                    # rc=0（122 tasks）
$ make test                                   # rc=0
  shell 集成测试: test_tdbbackup.sh / test_tdbdump.sh   通过
  TAP 单元测试:  37/37                                  通过
  tdbtorture:    testsuite returned 0                   通过
  python 测试:   python testsuite skipped (--disable-python)
```

conan 侧验证（conan create：构建 + make test + test_package）见 reports/test-report.md 与
`.ci-result.json`；消费者测试（test_package）9 处断言 + 包内 `tdbdump` 执行通过。

## 注意事项

- 本包**未启用** python 绑定（`pytdb`）：如需 python 模块，平台 python 工具链需先修复
  `python3-config --embed` 的 `-lintl` 依赖问题。
- 构建必须在源码目录内原地进行（wafsamba 的 `IN_LAUNCH_DIR()` 判定 standalone；
  且 `configure` 包装脚本假定工作目录为源码根）。
- `configure` / `make` 均要求 `PYTHON` 环境变量指向可用的 python3（conanfile.py 已显式传入）。

**编译结束**: 2026-09-16
---

**编译结束**: 2026-09-16 18:35
**最终状态**: built
