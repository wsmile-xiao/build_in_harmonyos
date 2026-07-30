# xapian-core 1.4.26 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-07-29
- 状态: built

## 编译步骤

Conan recipe 使用官方 release 包 `xapian-core-1.4.26.tar.xz`，应用 `config.guess`、`config.sub` HarmonyOS 识别补丁、UUID 熵源 fallback 补丁和 OHOS upstream 测试补丁后执行 `./configure && make && make install`。

关键配置:

```bash
--disable-documentation
--disable-dependency-tracking
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess/config.sub` 不认识 HarmonyOS | 上游 autotools 辅助脚本没有 `linux-ohos` 规则 | 使用本地已有 `0001-config.guess.patch` 和 `0002-config.sub.patch` |
| 2 | glass/chert 后端需要 zlib | 上游 INSTALL 明确要求 zlib | Conan recipe 声明 `zlib/1.3.1.1` |
| 3 | 真机 `configure` 执行时报 `Permission denied`；改用 shell 后 profile 中 `/data/service/hnp/bin/clang` 路径不存在；PATH 中 clang 包装脚本的 `/bin/sh` shebang 也被拒 | OHOS 真机环境直接 exec 解包后的 autotools 脚本不稳定；隔离 job 中实际工具链位于 `PATH` 里的 `$HOME/usr/local/bin`；clang/clang++ 是 shell 包装脚本 | `build()` 中对 `configure` 设置 `0755`，并在 OHOS 上通过 `PATH` 中的 bash 显式解释 configure 和 clang/clang++ 包装脚本 |
| 4 | `configure` 误探测到 `/bin/link -lib`，报 `could not determine link -lib interface` | PATH 中没有 GNU `ar` 命名，Autotools 未自动选中 LLVM binutils | 在 OHOS configure 环境中显式设置 `AR=llvm-ar`、`RANLIB=llvm-ranlib`、`NM=llvm-nm` |
| 5 | `configure` 报 `no acceptable ld found in $PATH` | OHOS 工具链提供的是 `ld.lld`，未以 `ld` 名称暴露 | 在 OHOS configure 环境中显式设置 `LD=ld.lld` |
| 6 | `config.status` 报 `./conf*/subs1.awk: Permission denied` | OHOS 真机构建目录继承 setgid，Autoconf 默认 `umask 077` 创建的临时目录无法写入生成的 awk 脚本 | OHOS 下运行 `configure` 前将生成脚本中的临时目录 `umask 077` 调整为 `umask 022` |
| 7 | `include/xapian/version.h` 为空，编译时报 `XAPIAN_DOCID_BASE_TYPE` 等宏未定义 | OHOS 新端口环境只有 toybox sed，上游 `configure` 生成 `version.h` 时使用 GNU sed 扩展/反斜杠替换，失败后留下空文件但 configure 仍返回 0 | OHOS 下在 `configure` 后检测空 `version.h` 并生成等价 public version header |
| 8 | upstream `make check` 中大量数据库用例报 `Opening UUID generator failed (Permission denied)`，`unittest` 的 `uuid1` 失败 | `configure` 在 OHOS 上启用 `USE_PROC_FOR_UUID`，但真机禁止普通用户读取 `/proc/sys/kernel/random/uuid`；`/dev/urandom` 可读 | 新增 `0003-uuids-urandom-fallback.patch`，优先使用上游 `/proc` UUID，打开失败时改用 `/dev/urandom` 生成 RFC 4122 version 4 UUID |
| 9 | upstream `make check` 直接执行 `runtest` 报 `/bin/sh: bad interpreter: Permission denied` | 上游 `tests/runtest.in` 和 `tests/runsrv.in` 硬编码 `/bin/sh`，OHOS 旧端口禁止该 shebang 路径 | `0004-ohos-lockfile-umask-test.patch` 将测试脚本模板 shebang 改为 Autoconf 配置出的 `@SHELL@` |
| 10 | old port upstream `make check` 仅 `lockfileumask1` 失败，期望 `0644` 但实际 `0640` | OHOS storage 权限策略会屏蔽 others read 位，普通 `umask(022)` 后创建的 lock file 不是 Linux 预期的 world-readable | `0004-ohos-lockfile-umask-test.patch` 在运行时用 POSIX `open/stat/unlink` 探测同目录实际权限，并用探测结果校验 lock file |

## 源码修改

- `0001-config.guess.patch`: 将 HarmonyOS/aarch64 映射为 `aarch64-unknown-linux-ohos`。
- `0002-config.sub.patch`: 接受 `linux-ohos` OS/kernel 组合。
- `0003-uuids-urandom-fallback.patch`: `/proc/sys/kernel/random/uuid` 不可读时回退到 `/dev/urandom`，并设置 UUID version/variant 位。
- `0004-ohos-lockfile-umask-test.patch`: 测试脚本模板使用配置出的 shell；lockfile umask 测试在运行时探测同目录实际文件权限，避免依赖平台条件编译宏。

## 验证结果

本地已完成 recipe 解析类验证；Windows 本机不作为 autotools/OHOS 构建验证环境。Conan inspect/export 使用项目 venv，并在 OHOS 旧端口 job 环境中复核通过。

```bash
python -m py_compile archives/x/xapian-core/1.4.26/conanfile.py archives/x/xapian-core/1.4.26/test_package/conanfile.py
conan inspect archives/x/xapian-core/1.4.26
conan export archives/x/xapian-core/1.4.26
git diff --check -- archives/x/xapian-core
```

OHOS 旧端口 `56267` 最新真机验证通过:

```bash
run_dir=/storage/Users/currentUser/ohos-test-runs/codex-a-xapian-core-xapian-core-1.4.26-conan-r18-oldport-testpatch-20260729-220317-24172
recipe_revision=xapian-core/1.4.26#d28d65417aa55deacdc4787661303b42
package_id=4178e02c63d7574e37468da4e7276fa15c76c47c
package_revision=fe6dd6a32112f8ecb243a6de44379d19
L0_RESULT=pass
L1_RESULT=pass
L2_RESULT=skip: generic version/help checks are not applicable to these CLI tools on old port
L4_RESULT=warn: dangerous functions in config.guess patch
L5_RESULT=pass
test_package=xapian-core smoke test passed: 1.4.26
```

Bot review 后做 R8/R38/P3 最小修正，本地重新 `conan export` 通过，当前 recipe revision 为 `xapian-core/1.4.26#70fd117ac63f769b18c1abdec3225e0b`。本次 review 修正未改变库构建目标，仅将测试断言改为运行时权限探测、调整 `commands.json` schema，并移除对 Conan 私有 configure 参数属性的直接访问。

额外 upstream `make check -j1`:

- r1 在补 UUID fallback 前失败，主因是 `/proc/sys/kernel/random/uuid` 权限拒绝。
- r2 在补丁后尝试重跑，但 heavy 锁被其他任务占用，`--try-lock` 按规则退出 `rc=75`；待锁释放后继续重试。
- old port r8 在显式 bash 运行 `runtest` 后完成 upstream `make check -j1`，`internaltest`、`stemtest`、`unittest` 通过，`apitest` 仅 `lockfileumask1` 失败：期望 `0644`，OHOS 实际 `0640`。
- old port r10 重编 `apitest` 后单独验证 `lockfileumask1` 在 `chert` 和 `glass` 后端均通过。
- old port r11 完整 `make check -j1` 通过，run_dir `/storage/Users/currentUser/ohos-test-runs/codex-a-xapian-core-xapian-core-1.4.26-upstream-check-r11-oldport-20260729-213925-35584`，`apitest/internaltest/stemtest/unittest` 全部 PASS；`apitest total: All 4245 tests passed, 13 expected failures, 50 skipped`。

## 注意事项

- `xapian-core` 会安装库和若干命令行工具，`commands.json` 仅登记常用检查/查看/压缩命令。
