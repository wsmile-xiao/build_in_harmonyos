# quill — HarmonyOS 适配归档

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | quill |
| 版本 | 13.0.0 |
| 上游 | https://github.com/odygrd/quill |
| 类型 | C++17 header-only 异步日志库（内置 bundled fmt） |

## 归档列表

| 版本 | 状态 | 说明 |
|------|------|------|
| 13.0.0 | published | CMake header-only 配方；OHOS /tmp 只读适配（TMPDIR）；上游 419/419 测试通过 |

## 鸿蒙适配要点

- quill 为 CMake INTERFACE header-only 库，配方 `package_type=header-library`，强制 `QUILL_ENABLE_INSTALL=ON` 导出头文件。
- OHOS `/tmp` 只读：BackendWorkerLock 锁文件与测试捕获流改为 `$TMPDIR` 解析（见 `13.0.0/patches/`）。
- 无 .so/.a 产物，无需 commands.json（R38）。

## 下游消费

```python
self.requires("quill/13.0.0")
```

消费侧需链接 Threads（pthread）。