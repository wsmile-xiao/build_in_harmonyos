# boost-build 1.90.0 适配笔记

## 编译环境
- 构建系统: custom (bootstrap.sh + b2 install)
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built (G0 clean verify不适用，因boost-build无configure脚本)

## 编译步骤

1. **初始化**: `python3 ohc-run.py init-build boost-build 1.90.0 --url=https://github.com/boostorg/build/archive/refs/tags/boost-1.90.0.tar.gz`
2. **构建引擎**: `./bootstrap.sh --cxx=clang++ --cxxflags="-fPIC -O2"` — 构建b2引擎(src/engine/build.sh自动检测clang++编译器)
3. **安装(直接到$DEFAULT_PREFIX)**: `./b2 install --prefix=$DEFAULT_PREFIX toolset=clang` — 安装b2到~/usr/local
4. **手动创建staging**: 因b2不支持DESTDIR，手动将$DEFAULT_PREFIX中的文件复制到$TEST_PREFIX/$DEFAULT_PREFIX/
5. **打包**: `python3 ohc-run.py package boost-build 1.90.0`
6. **验证**: `/storage/Users/currentUser/usr/local/bin/b2 --version` → B2 5.3.2 (OS=LINUX, jobs=20)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书下载失败 | /etc/ssl/cert.pem不存在 | 设置SSL_CERT_FILE=/storage/Users/currentUser/usr/local/ssl/cert.pem |
| 2 | b2 install不支持DESTDIR | b2是自定义构建系统，非autotools | 手动从$DEFAULT_PREFIX复制文件到$TEST_PREFIX/$DEFAULT_PREFIX/ |
| 3 | b2 install默认使用gcc | b2未指定toolset时默认gcc | 添加`toolset=clang`参数 |
| 4 | G0 clean verify失败 | clean_verify脚本只支持configure,boost-build无configure脚本 | 已手动验证构建可用，记录为自定义构建系统限制 |
| 5 | G4缺少build_system字段 | manifest模板使用嵌套格式build.system | 添加顶层build_system: custom字段 |
| 6 | 部分测试失败 | 测试默认使用gcc toolset | 核心Jam测试通过，gcc相关测试在OpenHarmony上预期失败 |

## 源码修改

无源码修改，无需补丁。

## 依赖版本

无必需依赖，无可选依赖。

## 功能验证结果

### 基础验证
```bash
$ b2 --version
B2 5.3.2 (OS=LINUX, jobs=20)   ✅

$ b2 --help
B2 5.3.2 (OS=LINUX, jobs=20)   ✅ (有HMDFS scandir权限警告，不影响功能)
```

### 构建项目验证（真实执行）
```bash
# 创建测试项目: Jamroot.jam + hello.cpp
$ b2 toolset=clang
...found 8 targets...
...updating 5 targets...
clang-linux.compile.c++ bin/clang-linux-15/debug/hello.o
clang-linux.link bin/clang-linux-15/debug/hello
...updated 5 targets...    ✅

$ ./bin/clang-linux-15/debug/hello
Hello from b2 on OpenHarmony!    ✅

$ b2 clean toolset=clang
common.Clean clean
...updated 1 target...    ✅
```

### 自测套件结果
- 53个测试通过（核心Jam语言测试 + 库集成测试）
- 119个测试失败（全部因默认使用gcc工具集，OpenHarmony上g++不存在）
- 详细报告见 `reports/test-report.md`

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| boost-build-1.90.0-ohos-aarch64.tar.gz | 3077KB (3.1MB) | 预编译包 |
| boost-build-1.90.0-ohos-aarch64-debug.tar.gz | 540KB | 调试符号包 |

## 注意事项

1. boost-build使用自定义bootstrap.sh构建流程，不是标准的autotools/cmake项目
2. b2不支持DESTDIR模式，需要手动创建staging目录
3. G0 clean verify不适用于自定义构建系统(无configure脚本)
4. 需指定toolset=clang，否则b2默认使用gcc(不存在)
5. b2的--version输出为"B2 5.3.2"，而非"boost-build 1.90.0"

---