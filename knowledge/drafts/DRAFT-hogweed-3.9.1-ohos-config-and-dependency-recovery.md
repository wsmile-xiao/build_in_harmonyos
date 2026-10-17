# DRAFT-hogweed-3.9.1-kv1 — OHOS autotools 平台识别+HMDFS umask 适配组合与 Conan 依赖缓存恢复

> 对应 KV：`knowledge/drafts/DRAFT-hogweed-3.9.1-ohos-config-and-dependency-recovery.kv`
> 触发事件：hogweed 3.9.1 HarmonyOS PC 适配（R02 本地适配闭环）

## 问题（error_signature）

hogweed（GNU Nettle）3.9.1 在 OHOS aarch64 本地适配时连续命中四类配置/依赖问题：

1. `config.sub` 拒绝 OHOS triplet：
   ```text
   Invalid configuration `aarch64-linux-ohos': OS `ohos' not recognized
   ```
2. `config.guess` 无法探测本机（HMDFS 临时目录权限）：
   ```text
   can't create <TMP>/cgXXXXXX/dummy.c: Permission denied
   config.guess: unable to guess system type
   ```
3. `config.status` 建临时目录失败：
   ```text
   config.status: can't create ./confXXXXXX/subs1.awk: Permission denied
   config.status: error: could not setup config files machinery
   ```
4. configure 求 `GMP_NUMB_BITS` 时 conftest 无法运行 + 依赖缓存损坏：
   ```text
   checking Running simple test program failed. Trying -R flags... failed
   configure: error: cannot find value of GMP_NUMB_BITS
   ERROR: Package 'gmp/6.3.0.1' not resolved: Cannot load recipe.
   Error loading conanfile at '.../conanfile.py': ... not found!
   ```

## 根因（root_cause）

- 随源码发布的 `config.sub`（2023-01-01 旧版）未登记 `ohos` 操作系统，OHOS 适配版
  conan 自动生成的 `aarch64-linux-ohos` triplet 在校验阶段被拒。
- HMDFS 上 `config.guess` 的 mktemp 临时目录受 `umask 077` + setgid/UID 映射影响，
  创建的 0700 目录 owner 非当前进程，`dummy.c` 无法写入 → 探测必然失败。
- `config.status`/`configure` 以 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录，
  HMDFS 下同样不可写（E011/E206 根因一致）。
- nettle configure 的 `ac_fn_c_compute_int` 求 `GMP_NUMB_BITS` 需要编译**并运行** conftest；
  `libgmp.so` 不在运行期搜索路径（缺 `LD_LIBRARY_PATH`/`-rpath`）→ 运行失败 → configure 中止。
- conan 本地缓存 recipe 目录结构损坏（metadata 声称已缓存，但缺 `e/conanfile.py`）时，
  `conan install` 报 "Cannot load recipe"，易被误判为依赖未发布/不可消费。

## 方案（fix_approach）

1. **config.sub 补丁**：在 `config.sub` 的分字段校验前加
   `case $1 in aarch64-*-ohos* | aarch64-*-linux-ohos*) echo "$1"; exit 0;; esac`
   （与 a52dec `0001-config-sub-aarch64.patch` 同法），随配方 `patches/` 落盘。
2. **显式 triple 绕过 config.guess**：配方 `generate()` 对 OHOS 追加
   `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`。
3. **umask 补丁**：将 `configure`/`config.status` 中 `(umask 077 && mktemp` / `(umask 077 && mkdir`
   改为 `umask 022`（gnutls/a52dec 历史先例；HMDFS 下 022 保证组/他可写）。
4. **GMP 探测运行期路径**：配方 `generate()` 把依赖 `cpp_info.libdirs`（绝对路径）前置到
   `LDFLAGS`（`-L` + `-Wl,-rpath`），并 `prepend LD_LIBRARY_PATH`，使 GMP_NUMB_BITS 的
   conftest 运行期能加载 `libgmp.so`。
5. **依赖缓存损坏恢复序列**：
   ```bash
   conan remove "gmp/6.3.0.1" -c                     # 清损坏缓存项（仅本地缓存）
   conan download "gmp/6.3.0.1" -r=ohpcd --only-recipe  # 重下配方
   ls <cache>/e/conanfile.py                          # 验证导出文件齐全
   conan install --requires="gmp/6.3.0.1" ...         # 复验 recipe+binary 可消费
   ```
   禁止用 `--build=missing` 掩盖依赖缺失。

## 验证（verification）

R02 实测证据：

- `conan create hogweed/3.9.1` EXIT=0：`checking for __gmpn_zero_p in -lgmp... yes`，
  `libhogweed.a`+`libnettle.a` 构建成功，`test_package` 实际运行
  `hogweed rsa API assertion: 1 passed`。
- 上游 `make check` EXIT=0：`All 116 tests passed`（testsuite）+ `All 3 tests passed`（examples），
  台账 PASS=119 / FAIL=0 / SKIP=1（x86-ibt 预期跳过）。
- `harmonyos_specific_test` EXIT=0：`rsa keygen=1024, sign_tr, verify, tamper-reject`。
- `conan-verify` G0-G4/L2/L4/L5 全 PASS；`finish` EXIT=0（status=built，.ci-result.json 写入）。
- gmp 缓存损坏恢复后 `conan install` EXIT=0：`Downloaded package revision 56b2547c...`。

## 适用边界（applicable_to）

- 在 OHOS/HarmonyOS 上构建、随源码带旧版 `config.sub`/`config.guess` 的 autotools 项目；
- 依赖共享库（尤其 GMP）且 configure 需运行期探测的配方；
- 任何遇到 conan 本地缓存损坏的依赖消费场景。

## 不可适用情形（not_applicable_to）

- ext4/其他 POSIX 文件系统（umask 077 正常，不需要 umask 补丁）；
- CI worker 无 HMDFS（config.guess 可正常探测，无需显式 triple 绕行）；
- 依赖**确实未发布**到制品仓的真实缺失——必须先按 R36 发布依赖，不能用缓存恢复冒充。

## 查重（dedup）

查重范围：`knowledge/{doc,graph,drafts,index.tsv}`。

- config.sub/ohos 要素：E007（config.guess/config.sub 补丁）、E072（config.sub ohos 不识别）、
  E122（linux-ohos kernel validation）、E205/E268（OHOS triplet）已覆盖——本稿为其组合复用与
  配方级落地形态。
- umask 077：E011/E136/E206/E223 已覆盖——本稿补充 conan 构建上下文与配方补丁形态。
- **GMP_NUMB_BITS conftest 运行期加载失败**与 **conan 本地缓存损坏恢复**（含 `e/` 结构校验、
  remove→download→install 恢复序列）：现有 doc/graph/drafts 中未见专条，为本稿新增价值核心。
- `knowledge/drafts/` 无同名/同 stem 草稿；本稿不占用正式 E 编号、不写 `knowledge/doc`、
  `knowledge/graph` 或 `index.tsv`。

## 新增价值

把分散于 E007/E011/E072/E136/E205/E206/E223/E268 的单个陷阱整合为一条可复用的
"OHOS autotools 适配 + 依赖可消费"完整组合流程，并新增两块无既有覆盖的知识：
(1) configure 运行期探测共享库依赖所需的 `LD_LIBRARY_PATH`/`-rpath` 传递（GMP_NUMB_BITS 场景）；
(2) conan 本地缓存损坏的判定与恢复序列（含 `conan remove -c` + 结构校验 + 复验）。
