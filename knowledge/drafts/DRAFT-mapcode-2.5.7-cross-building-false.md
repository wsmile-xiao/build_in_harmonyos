# DRAFT — `cross_building()` 在 OHOS 同 profile 双传时恒为 False

> Status: **Draft**（待主编 promote） | severity: `2` | category: `build-system` | Updated: 2026-09-26
> 源文件：`knowledge/drafts/DRAFT-mapcode-2.5.7-cross-building-false.kv`
> 来源：mapcode 2.5.7 适配（`feat/mapcode-2.5.7`）

---

**关键词**：cross_building, settings_build, -pr:h, -pr:b, qemu-aarch64, binfmt_misc, -static

## 现象（error_signature）

```text
aarch64-binfmt-P: Could not open '/lib/ld-linux-aarch64.so.1': No such file or directory
```

同时在 test_package 里实测到判定与事实相反：

```text
PROBE host  os=OHOS arch=armv8
PROBE build os=OHOS arch=armv8
PROBE cross_building = False      # 但构建机是 x86_64，产物是 aarch64
```

## 根因（root_cause）

`build_and_test.sh` 用**同一个** profile 文件同时传给 `-pr:h` 与 `-pr:b`：

```bash
CONAN_CREATE_ARGS+=(-pr:h="$PROFILE_FILE" -pr:b="$PROFILE_FILE")
```

而 `cross_building()` 的实现是「比较 `settings_build` 与 `settings` 的 os/arch」：

```python
if host_os is not None and (build_os != host_os): return True
if host_arch is not None and (build_arch != host_arch): return True
return False
```

两段被解析成完全相同的 `os=OHOS arch=armv8` → 返回 `False`。
于是惯用写法

```python
if cross_building(self):
    self.run(f'qemu-aarch64 {binary}')
else:
    self.run(binary)                       # ← 实际走这里，直接 exec aarch64 产物
```

在 x86_64 构建机上直接执行 aarch64 ELF，命中宿主 `binfmt_misc` 后找不到 OHOS 动态链接器。

## 处方（rec_approach）

1. **以构建机 CPU 判定**，不再信任 `cross_building()`：

   ```python
   return cross_building(self) or platform.machine().lower() not in ("aarch64", "arm64")
   ```

2. **静态链接**（`tc.extra_exelinkflags.append("-static")`，仅链接期）：
   静态 aarch64 可执行文件在 `qemu-user` 下无需设备根文件系统即可运行。

两者缺一不可：只改判定不加 `-static`，qemu 仍会因缺
`/lib/ld-linux-aarch64.so.1` 失败。

## 备选（fallback）

宿主已注册 `binfmt_misc` 时可以直接 `self.run(<静态产物>)`，不写任何判定。
实测 `archives/t/tsl-ordered-map/1.1.0` 正是这样「碰巧」通过的
（其 `cross_building` 分支永不触发）。缺点是依赖宿主 binfmt 配置，换机器/CI 即失效。

## 反模式（forbid_1）

```text
if[[:space:]]+cross_building\(self\)[[:space:]]*(:|\))[^\n]*qemu
```

只靠 `cross_building()` 判定的 qemu 分支在本仓 profile 下永不触发，
测试会在 x86_64 构建机上直接 exec aarch64 产物而失败，
且报错信息（缺 OHOS 动态链接器）极具误导性，易被误判为「平台不兼容」。

## 验证

```bash
conan create <recipe> -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
```

在 test_package 的 `test()` 里打印 `self.settings_build.get_safe("os")`：
看到 `Linux` 说明 profile 两段不同（本条不命中）；看到 `OHOS` 即命中本条。

---

*本条目为草稿。正式化请用 `ohc-run.py graph promote` 提升到 `knowledge/graph/`。*
