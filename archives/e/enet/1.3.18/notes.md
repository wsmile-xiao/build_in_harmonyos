# enet 1.3.18 适配笔记

## 编译环境
- 构建系统: autotools (configure.ac + Makefile.am, libtool)
- 编译日期: 2026-08-19
- 编译器: clang 15.0.4 / clang++
- 状态: published
- 上游仓库: https://github.com/lsalzman/enet
- tag: v1.3.18

## 编译步骤

enet 源码仅含 configure.ac（无预生成 configure），需先 autoreconf 生成：

```bash
source .build-context-enet-1.3.18
cd $BUILD_SRC_DIR
# 1. 生成 configure + config.guess/config.sub（automake/1.18 tool_requires，2024-07-27，无 HarmonyOS case）
autoreconf -fi
# 2. E007: 补 OHOS 识别到 config.guess/config.sub（automake/1.18 未含 HarmonyOS case）
perl $REPO/scripts/patch-autotools-ohos.pl config.guess config.sub
# 3. 修复 HMDFS umask 077 权限问题（E011/E129）
sed -i 's/umask 077/umask 022/g' configure
# 4. configure（原生编译，禁用 --host/--build/--target，R15/E007）
./configure --prefix=$DEFAULT_PREFIX
# 5. 编译 + 安装
make -j2
make install DESTDIR=$TEST_PREFIX
# 6. make check（enet 无 test suite，"Nothing to be done"）
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 下载失败 (v-1.3.18 tag 404) | 上游 tag 名为 v1.3.18 而非 v-1.3.18 | 改用 URL https://github.com/lsalzman/enet/archive/refs/tags/v1.3.18.tar.gz |
| 2 | config.status: can't create ./confXXXXXX/subs1.awk: Permission denied | HMDFS umask 077 创建临时目录权限 drwx--S--- 不可写 (E011/E129) | sed -i 's/umask 077/umask 022/g' configure |
| 3 | conan create: aclocal "Can't exec: No such file or directory" (E116/E178) | CI Worker 的 /data/service/hnp/bin autoconf 套件不含 aclocal/automake/libtoolize，系统 PATH 无可用 automake | build_requirements() 通过 build profile 拉入完整 automake/1.18 + libtool/2.5.4（afuse/aircrack-ng/adcli/air-quality-sensor 同款 E178 模式） |
| 4 | 配方曾用 shutil.which + PERL5LIB 拼凑系统残缺 automake | 仅作者本地预检机有残缺 aclocal，CI Worker 上 aclocal 可执行文件不存在，拼凑方案不可复现 | 改为 tool_requires automake/libtool（build profile 解析），build() 直接 autoreconf --install --verbose，无硬编码路径（R33-safe） |
| 5 | configure: error: cannot guess build type (E007) | automake/1.18 ships unpatched config.guess (2024-07-27) with no HarmonyOS case; config.guess compile-dummy fallback hits HMDFS umask 077 Permission denied | build() runs patch-autotools-ohos.pl after autoreconf --install to add OHOS recognition |

### 关键决策

- **未使用 --host=aarch64-linux-ohos**：SKILL R15/E007 明确禁止 --build/--host/--target。
  本平台为原生编译（build=host=OHOS/aarch64），config.guess 正确返回
  aarch64-unknown-linux-ohos。automake/1.18 (tool_requires) 提供 2024-07-27 版
  config.guess/config.sub，未含 HarmonyOS case，build() 需在 autoreconf --install
  之后运行 scripts/patch-autotools-ohos.pl 补 OHOS 识别（E007）。此为 addrwatch 等
  autotools 配方同款模式。
- **umask 修复为构建步骤而非源码补丁**：configure 由 autoreconf 从 configure.ac
  生成，umask 077 来自 autoconf 模板（系统级）。每次 autoreconf 后需 sed 修复。
  此修复固化为 conanfile.py 的 build() 步骤。
- **autotools 工具链修复（E178）**：CI Worker 的 /data/service/hnp/bin 只有
  autoconf 2.72 套件，无 aclocal/automake/libtoolize；系统 PATH 也不含可用
  automake。配方不拼凑系统残缺工具，而是 build_requirements() 通过 build profile
  拉入完整 automake/1.18 + libtool/2.5.4，build() 直接 `autoreconf --install
  --verbose`（afuse/aircrack-ng/adcli/air-quality-sensor 同款模式，R33-safe，
  无硬编码绝对路径）。早期版本曾用 shutil.which + PERL5LIB 拼凑系统残缺 automake，
  但 CI Worker 上 aclocal 可执行文件不存在（No such file or directory），方案不可复现。

## 源码修改

无源码 (.c/.h/configure.ac) 修改。唯一调整为生成文件 configure 的 umask 077→022
（构建步骤，非源码补丁）。track-edit scan 确认 37 个源文件零变更。

## 依赖版本

无外部依赖（纯 C UDP 网络库，仅依赖 POSIX socket API）。

## 验证结果

```bash
# config.guess 识别 OHOS
$ ./config.guess
aarch64-unknown-linux-ohos

# 编译产物
$ ls .libs/
libenet.a  libenet.so  libenet.so.7  libenet.so.7.0.6

# staging 安装
$ find $TEST_PREFIX -name 'libenet*'
libenet.so.7.0.6 / libenet.so.7 / libenet.so / libenet.a / libenet.la / libenet.pc
+ 9 headers (include/enet/*.h)

# make check
$ make check
make: Nothing to be done for 'check'.   # enet 无 test suite
```

## 交付物

| 文件 | 说明 |
|------|------|
| libenet.so.7.0.6 | 共享库 (soname libenet.so.7) |
| libenet.a | 静态库 |
| libenet.pc | pkg-config 文件 |
| include/enet/*.h | 9 个头文件 |

## 注意事项

- enet 同时提供 CMakeLists.txt 和 autotools，本配方使用 autotools（与 SKILL 模式 B 一致）。
- 构建步骤必须包含 autoreconf -fi + umask sed 修复，否则 configure 阶段失败。
---

**编译结束**: 2026-08-19 10:42
**最终状态**: published
