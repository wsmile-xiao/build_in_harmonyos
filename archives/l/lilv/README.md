# Lilv

## 简介
Lilv 是一个用于加载和使用 LV2 音频插件的 C 库，是 LV2 生态系统的核心组件之一。

## 功能概述
- 加载和枚举 LV2 插件
- 提供插件信息查询接口
- 支持插件实例化和运行
- 提供 lv2info 和 lv2ls 工具

## OHOS 适配
- 构建系统: meson 1.11.1 + ninja 1.13.1
- 编译器: clang 15.0.4
- 目标平台: aarch64 (鸿蒙系统)
- ELF 签名: 必须对共享库和可执行文件签名才能执行
- Python 绑定: 可用但测试因签名时机问题失败，核心功能正常

## 依赖
- lv2 >= 1.18.2 (LV2 规范核心库)
- serd >= 0.30.10 (RDF 序列化库)
- sord >= 0.16.16 (SPARQL 库)
- sratom >= 0.6.10 (Atom 序列化库)
- zix >= 0.6.0 (基础工具库)

## 功能验证
```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib
lv2info --version  # 输出: lv2info (lilv) 0.26.5
lv2ls --version    # 输出: lv2ls (lilv) 0.26.5
```

## 参考
- 官网: https://drobilla.net/software/lilv
- 源码: https://gitlab.com/lv2/lilv
- LV2 规范: https://lv2plug.in