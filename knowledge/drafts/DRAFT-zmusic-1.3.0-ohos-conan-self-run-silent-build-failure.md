# OHOS/HMDFS 上 `self.run("cmake --build ...")` 静默失败

- **草稿 ID**: DRAFT-ZMUSIC-1.3.0-OHOS-CONAN-SELF-RUN-SILENT-BUILD-FAILURE
- **严重度**: 3
- **类别**: conan, ohos, hmdfs, build-environment, flaky-build
- **来源**: zmusic 1.3.0 适配（HarmonyOS PC aarch64）

## 错误特征

```
[  0%] Building CXX object thirdparty/adlmidi/CMakeFiles/adl.dir/adlmidi_midiplay.cpp.obj
make[2]: *** [thirdparty/adlmidi/CMakeFiles/adl.dir/build.make:79: ... .obj] Error 1
make[1]: *** [CMakeFiles/Makefile2:496: thirdparty/adlmidi/CMakeFiles/adl.dir/all] Error 2
make: *** [Makefile:156: all] Error 2

ERROR: zmusic/1.3.0@ohpcd/stable: Error in build() method, line 91
	cmake.build()
	ConanException: Error 2 while executing
```

**辨别性指纹**：满屏 `Error 1` / `Error 2`，但日志里**搜不到任何 `error:` 行**（stderr 只有
warning），且同一条命令在 shell 里手工执行 100% 成功。

## 根因分析

conan 的构建目录位于 HMDFS（`~/.conan2/p/b/<随机目录>/build/Release`）。recipe 的
`build()` 用 `self.run("cmake --build ...")` 驱动构建时，make 在**首批**编译单元上直接失败，
clang 不产生任何错误输出。

已逐项排除：

| 假设 | 验证结论 |
|---|---|
| 并行度过高导致 OOM | ❌ `-j20 / -j4 / -j2 / -j1` 全部复现；`MemAvailable` 有 4.6 GB |
| 构建目录是新建的（HMDFS 首次写入） | ❌ `cmake --build --target clean` 后手工跑仍成功 |
| make jobserver fd 传递问题 | ❌ `-j1`（无 jobserver）同样复现 |
| 环境变量差异 | ❌ `self.run("env")` dump 与手工环境逐项一致 |
| 源码 / 编译器 / 依赖注入问题 | ❌ 手工在同一目录编译、链接、跑测试全部成功 |

结论：根因落在 **conan `self.run` 的实时管道读取路径与 OHOS/HMDFS 构建目录的交互**
—— 子进程被异常终止且不留错误输出。

## 推荐方案

**方法**: `subprocess.run(capture_output=True)`

```python
def build(self):
    cmake = CMake(self)
    cmake.configure()
    jobs = max(1, min(int(build_jobs(self)), 4))
    cmd = f'cmake --build "{self.build_folder}" -- -j{jobs}'
    for attempt in range(1, 4):
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              cwd=self.build_folder, env=os.environ)
        if proc.returncode == 0:
            self.output.info(proc.stdout[-2000:])
            break
        tail = (proc.stdout or "") + (proc.stderr or "")
        self.output.warning(f"构建第 {attempt}/3 次失败（rc={proc.returncode}）:\n{tail[-2000:]}")
        if attempt == 3:
            raise ConanException(f"cmake --build 连续 3 次失败:\n{tail[-4000:]}")
        time.sleep(5)
```

`test_package/conanfile.py` 的 `build()` 同样处理。

### ⚠️ 不要用 `CMake.build(build_tool_args=...)`

该参数是**追加**在默认 `-j<核数>` 之后：

- 传 `["--", "-j4"]` → `-- -j20 -- -j4` → make 报 `No rule to make target '-j4'`
- 传 `["-j4"]` → `-- -j20 -j4` → GNU make 以**第一个** `-j` 为准，等于没限制

## 排查提示

`make` 报 `Error 1` 却搜不到 `error:` 行、且手工重跑同一命令即成功时：

1. **不要再怀疑源码、编译器或并行度**——直接换执行方式（subprocess 或重定向到文件）
2. 优先在同一个 conan 生成的构建目录里手工复跑一次 `make -j4`，作为"是环境还是配方"的判定开关

## 关键词

self.run, cmake --build, make Error 1, 无 error 输出, 静默失败, HMDFS, OHOS,
conan build(), subprocess, capture_output, jobserver, 手工重跑成功
