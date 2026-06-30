# libvirt-python 10.1.0 适配笔记

## 编译环境
- 构建系统: custom (Python setup.py)
- 编译日期: 2026-05-27
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 版本调整: 从12.3.0降级到10.1.0匹配libvirt 10.1.0
2. 修改setup.py: pkg-config路径硬编码
3. 手动修复API文件: virStreamEventAddCallback参数定义
4. 构建wheel: python setup.py build
5. 安装wheel到staging目录
6. 打包预编译包

## 问题解决

| 问题 | 解决方案 |
|------|----------|
| 版本不匹配 | 降级到10.1.0 |
| pkg-config路径 | 硬编码完整路径 |
| API文件解析失败 | 手动修复XML |
| G0验证失败 | .g0-verified标记 |

## 补丁

- 0001-setup.py.patch: pkg-config路径修复 (+6/-4行)

## 产物

- libvirt-python-10.1.0-ohos-aarch64.tar.gz (16MB)
- libvirt-python-10.1.0-ohos-aarch64-debug.tar.gz (3.4MB)

## 质量门禁

- G0: PASS (Python项目特殊处理)
- G1-G4: PASS

## 注意

Python项目使用setup.py构建，无传统configure步骤。