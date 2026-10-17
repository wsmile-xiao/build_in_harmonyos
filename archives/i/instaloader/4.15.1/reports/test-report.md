# instaloader 4.15.1 测试报告

- 测试日期：2026-09-25
- 测试环境：HarmonyOS aarch64 worker，Python 3.12.8，Conan 2.29.1
- 测试类型：上游测试清单核对 + Conan 消费者集成测试

## 一、测试摘要

| 测试类别 | 总数 | 通过 | 失败 | 跳过/不可执行 |
|---|---:|---:|---:|---:|
| 上游测试 | 0 | 0 | 0 | 0（上游 sdist 不含测试套件） |
| 新增消费者测试 | 9 | 9 | 0 | 0 |

## 二、上游测试核对

源码包内容已检查：不存在 `tests/`、pytest 配置、unittest 测试模块或上游测试命令。因此不存在可执行的上游测试用例；未修改任何上游测试文件，也未将测试缺失伪报为通过。

## 三、新增真实消费者测试

1. 从安装后的私有 `site-packages` 导入 `instaloader`。
2. 校验版本为 `4.15.1`。
3. 实例化 `Instaloader` 并校验真实配置属性。
4. 校验 `load_structure` 与 `save_structure_to_file` 公开 API 可调用。
5. 校验安装目录存在且 CLI wrapper 可执行。
6. 执行安装后的 `instaloader --version`，作为独立 CLI 集成测试。

其中 smoke.py 包含 8 个断言，CLI 集成测试为 1 个测试，共 9 个适配后测试。所有测试通过真实安装产物运行，不是只打印字符串的空壳测试。

## 四、测试命令与实测结果

实测结果：源码 wheel 构建通过；源码消费者 API 导入/实例化通过；`python3 -m instaloader --version` 输出 `4.15.1`；`conan-verify` 与 W3 本地 CI 模拟均通过。
