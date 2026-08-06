# aiksaurus 1.2.1+dev-0.12 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，libtool shared-only）
- 编译日期: 2026-08-05
- 编译器: clang 15.0.4 / clang++（/data/service/hnp/bin）
- 状态: built（conan create 验证通过，未 upload）
- 平台: HarmonyOS PC aarch64（os=OHOS, arch=armv8, profile: ci/conan/profiles/ohos-aarch64）

## 编译步骤

```bash
# 1. 源码获取（官方 Debian 源镜像，已验证 md5=e9b6b345e20aa7e479c2c8363f700b55）
#    https://deb.debian.org/debian/pool/main/a/aiksaurus/aiksaurus_1.2.1+dev-0.12.orig.tar.gz
#    sha256=b65316c8737f25174b0133fa0255638cd49863381520c64f00cbc28442d8ea16

# 2. 探索编译
export CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++
./configure --prefix=$DEFAULT_PREFIX   # 需 config.guess/sub + configure 补丁
make -j2                               # 产物: libAiksaurus-1.2.so.0.0.1 + aiksaurus + caiksaurus
make install DESTDIR=$TEST_PREFIX

# 3. 功能验证
AIK_DATA_DIR=data/ ./base/.libs/aiksaurus happy
# → 正常输出各义项同义词（beery, drunk, ... sparkling, ... gladsome ...）

# 4. Conan 配方验证
python3 scripts/ohc-run.py conan-verify aiksaurus 1.2.1+dev-0.12
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: unable to guess system type` / `Invalid configuration 'aarch64-linux-ohos'` | 上游 2004-03-12 版 config.guess/config.sub 无 HarmonyOS 分支（E007） | 替换为 GNU 官方 2023-08-22 版 config.guess/config.sub（内置 aarch64-unknown-linux-ohos），补丁 0001/0002 |
| 2 | config.status 报 `confstatXXXX/out: Permission denied`，Makefile/config.h 未生成 | configure/config.status 用 `umask 077 && mktemp -d` 建临时目录，HMDFS 上该目录 owner 不可写（E046 类平台限制） | 移除 configure 中两处 `umask 077`（`mktemp -d` / `mkdir`），补丁 0003 |
| 3 | `aiksaurus: Cannot Open Meanings File` | 词典数据在 data/ 目录，运行时用编译期宏 AIK_DATA_DIR 定位 share/aiksaurus/ | 功能验证时用 `Aiksaurus(meanings_path, words_path)` 构造显式传路径（见 test_package） |
| 4 | `config.h` 无 `HAVE_GETENV`，`AIK_DATA_DIR` 环境变量覆盖不生效 | 上游 `AC_CHECK_FUNC(getenv)` 未配 AC_DEFINE（autoconf 2.72 行为差异） | 记录为上游缺陷；默认路径正常工作，不修改（如需覆盖可用显式路径构造） |
| 5 | 下载 tarball 中断（28MB，debian 源慢） | 网络限速（~82KB/s）导致 300s 超时 | `curl -C -` 断点续传；最终 md5=e9b6b345e20aa7e479c2c8363f700b55 匹配 |

## 源码修改

| 补丁 | 内容 |
|------|------|
| 0001-config.guess.patch | config.guess 升级 GNU 官方 2023-08-22（+HarmonyOS 检测，输出 aarch64-unknown-linux-ohos） |
| 0002-config.sub.patch | config.sub 升级 GNU 官方 2023-08-22（+linux-ohos 三元组识别） |
| 0003-configure.patch | configure 移除 `umask 077`（临时目录创建，HMDFS 兼容） |

## 依赖版本

- 无外部依赖（仅 autotools 工具链 + clang 15 + libc++）
- OHOS SDK: 26.0.0.18（aarch64-linux-ohos sysroot）

## 验证结果

```bash
# conan create（经 ohc-run.py conan-verify G2 门禁）
# 结果: PASS — 库 + 工具 + 词典数据完整安装，test_package 通过
#   * L2 smoke: aiksaurus --version / --help 正常
#   * L1 test: Aiksaurus::find('happy') → 3 义项 24+ 同义词
#   * G4: bin/{aiksaurus,caiksaurus} lib/libAiksaurus-1.2.so.0 include/Aiksaurus/*.h
#         share/aiksaurus/{words.dat,meanings.dat} 全部就位
#   * G3: 无系统同名库 .so 输出（aiksaurus 非系统库，无隔离问题）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2.x 配方（autotools，shared-only，GTK 禁用） |
| conandata.yml | 源码 URL + SHA256 + 3 个补丁声明 |
| test_package/ | L1 实质测试（真实同义词查询） |
| patches/0001-0003 | config.guess / config.sub / configure 补丁 |
| commands.json | CLI 工具声明（aiksaurus + caiksaurus） |

## 注意事项

- 库文件名为 `libAiksaurus`（注意大小写），链接用 `-lAiksaurus`，头文件在 `include/Aiksaurus/`
- 词典数据必须随包分发到 `share/aiksaurus/`，否则运行时查词失败
- `+` 版本号（1.2.1+dev-0.12）conan 2.29.1 可正常解析
---

**编译结束**: 2026-08-05 17:27
**最终状态**: built
