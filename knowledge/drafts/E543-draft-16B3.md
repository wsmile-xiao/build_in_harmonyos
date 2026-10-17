# E543-draft-16B3 — OHOS 上 CPython subprocess 不按 PATH 解析可执行名（meson 探测 llvm-ar 失败）

- 来源软件：kea-hook-limits 3.0.3（ISC Kea 3.0.3，Meson 全树构建）
- 日期：2026-09-16
- 状态：草稿（待审核 promote 为正式条目）

## 错误面

```
meson.build:17:0: ERROR: Unknown linker(s): [['llvm-ar']]
The following exception(s) were encountered:
Running `llvm-ar --version` gave "[Errno 2] No such file or directory: 'llvm-ar'"
```

meson-log 中对应行：`Detecting archiver via: 'llvm-ar --version' -> [Errno 2] No such file or directory: 'llvm-ar'`

## 根因（实测取证）

1. 宿主环境导出 `AR=llvm-ar`（裸名），meson 的 `detect_static_linker` 直接采用该值。
2. meson 用 Python `subprocess` 执行 `llvm-ar --version`。在 OHOS(musl) 上 CPython 3.12
   的 subprocess 走 `posix_spawn` 路径，**不按 PATH 解析不含 `/` 的可执行名**，直接
   `execve("llvm-ar")` → `FileNotFoundError: [Errno 2]`。
3. 同环境下的对照实验（同一次 shell，同一 PATH）：

   ```
   $ which llvm-ar                 → /data/service/hnp/bin/llvm-ar   (rc=0)
   $ python3 -c "import shutil; print(shutil.which('llvm-ar'))"
                                   → /data/service/hnp/bin/llvm-ar
   $ python3 -c "import subprocess; subprocess.run(['llvm-ar','--version'])"
                                   → FileNotFoundError: [Errno 2] No such file or directory: 'llvm-ar'
   ```

   即：PATH 里确实有 llvm-ar，但 subprocess 用裸名无法启动它 —— 这是 OHOS 平台行为，
   与“PATH 未提供工具”是两类不同的故障。

## 修复（最小改动）

在 conanfile 的 `generate()` 里把归档工具以**绝对路径**写进 meson machine file：

```python
compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
cc = compilers.get("c") if compilers else None
if cc:
    tool_dir = os.path.dirname(cc)          # /data/service/hnp/bin
    tc.binaries["ar"] = os.path.join(tool_dir, "llvm-ar")
    tc.binaries["ranlib"] = os.path.join(tool_dir, "llvm-ranlib")
```

生成的 `conan_meson_native.ini` 得到：

```ini
[binaries]
c = '/data/service/hnp/bin/clang'
cpp = '/data/service/hnp/bin/clang++'
ar = '/data/service/hnp/bin/llvm-ar'
ranlib = '/data/service/hnp/bin/llvm-ranlib'
```

## 验证

| 阶段 | 结果 |
|------|------|
| 不带注入 | `meson setup` exit 1，报 Unknown linker(s) |
| 注入绝对路径后 | `meson setup` exit 0（242 构建目标） |
| 后续构建 | `ninja` 255 目标 0 错误；上游测试 207/207 通过；`conan create` exit 0 |

## 推广范围

任何在 OHOS 上运行、且把外部工具名（不经绝对路径）交给子进程的构建系统或脚本都适用：
autotools 的 `AR` 探测、CMake 的 `CMAKE_AR` 查找、自定义 shell/python 探测脚本等。
判定口径：**OHOS 上不要依赖 PATH 解析裸可执行名，配置里一律写绝对路径。**

## 关联

- E481：同现象（llvm-ar 探测失败），根因登记为“SDK profile 只声明 clang”；本条目给出
  实测根因（subprocess PATH 解析失效），修复动作一致。
- E090：Meson 在 OHOS 上报 `harmonyos`（同一 Kea 任务命中）。
- E091：`sockaddr_storage` 重定义（同一 Kea 任务命中）。
