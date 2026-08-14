# ncmdump

网易云音乐 NCM 加密文件解密命令行工具（跨平台 C++17 实现）。

## 功能概述
- 解密单个或多个 .ncm 文件为 MP3/FLAC 等常见音频格式
- 支持 `-d` 目录批量处理、`-r` 递归、`-o` 输出目录、`-m` 删除源文件

## OHOS 适配
- 唯一硬依赖 taglib/2.3（已适配），CMake 目标名映射为 TagLib::tag
- 上游无自动化测试，test_package 用官方样例 test.ncm 真实解密验证
- 产物为可执行文件，需 ELF 签名后在鸿蒙执行

## 依赖关系
- 编译依赖：taglib/2.3（CMake `find_package(TagLib REQUIRED)`）
- 运行依赖：无外部运行库（静态链接 taglib）

## 参考资料
- 官网: https://github.com/taurusxin/ncmdump
