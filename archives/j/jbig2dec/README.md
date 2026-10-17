# jbig2dec

## 简介
jbig2dec 是 JBIG2 图像压缩标准的解码器实现，主要用于 PDF 文档中的 JBIG2 图像解码。

## OHOS 适配
- 标准 autotools 项目（configure + make），但需以下 OHOS 专项适配：
  - E007 补丁修改 config.guess/config.sub 识别 HarmonyOS（禁止 --build/--host 绕过）
  - TMPDIR 重定向到 `~/.conan_build_tmp`，避免 HMDFS 权限问题
  - configure 脚本 `umask 077` → `umask 022` 替换
  - `--without-libpng` 禁用可选依赖
- 产出动态库 libjbig2dec.so

## 依赖
- 编译依赖：clang, make
- 运行依赖：libc

## 功能验证
```bash
jbig2dec --version
```

## 参考
- 源码：https://github.com/ArtifexSoftware/jbig2dec
