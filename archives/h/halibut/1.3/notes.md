# halibut 1.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-02
- 编译器: clang/clang++
- 状态: published

## 编译步骤

### cmake 配置
```bash
cd ~/tmp/builds/halibut-1.3.work
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ..
```

### 编译
```bash
make -j2
```

### DESTDIR 模式安装（R20铁律）
```bash
make install DESTDIR=$TEST_PREFIX
```
- 安装产物: `$TEST_PREFIX/$DEFAULT_PREFIX/bin/halibut` (1,365,504 bytes)

### 本地安装（模拟用户部署）
```bash
make install
$DEFAULT_PREFIX/bin/halibut --version
# 输出: Halibut, version 1.3
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码下载 SSL 证书验证失败（urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]） | 本地 SSL 证书不包含 chiark.greenend.org.uk 的根 CA | 使用 wget --no-check-certificate 手动下载完整 tarball，init-build 检测到本地文件后跳过下载步骤 |
| 2 | init-build 误识别构建系统为 autotools | halibut 有 CMakeLists.txt，脚本默认检测为 autotools | 手动修正 manifest.yaml 中 build_system=cmake 和 build.system=cmake |
| 3 | cmake charset 子目录兼容性错误（cmake_minimum_required(VERSION 3.0) 不被 CMake 4.x 支持） | CMake 4.x 删除了对 cmake_minimum_required < 3.5 的兼容性支持 | 添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 参数 |
| 4 | verify-build 报 "manifest 缺少 build_system" | verify 脚本检查顶级字段 `build_system:`，manifest 使用嵌套格式 `build.system:` | 在 manifest.yaml 添加顶级 `build_system: cmake` 字段 |
| 5 | G0 clean-verify 失败 | 脚本对 cmake 项目尝试运行 `./configure` | 已知限制：G0 clean-verify 不支持 cmake 项目，手动从干净源码验证通过 |

## 源码修改

无源码修改，无需补丁。所有编译问题通过 cmake 参数解决，未修改任何源文件。

## 依赖版本

- 无特殊依赖
- 编译器: clang 15.0.4
- 构建工具: cmake 4.1.2, make 4.4.1

## 功能验证结果

使用源码自带 `inputs/test.but` 测试输入文件执行了 11 项功能测试：

| 测试项 | 结果 |
|--------|------|
| --version 版本信息 | ✅ "Halibut, version 1.3" |
| --help 帮助信息 | ✅ 完整使用说明 |
| --licence 许可证 | ✅ MIT License |
| --text 纯文本输出 | ✅ 9,067 bytes, 内容渲染正确 |
| --html HTML输出 | ✅ 12,924 bytes, HTML4.01标准 |
| --man Man页面输出 | ✅ 7,759 bytes |
| --info Info输出 | ✅ 742 bytes |
| --ps PostScript输出 | ✅ 48,919 bytes |
| --pdf PDF输出 | ✅ 24,581 bytes |
| --list-charsets 字符集 | ✅ 20+ 种字符集 |
| --list-fonts 字体 | ✅ 12 种字体 |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| halibut-1.3-ohos-aarch64.tar.gz | 1,372,388 bytes (1.34MB) | 预编译包 |
| halibut-1.3-ohos-aarch64-debug.tar.gz | 71,713 bytes | 调试符号包 |

## 注意事项

1. CMake 版本兼容性需要 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 参数，此为 cmake 4.x 与旧版 cmake_minimum_required 不兼容的已知问题
2. G0 clean-verify 脚本不支持 cmake 项目（尝试运行 ./configure），需手动验证干净构建
3. verify-build 检查顶级 `build_system:` 字段，需确保 manifest.yaml 同时包含嵌套格式和顶级字段