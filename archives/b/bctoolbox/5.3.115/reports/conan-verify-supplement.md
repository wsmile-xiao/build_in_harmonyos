# conan-verify 人工补测报告 — bctoolbox 5.3.115

> 背景：conan-verify（最终 SHA `b12fb70434fe55bd48869f4dea28af39ed07edd5`，round 9 清缓存实跑：`conan remove "bctoolbox/*" -c` + 手工清理 `p/b/bctoo*` 分片缓存后执行；G1/G0/G2/G3 PASS）中 G4 因 package_id 解析失败未定位缓存路径，L2/L4/L5 显示「跳过（无 cache 路径）」却总判 PASS（workflow 第 7.2/17 节已知工具缺陷）。按同节要求人工补测如下。
> 对应 workflow 先例：heatshrink / btparse / canfigger / cjose。
> 采信轮原始日志副本：`$HOME/tmp/bctoolbox-5.3.115/conan-create-b12fb70.log`（25593 B，sha256 `df968f7d1b8fe1c1e30b59c3f3e23b471af6dadd3d765ef67ca2defbb8cb2ce1`，与 `reports/conan-create.log` 同内容，留存以防 finish 缓存轮覆盖）。
> 变体证据（shared 形态 / 全特性 35 用例）产自 SHA `3b25e78722cb5e0973e28c73d947f822add36867`；最后两个提交仅改 `notes.md`（文档），构建输入逐字节未变，可用
> `git diff 3b25e78722cb5e0973e28c73d947f822add36867..b12fb70434fe55bd48869f4dea28af39ed07edd5 -- archives/b/bctoolbox/5.3.115/conanfile.py archives/b/bctoolbox/5.3.115/conandata.yml archives/b/bctoolbox/5.3.115/patches archives/b/bctoolbox/5.3.115/test_package` 输出为空反证；最终 SHA 自身的干净轮为 round 9（本文件 L1 表首行）。

## G4 产物清单

static 包（默认 `shared=False`，本轮缓存 `p/b/bctooa62252b096bb6/p`，package_id `4b977264131a1c74e82bd6bb51b63cc9aadc4cfa`）：

- `include/bctoolbox/`：18 个头文件（charconv.h compiler.h defs.h exception.hh list.h logging.h map.h ownership.hh param_string.h parser.h port.h regex.h **tester.h** utils.hh vconnect.h vfs.h vfs_encrypted.hh vfs_standard.h）
- `lib/libbctoolbox.a`（453092 B）
- `lib/libbctoolbox-tester.a`（56354 B，上游 `ENABLE_TESTS_COMPONENT=ON` 的安装产物）
- `lib/pkgconfig/bctoolbox.pc`、`lib/pkgconfig/bctoolbox-tester.pc`
- `share/BCToolbox/cmake/`：9 个文件（BCToolboxConfig/ConfigVersion/Targets/Targets-release、BCGitVersion、BCToolboxCMakeUtils、ConfigureSpecfile、MakeArchive、gitversion.h.in）
- **无 `bin/`**：tester 可执行文件已在 `package()` 内剔除（构建期验证产物，且其 `bcunit` 依赖不在交付依赖链中）——与 `package_info()` 声明（`cpp_info.libs=["bctoolbox"]`）一致。

shared 包（`shared=True`，本轮缓存 `p/b/bctoo799f9db7c8bfa/p`）：同上，`lib/libbctoolbox.a` 换为 `lib/libbctoolbox.so`（293312 B）+ `libbctoolbox-tester.so`（96640 B）。

## L2 消费者实测

| # | 消费者 | 链接形态 | 证据 | 结果 |
|---|--------|----------|------|------|
| 1 | test_package C 消费者（list + logging） | static 包 + `-lc++`（system_libs 传播） | `reports/conan-create.log`（round9 干净轮）RUN 行 + 6/6 断言 | ALL C TESTS PASSED |
| 2 | test_package C++ 消费者（regex + BctbxException） | 同上 | 同上 | ALL C++ TESTS PASSED |
| 3 | test_package 双消费者 | shared 包（无需 `-lc++`，验证 system_libs 按 shared 门控） | `$TASK_DIR/variants-3b25e78.log`（SHARED 段，`SHARED_EXIT=0`） | 6/6 PASS |
| 4 | dlopen 动态加载（`dlopen_consumer.c`） | `dlopen(libbctoolbox.so, RTLD_NOW\|RTLD_LOCAL)` + `dlsym(bctbx_is_matching_regex)` + 调用 | 设备实测输出 `dlopen+dlsym+call: regex match=1`，exit=0（`$TASK_DIR/dlopen_consumer_3b25e78`） | PASS |
| 5 | 原生共享库 C/C++ 消费者（探索阶段） | 设备真机直接链接运行 | exit=0（list size=2 first=hello；regex=1 exception=1） | PASS |

另：上游 tester 本体也是真实消费者——它链接交付的 `bctoolbox` 目标并在构建中执行（static 与 shared 两形态各 20/20 PASS，见下节）。

## L1 上游测试在包构建内执行（补充证据）

| 配置 | 日志 | suites | tests | passed | failed | asserts |
|------|------|--------|-------|--------|--------|---------|
| 交付 static（round9 干净轮，最终 SHA） | `reports/conan-create.log` | 6 | 20 | 20 | 0 | 779 |
| 交付 shared（`-o shared=True`） | `$TASK_DIR/variants-3b25e78.log` | 6 | 20 | 20 | 0 | 779 |
| 全特性（测试专用 mbedtls 3.6.6） | `$TASK_DIR/variants-3b25e78.log`（FULL FEATURE 段） | 8 | 35 | 35 | 0 | 103688 |

两次构建日志均含 4 条 `Apply patch` 与全部编译行（round9 为 23 条 `Building C/CXX object`）。全特性配置的完整说明见 `upstream-test-full-feature.md`。

## L4 安全属性

`lib/libbctoolbox.so`（shared 包 `bctoo799f9db7c8bfa`）：
- `GNU_RELRO` 段存在，且 `DT_FLAGS` 含 `BIND_NOW`、`DT_FLAGS_1` 含 `NOW` → **full RELRO**
- `GNU_STACK` 段存在（RW，无 E 位）→ **NX 栈**
- ELF Type：`DYN (Shared object file)`
- `DT_NEEDED`：`libc++_shared.so`、`libc.so`（OHOS musl/libc++ 运行时，符合预期）

test_package 消费者可执行文件：
- ELF Type：`DYN (Position-Independent Executable file)` → **PIE**
- `GNU_RELRO` + `GNU_STACK` 均存在

static 归档（`.a`）：链接产物的 PIE/RELRO/NX 由消费方链接决定；上表消费者与 tester 实测全部 PIE+RELRO+NX，证明归档目标文件 PIC 兼容。

## L5 产物基线

| 产物 | SHA-256 | 大小 |
|------|---------|------|
| static `libbctoolbox.a`（bctooa62252b096bb6） | `977d24b9aca51c9e5096b816519a93d53b024e15c77f124ebb7c21e772fbd9b3` | 453092 |
| static `libbctoolbox-tester.a`（同上缓存） | `980e9f0e350fad3ce80314e5ca8d23f724c2f157135bf0cfeea1e891960677b8` | 56354 |
| shared `libbctoolbox.so`（bctoo799f9db7c8bfa，第一次独立构建） | `26f2b96eb404709c37d40dfe71eb1216d7d6b61799d2c55540b9efd689ec4f15` | 293312 |
| shared `libbctoolbox.so`（bctoo5757e2ff4922b，第二次独立构建：先删共享包缓存再重建） | `26f2b96eb404709c37d40dfe71eb1216d7d6b61799d2c55540b9efd689ec4f15` | 293312 |

两次完全独立的 shared 构建哈希逐字节一致——同 SHA 配方构建可复现，无异常漂移。

## G2 真实构建证据（非缓存轮）

- round9 采信轮（最终 SHA）`reports/conan-create.log` 含 23 条 `Building C/CXX object` 编译行与 `RUN: cmake --build ... -- -j20`，且 test_package 段完整（`ALL C TESTS PASSED` / `ALL C++ TESTS PASSED`）；准备阶段确已执行 `conan remove -c` + `rm -rf p/b/bctoo*`（构建前缓存目录不存在）。
- 自检符合 workflow 7.2「本轮日志含等价构建行 + 测试计数」要求。

## 遗留说明

- conan-verify 工具的 G4 package_id 正则未命中 `bctoolbox/5.3.115@ohpcd/stable` 的分片缓存布局（`p/b/<hash>/p`），属工具侧已知缺陷（workflow 第 17 节），待框架修复后摘除本补测。
- 跨包可复用经验（已写入 `notes.md` 发现与知识）：`build()` 内运行测试时工作目录须为可执行文件所在目录——上游 shared 构建记录相对 `DT_NEEDED`（如 `../src/libbctoolbox.so`），加载器把含 `/` 的名字当字面路径相对 cwd 解析，从 build 根目录启动会 `Error loading shared library` 后整串 relocation 失败。
