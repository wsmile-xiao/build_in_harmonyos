# LockFile-Simple

## 描述

LockFile::Simple - Simple file locking scheme

这是一个纯 Perl 模块，提供简单的文件锁定机制。不基于 flock() 或 lockf() 系统调用，而是依赖基本的文件系统属性和原子性。

## 版本

- 0.208 (2012-06-02)

## 构建系统

- Perl (Makefile.PL)

## 特点

- 纯 Perl 实现，无 XS 代码
- 无二进制文件
- 安装路径: Perl 模块标准路径

## 依赖

无额外依赖（Perl 核心模块）

## 已编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.208 | built | 2026-06-13 |