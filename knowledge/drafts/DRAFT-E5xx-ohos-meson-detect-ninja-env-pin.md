# DRAFT-E5xx-ohos-meson-detect-ninja-env-pin

## 现象

meson configure 阶段直接失败：

```
ERROR: Could not detect Ninja v1.8.2 or newer
A full log can be found in .../builddir/meson-logs/meson-log.txt
```

ninja 明明已安装且 `ninja --version` 在交互 shell 返回 1.13.1。

## 根因

OHOS 的 musl python3 对 subprocess 的 PATH 裸名解析有缺陷：
`python3 -c "subprocess.run(['ninja','--version'])"` 报
`FileNotFoundError`（posix_spawn 路径），而绝对路径执行正常。
meson 的 `detect_ninja_command_and_version()`（mesonbuild/tooldetect.py）
用 `ExternalProgram('ninja')` 经 PATH 搜索探测，在 conan 重写过的
buildenv 里必现失败。E346（make Error 127）是同根因的 make/cmake 表现。

## 修复

在 conanfile.py 的 `generate()` 里、`tc.generate()` 之前注入 NINJA
环境变量（meson detect_ninja 的第一优先探测源）：

```python
_ninja = shutil.which("ninja") or "/data/service/hnp/bin/ninja"
os.environ["NINJA"] = _ninja
tc.generate()
```

meson configure 成功后，meson compile 内部用探测到的绝对路径 command
列表调 ninja，不再依赖 PATH 搜索。

## 验证

- gtksourceview5 5.22.0 本地 conan create RC=0（335 目标全编译，
  上游 testsuite 26 二进制全链接，UPSTREAM-TESTS passed=2）
- 复现：`env -i PATH=... python3 -c "subprocess.run(['ninja','--version'])"`
  → FileNotFoundError（绝对路径正常）

## 适用范围

所有 OHOS 上的 meson 包（conan MesonToolchain 路径），尤其 CI worker
的 clean buildenv 场景。
