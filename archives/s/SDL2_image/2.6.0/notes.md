# SDL2_image 2.6.0 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-05-27
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. **依赖安装**: 通过 cmd-pkgs 安装 SDL2 预编译包
   ```bash
   curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- SDL2 2.30.0
   ```

2. **环境设置**: 设置 pkg-config 路径
   ```bash
   export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
   ```

3. **CMake 构建**: 使用 CMake 绕过 autotools heredoc 权限问题
   ```bash
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release ..
   make -j1
   make install DESTDIR=$TEST_PREFIX
   ```

4. **打包**: 使用 ohc-run.py package 制作预编译包
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py package SDL2_image 2.6.0
   ```

5. **验证**: 本地安装验证
   ```bash
   make install  # 安装到 ~/usr/local
   pkg-config --modversion SDL2_image  # 输出: 2.6.0
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: heredoc Permission denied | E009/E011: HMDFS 文件系统权限限制 | 切换到 CMake 构建系统绕过 autotools |
| 2 | SDL2 依赖缺失 | 未安装 SDL2 库 | 通过 cmd-pkgs 安装 SDL2 2.30.0 预编译包 |
| 3 | pkg-config 找不到 sdl2 | PKG_CONFIG_PATH 未设置 | 设置 PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig |
| 4 | G4 档案完整性失败 | 缺少软件级 README.md 和顶层 build_system 字段 | 创建 README.md + 添加 build_system 字段 |

## 源码修改

- **0001-config.guess.patch**: 添加 HarmonyOS 平台检测（E007）
- **0002-config.sub.patch**: 支持 ohos-linux 三元组（E007）

## 依赖版本

- SDL2 2.30.0（通过 cmd-pkgs 安装）

## 验证结果

```bash
$ pkg-config --modversion SDL2_image
2.6.0

$ pkg-config --cflags --libs SDL2_image
-D_REENTRANT -I~/usr/local/include/SDL2 -L~/usr/local/lib -lSDL2_image -lSDL2

$ file ~/usr/local/lib/libSDL2_image.so
ELF 64-bit LSB shared object, ARM aarch64, version 1 (SYSV), dynamically linked
```

**测试套件**: 无标准测试套件（cmake/test/ 为示例程序），跳过测试

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| SDL2_image-2.6.0-ohos-aarch64.tar.gz | 1.8M | 预编译包（主产物） |
| SDL2_image-2.6.0-ohos-aarch64-debug.tar.gz | 341K | 调试符号包 |
| 0001-config.guess.patch | 1.0K | 平台检测补丁 |
| 0002-config.sub.patch | 2.5K | 三元组支持补丁 |

## 注意事项

- **构建系统选择**: 推荐使用 CMake 构建，避免 autotools heredoc 权限问题（E009/E011）
- **依赖安装**: 必须先安装 SDL2，建议使用 cmd-pkgs 预编译包
- **pkg-config**: 需正确设置 PKG_CONFIG_PATH 才能检测 SDL2

---

**编译结束**: 2026-05-27 18:17
**最终状态**: built
**质量门禁**: G1-G4 PASS ✅