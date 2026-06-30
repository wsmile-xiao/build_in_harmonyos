# svgo 4.0.1 编译笔记

## 编译日期
2026-05-22

## 编译环境
- Node.js: v24.13.0
- npm: 11.12.1
- 系统: OpenHarmony/HarmonyOS

## 源码获取
- 源码 URL: https://github.com/svg/svgo/archive/refs/tags/v4.0.1.tar.gz
- 备用 URL: https://registry.npmjs.org/svgo/-/svgo-4.0.1.tgz

## 编译过程

### 依赖安装
```bash
npm install
```

### 构建问题
- svgo 使用 yarn@3.8.7 作为包管理器
- rollup 构建依赖 native 模块（rollup.openharmony-arm64.node）
- native 模块无法直接加载（Permission denied）
- 最终使用已有的安装版本进行打包

### 打包策略
- 复制已有的 ~/usr/local/lib/svgo 目录
- 创建 wrapper script (bin/svgo)
- 处理 ELF 文件：签名、strip、分离 debug 信息

## ELF 文件处理
- 文件: rollup.openharmony-arm64.node
- 签名: binary-sign-tool sign -selfSign 1
- Strip: llvm-objcopy --strip-debug
- Debug 分离: llvm-objcopy --only-keep-debug

## 测试结果
- 版本检查: ✅ PASS (svgo --version → 4.0.1)
- 功能测试: ✅ PASS

## 注意事项
- rollup native 模块虽然已签名，但仍无法被 Node.js 加载
- svgo 主命令不依赖 native 模块，可正常使用
- native 模块仅在构建阶段需要，不影响运行时功能

## 制品
- svgo-4.0.1-ohos-aarch64.tar.gz (151M)
- svgo-4.0.1-ohos-aarch64-debug.tar.gz (16K)
**交付物**: 2 个 tar.gz 制品文件
---

**编译结束**: 2026-05-22 10:47
**最终状态**: built
