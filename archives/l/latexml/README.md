# latexml — HarmonyOS编译包

## 简介
LaTeXML是将LaTeX文档转换为XML/HTML/MathML格式的工具，由NIST开发。

## 可用版本
- **0.8.8** — 编译于 2026-05-27, status: published

## 构建系统
Perl (Makefile.PL), 构建命令: `perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX`

## 依赖
- perl >= 5.42.0

## 已知限制
- HarmonyOS需签名.so文件才能加载XS Perl模块
- DB_File/XML::LibXSLT使用stub替代
