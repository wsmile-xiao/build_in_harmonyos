# DRAFT — OHOS Python ctypes 按 platform.system() 选动态库后缀落空（audioflux 0.1.9）

**对应 .kv:** `DRAFT-audioflux-0.1.9-python-ctypes-platform-harmonyos.kv`

## 问题

`import audioflux` 直接抛 `ValueError: Platform[harmonyos] is not support.`（python/audioflux/fftlib.py:47）。

根因：OHOS 设备 Python 的 `platform.system()` 返回发行版定制的 `"HarmonyOS"`（实测
`platform.system().lower()` == `'harmonyos'`）。audioflux 的 fftlib.py `get_fft_lib_name()`
按 `system` 分支构造 ctypes 加载的动态库文件名后缀：

```python
if system == 'darwin':   suffix = 'dylib'
elif system == 'linux':  suffix = 'so'
elif system.startswith('win'): suffix = 'dll'
else: raise ValueError(f'Platform[{system}] is not support.')
```

HarmonyOS 无分支命中 → 直接 ValueError，任何 `import audioflux` 都失败（ctypes 尚未加载库）。

## 根因

与既有草稿 DRAFT-bs-thread-pool-5.1.0-ohos-python-platform-system 同根因：OHOS Python
`platform.system()` 返回 `"HarmonyOS"` 而非上游预期的 Linux/Darwin/Windows 之一。
差异点：bs-thread-pool 是**构建期**脚本按 OS 分支选编译器；本候选是**运行期** ctypes
按 OS 分支选动态库文件名后缀——同触发、同根因、不同应用阶段（边界扩展）。

## 方案

最小补丁把 HarmonyOS 与 linux 同判 `.so`（OHOS 为 ELF 动态库形态，与 Linux 一致）：

```python
elif system in ('linux', 'harmonyos'):
    suffix = 'so'
```

补丁文件：`patches/0001-python-audioflux-fftlib.py.patch`（conandata.yml 引用），
对官方 tag v0.1.9 逐字应用。

## 验证（本轮真实日志）

1. `python3 -c "import platform; print(platform.system())"` → `HarmonyOS`
2. 修复前：conan create test_package `import audioflux` → `ValueError: Platform[harmonyos] is not support.`
3. 修复后：conan create test_package → 3 checks PASS：
   - `CHECK: MelSpectrogram.spectrogram -> shape=(128, 5), finite=True`
   - `CHECK: audioflux.__version__ = 0.1.9`
   - `CHECK: ctypes loaded .../libaudioflux.so (via fftlib)` → `PASS: 3 consumer checks`

## 适用边界

- 适用：经 ctypes 按 `platform.system()` 构造动态库文件名后缀的 python 包（fftlib 模式）
- 反例：用 `find_library`/`ctypes.util` 的包（走 E068 方案，非本候选）；构建期 OS 分支脚本（DRAFT-bs-thread-pool）

## 查重差异（七轴对照 DRAFT-bs-thread-pool-5.1.0-ohos-python-platform-system）

| 轴 | 结果 | 说明 |
|---|---|---|
| exact_duplicate | false | 阶段不同：构建期编译器 vs 运行期库加载 |
| causal_duplicate | false | 同根因但方案落点不同 |
| trigger_overlap | true | platform.system() 返回 HarmonyOS |
| solution_overlap | true | 都并入 Linux/HarmonyOS 判定 |
| combination_novelty | false | 非组合创新 |
| boundary_novelty | true | 从构建期扩展到运行期 ctypes 库名选择 |
| test_migration_novelty | false | 无测试迁移 |

决定：`new_draft`（部分重复，新增差异已由本轮真实日志验证并可跨库复用）
