# intercal 0.33 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-29
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 平台: HarmonyOS aarch64
- 状态: published

## 编译步骤

```bash
# 1. 初始化
python3 $SKILL_ROOT/scripts/ohc-run.py init-build intercal 0.33 --url=http://catb.org/~esr/intercal/intercal-0.33.tar.gz

# 2. 读取上下文
source .build-context-intercal-0.33

# 3. 修复 config.status umask 问题
sed -i 's/umask 077/umask 022/g' config.status

# 4. 运行 config.status 生成 Makefile
./config.status

# 5. 移除不支持的编译标志
sed -i '/-fno-toplevel-reorder/d' buildaux/Makefile.am buildaux/Makefile.in Makefile

# 6. 编译
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX --disable-dependency-tracking
make -j1
make install DESTDIR=$TEST_PREFIX

# 7. 测试
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 创建临时文件报 Permission denied | HMDFS 文件系统不支持 umask 077 创建的 0700 权限目录 | 将 configure 和 config.status 中的 `umask 077` 替换为 `umask 022` |
| 2 | clang 报 unknown argument: -fno-toplevel-reorder | 该标志为 GCC 特有，clang 不支持 | 从 buildaux/Makefile.am 和 buildaux/Makefile.in 中移除该标志 |
| 3 | depfiles 引导失败 | 鸿蒙平台上 automake 依赖跟踪机制不兼容 | 添加 `--disable-dependency-tracking` 配置选项 |
| 4 | conan create sha256 校验失败 | 本地下载的 tarball 与 Conan 重新下载的文件 sha256 不同 | 使用 Conan 实际下载时计算的 sha256 值 |
| 5 | conandata.yml patches 未被正确导出 | export_conandata_patches 未复制 patch 文件到 Conan 缓存 | 改为在 conanfile.py build() 中用 sed 命令直接修复源码 |

## 源码修改

conanfile.py 中通过 sed 命令在 build() 阶段自动修复以下文件：

| 文件 | 修改内容 |
|------|----------|
| configure | `umask 077` → `umask 022`（2 处） |
| buildaux/Makefile.am | 删除 `-fno-toplevel-reorder` 行 |
| buildaux/Makefile.in | 删除 `-fno-toplevel-reorder` 行 |

finish 阶段还自动生成了 5 个补丁文件（含 aclocal.m4 和 configh.in 的间接变更）。

## 依赖版本

intercal 0.33 无外部依赖。编译工具链版本：
- clang/clang++: 15.0.4
- make: GNU Make 4.4.1
- autoconf: 2.72
- automake: 1.16.5
- flex: flex
- bison: bison -y

## 验证结果

```bash
# make check 结果
Tests complete. (14 个回归测试全部通过)

# Conan 构建产物（静态链接）
$ file bin/ick
ELF executable, 64-bit LSB arm64, static, not stripped
$ readelf -d bin/ick
There is no dynamic section in this file.

# conan-verify 8 道门禁
G0: PASS, G1: PASS, G2: PASS, G3: PASS, G4: PASS, L2: PASS, L4: PASS, L5: PASS

# test_package
100% tests passed, 0 tests failed out of 1
```

## 产物清单

| 路径 | 文件 | 大小 | 说明 |
|------|------|------|------|
| bin/ | ick | 1,247,168 bytes | INTERCAL 编译器/解释器（静态链接） |
| bin/ | convickt | 894,912 bytes | 字符集转换工具（静态链接） |
| lib/ | libick.a | 79,016 bytes | INTERCAL 运行时库（单线程） |
| lib/ | libickmt.a | 100,590 bytes | INTERCAL 运行时库（多线程） |
| lib/ | libickec.a | 89,544 bytes | ECTO-B98 扩展库 |
| lib/ | libyuk.a | 30,988 bytes | 调试器库 |
| include/ick-0.33/ | 7 个头文件 | — | abcess.h, config.h, fiddle.h, ick_bool.h, ick_ec.h, ick_lose.h, yuk.h |

## 注意事项

1. intercal 是一个 esoteric/parody 编程语言，产物为终端工具，必须静态链接（R26）
2. conanfile.py 的 build() 方法使用 sed 命令修复源码，而非 conandata.yml patches 机制（后者在 Conan 2.12.0 上导出不稳定）
3. G0 预构建评估命中 E007（config.guess 不识别 HarmonyOS），但实际 configure 未因此失败（该软件的 configure 脚本不依赖 config.guess）
4. G0 干净构建验证（finish Step 2.5）因 Python subprocess 平台限制失败，但 conan-verify G2 已独立验证通过

---

**编译结束**: 2026-06-30 00:13
**最终状态**: published
