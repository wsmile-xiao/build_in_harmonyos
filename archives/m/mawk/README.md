# mawk - Interpreter for the AWK Programming Language

## 描述
mawk 是 AWK 编程语言的实现，特点是速度快、占用资源少。
适用于文本处理、数据提取、报告生成等场景。

## 版本信息
- 当前版本: 1.3.4-20260302
- 发布日期: 2026-03-02
- 主页: https://invisible-island.net/mawk/

## 编译方法
```bash
# 标准 autotools 编译（在其他系统）
./configure --prefix=/usr/local
make
make install

# 鸿蒙编译（需手动配置）
# 由于 HMDFS 文件系统限制，需要手动创建 config.h 和 Makefile
# 参考 notes.md 中的详细步骤
```

## 依赖
- 编译依赖: gcc, bison (可选)
- 运行依赖: libc (musl), libm

## 功能
- 正则表达式支持 (regex.h)
- 管道和 fork 支持
- 完整的 AWK 语法支持
- POSIX 扩展

## 已知问题
- 不支持 `{,N}` 形式的区间表达式（需完整 `{0,N}`）
- NaN/Inf 符号可能与标准不同
- /dev/full 不存在，跳过相关测试

## 安装验证
```bash
mawk --version
echo 'test' | mawk '{print}'
```

## 许可证
GPL-2.0
