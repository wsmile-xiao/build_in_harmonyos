# aircrack-ng

## 简介

Aircrack-ng是一个完整的WiFi安全评估工具套件，用于监控、攻击、测试和破解WiFi网络。

## 版本信息

- 当前版本: 1.7
- 发布日期: 2022-05-10
- 官方网站: https://aircrack-ng.org
- 许可证: GPLv2

## 编译信息

- 构建系统: autotools
- 编译器: gcc (clang 15.0.4)
- 目标平台: HarmonyOS aarch64
- 编译状态: partial（部分工具编译成功）

## 已编译工具

### kstats
显示IVS文件中的密钥统计信息
```bash
kstats <ivs file> <104-bit key>
```

### makeivs-ng
生成测试用的IVS文件
```bash
makeivs-ng [options]
```

## 编译挑战

1. **autotools依赖**：automake Perl模块缺失，无法运行autogen.sh
2. **动态加载限制**：crypto_engine_loader需要dlopen支持
3. **无线驱动依赖**：部分工具需要无线网卡驱动支持

## 相关链接

- 官方网站: https://aircrack-ng.org
- GitHub: https://github.com/aircrack-ng/aircrack-ng
- 文档: https://aircrack-ng.org/documentation.html