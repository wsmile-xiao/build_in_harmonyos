# DRAFT-8959-raqm-0.11.0-meson-ninja-ld-library-path-whitespace — 设备环境 LD_LIBRARY_PATH 空白污染使 meson 探测 ninja 失败（exit 127）

- 触发事件：raqm 0.11.0 适配，conan create 阶段 meson setup 报 `ERROR: Could not detect Ninja v1.8.2 or newer`
- 路径：Path B（知识库扩展）
- 编号：DRAFT-8959

## 现象

conan create 在 `Meson.configure()`（`meson setup`）最后一步失败：

```
ERROR: Could not detect Ninja v1.8.2 or newer
```

PATH 里明明有 ninja（`/data/service/hnp/bin/ninja --version` 在 bash 里
直接跑正常输出 1.13.1）。

## 根因

设备登录环境的 `LD_LIBRARY_PATH` 带空白污染段（实测值）：

```
...:/system/lib64/chipset-pub-sdk:         /system/lib64:/system/lib64/ndk:/data/storage/el1/bundle/libs/arm64
```

（`chipset-pub-sdk:` 冒号后跟一串空格/tab 再接 `/system/lib64`）

- bash 直接执行 ninja 不受影响；但 python3 `Popen` 子进程继承该变量后，
  OHOS 动态加载器对污染段解析失败——`/data/service/hnp/bin/ninja`
  （NEEDED `libc++_shared.so`，无 RPATH）报
  `Error loading shared library libc++_shared.so` + 数百行
  `Error relocating ...: symbol not found`，exit 127。
- meson 1.12 的 `detect_ninja_command_and_version`（tooldetect.py）用
  `Popen_safe(['ninja', '--version'])` 探测，rc=127 → 判定无可用 ninja。

## 可复用处置

meson 类配方的 `build()` 开头（任何 meson 子进程之前）清洗：

```python
ld = os.environ.get("LD_LIBRARY_PATH", "")
if ld:
    cleaned = ":".join(seg.strip() for seg in ld.split(":") if seg.strip())
    if cleaned != ld:
        os.environ["LD_LIBRARY_PATH"] = cleaned
```

conan 的 `self.run` → `command_env_wrapper` 会 source conanbuild.sh，其
`${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}` 展开取的是子进程继承值（已清洗），
所以只需在 conan 主进程 `os.environ` 做一次。

## 验证

raqm 0.11.0（feat/raqm-0.11.0 分支）：
- 修复前：conan create → meson setup → `Could not detect Ninja`；
- 复现：`source conanbuild.sh && python3 -c "Popen(['ninja','--version'])"`
  → rc 127 + Error relocating；
- 修复后：ninja 10 目标全编译 + `meson test` 51/51 OK + test_package
  `raqm 0.11.0 bidi layout: PASS (resolved RTL, 19 glyphs)`。

## 边界

- 与 E540（PATH 缺 /data/service/hnp/bin，make not found）区分：本条
  PATH 正常、rc=127 + Error relocating；E540 是 FileNotFoundError。
- 空白源于设备环境注入，不同会话可能不出现；配方内清洗是幂等自防御。
