# autotiling

自动切换 sway/i3 窗口分割方向的 Python 脚本：根据当前聚焦窗口的宽高比自动选择
`splitv`/`splith` 布局。上游仓库：https://github.com/nwg-piotr/autotiling

## 功能

- 监听 i3/sway 的 WINDOW/MODE 事件，自动切换分割方向
- `-o/--outputs`、`-w/--workspaces` 限制生效范围
- `-l/--limit` 限制分割层级（master-stack 布局）
- `-sw/-sh/-sr` 调整分割宽度/高度/比例因子
- `-e/--events` 自定义订阅事件

## 安装

```bash
# 通过本仓库 Conan 配方安装（自动处理 i3ipc 运行依赖）
conan install --requires=autotiling/1.9.3 -pr=ohos-aarch64
# 或上游方式：pip install autotiling
```

## OHOS 适配

- 纯 Python 实现，无 C/C++ 编译
- 运行依赖 i3ipc（python-i3ipc）由 pip 从 pypi.cnb.cool 镜像解析
- 真机验证 console script `--version`/`--help`（argparse 阶段退出，无需 sway/i3 环境）
- 上游无测试套件（已审计，见 test_package/MANIFEST.yml）

## 依赖

- 运行依赖：i3ipc（i3ipc-python ≥ 2.0.1）
- 构建依赖：setuptools、wheel（PEP 517）
