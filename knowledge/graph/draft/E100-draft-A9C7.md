# E100: Meson 构建系统手动编译方案

## 问题识别

当软件使用 Meson 构建系统而非 autotools，且 Meson 工具不可用时，会出现以下错误：
- `python.*meson.*PackageNotFoundError`
- `configure.*not found`
- 项目目录只有 `meson.build` 文件，没有 `configure` 脚本

## 根因分析

Meson 是新一代构建系统，依赖 Python 运行。当 Meson Python 包未正确安装或存在依赖问题时，无法使用 `meson setup/build` 命令。但对于简单的静态库软件，手动编译通常更快速可靠。

## 解决方案

### 手动编译流程（适用于小型静态库）

1. **识别源文件**：
   ```bash
   ls *.c *.h
   ```

2. **编译目标文件**：
   ```bash
   /data/service/hnp/bin/clang -O2 -Wall -fPIC -c *.c
   ```

3. **创建静态库**：
   ```bash
   /data/service/hnp/bin/ar rcs lib*.a *.o
   /data/service/hnp/bin/ranlib lib*.a
   ```

4. **Staging 安装**（R20 DESTDIR 模式）：
   ```bash
   mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/lib
   mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/include
   cp lib*.a $TEST_PREFIX/$DEFAULT_PREFIX/lib/
   cp *.h $TEST_PREFIX/$DEFAULT_PREFIX/include/
   ```

5. **创建 pkg-config 文件**：
   ```bash
   echo "prefix=$DEFAULT_PREFIX
   Name: <软件名>
   Version: <版本>
   Libs: -L\${prefix}/lib -l<库名>
   Cflags: -I\${prefix}/include" > $TEST_PREFIX/$DEFAULT_PREFIX/lib/pkgconfig/<软件名>.pc
   ```

6. **验证**：
   ```bash
   file lib*.a
   pkg-config --cflags --libs <软件名>
   ```

## 适用范围

- Meson 构建系统的小型静态库软件
- 只有少量 .c/.h 文件的项目
- 如 inih、cJSON、libconfig 等

## 实战案例

**inih r58**：
- 构建系统：Meson
- 问题：Meson Python 包未正确安装
- 解决方案：手动编译静态库
- 结果：成功编译 libinih.a (3.3KB)，所有质量门禁通过

## 注意事项

1. 手动编译不需要 DESTDIR，但为了符合 R20，仍应使用 staging 目录
2. 需要手动创建 pkg-config 文件以支持依赖发现
3. 简单的静态库通常无需补丁
4. 验证时可通过编译测试程序确认库可用性

## 质量门禁

手动编译需满足：
- G1：静态库文件存在且为 ar archive
- G2：可通过 pkg-config 查询
- G3：静态库无需 RPATH
- G4：manifest.yaml、notes.md、packaging/ 完整