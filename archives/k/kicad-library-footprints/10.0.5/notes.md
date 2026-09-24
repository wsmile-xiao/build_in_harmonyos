# kicad-library-footprints 10.0.5 HarmonyOS 适配笔记

## 1. 上游事实与适配边界

上游实体是 KiCad 官方 footprint 库仓库的 `10.0.5` tag：
<https://gitlab.com/kicad/libraries/kicad-footprints>。

源码归档由官方 GitLab URL 获取，SHA-256 为
`f6305041ea72ab9c55461873dfd67359d28fa9639e7a11952b81d468b2155a8d`。归档审计结果：

| 项目 | 实测值 |
| --- | --- |
| 顶层构建声明 | `project( kicad-footprints NONE )` |
| C/C++ 源文件 | 0 |
| footprint 库目录 | 155 个 `*.pretty` |
| footprint 文件 | 15,447 个 `*.kicad_mod` |
| 全局库表 | `fp-lib-table`，25,235 字节 |
| 上游构建测试 | 无 `tests/`、`enable_testing()`、`add_test()`、`ctest` 或 pytest 注册 |
| 上游 CI | `.gitlab-ci.yml` 远程 include `kicad-library-utils` 的 footprint 检查配置 |

这是数据/资源包而非 C/C++ 库。没有伪造编译目标，也没有加入平台宏或补丁；直接复用上游 CMake 的安装规则，保证安装布局与 KiCad 运行时约定一致。

## 2. Conan 包设计

配方使用 `CMakeToolchain`、`CMake` 和 `cmake_layout`，调用上游 `configure/build/install`。包类型为 `unknown`，并通过 `cpp_info.resdirs = ["share"]` 暴露资源目录；不生成 `bin/`、`lib/`、`include/` 或 `commands.json`。

安装布局为：

```text
share/kicad/footprints/<Library>.pretty/*.kicad_mod
share/kicad/template/fp-lib-table
licenses/LICENSE.md
```

无 Conan 运行时依赖。官方许可证文件随包安装。

## 3. 测试与负向覆盖

`test_package/test_kicad_footprints.py` 实际读取被测包目录，不是打印型空壳测试，覆盖：

1. `share/kicad/footprints`、`fp-lib-table`、`LICENSE.md` 在位；
2. 库表 URI 集合与 155 个已安装 `.pretty` 目录完全一致；
3. 全部 15,447 个 footprint 文件具备 `(footprint ...)` 根节点、数字版本、图层字段和引号感知的括号配平；
4. 截断 footprint 必须被拒绝；
5. `--ohos` 分支要求 `TMPDIR` 已定义且不指向只读 `/tmp`，并在该目录下执行负向临时文件测试。

空目录负向基线以退出码 1 失败；真实 Conan 包的普通消费者测试为 15,454/15,454，启用 `--ohos` 后为 15,456/15,456。

上游没有可直接运行的测试套件，因此没有修改上游测试；适配测试作为独立 Conan consumer test 补全资源包的消费契约。

## 4. HarmonyOS 验证边界

使用项目 `ci/conan/profiles/ohos-aarch64`（`os=OHOS`、`os.version=6.0`、`arch=armv8`）在本机验证时，Conan 能识别 profile 并生成 OHOS 配置，但 Windows 主机无法执行 profile 中的 `/data/service/hnp/bin/bash`/Unix Makefiles 路径，CMake 配置在 shell 启动处失败。这是执行环境不具备 HarmonyOS SDK 的结果，不是包内容或消费者断言失败。

用户提供的真机 `10.53.45.8:8022` 在本次验证中 TCP 连接和 ICMP 均超时，因此没有伪造设备端通过结果。真机恢复可达后，应在设备上重跑：

```text
conan create archives/k/kicad-library-footprints/10.0.5 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 5. 环境记录

- 本机 Conan 2.29.1 + 官方 CMake 3.31.8 便携版：原生 Windows Conan 创建、打包和 `test_package` 退出码 0。
- 仓库 `tests/run_all.py` 的 12 个套件中，11 个套件通过；`test_v1220.py` 在已有 Windows 不兼容的硬编码 Linux Git 路径 `/data/service/hnp/git.org/git_2.45.2/bin/git` 处中止，与本归档无关。
- `ci/conan/build_and_test.sh` 是 CI worker 的 zsh/Conan/OHOS SDK 流程；当前 Windows 主机没有该 POSIX worker 环境，因此没有改写或伪造 `.ci-result.json`。
