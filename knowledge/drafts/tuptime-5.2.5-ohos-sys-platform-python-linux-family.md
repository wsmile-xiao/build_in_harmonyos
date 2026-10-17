# Python 程序在鸿蒙PC上的 sys.platform 判定：'ohos' 必须并入 Linux 族

> Draft: `DRAFT-TUPTIME-525-OHOS-SYS-PLATFORM-PYTHON-LINUX-FAMILY`
> Stem: `tuptime-5.2.5-ohos-sys-platform-python-linux-family` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-TUPTIME-525-OHOS-SYS-PLATFORM-PYTHON-LINUX-FAMILY
- **严重度**: 2
- **类别**: platform|compat
- **触发工具**: manual|conan
- **阶段**: porting

## 错误特征

```console
$ python3 src/tuptime -f /tmp/x/tuptime.db
ERROR:root:System = ohos not supported
$ echo $?
1
```

而工具本身完全正常（Python 标准库程序，无编译）。

## 根因

CPython on OpenHarmony：

```console
$ python3 -c "import sys, platform; print(sys.platform); print(platform.platform())"
ohos
HarmonyOS-HongMeng_Kernel_1.12.0-aarch64-64bit
```

`sys.platform` 是 **`'ohos'`**，不是 `'linux'`。上游 tuptime 5.2.5 的后端选择是：

```python
    if sys.platform.startswith('linux'):
        sis = os_linux(sis)
    elif sys.platform.startswith(('freebsd', 'darwin', ...)):
        sis = os_bsd(sis)
    else:
        logging.error('System = %s not supported', sys.platform)
        sys.exit(1)
```

于是落进 `else`，**一条记录都没写就退出**。

## 关键判断：OHOS 是 Linux 族，不是"又一个 OS"

鸿蒙PC 用 HongMeng 内核，但对上层暴露的就是 Linux 接口 —— `os_linux()` 消费的
全部接口实测可用：

| 接口 | 实测 |
|---|---|
| `/proc/uptime` | `3415.15 23628.47` |
| `/proc/stat` | `btime` 行可读 |
| `/proc/sys/kernel/random/boot_id` | `31df778d-ff59-481c-99bd-c1eb317eca43` |
| `clock_gettime(CLOCK_BOOTTIME/MONOTONIC)` | 可用（btime 由二者差值算出） |

所以正确做法是**并入**，不是**重写**：

```diff
-    if sys.platform.startswith('linux'):
+    if sys.platform.startswith(('linux', 'ohos')):
         sis = os_linux(sis)
```

修复后 `-v` 日志：`INFO:System = Linux`，完整汇总报告，`EXIT=0`。

## 推荐方案

**方法**: `add-ohos-to-linux-family-branch`

1. **先实测**：`python3 -c "import sys;print(sys.platform)"`，不要照文档假设是 `'linux'`。
2. **并入 Linux 分支**（`startswith(('linux','ohos'))` / `in ('linux','ohos')`）——
   这是实质适配（走完 Linux 后端全路径），不是 stub。
3. **不要**为 OHOS 新写一套后端（重复代码、无从验证）；
   **不要**用 try/except 把"不支持"吞掉（掩盖真正的不兼容）。
4. Python 补丁 `patch_type: portability`，无平台宏（R8 的 `__OHOS__` 禁令面向 C）。
5. `test_package` 留一条**仅 OHOS 生效**的回归用例：断言走 Linux 后端、rc=0、
   不出现 `not supported` —— 移除补丁该用例即失败。

## 验证命令

```bash
python3 scripts/ohc-run.py refresh-patch --auto <name> <ver>   # 生成 patches/0001-*.patch
python3 <pkg>/bin/<tool> -f <writable-db>; echo "exit=$?"      # 期望 0
```

## 取证记录

- 包: tuptime 5.2.5（`archives/t/tuptime/5.2.5`）
- 逐字证据: `reports/upstream-tests.log`、`reports/conan-create.log`（test_package 段）
