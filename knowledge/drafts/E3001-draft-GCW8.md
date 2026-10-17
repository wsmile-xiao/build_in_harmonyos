# DRAFT-E3001：Waf 私有 Python 构建系统跨平台（OHOS）适配

- **触发实例**：samba 4.21.0 适配（2026-09-21，任务 samba，分支 feat/samba-4.21.0，wafsamba + 内置 waf + conan recipe）
- **错误签名**：`The configuration failed` / `PYTHONHASHSEED=1 missing! Don't use waf directly, use ./configure and make!` / `IN_LAUNCH_DIR` / `Could not build a python embedded interpreter`
- **类别**：build-system（Samba waf 生态）
- **严重度**：3（configure 确定性中断）

## 症状（可复现）

在 OHOS aarch64 上按常规姿势直接执行 waf：

```text
PYTHONHASHSEED=1 missing! Don't use waf directly, use ./configure and make!
# 或在未放源码根目录时：
configure: error: IN_LAUNCH_DIR: must run configure from the source root
# 或 pyembed 探针失败：
Testing pyembed configuration : Could not build a python embedded interpreter
err: ld.lld: error: unable to find library -lintl
```

## 根因

Samba 系（samba/tdb/talloc/tevent/ldb）用自带 waf（wafsamba）而非 autotools/cmake：

1. **调用链要求**：`configure` 包装脚本执行 `$PYTHON buildtools/bin/waf configure "$@"`（要求 `PYTHON` 指向可用 python3；脚本自行 `export PYTHONHASHSEED=1`、`unset LD_PRELOAD`）；`make` 包装脚本以 `WAF_MAKE=1` 调 waf。必须**源码根目录原地构建**——`wscript` 的 `conf.IN_LAUNCH_DIR()` 决定 standalone 语义。
2. **交叉编译注入**：需要 `CROSS_COMPILE`/目标三元组 + 交叉 clang（绝对路径），以及 `PKG_CONFIG_PATH`/`CPATH`/`LIBRARY_PATH`/`PERL5LIB` 等环境单点注入。
3. **pyembed 探针**：python3-config --embed 输出 `-lintl`，musl 无 libintl → 连锁失败（C-only 包用 `--disable-python` 规避）。

## 方案（可跨库复用）

1. **conan 配方内封装 `_waf`**：`configure`/`build`/`install` 全部经包装脚本，`PYTHON` 指向 python3，`PYTHONHASHSEED` 保证可复现；
2. **`_build_env` 单点注入**：CC/CXX/AR/RANLIB（交叉 clang 绝对路径）、PKG_CONFIG_PATH、CPATH、LIBRARY_PATH、PERL5LIB；
3. **裁剪透传**：`--without-ad-dc`/`--disable-python` 等（OHOS 无对应能力时如实裁剪并记录）；
4. 交叉探针用真实语义（CROSS_COMPILE 三元组），不伪造 `--cross-answers` 全量预填。

## 验证

```sh
PYTHON=python3 ./configure --prefix=$PREFIX --disable-python && make -j$(nproc) && make install
```

conan create 端到端绿（samba 4.21.0：waf configure ✅ → build [3571/3571] ✅ → install ✅ → Package created）。

## 边界 / 禁止

- 不直接执行 `buildtools/bin/waf`（缺 PYTHONHASHSEED 拒绝）；
- 不硬编码设备路径、不注入 `-D__OHOS__`（R8/PF5）；
- 不为探针伪造通过结果。

## 关联

- 强关联：TD2 同族独立库（tdb/talloc/tevent/ldb）同用 waf，DRAFT-11055 为 Samba 独立库同族范式。
- 触发 PR：!11515（samba 4.21.0）。
