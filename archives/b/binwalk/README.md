# binwalk

固件分析工具 — 在二进制镜像中搜索嵌入式文件与代码（签名扫描、提取、熵分析等）。

## 简介

binwalk 是经典的固件逆向分析工具：内置 magic 签名库，可快速识别固件镜像中嵌入的
文件系统、压缩流、 bootloader、加密数据等，并支持自动提取（`-e`）。本仓库适配的
v2.3.4 为纯 Python 实现（setuptools 打包），无需 C/C++ 编译。

## OpenHarmony 编译说明

- 纯 Python 项目：`pip install --target` 私有安装 setuptools 到 Conan 构建目录，
  经 `PYTHONPATH` 注入执行 `setup.py build/install --prefix`（不污染系统解释器）
- Python 3.12 已移除 `imp` 模块：补丁 0001/0002 将 `imp.load_source` 替换为
  `importlib.util` 系列 API（module.py / plugin.py）
- 提取功能（`binwalk -e`）两处平台修复（补丁 0003，extractor.py）：
  - `pwd.getpwuid()` 在 OHOS 上因 uid 无 passwd 条目抛 KeyError → 回退进程凭据
  - 捆绑 Python 的 `subprocess.call` 对裸命令名不走 PATH 搜索 → `shutil.which` 预解析
- v3（Rust 重写版）依赖 glibc 动态链接器，OHOS musl 环境无法编译，故选择 v2
- 提取功能依赖外部工具（tar/cpio/unzip/lzma 等），OHOS 默认 PATH 含 /system/bin 即可

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.1.0 | published | Rust 版（历史归档） |
| 2.3.4 | built | Python 版，Conan 配方适配 |

## 许可证

MIT
