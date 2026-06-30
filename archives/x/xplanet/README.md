# Xplanet

Xplanet 是一个行星渲染软件，可以将太阳系行星、卫星等天体渲染成图像，类似于太阳系动态屏保。

## 功能概述

- **行星渲染**：渲染太阳系内各行星及其卫星的高质量图像
- **天文图像生成**：生成指定时间和视角的天文图像
- **地图投影**：支持多种地图投影模式
- **云层渲染**：可渲染行星云层效果
- **标注功能**：在图像上标注城市、卫星轨道等信息
- **时间控制**：支持指定任意时间点进行渲染

## OHOS 适配

### 适配要点

1. **config.guess/config.sub 更新**
   - xplanet 1.3.0 的 config.guess 版本过旧（2003年）
   - 需要替换为 automake-1.16 提供的最新版本
   - 以正确识别 HarmonyOS 平台

2. **C++11 兼容性修复**
   - `getline` 返回值比较：C++11+ 中 getline 返回 `istream&` 而非指针，需移除 `!= NULL` 比较
   - narrowing 转换：初始化列表中 int 到 unsigned char 缩窄，需添加显式类型转换
   - 涉及文件：src/libannotate/*.cpp, src/libmultiple/*.cpp, src/readConfig.cpp

3. **umask 002 workaround**
   - HMDFS 文件系统的特殊限制
   - configure 脚本中临时目录创建使用 umask 002 替代默认的 umask 077
   - 未来平台更新可能不再需要此修复

### 已知问题

- 无 X11/freetype 等图形支持（符合预期，无显示环境）
- 仅支持命令行模式下的图像渲染

## 依赖关系

### 编译依赖

无外部编译依赖（使用内置库）

### 运行依赖

无外部运行依赖

## 功能验证

```bash
$ xplanet --version
Xplanet 1.3.0
Copyright (C) 2012 Hari Nair <hari@alumni.caltech.edu>
```

## 参考

- 官网：http://xplanet.sourceforge.net/
- 源码：https://sourceforge.net/projects/xplanet/
- 文档：http://xplanet.sourceforge.net/documentation.php