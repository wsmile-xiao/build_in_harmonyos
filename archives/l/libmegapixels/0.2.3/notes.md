# libmegapixels 0.2.3 鸿蒙适配笔记

## 环境信息
- 操作系统：HarmonyOS 6.0（aarch64）
- 编译器：Clang 15.0.4
- 构建系统：Meson

## 依赖
- libconfig 1.7.3（已适配）

## 构建步骤
1. 克隆上游源码：`git clone https://gitlab.com/megapixels-org/libmegapixels.git`
2. 切换到标签：`git checkout tags/0.2.3`
3. Meson 构建

## 测试
- 上游测试：check_mode（greatest.h 框架）
- 消费者测试：test_package（调用 libmegapixels_find_config）

## 相关 PR
（待填写）
