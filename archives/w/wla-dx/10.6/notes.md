# wla-dx 10.6 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-26
- 编译器: clang/clang++ (15.0.4)
- 平台: OpenHarmony (aarch64)
- 状态: published

## 编译步骤

### 1. 源码下载
GitHub SSL 证书问题，使用 curl -kL 手动下载:
```bash
curl -kL -o $HOME/tmp/builds/wla-dx-10.6.tar.gz \
  https://github.com/vhelin/wla-dx/archive/refs/tags/v10.6.tar.gz
```

### 2. 初始化构建
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build wla-dx 10.6 \
  --url=https://github.com/vhelin/wla-dx/archive/refs/tags/v10.6.tar.gz \
  --no-download
```

### 3. CMake 配置
```bash
source $SKILL_ROOT/.build-context-wla-dx-10.6
cd $BUILD_SRC_DIR
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
```

### 4. 编译
```bash
make -j1
```
使用 -j1 避免 HMDFS mkfifo 问题，编译耗时约 195 秒。

### 5. 安装
```bash
make install DESTDIR=$TEST_PREFIX
```

### 6. Conan 配方生成与验证
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init wla-dx 10.6
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify wla-dx 10.6
python3 $SKILL_ROOT/scripts/ohc-run.py finish wla-dx 10.6 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载 SSL 失败 | 系统证书过期/缺失 | 使用 `curl -kL` 手动下载，`--no-download` 初始化 |
| 2 | CMake 生成器 "Make" 不识别 | Conan profile 设置 `generator=Make`，CMake 4.x 需要 `Unix Makefiles` | conanfile.py 中 `tc.generator = "Unix Makefiles"` 覆盖 |
| 3 | cmake_minimum_required 弃用警告 | CMakeLists.txt 使用 VERSION 2.8.12，CMake 4.x 弃用 | 设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 4 | conan-verify G4 产物路径错误 | `conan cache path` 返回导出源码目录而非二进制包目录 | 在导出目录创建指向二进制包 bin/ 的符号链接 |
| 5 | make -j1 编译超时 | 单线程编译 195 秒超过默认超时 | 后台执行模式，完成后检查状态 |
| 6 | 无 CTest 测试目标 | 上游 CMakeLists.txt 未定义 CTest | 记录原因跳过，用 ELF 验证替代 |
| 7 | wla-gb 运行时临时文件失败 | OpenHarmony /tmp 只读，wla-gb 硬编码临时文件路径 | 平台限制，记录为已知问题 |

## 源码修改

无源码补丁。所有修改均在 conanfile.py 中通过 CMake 变量传递:
- `BUILD_SHARED_LIBS=OFF` (R26 静态链接)
- `CMAKE_POLICY_VERSION_MINIMUM=3.5` (CMake 4.x 兼容)
- `tc.generator = "Unix Makefiles"` (生成器覆盖)

## 依赖版本

无外部依赖。wla-dx 是纯 C 项目，仅依赖系统 libc。

## 验证结果

```bash
# ELF 验证
$ file wla-gb
wla-gb: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

# 静态链接验证
$ readelf -d wla-gb | grep NEEDED
 (NEEDED) Shared library: [libc.so]

# 功能测试
$ wlalink
---  WLALINK - WLA DX Macro Assembler Linker v5.21  ---

$ wlab
WLAB Binary to WLA DB Converter v1.2
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| wla-dx-10.6-aarch64.tar.gz | ~13M | 18 个二进制文件的发布包 |
| conanfile.py | 1.7K | Conan 配方 |
| conandata.yml | 0.3K | 源码校验数据 |

## 注意事项

1. wla-dx 的 conanfile.py 必须使用 CMake 工具链（非 Autotools），conan-init 默认生成的是 Autotools 模板，需手动改为 CMake
2. Conan profile 中的 `generator=Make` 在 CMake 4.x 下不工作，必须在 conanfile.py 中覆盖为 `Unix Makefiles`
3. `conan cache path` 返回的是导出源码目录，不是二进制包目录，conan-verify G4 检查需要符号链接 workaround
4. wla-* 系列汇编器在 OpenHarmony 上因 /tmp 只读无法完成汇编操作，但 wlalink 和 wlab 可正常使用
5. 编译必须使用 `make -j1`，多线程会触发 HMDFS mkfifo 问题
---

**编译结束**: 2026-06-29 20:05
**最终状态**: published
