# OHOS 无 whoami：CMake 构建信息注入 STRIP 崩溃 → DISABLE_BUILDINFO=ON

> **适用范围**：所有在 configure 阶段注入 whoami/hostname/git revision 构建信息的 CMake
> 项目（SetBuildInfo.cmake 模式及其同类），OHOS 平台跨库通用。

## 问题

libcec 8.1.7（CMake 构建）configure 失败：

```
CMake Error at src/libcec/cmake/SetBuildInfo.cmake:39 (string):
  string sub-command STRIP requires two arguments.
```

## 根因

上游 `SetBuildInfo.cmake` 非 Windows 分支：

```cmake
find_program(WHOAMI_BIN whoami /bin /usr/bin /usr/local/bin)
execute_process(COMMAND "${WHOAMI_BIN}" OUTPUT_VARIABLE BUILD_USER)
string(STRIP ${BUILD_USER} BUILD_USER)   # ← OHOS 无 whoami，BUILD_USER 为空 → 崩溃
```

OHOS 设备没有 `whoami`（`command -v whoami` → exit 127），`BUILD_USER` 未定义，
`string(STRIP ...)` 缺参报错，configure 以 "Configuring incomplete, errors occurred!" 结束。
同类隐患：`hostname -f`、`git rev-parse` 注入块（git 有仓库时可用，whoami 必缺）。

## 方案：官方 DISABLE_BUILDINFO=ON（零补丁）

libcec 上游自带"可复现/嵌入式构建"开关（与 `SOURCE_DATE_EPOCH` 同语义）：

```bash
cmake -DDISABLE_BUILDINFO=ON ...      # 跳过整个构建信息注入块
```

Conan 配方（generate()）：

```python
tc = CMakeToolchain(self)
tc.variables["DISABLE_BUILDINFO"] = "ON"
```

**为什么不用补丁**：改 SetBuildInfo.cmake 需维护 patches/，且上游官方选项已支持；
关闭的只是信息注入（版本号仍由 VERSION 属性写入），不影响产物功能。

## 验证（libcec 8.1.7，OHOS aarch64）

- 无该选项：configure 必失败（`string(STRIP)` 报错）→ 复现；
- 加 `-DDISABLE_BUILDINFO=ON`：configure 成功 → CMake 构建 → conan create
  （ohpcd/stable）→ W3 本地 CI（L0-L5 pass，`.ci-result.json` exit_code=0）→ 全部通过。

## 通用排查步骤

1. configure 阶段报 `string sub-command STRIP requires two arguments`（或类似缺参）→
   先查上游是否有 DISABLE_BUILDINFO / REPRODUCIBLE / BUILD_INFO 开关；
2. 有 → 直接用官方开关（本条目方案）；
3. 无 → 再考虑 patch：将 `execute_process(whoami)` 块加 `if(WHOAMI_BIN)` 守卫或
   改为 `${CMAKE_COMMAND} -E ...` 可移植写法。

## 边界与反例

- 仅适用于"构建信息注入依赖外部命令（whoami/hostname）"的 CMake 项目；
- 关闭信息注入不等于关闭版本号：`VERSION`/`SOVERSION` 仍由 CMake 属性写入，产物版本正常；
- 若上游选项名不同（如 `DISABLE_BUILDINFO`、`ENABLE_REPRODUCIBLE_BUILDS`），按实际排查。

## 关联

- similar_to：E117（cmake configure_file 模板域，触发器不同）
- 相关规则：R39（官方选项优先）、R33（不依赖未定义 shell 环境变量）
