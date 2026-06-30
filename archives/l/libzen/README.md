# libzen

ZenLib - small C++ library

## 描述

ZenLib 是一个小型 C++ 库，提供了一些通用的工具类和函数。

## 补丁说明

本软件需要以下补丁以适配鸿蒙平台：

- `0001-Source-ZenLib-Thread.cpp.patch`: 禁用鸿蒙平台不支持的 `pthread_cancel` 函数

## 已编译版本

- 0.4.41 (2026-05-20)