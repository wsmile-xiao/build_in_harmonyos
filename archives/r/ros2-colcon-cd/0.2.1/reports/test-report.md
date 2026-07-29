# ros2-colcon-cd 0.2.1 测试报告

| 测试层级 | 命令 | 结果 |
|----------|------|------|
| 上游测试收集 | `python3 -m pytest --collect-only -q` | PASS：5 个用例 |
| 上游官方测试 | `python3 -m pytest -q` | PASS：5/5 |
| Python 模块检查 | `python3 -m compileall -q colcon_cd` | PASS |
| Bash 语法检查 | `bash -n function/colcon_cd.sh` | PASS |
| Python 消费测试 | `python3 test.py <packaged-site-packages>` | PASS：1/1 |
| Shell 功能测试 | `bash test.sh <packaged-function-dir> <writable-work-dir>` | PASS：6/6 |
| 源码完整性 | `sha256sum colcon-cd-0.2.1.tar.gz` | PASS：`91f14108b6f9db780fc5a579b9c809e9a8c62b688e81f2267788fd0e12f178dc` |

上游测试使用与 0.2.1 源码兼容的 flake8 6.1.0。消费者测试真实导入包内 Python 扩展并加载 Shell 函数，通过受控的 `colcon list` 输出验证目录切换，不依赖网络或 ROS graph。
