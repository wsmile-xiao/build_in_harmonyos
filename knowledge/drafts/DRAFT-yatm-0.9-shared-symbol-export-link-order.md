# DRAFT-yatm-0.9-shared-symbol-export-link-order — 传递共享库导出同名符号导致链接顺序抢占与未签名 NEEDED 依赖

> Status: DRAFT
> Source: yatm 0.9 / PR #14051
> PR: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/14051

## 相关既有条目

| 条目 | 已覆盖内容 | 本草稿增量 |
|---|---|---|
| E537 | Conan cache 绝对路径与 SONAME 修复 | 不覆盖“共享库导出同名符号导致静态归档被抢占”的链接顺序机制 |
| E669 | application 消费者运行闭包跳过传递共享库 | 不覆盖“传递共享库反过来抢占静态提供者符号”的构建期链接顺序问题 |
| DRAFT-json-parser-1.1.0-cmakedeps-dual-lib-form-symbol-not-found | 同包内 .a/.so 并存导致 CMakeDeps 误选 | 不覆盖跨包传递共享库导出符号、`--as-needed` 剔除未用 NEEDED 的场景 |

检索关键词：`link order`、`shared symbol export`、`as-needed`、`libpulsecommon`、`sndfile`、`symbol not found`。现有条目均未覆盖本机理。

## Scope

适用于任何使用 Conan + CMake/ld 的包，且满足：

1. 目标实际需要的符号由静态归档提供；
2. 依赖图中存在一个传递共享库导出同名符号；
3. 该共享库出现在静态归档之前；
4. 运行期依赖未签名共享库或错误符号提供者导致失败。

不适用于：必须以共享库形态交付且不能被 `--as-needed` 剔除的依赖。

## Symptom

CI 运行 `yatm` 时出现：

```text
Error loading shared library libpulse-simple.so.0: (needed by .../bin/yatm)
Error loading shared library libpulse-mainloop-glib.so.0: (needed by .../bin/yatm)
Error loading shared library libpulse.so.0: (needed by .../bin/yatm)
Error loading shared library libpulsecommon-17.0.so: (needed by .../bin/yatm)
Error relocating .../bin/yatm: sf_open_fd: symbol not found
Error relocating .../bin/yatm: sf_seek: symbol not found
Error relocating .../bin/yatm: sf_readf_float: symbol not found
```

修复前 `readelf -d bin/yatm` 包含 `libpulse-simple.so.0`、`libpulse-mainloop-glib.so.0`、`libpulse.so.0`、`libpulsecommon-17.0.so`。

## Root Cause

Conan/CMake 把依赖拉平后，`AO_LIBRARIES` 中的 `libpulsecommon-17.0.so` 先于 `SNDFILE_LIBRARIES` 中的 `libsndfile.a` 进入链接命令。`libpulsecommon-17.0.so` 导出了 `sf_*` 符号，链接器按首次命中解析，导致 `libsndfile.a` 没有被拉入；同时未使用的 pulse 共享库被写入 `DT_NEEDED`。由于这些 Conan 端共享库未签名，OHOS loader 拒绝加载，最终表现为 `symbol not found` / `Error loading shared library`。

## Recommended Fix / Workaround

1. 把真正提供符号的静态依赖放在传递共享库之前：

```cmake
target_link_libraries(yatm
    ${SNDFILE_LIBRARIES}
    ${MAD_LIBRARIES}
    ${OGG_LIBRARIES}
    ${SLANG_LIBRARIES}
    ${SOUNDTOUCH_LIBRARIES}
    ${SPEEX_LIBRARIES}
    ${AO_LIBRARIES})
```

2. 在 Conan `CMakeToolchain` 中追加：

```python
toolchain.extra_exelinkflags.append("-Wl,--as-needed")
```

修复后 `NEEDED` 只保留 `libao.so.4`、`libogg.so`、`libslang.so.2`、`libSoundTouch.so.1`、`libc++_shared.so`、`libc.so`；`sf_*` 符号由静态 `libsndfile.a` 解析，pulse 依赖被剔除。

## Fallback

如果不能全局调整链接顺序，用完整路径或链接分组把静态提供者提前；或拆分依赖图，避免传递共享库出现在静态提供者之前。

## Forbidden Approaches

禁止把 `AO_LIBRARIES`（含 pulse 共享库）放在 `SNDFILE_LIBRARIES` 之前。这样会让 `libpulsecommon` 再次抢占 `sf_*` 符号，`NEEDED` 混入未签名 pulse 库，运行期 rc=127。

## Verification

在构建机上执行：

```bash
BIN=$(find "$HOME/.conan2/p" -path "*/yatm*/p/bin/yatm" -type f | sort | tail -1)
PULSE=$(find "$HOME/.conan2/p" -name "libpulsecommon-17.0.so" | head -1)
readelf -d "$BIN" | grep NEEDED
nm -D "$PULSE" | grep -E "sf_open_fd|sf_seek|sf_readf_float"
```

预期：

- `readelf` 不再输出 pulse 相关 `NEEDED`；
- `nm` 证明 `libpulsecommon` 确实导出 `sf_*`，解释抢占机制；
- CI #65894 通过，4/4 消费者检查通过。

## Prevention

- 检查最终 ELF 的 `NEEDED`，不要只看链接是否成功；
- 对“静态提供者 + 传递共享库”的依赖图，把静态提供者放在前面；
- 使用 `--as-needed` 剔除未被引用的共享库；
- 不要假设符号一定来自显式声明的包，必要时用 `nm`/`readelf` 确认实际提供者。

## References

- PR #14051
- CI build #65894
- `archives/y/yatm/0.9/patches/0001-CMakeLists.txt.patch`
- `archives/y/yatm/0.9/conanfile.py`
