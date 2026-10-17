# libvorbis 1.3.7 适配记录

## Conan 配方补充（2026-07-29）

- 新增 CMake Conan 配方，依赖 `libogg/1.3.6`，并将 libogg 作为
  transitive headers/libs 暴露给消费者；`vorbis/codec.h` 公开包含
  `ogg/ogg.h`，因此 test_package 只依赖 libvorbis 时也应拿到 Ogg 头文件。
- 使用上游 CMake 构建路径，避开 Autotools `config.status` 临时目录权限问题。
- 在 `source()` 阶段将上游 `cmake_minimum_required(VERSION 2.8.12)` 提升到
  `3.5`，避免新版本 CMake 在配置阶段因移除 3.5 以下兼容模式而直接失败。
- 导出 Conan 组件：`Vorbis::vorbis`、`Vorbis::vorbisenc`、`Vorbis::vorbisfile`。
- 新增非交互 `test_package/test_libvorbis.c`，覆盖版本字符串、编码初始化、comment API 与 vorbisfile 符号链接。
- 将上游 v1.3.7 `test/` 中的 `test.c`、`util.c`、`write_read.c` 及对应头文件原样接入
  `test_package`，在打包后的库上执行上游编码/解码往返测试程序。

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **初始化编译环境**
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build libvorbis 1.3.7
   ```

2. **安装依赖**
   - libogg 1.3.6（通过 cmd-pkgs 预编译包安装）
   - coreutils 9.10（通过 cmd-pkgs 预编译包安装，解决管道命令权限问题）

3. **修复平台识别问题（E007）**
   ```bash
   patch-autotools-ohos.pl
   ```
   输出: `aarch64-unknown-linux-ohos`

4. **执行 configure**
   ```bash
   ./configure --prefix=$DEFAULT_PREFIX
   ```

5. **修复 config.status 临时目录权限问题（E103）**
   ```bash
   sed -i 's|ac_tmp=$tmp|ac_tmp=./fixed_tmp_for_config_status|g' config.status
   mkdir -p ./fixed_tmp_for_config_status
   ```

6. **编译和安装**
   ```bash
   make -j1
   make install DESTDIR=$TEST_PREFIX
   ```

7. **预编译包制作**
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py package libvorbis 1.3.7
   ```

8. **本地安装验证**
   ```bash
   make install  # 不带 DESTDIR
   pkg-config --modversion vorbis  # 输出: 1.3.7
   ```

9. **完成归档**
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py finish libvorbis 1.3.7 built
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别平台 | HarmonyOS 未在 config.guess 中定义 | 使用 patch-autotools-ohos.pl 更新 config.guess 和 config.sub |
| 2 | libogg 依赖缺失 | configure 找不到 libogg 库 | 从 cmd-pkgs 安装 libogg 1.3.6 预编译包 |
| 3 | config.status 临时目录权限问题 | autotools 在 HMDFS 文件系统上动态创建临时目录失败 | 使用固定路径替代动态创建 |
| 4 | 管道命令权限问题 | toybox sed/head 不支持管道操作 | 安装 GNU coreutils 9.10 预编译包 |
| 5 | make check 测试失败 | 未签名的共享库在 HarmonyOS 上无法动态加载 | 跳过测试，预编译包制作时自动签名 |

## 源码修改

无永久性源码修改。所有修改均为临时性操作（config.status、config.guess/config.sub）。

## 依赖版本

- libogg 1.3.6
- coreutils 9.10

## 验证结果

```bash
$ pkg-config --modversion vorbis
1.3.7

$ pkg-config --cflags vorbis
-I/home/user/usr/local/include

$ pkg-config --libs vorbis
-L/home/user/usr/local/lib -lvorbis -lm -logg

$ ls ~/usr/local/lib/libvorbis*
libvorbis.a     libvorbisenc.a     libvorbisfile.a
libvorbis.so    libvorbisenc.so    libvorbisfile.so
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libvorbis-1.3.7-ohos-aarch64.tar.gz | 2.7M | 预编译包（库文件 + 头文件 + pkg-config） |
| libvorbis-1.3.7-ohos-aarch64-debug.tar.gz | 220K | 调试符号包 |

## 注意事项

**make check 跳过原因**: 未签名的共享库在 HarmonyOS 上无法动态加载。预编译包制作时会自动对 ELF 文件签名，测试可通过安装预编译包后执行。

**E103 知识图谱草稿**: 已创建 E103-draft-5C76.kv，记录 config.status 临时目录权限问题的解决方案，受影响范围包括所有使用 autotools 构建系统的软件。

---

**编译结束**: 2026-05-27 20:24
**最终状态**: built
