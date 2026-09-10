# DRAFT-nicovideo-dl-script-cli-conan-runtime：单文件 Python CLI 的 Conan 运行时与消费测试边界

> 路径 B 知识库扩展草稿；正式编号及是否提升由知识库维护者和赛事评审决定。
> 来源：nicovideo-dl 0.0.20190126 适配，PR #9377。

## 适用场景

有些历史 Python 命令行工具只有一个无扩展名入口文件，没有
`setup.py`、`pyproject.toml`、构建系统或上游测试套件。此时 Conan 配方的重点
不是伪造一个 Python 模块构建流程，而是明确验证和发布“可执行应用”边界。

## 现象与根因

如果只把脚本复制到包内普通目录，或者依赖宿主环境里碰巧存在的 `python` 命令，
会出现以下问题：

- 包虽能生成，消费者通过 `PATH` 找不到 `nicovideo-dl`；
- 脚本没有执行权限，出现 `Permission denied`；
- 构建验证绑定到某个环境的 `python/python3` 名称，而不是 Conan 当前使用的解释器；
- 只验证源码目录中的脚本，未验证安装后消费者实际拿到的命令。

`nicovideo-dl/0.0.20190126` 的源码审计确认：归档只有一个 Python 3 脚本，
使用标准库，没有标准 Python 打包元数据，也没有上游测试目标。

## 推荐方案

配方应采用以下边界：

1. 声明 `package_type = "application"`，并保留完整的 Conan settings 矩阵。
2. 在 `build()` 中用 `sys.executable` 执行源码入口的 `--version` 和 `--help`，
   证明当前构建解释器可以加载脚本。
3. 在 `package()` 中将无扩展名脚本安装到 `bin/nicovideo-dl`，并设置
   `0755` 权限；许可证单独安装到 `licenses/`。
4. 在 `package_info()` 中声明 `bindirs = ["bin"]`，让 Conan consumer 环境能够
   发现命令。
5. 用离线 `test_package` 验证安装后的命令、版本、帮助和确定性的非法参数路径。
   这类测试属于适配方消费测试，不应冒充上游测试。

核心实现形态：

```python
script = os.path.join(self.source_folder, "nicovideo-dl")
self.run(f'"{sys.executable}" "{script}" --version', cwd=self.source_folder)
self.run(f'"{sys.executable}" "{script}" --help', cwd=self.source_folder)

copy(self, "nicovideo-dl", src=self.source_folder, dst=bindir, keep_path=False)
os.chmod(os.path.join(bindir, "nicovideo-dl"), 0o755)
```

## 实证

在 Windows native Conan 2.12.0 环境中，`conan create` 完成源码下载、打包和
消费者测试；产物包含 `bin/nicovideo-dl` 与 `licenses/LICENSE`，test_package
执行的 8 个 Windows 断言全部通过。另有 2 个 POSIX-only `PATH` 断言，预计在
HarmonyOS/POSIX 目标上执行，总计 10 个断言。

上游脚本的 `--version` 输出为 `2011.02.08`，`--help` 输出完整选项列表；
测试不访问账号、网络或真实视频服务，因此可在 CI 中重复运行。

## 反模式与边界

- 不要把 `python` 或个人机器上的 Python 绝对路径硬编码进配方。
- 不要把脚本放到未声明的目录后声称命令可用。
- 不要用 `echo passed` 代替安装后消费测试。
- 不要把网络下载成功当作包的基础可用性证明。

本条适用于无标准 Python 构建元数据的 CLI 脚本包；若项目是正常的 Python
模块或有正式 wheel 构建流程，应优先采用对应的 Python 打包方案。

## 去重结论

本条聚焦“单文件、无扩展名 Python CLI 的 Conan 应用边界和安装后消费证据”，
不同于通用 Python 模块构建、上游测试依赖或 shell shebang 条目。当前案例提供
了源码 smoke、包内容和离线 consumer test 的完整闭环，故作为独立路径 B 草稿。
