- **三方库名称**：libnss-cache
- **上游版本**：0.22
- **上游仓库地址**：https://github.com/google/libnss-cache
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E276（codeload URL 无扩展名 → get() 显式 filename）、E392（raw makefile conan 配方模式：compiler_executables 字典 + source_folder 执行）、E483（explicit-filename-in-get）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 4 | 来源：make check 的 test_getent 目标（gen_getent 生成 passwd/group/shadow/gshadow 缓存并与 .out 期望逐项 diff）|
| 性能测试 | 8 | 来源：make check 的 time_lookups 目标（lookup 基于 cache 的线性/二进制索引计时）|
| **合计** | **12** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 4 | 不变 | test_getent 的 4 组 diff 断言在本机实测全部一致通过 |
| 性能测试 | 8 | 不变 | time_lookups 计时目标（依赖本机性能，非断言）|
| 鸿蒙特有测试 | 1 | 新增 | 独立入口 `tests/ohos_nss_cache_test`（OHOS/musl 无 nss.h/gshadow.h，验证补丁兼容层：`_nss_cache_setspent_path`/`setgrent` 等公开符号 + $TMPDIR 缓存文件读写，18 断言，含负向注入证明）|
| **合计** | **13** | **+1** | |

### 测试统计口径（固定为「独立可执行测试入口数」）

- 上游断言入口：`gen_getent` + 4 组 diff = 5（全部 rc=0 通过）
- 鸿蒙特有测试独立入口：1（`tests/ohos_nss_cache_test`，正向 18/18；负向注入 rc=1 有 FAIL 原文；恢复后再通过）
- Conan test_package L1 入口：1（`test_package/test.c` 经 add_test 执行，正向 rc=0；负向 `-DEXPECTED_UID=9999` rc=2 有 FAIL 原文，R34 非恒绿）
- 去重合计：7 个独立入口，全部真实执行通过（gcov/sort -R 为本环境工具缺失或非断言输入生成，不计入口）

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：鸿蒙特有测试独立入口 + Conan test_package 消费者契约测试
> - **补全原因**：上游 make check 面向 NSS 模块内部逻辑（需生成缓存文件），未提供面向消费者链接的契约测试；OHOS/musl 缺 `<nss.h>`/`<gshadow.h>` 且 `fgetspent_r`/`fgetsgent_r` 未声明，需验证补丁兼容层行为（R34 非空壳 + R02 独立可核验入口）
> - **新增测试文件清单**：
>   1. `tests/ohos_nss_cache_test.c` + `tests/run_ohos_test.sh` — 独立入口：驱动 `_nss_cache_getspnam_r`/`_nss_cache_getsgnam_r`/`_nss_cache_getpwuid_r` 解析 $TMPDIR 缓存文件，18 断言可失败（负向注入 sp_lstchg=12345 时 rc=1 有 FAIL 原文）
>   2. `test_package/test.c` — R34 修复：不再只断言路径回显（恒绿），改为实际写入 $TMPDIR passwd.cache 并经 `_nss_cache_getpwuid_r` 断言 uid/gid/name；负向 `-DEXPECTED_UID=9999` 时 rc=2 有 FAIL 原文

## 验证结果

- 编译状态：通过（conan create / G2-G4 / W3 本地 CI 模拟全部 PASS，OHOS aarch64 profile）
- 上游测试用例通过率：5/5（100%）（实测 gen_getent rc=0 + 4 组 diff 断言全部一致；gcov 覆盖率工具本环境缺失，非测试失败）
- 鸿蒙特有测试：1/1（100%）正向 18 断言通过，负向注入真实失败后恢复通过
- 新增测试用例通过率：1/1（100%）(test_package 在 conan create 中实际执行，R34 负向证明 rc=2)
- 远端 CI fork-OOM 归因：`ci/conan/build_and_test.sh:907` 为 L0 门禁 L0o 静态检查的命令替换管道（3 个 grep 子进程），在 CI 环境 RLIMIT_AS 受限时 fork 失败（ENOMEM）——属 CI 执行环境资源限制，非当前库配方/归档/测试所致（907 行原文、所在 step、被 fork 命令与本机复现证据见回报日志）

## 补充说明

- 上游为纯 Makefile 构建（无 configure），产物为共享库 `libnss_cache.so.2`；配方以 Conan toolchain clang 覆盖 Makefile 默认 `CC=gcc`（R33）
- `patches/0001-ohos-musl-compat.patch`：OHOS/musl 无 `<nss.h>`/`<gshadow.h>` 且 `fgetspent_r`/`fgetsgent_r` 未声明，补丁加入 tree-local 兼容头与 musl 派生重入解析器并链接进 `libnss_cache.so.2`
- `package()` 额外复制无版本名 `libnss_cache.so` 供 CMake 链接解析（HMDFS 软链接不可靠，采用复制）
- 官方标签 `version/0.22`（commit 35d28bf60b7f），SHA-256 = `8b13a2b08d08a84e5c91b48996a27754208e003d7f3d1b4cfcb788f0fcc17a3c`（本地与官方一致）
