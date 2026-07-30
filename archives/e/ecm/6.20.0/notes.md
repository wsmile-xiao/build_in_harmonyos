# ECM 6.20.0 适配笔记

## 软件简介

ECM (Extra CMake Modules) 是 KDE 提供的额外 CMake 模块集合，为 CMake 构建系统提供额外功能。

## 构建系统

- 构建系统: CMake
- 无编译依赖（仅需 CMake）

## 适配过程

### 编译配置

```bash
cmake -DCMAKE_INSTALL_PREFIX=$PREFIX -DBUILD_TESTING=OFF ..
make
make install
```

### 关键配置

- `BUILD_TESTING=OFF`: 禁用测试，加快构建速度
- ECM 是纯 CMake 模块库，不编译任何二进制代码

### 遇到的问题

无

## 安装路径

- `share/cmake/ECM/`: CMake 模块文件
- `share/doc/ECM/`: 文档（可选）

## 测试验证

- 验证 CMake 模块文件是否正确安装
- 验证 find_package(ECM) 是否能找到模块

## OHOS 适配要点

1. ECM 是纯配置文件库，无需编译二进制
2. package_id() 使用 self.info.clear() 避免编译器差异导致的包 ID 变化
3. 不需要 commands.json（无可执行文件）
4. 无平台特定补丁需求