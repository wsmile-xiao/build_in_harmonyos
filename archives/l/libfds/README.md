# libfds

## 简介
libfds 是 Flow Data Storage 库，提供处理流量记录（IPFIX）的工具集。支持IPFIX信息元素管理、模板解析、数据记录遍历、过滤器、Trie查找、文件读写等核心功能。

## OHOS 适配
- cmake 构建
- 0.6.0 版本编译成功
- 核心API全部功能正常（IEMGR/模板/Trie/文件/过滤器/转换器）
- 已通过鸿蒙平台功能测试验证

## 依赖
- libxml2（必需）
- liblz4（运行时依赖，用于LZ4压缩）
- libzstd（运行时依赖，用于ZSTD压缩）

## 功能验证
```bash
# pkg-config 验证
pkg-config --modversion libfds    # 输出: 0.6.0
pkg-config --libs libfds          # 输出: -L~/usr/local/lib -lfds
pkg-config --cflags libfds        # 输出: -I~/usr/local/include

# 核心API测试（功能测试程序已验证）
# - IEMGR: 加载定义、查找IE、名称查找、类型转换 ✅
# - 模板: 解析IPFIX模板、创建管理器 ✅
# - Trie: 添加网段、查找匹配 ✅
# - 文件: init/close/open ✅
# - 过滤器: 创建选项、解析表达式 ✅
# - 转换器: bool/uint/ip转换 ✅
```

## 测试报告
- 详细测试报告见: `reports/test-report.md`

## 参考
- 主页: https://github.com/CESNET/libfds