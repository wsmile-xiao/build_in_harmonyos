# continuable 4.2.2 HarmonyPC 适配笔记

## 结论

已完成 `continuable/4.2.2` 的 Conan 头文件库适配。配方、消费者测试和归档
文件位于本目录；本地 worktree 的最终提交和 HarmonyOS 设备验证结果以任务结束
报告为准。状态保持 `built`，因为尚未执行合并后的 release upload，不能标记
`published`。

## 源码与依赖

- 上游：<https://github.com/Naios/continuable>
- tag commit：`23a724cf5c3026155550dc802d283d713fdfd97e`
- 官方源码归档：`https://github.com/Naios/continuable/archive/refs/tags/4.2.2.tar.gz`
- SHA256：`49bf82a349b26c01194631e4fe5d1dbad080b3b4a347eebc5cf95326ea130fba`
- 构建系统：CMake；库本体为 C++14 header-only
- 依赖：`function2/4.2.3`

上游 CMake 对 `function2` 只要求 major version 4。当前 ohpcd 远端实证为：

```text
conan download "function2/4.2.3" -r=ohpcd --only-recipe
Download completed in 0s
function2/4.2.3#3bb3d3a7bee78533b746794a70d3b512

conan download "function2/4.2.4" -r=ohpcd --only-recipe
ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]
```

因此没有把 ConanCenter 当前 recipe 的 `function2/4.2.4` 直接写入本适配：它在
本次目标制品仓不可下载；选择已发布的 4.2.3 有明确版本兼容依据和远端证据。

## 配方设计

- `conanfile.py` 使用 `header-library`、空 package ID、C++14 校验和官方源码
  SHA256 校验。
- 只复制 `include/continuable` 与 LICENSE，不生成静态/动态库。
- OHOS 与 Linux 均传播 `pthread`；系统判断使用 `in ("Linux", "OHOS")`。
- `build()` 保留 `apply_conandata_patches()` 钩子；本版本无 OHOS 源码补丁，
  `patches: []`，未创建 `patches/` 目录。
- 没有 `commands.json`：这是库而不是可执行工具。

## 测试设计与统计口径

上游 `test/` 的 CMake 注册 12 个 CTest 测试：线程 1、链接 1、单元单步 1、
异步 1、多步 5、ready 多步 1、mock 1、playground 1。GitHub 源码归档不带
submodule 内容，所以 Conan recipe 不在空目录上伪称运行上游测试；设备端使用
同一 tag 检出并初始化 continuable 所需的 4 个顶层 submodule 后执行完整上游测试。
递归初始化 function2 自身的测试 submodule 时，设备记录了：
`fatal: Unable to find current revision in submodule path 'dep/function2/function2/test/googletest'`；
该嵌套测试目录不被 continuable 注册的 12 个顶层 CTest 测试引用，因此未将其
伪计入通过项，顶层 submodule 仍按实际命令完成构建和测试。

适配后的 `test_package` 编译并运行 `test_continuable`，包含 3 个实际断言：
`then`/`to_future` 链式结果、`when_all` 聚合结果、`fail` 异常恢复结果。

最终设备证据（详见设备日志）为：

```text
上游：注册 12，实际执行 12，通过 12，失败 0，跳过 0
test_package：注册 1，实际执行 1，通过 1，失败 0
```

## 未执行项

- 本地 macOS 未执行 Conan 构建；按工作区规则只做静态检查，Conan create 和
  HarmonyOS 运行验证在 `ssh hm` 设备端执行。
- PR 创建、`/rebuild`、CI、AI Review 和 release upload 在适配完成后按工作区流程执行；
  本笔记中的设备证据对应创建 PR 前的验证阶段。

## 结束

本适配阶段的文件交付已关闭；设备命令、日志路径和最终 SHA 在任务报告中记录。
