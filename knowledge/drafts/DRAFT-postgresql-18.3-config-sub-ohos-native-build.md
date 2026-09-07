# DRAFT-postgresql-18.3-config-sub-ohos-native-build

> 草稿知识项 — 显式 --build=aarch64-linux-ohos 免外置 config.sub/config.guess
> 来源：postgresql 18.3 Conan 配方化（feat/postgresql-18.3，2026-09-03）
> 同 stem 配对：`knowledge/drafts/DRAFT-postgresql-18.3-config-sub-ohos-native-build.kv`

## 问题（现象 / error_signature）

- 旧适配方案（2026-06 手动构建 build.sh）依赖从
  `$HOME/usr/local/share/config/` 拷贝外置 config.sub/config.guess
  进源码树，该路径在当前环境已不存在、CI 干净环境更不可依赖。
- 不拷贝时，configure 若需推导 build 平台会调用 config.guess，
  其数据库不识别 OHOS 且其临时文件探测在 hmdfs 上受 umask 077 破坏。

## 根因（root_cause）

1. PG 18.3 官方 tarball 自带的 `config/config.sub`（较新版本）已能识别
   `aarch64-linux-ohos` triplet——旧方案外置拷贝针对的"自带不识别"前提已失效。
2. configure 的 `AC_CANONICAL_HOST` 逻辑：用户显式传 `--build=<triplet>`
  后**完全跳过 config.guess 调用**（config.guess 仅在 build_alias 为空时运行），
  其两大问题（不识别 OHOS、hmdfs umask）同时绕开。
3. OHOS PC 本机即 aarch64 OHOS，构建为原生（非交叉）模式，
  host==build==target，与历史手动构建语义一致。

## 可复用方案（rec_approach: explicit-build-triplet-skip-config-guess）

1. 先确认自带支持：`grep -c "ohos" <src>/config/config.sub`（>= 1）。
2. 配方 `generate()` 中（`settings.os == "OHOS"` 时）：
   ```python
   tc.configure_args.append("--build=aarch64-linux-ohos")
   ```
3. 不拷贝任何外置 config.sub/config.guess。
4. **umask 077→022 修复仍需保留**：显式 --build 只解决 config.guess，
   configure 自身 conftest 的 hmdfs 临时目录问题独立存在。

## 适用条件

- OHOS PC 原生（非交叉）构建；
- 软件自带 config.sub 版本 >= 2024-01-01（含 `*-linux-ohos`）；
- PG 18.x 全系；其他含新版 config.sub 的 autotools 软件同理。

## 反例（不适用场景）

- 真·交叉编译（build != host）时 --build/--host 都要显式给出且值不同；
- 自带 config.sub 过旧（不识别 ohos）——此时仍需补丁更新 config.sub
  （而非依赖外置路径拷贝）；
- 非 conan 的裸机构建（无 DESTDIR 语义差异时）不涉及本条的 CI 依赖问题。

## 验证证据（真实命令 + 结果）

- `grep -c "linux-ohos" postgresql-18.3/config/config.sub` 命中；
- `configure --build=aarch64-linux-ohos ...` 全参数成功
  （2026-09-03 本机实测，无外置 config 拷贝）；
- `conan create` G2 PASS；W3 本地 CI 全绿。

## 限制与恢复条件

- 结论绑定 PG 18.3 tarball 的 config.sub 版本；升级 PG 大版本时需重验 grep；
- 若未来 conan profile 进入真交叉模式（如 x86 主机构建 OHOS 目标），
  需改为显式 `--build=<build_triplet> --host=aarch64-linux-ohos` 双参数。
