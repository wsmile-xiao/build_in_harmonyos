# libtickit

Terminal Interface Construction Kit - 用于构建交互式全屏终端程序的抽象库。

## 功能特性

- 将终端划分为嵌套的可重叠矩形窗口层次结构
- 在任意窗口区域独立渲染输出内容和响应输入事件
- 支持完整的 Unicode 字符串，包括非 BMP、全宽和组合字符
- 使用 Unicode 方框绘制字符绘制线条图形
- 通过文件描述符同步或异步操作，或通过字节缓冲区抽象操作
- 识别任意键盘输入，包括修饰键

## 支持的终端特性

- 多种渲染属性：粗体、斜体、下划线、反显、删除线、备用字体
- 256色和24位（1600万色）颜色
- 鼠标支持，包括鼠标滚轮和大于224列的位置报告
- 任意滚动区域

## 最新版本

- **版本**: 0.4.6
- **发布日期**: 2026-02-12
- **状态**: built

## 编译依赖

- termkey >= 0.22
- unibilium >= 2.1.2

## 下载地址

- 官方源码: http://www.leonerd.org.uk/code/libtickit/
- GitHub镜像: https://github.com/leonerd/libtickit

## OHOS平台注意事项

在OHOS平台上编译时，需要应用补丁解决系统头文件中winsize结构体重复定义的问题。
详见版本级notes.md和patches目录。

## 项目管理

- Launchpad项目主页: https://launchpad.net/libtickit
- Bazaar源码仓库: http://bazaar.leonerd.org.uk/c/libtickit