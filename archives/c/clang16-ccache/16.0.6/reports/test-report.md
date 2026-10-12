# 测试报告 — clang16-ccache 16.0.6（OHOS PC / aarch64）

- 参考: `clang16-ccache/16.0.6@ohpcd/stable`
- 验证日期: 2026-10-06
- 验证设备: HarmonyOS PC（HAD-W32/W24, aarch64），HarmonyOS 6.1.0.117（内核 1.12）
- 工具链: clang 15.0.4（OHOS SDK 26.0.0.18 native，aarch64-unknown-linux-ohos）、CMake 4.4.3、Conan 2.29.1（OHOS 适配版）
- Profile: ohos-aarch64（设备本地为同配置的 ohos-aarch64-device）

## 1. 上游测试清点（R51 三步法 · 清点）

| 测试类型 | 来源 | 规模 |
|----------|------|------|
| 单元测试（doctest 2.5.3） | ccache-4.14 `unittest/*.cpp` 的 TEST_CASE | 源码声明 279 / 注册执行 243 |
| 集成测试（ctest） | ccache-4.14 `test/suites/*.bash` | 54 套件（+ unittest 共 55 个 ctest 项） |

## 2. 执行方法与命令

### 2.1 构建（含上游测试）

```
cmake -G Ninja -S <ccache-4.14.work> -B <builddir> \
  -DCMAKE_BUILD_TYPE=Release -DDEPS=LOCAL \
  -DDEP_HIREDIS=DOWNLOAD -DDEP_XXHASH=DOWNLOAD -DDEP_ZSTD=DOWNLOAD \
  -DDOCTEST_INCLUDE_DIR=<doctest-2.5.3 预置目录> \
  -DREDIS_STORAGE_BACKEND=ON -DHTTP_STORAGE_BACKEND=ON \
  -DENABLE_TESTING=ON -DENABLE_IPO=OFF
cmake --build <builddir> -j 20        # 实测 39s wall（20 核）
```

本地验证环境预置（仅测试环境，**不入配方/补丁**；设备平台工具差异的规避）:

- `awk`：mawk 1.3.4。设备 toybox awk 不支持 `-v ORS=:`，会破坏 `test/run` 的 PATH 重写（导致全部套件误 skip）。
- `grep`：GNU grep 3.11。设备 toybox grep 不检索含 NUL 的二进制文件（`expect_contains main.o` 类用例误判）。
- `objdump`：llvm-dwarfdump 包装（设备无 GNU objdump；debug_* 套件需要 DWARF 字符串）。
- `XDG_RUNTIME_DIR`：短路径可写目录（设备 `/tmp` 只读，ccache helper IPC 回退长路径 unix socket 失败）。
- `testdir/TMPDIR/TMP/TEMP`：置于 `/data/storage/el2/base/haps/entry/files`（合格 0700 挂载点）。HMDFS 挂载点 `st_uid` 与 `geteuid()` 不一致（ccache 拒绝目录级配置），且不支持 mkfifo/fallocate。

### 2.2 单元测试（doctest）

```
cd <el2 合格挂载点> && TMPDIR=<el2> <builddir>/unittest/unittest
```

实测: **243 注册 | 240 通过 | 3 失败 | 5 跳过**（断言 2821: 2808 通过）
通过率: **240/243 = 98.8%**（当前配置可执行口径）；240/279 = 86.0%（源码声明口径）

### 2.3 集成测试（ctest）

```
cd <builddir> && TMPDIR=<el2> ctest --output-on-failure -j 6 --timeout 300
```

实测: 55 项 = **30 通过 | 3 失败（含 unittest 入口）| 22 跳过**
套件口径: 54 套件 = **30 通过 + 2 失败 + 22 跳过**

## 3. 失败台账（全部为设备平台限制，非 ccache 缺陷）

### 3.1 unittest 3 例 — `link(2)` 硬链接 EPERM（E079）

- 入口: `unittest`（doctest）
- 用例: `ccache.guess_compiler`（hardlink 探测）/ `util::DirEntry Hard links` / `util::write_file modes`
- 首错证据: `test_ccache.cpp:236 CHECK( fs::create_hard_link(cc, gcc) ) is NOT correct`；`test_util_direntry.cpp:439 REQUIRE( link("a", "b") == 0 )`；`test_util_file.cpp:229 CHECK( link("test", "test2") == 0 )`
- 复现证据: 设备全部可写挂载点实测 `link(2)` 均被拒（HMDFS `Operation not permitted`；el2 `Permission denied`）
- 恢复条件: 支持 POSIX `link(2)` 的标准文件系统（ext4 等）

### 3.2 test.base — 硬链接（E079）

- 用例: “Unsupported source language” 需要 `ln -f test1.c test1.ccc`
- 首错证据: `ln: cannot create hard link from 'test1.c' to 'test1.ccc': Permission denied`；`unsupported_source_language` 期望 1 实际 0

### 3.3 test.readonly — 上游测试硬编码 `CCACHE_TEMPDIR=/tmp`，设备 `/tmp` 只读（E002）

- 首错证据: `ccache: error: failed to create temporary file for /tmp/stdout.tmp.XXXXXX.tmp: Read-only file system`
- 说明: 上游用例显式设置 `CCACHE_TEMPDIR=/tmp`（readonly.bash line 22 起），设备 `/tmp` 为只读系统挂载，环境无法满足

## 4. 跳过台账（22 项，上游 PROBE 条件不满足，exit 125）

| 套件 | 上游输出原因 |
|------|--------------|
| clang_cu / clang_cu_alias / clang_cu_direct | nvcc is not available（无 CUDA） |
| nvcc / nvcc_direct / nvcc_ldir | nvcc is not available |
| profiling_gcc / profiling_gcc_10+ | compiler is not GCC |
| profiling_hip_clang | Hip not supported |
| remote_redis | neither redis-server nor valkey-server found |
| remote_redis_unix | redis-server not found |
| fdiagnostics_addset_output | -fdiagnostics-set-output=sarif not supported by compiler（clang 15.0.4） |
| fdiagnostics_format | -fdiagnostics-format=text not supported by compiler |
| input_charset | compiler doesn't support -finput-charset |
| source_date_epoch | SOURCE_DATE_EPOCH not supported by compiler |
| split_dwarf | -gsplit-dwarf not supported by compiler |
| multi_arch | multiple -arch options not supported on HarmonyOS |
| fmodule_file | compiler does not support C++ modules |
| fileclone | file system doesn't support file cloning |
| hardlink | file system doesn't support hardlinks |
| inode_cache | inode cache not supported on unknown |
| masquerading | compiler 非经 PATH 解析（测试环境 CC 为绝对路径） |

## 5. 鸿蒙消费者/特有测试（test_package，conan create 自动执行）

- `ccache --version` → `ccache version 4.14`（Features 含 file/http/redis/remote-storage）
- `consumer_verify.sh`：编译随包分发的 `consumer_hello.c`（包内 ccache 包装 OHOS clang，aarch64-unknown-linux-ohos）
  - 两次编译 rc=0，链接 rc=0
  - **缓存命中断言**：`--print-stats` 中 direct+preprocessed 命中总数 ≥ 1（实测 preprocessed_cache_hit=1）
  - 运行输出 `consumer-ohos-hello: clang16-ccache works, sum=3` → **CONSUMER_PASS**
- 证据: `reports/conan-create.log` 的 `Launching test_package` 段（G2 运行日志）

## 6. 门禁与本地 CI

- conan-verify: **G0/G1/G2/G3/G4 全 PASS**（`reports/conan-verify-report.md`）
- W3 本地 CI（finish 内嵌）: 见版本目录 `.ci-result.json`（exit_code=0）
- 原始日志（conan create / ctest / unittest）留存于设备构建目录，本报告已内联关键证据行；
  平台 CI 结论以 PR 评论为准

## 7. 结论

- 上游测试全部失败项均可 100% 归因于设备平台限制（硬链接 `link(2)`、只读 `/tmp`），无 ccache 功能缺陷
- 消费者链路（编译 → 缓存命中 → 链接 → 运行）在鸿蒙 PC aarch64 全通
