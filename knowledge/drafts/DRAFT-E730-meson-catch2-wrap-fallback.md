# DRAFT-E730 — meson dependency() 系统查优先、wrap 回退（catch2 实测）

- **任务**: libnpy 1.0.1（2026-09-25）
- **号段**: DRAFT-E730（`knowledge_id.py --claim` 三面扫描取号）
- **状态**: DRAFT — 待维护方审入 graph

## 现象

`tests/meson.build` 用 `dependency('catch2')` 获取断言框架，设备上 conan 侧虽有
`catch2/2.13.10-r0`，但 `meson setup` 日志显示系统查未命中：

```
Run-time dependency catch2 found: NO  (tried pkg-config and cmake)
Looking for a fallback subproject for the dependency catch2
Downloading catch2 source from https://github.com/catchorg/Catch2/archive/v2.13.8.tar.gz
Downloading catch2 patch from https://wrapdb.mesonbuild.com/v2/catch2_2.13.8-1/get_patch
Dependency catch2 for host machine from subproject subprojects/Catch2-2.13.8 found: YES 2.13.8
```

## 根因

meson `dependency()` 解析顺序 = **pkg-config → cmake（系统查）→ subproject wrap 回退**。
conan `catch2/2.13.10-r0` 只声明 `cmake_file_name=Catch2`（无 `pkg_config_name`），
且 `find_package(catch2)` 与 `Catch2Config.cmake` 大小写在大小写敏感文件系统上不匹配，
系统查必然未命中 → 稳定走 wrap 回退。设备与 CI worker 实测 GitHub 与 wrapdb 两条下载链
均可达，wrap 文件的 `source_hash`/`patch_hash` 锁定内容，可复现。

## 处置口径

1. **默认允许回退**：保持上游原样 `meson setup`，不加 `--wrap-mode`。
2. **只有无网络环境**才 conan 化依赖：`PkgConfigDeps` 暴露与 `dependency()` 同名的 `.pc`
   （`pkg_config_name` 必须等于 `catch2`）→ `PKG_CONFIG_PATH` 让系统查先命中 → 再加
   `--wrap-mode=nodownload`。顺序反了会直接 setup 失败。
3. `found: NO` 本身**不是错误**，判绿看其后的回退是否成功。

## 复现命令（设备可直接执行）

```bash
# 1) 看本轮实测日志（两行都在 = 走了系统查未命中 → wrap 回退）
grep -E "found: NO \(tried pkg-config and cmake\)|Downloading catch2 source" \
  "$HOME/tmp/libnpy-1.0.1/native-setup.log"
# 2) 从 pristine 源重跑（wrap 重新下载）
TD="$HOME/tmp/libnpy-1.0.1"
SRC="$HOME/ws/tmp/builds/libnpy-1.0.1.work"
HOME="$TD/test-home" PATH="$TD/test-home/.local/bin:$PATH" \
  meson setup "$SRC/tests/builddir-repro" "$SRC/tests" 2>&1 | \
  grep -E "found: NO|Downloading catch2|found: YES"
```

日志证据：`$HOME/tmp/libnpy-1.0.1/native-setup.log`（2026-09-25 原生测试轮）。
