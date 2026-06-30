# kcat 1.7.1-r2 适配笔记

## 编译环境
- 构建系统: mklove
- 编译日期: 2026-05-20
- 编译器: clang/clang++
- 状态: published

## 编译步骤
1. 编译依赖 librdkafka 2.5.3
2. configure --prefix=$DEFAULT_PREFIX --arch=aarch64
3. make && make install

## 依赖版本
- librdkafka 2.5.3

## 验证结果
$ kcat -V
Version 1.7.1 (librdkafka 2.5.3)

---

**编译结束**: 2026-05-20 15:28