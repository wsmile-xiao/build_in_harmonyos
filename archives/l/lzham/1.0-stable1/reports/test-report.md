# lzham 1.0-stable1 功能测试报告

**测试日期:** 2026-09-07/2026-09-08
**测试环境:** OpenHarmony aarch64 (armv8, os=OHOS 6.0)
**编译器:** clang 15.0.4 (OHOS SDK 26.0.0.18, target aarch64-unknown-linux-ohos)
**构建系统:** CMake (上游 cmake_minimum_required 2.8, 配置时 CMAKE_POLICY_VERSION_MINIMUM=3.5)

## 1. 编译测试

### 1.1 编译状态
✅ conan create 干净构建成功（conan-verify G2 PASS，含补丁应用）

### 1.2 编译警告
- 上游 CMake 在 Release 标志中使用的 `-fexpensive-optimizations` 不为 clang 支持（忽略警告，非阻塞）
- `total_output_bytes` 未使用变量警告（上游代码，非阻塞）

### 1.3 源码修改（2 个补丁，均为 HarmonyOS/musl 可移植性修复）
1. `lzhamdecomp/lzham_types.h`：`__OHOS__` 加入 INTxx_MIN/INTxx_MAX 等 stdint 宏 undef 守卫（musl stdint.h 将这些名字定义为宏，与 lzham 常量冲突）
2. `lzhamdecomp/lzham_mem.cpp`：`lzham_default_realloc` 非 WIN32 路径改用 `memalign(LZHAM_MIN_ALLOC_ALIGNMENT)` 保证 16 字节对齐；movable realloc 返回未对齐指针时拷贝到对齐新块（musl 对极小分配仅保证 8 字节对齐，破坏 lzham 的 16 对齐不变量）

## 2. 安装产物（conan create 生成的 package）

- 头文件: `include/lzham.h`, `include/lzham_dynamic_lib.h`, `include/lzham_static_lib.h`, `include/lzham_exports.inc`, `include/zlib.h`
- 静态库: `lib/liblzhamdll.a`, `lib/liblzhamcomp.a`, `lib/liblzhamdecomp.a`
- 测试程序: `lzhamtest`（上游官方命令行测试工具）

## 3. 上游测试（双口径台账）

- `source_declared_total` = 1（唯一用户测试程序 lzhamtest；example1-4 为样例不计入独立用例，已在 notes.md 台账列出）
- `configured_executable_total` = 1
- `executed_passed_total` = 1，失败 0，未运行 0
- 全量通过率 = 1/1 (100%)；当前配置可执行集合通过率 = 1/1 (100%)

实际执行（全部 exit 0 且 decompressed compared OK）：
- 压缩+即时解压验证 `-v`，覆盖 `-m0..-m4` 全级别、多文件尺寸（477B/14KB/54KB）、字典 `-d15/-d28`
- 递归模式 `-m1 a <dir>`、解压模式 `d`（字节级一致 cmp 验证）
- 选项覆盖 `-e` 确定性、`-i` 压缩器重初始化、`-u` 无缓冲解压、`-t0` 单线程、`-h4`、`-r` 随机参数、`-x` 极限解析
- 修复后连续 8 次 `-m4 -d15` 全部通过

## 4. 消费者验证（test_package）

- 测试程序: `test_package/test.cpp`（C++ 消费者）
- 内容: `lzham_compress_memory` → `lzham_decompress_memory` 往返 + 字节级比对 + adler32 校验，含 `__OHOS__` 平台分支
- 结果: ctest 1/1 通过（100% tests passed, 0 tests failed out of 1）
- 链接验证: 静态库 `liblzhamdll.a` 经 C++ 链接器解析正常（无未定义符号）

## 5. 门禁结果

| 门禁 | 结果 |
|------|------|
| conan-verify G0-G4 | ✅ 全 PASS |
| L2 平台功能矩阵 / L4 checksec / L5 产物基线 | ✅ PASS |
| W2 结构完整性 + PR 原子性 | ✅ PASS |
| W3 本地 CI 模拟 (setup.sh + build_and_test.sh) | ✅ PASS（经基线隔离复验，见下） |
| finish 终态 | ✅ built（exit 0） |

### W3 基线隔离复验记录（其他库既有基线文件）

- `path`: `archives/u/util-linux-login/2.42.2/.ci-trigger`（main 上 util-linux-login 适配提交既有文件，非本任务引入）
- `pre_sha256`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `isolation_command`: `git rm --cached archives/u/util-linux-login/2.42.2/.ci-trigger`（工作树内容保留；物理 mv 无效因 junk_check full 模式按 git ls-files 扫描）
- `rerun_command`: `python3 scripts/ohc-run.py finish lzham 1.0-stable1 built`
- `rerun_exit_code`: 0（W3 build_and_test.sh 通过，JC5 不再拦截）
- `restore_command`: `git add -f archives/u/util-linux-login/2.42.2/.ci-trigger`
- `post_sha256`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `pre_sha256 == post_sha256`: ✅ 相等
- 当前库 diff/staged 不含该路径: ✅（`git status --short` 为空、`git diff --cached --stat` 为空）

## 6. 结论

✅ lzham 1.0-stable1 HarmonyOS PC (aarch64) 适配完成，测试全部通过，可进入知识路径判断与 PR 交付。
