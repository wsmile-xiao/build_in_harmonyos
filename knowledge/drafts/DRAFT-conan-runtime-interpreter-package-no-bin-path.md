# DRAFT: Conan 运行时解释器依赖不暴露 bin PATH，env-shebang 脚本软件的消费者必须自解析 dependencies[].package_folder 注入 PATH

- slug: conan-runtime-interpreter-package-no-bin-path
- 分类: 构建系统语义（B 机理分层: L2 跨库工程模式）
- 实例库: kworkflow 0.10（案例; 同模式历史实例 bamclipper/1.0.0、bash-argsparse/1.8.22、bashdb/5.2-1.2.0）
- 状态: 草稿（最终编号 Exxx 由知识库主编确认）

## 一句规则

解释器类运行时依赖（bash/5.3 等）的制品只暴露 cpp_info.libs、不暴露 bin PATH；入口保留 `#!/usr/bin/env bash` 的脚本软件（E049 族），其 conan 化消费必须在 test_package 把解释器声明为直接依赖并用 `dependencies[].package_folder` 注入 PATH，而不能指望传递依赖图或 conanrun 脚本自动携带解释器。

## 机理链（工具证据 → 触发 → 失败点 → 归类）

1. bash/5.3 制品 package_info 仅暴露 cpp_info.libs=["bash"]（工具实现证据：archives/b/bash/5.3/conanfile.py）。
2. kw 等脚本工具入口 shebang 为 `#!/usr/bin/env bash`，解释器必须经 PATH 命中（触发条件）。
3. 失败点 A：test_package 图中 bash 只是传递依赖时，`self.dependencies["bash"].package_folder` 为 None → `TypeError: expected str, bytes or os.PathLike object, not NoneType`（ci03 实证）。
4. 失败点 B：即使 package_folder 可得，消费进程 PATH 不含解释器 bin → 入口脚本完全不可执行。
5. 归类：Conan 图与生成器语义 × 解释器类运行时依赖（构建系统语义域）。

## 方案空间

- rec（env-shebang 场景必选）：test_package 同时声明 `tested_reference_str` 与 `bash/5.3`；generate() 判空守卫 + `Environment().prepend_path("PATH", bash_bin)` + `save_script("conanrun")`；被测包 package_info() 用 buildenv_info/runenv_info 传播自身 bin 与环境契约变量（实例：kworkflow/0.10）。
- fallback（诚实权衡）：显式绝对路径调用解释器（bamclipper/bash-argsparse/bashdb 形态）。仅适合消费者显式调起；入口被直接执行的 env-shebang 场景不适用，必须回到 rec。构建上下文消费（tool_requires）同根因，用绝对路径 helper（blogc/castget/cubelib/acpica-unix/libevtx 五实例）。
- forbid：①对传递依赖直读 package_folder（必然 NoneType，报错点远离根因）；②假设 conanrun 环境脚本自动携带依赖 bin（依赖未暴露 bin 时 VirtualRunEnv 不会凭空注入）。

## 自包含 verification_cmd（新 shell 可跑）

```sh
# 工具实现证据: bash/5.3 只有 libs, 无 bindirs
grep -n 'cpp_info' archives/b/bash/5.3/conanfile.py | head
# 定向复现: 同模式实例对照
grep -rn 'package_folder, "bin"' archives/b/bash-argsparse/1.8.22.ga05fe6d/conanfile.py
grep -rn 'prepend_path("PATH"' archives/k/kworkflow/0.10/test_package/conanfile.py
```

## 挂钩与泛化

- affected_scope: 任何"解释器类运行时依赖 + env 风格 shebang"的脚本型软件在 conan 化打包与 test_package 执行中的适配。
- principles: P014（环境变量与构建系统语义冲突陷阱）。
- similar_to: E049、E396（NoneType 机理近邻）、E449/E499（libdir 传播对照）、E241；另有经验仓 build-system/cairo-1.18.4.md 的 package_folder=None→TypeError（includedirs/编译期 flag 拼接语境）为 NoneType 机理另一近邻（已核不覆盖解释器 PATH 注入）。

## 阻塞面证据（实例 run）

- ci03.log L225–226 TypeError；无 PATH 注入时 kw 入口不可执行（test_package generate() 以 ConanException 守卫）。
- 配方树同模式实践 ≥3 处（运行时 4 + 构建上下文 5），L2 准入证据见 curation-report §1.2。
