# ros2-colcon-cd

ros2-colcon-cd 是 colcon 提供的目录快速切换扩展，通过 Shell 函数按 ROS 2 包名切换工作目录。

## 功能概述

- 使用 `colcon_cd <package_name>` 切换到指定 ROS 2 包目录
- 保存、返回或重置工作区根目录
- 提供 Bash 和 Zsh 命令补全资源

## OHOS 适配

配方通过离线 setuptools 安装保留 Python 包元数据、colcon entry point 和 Shell hook。项目不包含 C/C++ 源码，不生成 ELF 文件，也不需要平台补丁。消费者测试使用 Conan 构建目录，不依赖 OHOS 上可能只读的 `/tmp`。

已知限制：运行功能需要使用者提供包含 `colcon list` 的 ROS 2/colcon 环境。

## 依赖关系

- 构建依赖：Python 3、pip、setuptools
- 运行依赖：Python 3、colcon-core 0.4.1 或更高版本、colcon-package-information
- 可选依赖：colcon-argcomplete

## 已适配版本

| 版本 | 状态 | Conan 引用 |
|------|------|------------|
| 0.2.1 | built（本地通过，待 OHOS CI 验证） | `ros2-colcon-cd/0.2.1` |

配方打包 Python 扩展模块以及 Bash、Zsh 的 Shell 函数资源。使用前需要安装可提供 `colcon list` 的 colcon 环境，并加载包内 `share/colcon_cd/function/` 下对应 Shell 的脚本。

## 参考资料

- 上游源码：https://github.com/colcon/colcon-cd
- colcon 文档：https://colcon.readthedocs.io/
