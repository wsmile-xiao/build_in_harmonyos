# lcms2 (Little CMS 2)

## 简介
lcms2 是一个色彩管理引擎，支持 ICC 配置文件处理，广泛用于图像处理软件。

## OHOS 适配
- autotools 构建，需要更新 config.guess/config.sub 支持 HarmonyOS
- config.sub 保留上游 2024 版本，并使用有锚点的替换块兼容 Conan `patch-ng`
- 针对正式 CI #7521 暴露的 HMDFS 权限差异，仅将 `configure` 创建 `confXXXXXX` 临时目录的两处 `umask 077` 改为 `022`（E129）
- Conan 标准 `shared` 选项自动映射 `--enable-shared/--disable-static` 或相反组合
- 打包阶段按平台放置库产物：Windows DLL 位于 `bin`、导入库位于 `lib`，macOS dylib 与 Linux/OHOS `.so` 位于 `lib`，静态 `.a`/`.lib` 也位于 `lib`
- 为保持核心色彩管理库依赖最小化，禁用可选 JPEG、TIFF 和 zlib 支持
- `package_info()` 直接按 Conan `SettingsItem` 匹配 Linux/OHOS，并为两者传播 `m`、`pthread`

## 依赖
- 无编译依赖

## 功能验证
```bash
conan create archives/l/lcms2/2.19 -o 'lcms2/*:shared=True'
conan create archives/l/lcms2/2.19 -o 'lcms2/*:shared=False'
```

WSL Clang 15 近似验证中，上游 testbed 270/270 项检查及消费者 RGB 到 Lab 转换测试的 13/13 个条件检查均通过；Review 修复后的 Build #7578 已通过，后续跨平台打包修改仍以再次更新后的当前 HEAD CI 为准。

## 参考
- 主页: https://www.littlecms.com/
- 源码: https://github.com/mm2/Little-CMS
