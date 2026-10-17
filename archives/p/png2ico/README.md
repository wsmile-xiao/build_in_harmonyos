# png2ico

png2ico 是一个命令行工具，用于把一个或多个 PNG 图片转换成 Windows ICO 图标文件。

## Conan 包

- 包引用：`png2ico/2002-12-8`
- 类型：application
- 依赖：`libpng/1.6.58.2`
- 入口：`bin/png2ico`
- 上游主页：https://www.winterdrache.de/freeware/png2ico/

## 用法

```text
png2ico output.ico [--colors 2|16|256] input1.png [input2.png ...]
```

输入图片宽度必须是 8 的倍数且小于 256，高度必须小于 256；这是上游格式处理逻辑的限制。

## HarmonyOS 说明

该包使用 Conan OHOS profile 提供的编译器和依赖路径构建。程序安装到 Conan 包的 `bin` 目录，测试使用设备可写的 `TMPDIR` 私有目录，不需要 root 权限，也不写入固定系统路径。
