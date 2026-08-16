# liquid-dsp 1.8.0.1 B 类知识库扩展证据

## 申报结论

建议按 B 类“知识库扩展”申报，候选知识为
`knowledge/drafts/E327-draft-D220.{kv,md}`：

> CMake static-only 构建不得修改安装导出的逻辑包身份；target/制品变体与
> Config/Targets/install directory 使用的 package identity 必须分离。

该模式不依赖 liquid-dsp API，可迁移到任何同时生成 static/shared 目标和 CMake
package export 的工程。

## 问题因果链

上游 v1.8.0 的 `CMakeLists.txt` 在 static-only 分支执行：

```cmake
add_library(${LIBNAME}-static STATIC ...)
set_target_properties(${LIBNAME}-static PROPERTIES OUTPUT_NAME ${LIBNAME})
if(NOT BUILD_SHARED_LIBS)
    set(LIBNAME ${LIBNAME}-static)
endif()
```

变异后的 `LIBNAME` 继续驱动 `export(EXPORT ${LIBNAME}Targets)`、
`install(EXPORT ...)`、Config 文件名、安装目录和 include path。与此同时，
`cmake/Config.cmake.in` 以不可变的 `@PROJECT_NAME@` include
`@PROJECT_NAME@Targets.cmake`。

因此 static-only 安装得到 `liquid-staticConfig.cmake` 和
`liquid-staticTargets.cmake`，Config 内部却引用 `liquidTargets.cmake`；消费者按稳定
项目名调用 `find_package(liquid)` 时也没有 `liquidConfig.cmake` 可发现。

当前补丁只停止修改逻辑 `LIBNAME`。真实 target 仍为 `liquid-static`，导出 target
仍为 `liquid::liquid-static`，磁盘制品仍通过 `OUTPUT_NAME` 为 `libliquid.a`；变化只限
Config/Targets/install export 回到稳定的 `liquid` 身份。

## 真机 before/after 证据

- 设备：OpenHarmony PC，AArch64，clang 15.0.4
- Run ID：`xuguowei-liquid-dsp-issue-2206-path-b-evidence-r3-20260815-225009-42915`
- 时间：2026-08-15 22:50:09 至 22:50:52 +0800
- runner：`ohos-test-runner.sh --mode heavy --try-lock`
- 锁：0 秒取得，run 结束后释放
- 总退出码：0

对照双方复制同一个隔离 Conan source cache；该 source cache 是下载后、进入
`build()` 应用补丁前的上游 v1.8.0 源码。两份构建的唯一源码差异是
`0001-cmakelists-static-config.patch`。

| 断言 | 修复前 | 修复后 |
|---|---|---|
| canonical `find_package(liquid)` | 失败，返回 1 | 通过 |
| Config | `liquid-staticConfig.cmake` | `liquidConfig.cmake` |
| Targets | `liquid-staticTargets.cmake` | `liquidTargets.cmake` |
| Config 内部 include | 不存在的 `liquidTargets.cmake` | 已安装的 `liquidTargets.cmake` |
| 导出 target | 无法由 canonical package 消费 | `liquid::liquid-static` |
| 最小消费者运行 | 未配置 | PASS |

固定日志标记：

```text
PATH_B_BEFORE_RC=1
PATH_B_BEFORE_BROKEN_INCLUDE=liquidTargets.cmake
PATH_B_AFTER_TARGET=liquid::liquid-static
PATH_B_CONSUMER=PASS
```

stderr 包含 CMake 对 HarmonyOS platform module 和 `/proc/meminfo` 的非阻塞告警；
两份源码均完成 159 个 build step，最终 runner exit 0，不把这些环境告警描述为知识根因。

## 去重边界

全量关键词扫描未发现现有正式/草稿条目覆盖 static-only install export 身份漂移。

- `E216`：Conan CMakeDeps 组件的 include/target 元数据传播。
- `E278`：条件排除内部 target 后，裸链接项静默退化为 `-l<name>`。
- `E242`：Fortran `.mod` ABI 与 Conan package identity 绑定。

E327 讨论的是上游 CMake 生产者内部，多个安装导出节点使用了不同逻辑包名。错误面、
根因和修复动作均与上述条目不同。

## 新增价值与诚实边界

归档的 liquid-dsp 1.8.0 测试报告已经记录该库的具体补丁和消费者验证。本次不把旧补丁
包装成“新发现”；新增贡献是：

1. 用正式真机 runner 补齐同源、单变量的修复前后对照证据。
2. 把单库现象抽象为 target 名、artifact 名和 package identity 分离的通用规则。
3. 给出可匹配的错误签名、适用范围、推荐/回退方案、禁止策略和可执行验证命令。
4. 与相邻正式条目完成明确去重，形成可由后续库复用的 draft 知识。

最终是否认定 B 类由赛事评审决定；本报告提供可复核证据，不承诺评审结果。
