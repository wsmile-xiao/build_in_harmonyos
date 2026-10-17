# libmseed

## 简介
miniSEED 地震时间序列数据格式的 C 语言读写库, 提供记录解析、打包、轨迹重建能力。

## OHOS 适配
- 构建系统: 纯 Makefile, 无 configure
- `CC/AR/RANLIB/SHELL` 经 make 命令行覆盖, 零补丁
- `make -j1` 单作业构建, 上游 `make check` 完整运行 test/ 套件
- 详见各版本 notes.md 获取适配详情

## 依赖
- 无外部依赖 (仅 C 标准库)

## 功能验证
- 上游 `make check` 完整测试清单 (2 个构建程序 + 31 个 diff 用例)。
- Conan 消费者链接并调用 libmseed 公开 API (版本/记录与轨迹生命周期/时间转换/采样与编码查询)。

## 参考
- https://github.com/EarthScope/libmseed
- https://earthscope.github.io/libmseed
