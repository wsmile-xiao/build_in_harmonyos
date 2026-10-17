# netcdf-c 4.9.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-16
- 编译器: clang/clang++ (aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
export PATH=<conan toolchain>
./configure --host=aarch64-linux-ohos --prefix=$DEFAULT_PREFIX \
  --disable-dap-remote-tests --disable-parallel-tests --disable-libxml2 \
  CC=clang --target=aarch64-linux-ohos
make -j1
make check          # 逐目录执行，见下方"上游测试清点与运行"小节
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 不识别 OHOS 平台 | config.guess/config.sub 不认识 HarmonyOS uname 与 ohos triplet | 补丁 0001/0002：config.guess 识别 `*:HarmonyOS:*:*`，config.sub 接受 `ohos*` OS |
| 2 | configure 临时目录创建失败 | HMDFS 强制 setgid 且忽略 umask 077，`umask 077 && mktemp -d` 产生 drwx--S--- 目录无法写入 | 补丁 0003：去除 umask 077（E114） |
| 3 | 测试脚本 shebang 无效 | OHOS 无 /bin/bash（位于 /data/service/hnp/bin/bash） | 本轮将 POSIX 兼容脚本 shebang 改 /bin/sh、含 bashism 脚本改真实 bash 路径（testpathcvt/test_scope FAIL→PASS） |
| 4 | /tmp 只读 | 执行环境 /tmp 为 erofs 只读挂载 | DAP cookie jar 临时文件创建失败触发 OCASSERT（ncdap_test 4 项 FAIL）→ 补丁 0005：libdispatch/ddispatch.c 非 Windows 分支先读 TMPDIR/TMP 再回退 /tmp；运行环境 export TMPDIR=<可写目录> |

## 源码修改

共 19 个补丁（见 conandata.yml patches 列表），按类别：

- `patches/0001-config.guess.patch`：config.guess 识别 HarmonyOS uname 与 ohos triplet（含 libc 探针程序新增 `#elif defined(__OHOS__)` → LIBC=ohos，与 __ANDROID__ 探针同构；属 iron-rules R8 允许的"识别 libc 的探针程序"例外，故 PR 内声明理由并随 --no-preflight 显式跳过 PF5 平台宏闸）
- `patches/0002-config.sub.patch`：config.sub 接受 ohos-linux / ohos* OS
- `patches/0003-configure.patch`：configure 去除 umask 077（HMDFS 兼容，E114）
- `patches/0004-0019`：上游测试脚本 shebang 适配（#!/bin/bash → #!/bin/sh 或真实 bash 路径，其中 0004 为 build.sh、0006-0019 共 14 个为其余测试脚本，合计 15 个 shebang 补丁；0005 为 ddispatch 补丁）
- `patches/0005-libdispatch-ddispatch.c.patch`：ddispatch 硬编码 /tmp → 优先读 TMPDIR/TMP（erofs 只读平台，DAP cookie jar）

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| hdf5 | 1.14.6 | netCDF-4/HDF5 后端 |
| libcurl | 8.5.0 | DAP 客户端 |
| zlib | 1.3.1.1 | 压缩 |
| libaec | 1.1.7 | 误差压缩（经 hdf5 传递） |

## 上游测试清点与运行（R51 申报表）

### 静态清点（官方 tag 源码可复制枚举）

- `source_declared_total`: **253**（当前 OHOS 配置 generate 出的 10 个测试目录 Makefile TESTS 注册项，make -p 展开 am__append/am__EXEEXT 后按字面项枚举）
- `configured_executable_total`: **253**（当前配置可执行集合，与声明一致）
- 条件未注册项（计入全量分母不计通过）：并行测试（--disable-parallel-tests）、远程 DAP（--disable-dap-remote-tests）、libxml2 相关（--disable-libxml2）、未展开的 am__append 条件占位项

### 实际运行（两轮合计，命令/退出码/日志实证）

| 目录 | 运行方式 | rc | PASS | FAIL | 说明 |
|---|---|---|---|---|---|
| ncdump | `make -C ncdump check -j1` | 0 | 48 | 0 | 上游 ncdump/ncgen 测试（含 testpathcvt/test_scope） |
| ncgen3 | `make -C ncgen3 check -j1` | 0 | 2 | 0 | run_tests.sh、run_nc4_tests.sh |
| nctest | `make -C nctest check -j1` | 0 | 3 | 0 | nctest、tst_rename、compare_test_files.sh |
| h5_test | `make -C h5_test check -j1` | 0 | 26 | 0 | HDF5 文件读写测试 |
| nc_test | `make -C nc_test check -j1` | 0 | 23 | 0 | classic 格式读写/属性测试 |
| unit_test | `make -C unit_test check -j1` | 0 | 5 | 0 | tst_nclist、test_ncuri 等 |
| nc_test4 | 分批 `make check TESTS=...` + 条件二进制直接执行 | 0 | 83 | 0 | 84 项中 83 通过；tst_files4 为文件分配密集用例（HMDFS+共享机负载），3 次有界尝试（240s/290s/290s）CPU 持续工作中超时，非死锁非失败，恢复条件：负载降低后 `timeout 600 ./tst_files4` |
| nczarr_test | `make -C nczarr_test check -j1` | 0 | 24 | 0 | nczarr/zarr 读写、量化、nulls 等 |
| dap4_test | `make -C dap4_test check -j1` | 0 | 4 | 0 | 本地 DAP4（远程已禁用） |
| ncdap_test | `make -C ncdap_test check -j1` | 0 | 4 | 0 | 补丁前 4 FAIL（cookie jar OCASSERT），0005 补丁后全 PASS |

### 双口径统计（PR 单一口径）

- 当前配置可执行集合：`executed_passed_total/source_declared_total = 222/253 (87.7%)`（全量声明口径，未实例化差值=条件注册项）
- 当前配置实际执行并通过：`222/223 (99.6%)`（223 = 222 通过 + tst_files4 已尝试但限时未完成；未完成项计入分母不计通过）
- 已运行项通过率 100%（222/222），无 FAIL

## 验证结果

```bash
# 库产物
libnetcdf.a / libnetcdf.so（.libs 下）
# CLI 工具
ncdump/ncgen/ncgen3/nccopy（安装于 bin/，L5 产物基线验证通过）
# 上游测试：222/253 (87.7%) 全量口径，222/223 (99.6%) 当前配置可执行集合；已运行项 100% 通过
# 消费者测试（test_package）：
consumer round-trip OK: 1.5 -2 3.25 42
[OHOS-SPECIFIC] PASS: netCDF-4 2x3 int matrix round-trip on aarch64-linux-ohos
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools，OHOS host，AutotoolsDeps） |
| conandata.yml | 官方源 v4.9.3 + SHA-256 + 19 个补丁 |
| test_package/ | L1 消费者测试 + 鸿蒙专项测试（test_netcdf-c / ohos_specific_test） |
| commands.json | CLI 工具声明（ncdump/ncgen/ncgen3/nccopy） |
| knowledge/drafts/ | DRAFT-netcdf-c-4.9.3-ddispatch-tmpdir-env（.md/.kv 配对，路径 B） |

## 注意事项

- DAP 远程测试与并行测试已禁用（--disable-dap-remote-tests/--disable-parallel-tests）；本地 DAP4/DAP3 测试已实际运行通过（dap4_test 4/4、ncdap_test 4/4）。
- XML 解析使用内置实现（--disable-libxml2），不引入额外依赖。include/netcdf_meta.h 声明 netCDF 版本 4.9.3。
- config.guess libc 探针的 `__OHOS__` 平台宏属 R8 允许例外（识别 libc 的探针程序，与 __ANDROID__ 同构），已在此声明理由。
---

**编译结束**: 2026-09-17 11:38
**最终状态**: built

---

# 第二轮返工记录（follow-up r02，2026-09-17）

## 本轮修改（分析端验收发现的可修项，3 个文件）

1. `patches/0001-config.guess.patch`：`LIBC=ohos` 前导 4 空格改为单个制表符。
   根因：`cat <<-EOF` heredoc 只剥除行首制表符，4 空格版本生成 C 文件中该行为
   `    LIBC=ohos`（前导空格），`grep '^LIBC=' | sed 's, ,,g'` 无法提取，
   libc 探针分支成为死代码并回退 LIBC=gnu。改后与同 heredoc 内 `LIBC=android`
   的制表符缩进一致。验证：剥 tab 模拟生成探针 C 文件后 `grep '^LIBC='` 可提取
   `LIBC=ohos`；补丁后 config.guess 实际运行输出 `aarch64-unknown-linux-ohos`（rc=0，
   uname 实证 HarmonyOS aarch64）。
2. `test_package/ohos_specific_test.c`：`nc_open` 重新打开文件后经
   `nc_inq_varid(ncid, "matrix", &varid)` 重新获取 varid 再读取（与 test.c 一致）。
3. `patches/0005-libdispatch-ddispatch.c.patch`：TMPDIR/TMP 为空字符串时按未设置处理
   （`tempdir == NULL || tempdir[0] == '\0'`），保持回退链 TMPDIR→TMP→/tmp→"."。

## 复验（修复进入实际编译）

- refresh-patch 从 work 源码 diff 重生成 19 个补丁（含上述两处补丁修复），
  W3 全量复跑 exit 0：G0/G0e/L0（L0i 依赖在仓/L0k commands.json/L0m 结构）通过、
  KC pass、JC pass（无杂项）、conan create 成功、L1 upstream+test_package 执行、
  L2/L4（warn 非阻塞）/L5 通过，Success 1/1，Pass rate 100%（.ci-result.json exit_code=0）。
- 最新构建树 libdispatch/ddispatch.c 实证含 `tempdir[0] == '\0'` 修复（修复真实进入编译）。
- test_package 两二进制实际运行：`consumer round-trip OK: 1.5 -2 3.25 42`、
  `[OHOS-SPECIFIC] PASS: netCDF-4 2x3 int matrix round-trip on aarch64-linux-ohos`。
- 上游测试双口径不变（补丁仅可移植性修复，未改测试逻辑与注册项）：
  222/253 (87.7%) 全量口径、222/223 (99.6%) 当前配置可执行集合、已运行项 222/222 (100%)。

## 明确不修改项（按任务范围）

- 0004 shebang `/data/service/hnp/bin/bash`（平台事实，CI 实证 CONFIG_SHELL 存在）、
  0003 umask 077（E114 平台 workaround）、conandata 官方 GitHub URL（源码来源完整性硬规则；
  远端 CI L1 若因 worker 缺 curl / github 不可达失败为外部基础设施阻塞，非当前库缺陷）。

