# GNU Global

GNU Global 是一个源代码标记系统，用于在大型项目中快速定位函数、变量、类等定义和引用位置。

## 主要工具
- **global**: 核心查询工具
- **gtags**: 标签生成工具
- **htags**: HTML 标签生成工具
- **gtags-cscope**: cscope 兼容接口

## 编译版本
- 版本: 6.6.8
- 平台: HarmonyOS (aarch64)
- 依赖: ncurses

## 平台适配
- config.guess: 添加 HarmonyOS 系统识别
- config.sub: 添加 linux-ohos 内核支持