# libvirt-python

libvirt 的 Python 绑定库，提供 Python API 用于管理虚拟化技术（KVM/QEMU/LXC等）。

## 版本列表

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 10.1.0 | built | 2026-05-27 | 匹配 libvirt 10.1.0 |

## 编译要点

- **构建系统**: Python setup.py（非传统 autotools）
- **依赖**: libvirt 10.1.0
- **补丁**: pkg-config 路径硬编码修复

## 注意事项

Python 项目使用 `setup.py` 构建，无传统 `configure` 步骤。需要确保 libvirt 开发库已安装。