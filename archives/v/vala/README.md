# Vala

## 简介
面向对象的编程语言，自托管编译器，目标是 GObject 系统，语法类似 C#。

## OHOS 适配
- 需修补 config.guess/config.sub 添加 HarmonyOS 识别
- autotools 构建

## 依赖
- GLib/GObject
- flex/bison

## 功能验证
```bash
vala --version
valac --version
```

## 参考
- 官网: https://wiki.gnome.org/Projects/Vala
