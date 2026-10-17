# munit 0.2.0 HarmonyPC 适配记录

## 结论

- 状态：`built`
- Conan 引用：`munit/0.2.0`
- 适配范围：仅新增该版本的 Conan 配方、消费者测试和审查元数据；未修改公共框架、脚本、CI、模板或知识图谱。
- 上游依赖：无。
- 补丁：1 个，仅为 OHOS `/tmp` 不可写时的测试运行时临时文件路径提供可配置入口；默认未设置 `MUNIT_TMPDIR` 时仍调用上游 `tmpfile()`。

## 来源与预检

- 上游仓库：[nemequ/munit](https://github.com/nemequ/munit)
- 上游 tag：`v0.2.0`
- 上游 commit：`53fd975883649217b4171d1733b4d7391bacc470`
- 源码 URL：`https://github.com/nemequ/munit/archive/refs/tags/v0.2.0.tar.gz`
- 源码包 SHA-256：`58c12f2ae08acfc270d47a5ff23380c300b24d7dc53f3a23f4527e0112146844`
- 依赖预检：无声明依赖，通过。
- 语言预检：检测主体为 C，按 C 任务预检通过。

## 配方设计

- `validate()` 仅接受 `Linux` 和 `OHOS`。
- 编译器、归档器和 ranlib 从 `tools.build:compiler_executables` 获取，默认分别为 `clang`、`llvm-ar`、`llvm-ranlib`；命令中不依赖空的 shell `${CC}`/`${CFLAGS}`。
- Conan-owned build 生成 `libmunit.a`（默认）或 `libmunit.so`，并安装 `munit.h` 与 `munit` 库。
- `build()` 应用 `0001-ohos-configurable-stderr-tmpdir.patch`，同时执行上游官方构建和 `make -j1 test`；测试通过 `MUNIT_TMPDIR` 指向 build 目录下的可写私有目录。上游没有 `check` target，`make -n check` 的结果为 “No rule to make target 'check'”。

## 测试统计

### 上游官方测试

上游 `example.c` 注册 3 个 suite entry，经参数展开发现 11 个用例；实际执行 11 个，成功 11 个，失败 0 个，跳过 0 个。源文件中统计到 21 次测试断言宏调用（仅计实际宏调用，不计注释中的名称）。

执行命令：

```text
make -j1 && make -j1 test
```

### Conan test_package

新增 `test_munit.c`，从消费者视角链接并运行打包后的 `munit`，注册 2 个用例，执行 2 个，成功 2 个，失败 0 个，跳过 0 个，显式断言 8 次。

## 验证边界

- 本地 macOS：执行 Python 语法、YAML/路径/差异静态检查和源码级可复现编译；不把 macOS 结果当作 OHOS 运行证据。
- HarmonyOS PC：使用 `conan create`、应用同一临时目录补丁后的独立上游测试和 `conan test` 验证；最终 SHA、远端 worktree 和日志路径在交付报告中给出。
- PR：按用户要求暂不创建；PR 正文草稿放在被忽略的 `reports/pr-body.md`。
