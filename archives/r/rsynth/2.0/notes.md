# rsynth 2.0 适配笔记

## 编译环境
- 构建系统: autotools（1994 年 autoconf 2.0 时代脚本）
- 编译日期: 2026-10-06
- 编译器: clang 15.0.4（OHOS SDK, aarch64-unknown-linux-ohos）
- 状态: published

## 源码来源
- 上游官方站点 www.speech.cs.cmu.edu/rsynth/ 已不可达（HTTP 404）。
- 采用 Debian snapshot 权威镜像中的原版上游源码包 `rsynth_2.0.orig.tar.gz`：
  https://snapshot.debian.org/archive/debian-archive/20090802T004153Z/debian/pool/non-free/r/rsynth/rsynth_2.0.orig.tar.gz
  （sha256 af4c849c62dc77405c12ebfec1e85ec2955322a5431567f8da36e580d10e583f）

## 编译步骤
```bash
# conan create（等价于下述手动步骤）
conan create archives/r/rsynth/2.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --user=ohpcd --channel=stable

# 手动复现
./configure --prefix=/
make -j1
make check              # 上游测试（./say -W "Hello there"）
make install DESTDIR=<pkg>   # 经 Makefile.in 补丁支持 DESTDIR
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/sub 无法识别 aarch64 | 1994 年 GNU 脚本不认识 aarch64/ohos | 替换为含 __OHOS__ 检测的现代版本（输出 aarch64-unknown-linux-ohos） |
| 2 | `make install` 忽略 DESTDIR | 1994 Makefile 安装规则无 DESTDIR 概念 | 补丁 Makefile.in 安装规则：目标目录改为 $(DESTDIR)$(BIN_DIR) 等（Conan Autotools.install() 依赖） |
| 3 | configure 报 `--bindir=${prefix}/bin: invalid option` | Conan AutotoolsToolchain 自动追加 bindir/libdir 等现代选项，1994 configure 不识别 | conanfile.py generate() 中裁剪这些 flag，仅保留 --prefix=/ |
| 4 | 运行时打印 `/dev/sbdsp: No such file or directory` | linuxplay 驱动尝试打开 Linux 声卡设备，OHOS 无 | 平台差异，无害降级（open 失败继续）；文件合成不受影响，不修改 |
| 5 | 上游 make check 中 `-W` 被当文本拼读 | -W 未在 getargs 注册，属上游行为 | 不修改；测试仍通过（完整流水线跑通） |

## 源码修改
补丁列表（patches/）：
- 0001-Makefile.in.patch: 安装规则增加 DESTDIR 支持（+4/-3）
- 0002-config.guess.patch: 1994 版→含 OHOS 识别的现代版（+1711/-229）
- 0003-config.sub.patch: 1994 版→支持 aarch64-unknown-linux-ohos 三元组的现代版（+1814/-789）

## 依赖版本
- 无第三方依赖（gdbm 可选，未启用；无 X11/nas）。全部功能仅用 libc/math（musl libc 内建）。

## 验证结果
```bash
make check                                        # ✅ PASS（上游 1/1）
say --help                                        # ✅ PASS
say -o t3.au "Hello world"                        # ✅ .au 有效（.snd, 8000Hz, ULAW）
say -l t4.raw "numbers 12345"                     # ✅ raw 16-bit 有效
say -r 12000 -o t5.au "..."                       # ✅ 采样率 12000Hz 生效
say -o t6.au "[hEl@U w3:ld]"                      # ✅ 音素输入
echo "..." | say -o t7.au                         # ✅ stdin 输入
conan-verify G0-G4 + L2/L4/L5                     # ✅ 全部通过（L2/L4/L5 因无 cache 跳过）
```

## 交付物
| 文件 | 说明 |
|------|------|
| archives/r/rsynth/2.0/conanfile.py | Conan 配方（application，Autotools） |
| archives/r/rsynth/2.0/conandata.yml | 源码 URL + sha256 + 3 个补丁声明 |
| archives/r/rsynth/2.0/test_package/ | test.sh 消费者测试（say --help + .au/.raw 合成校验） |
| archives/r/rsynth/2.0/patches/ | 3 个适配补丁 |
| archives/r/rsynth/commands.json | 工具声明（R38, say 命令） |
| archives/r/rsynth/2.0/reports/ | 本地验证证据（pre-analysis / test-report / conan-verify-report / conan-create.log，不入库，仅本地留存） |

## 注意事项
1. rsynth 为纯工具（可执行文件 `say`），非库，package_type=application，无 cpp_info.libs。
2. 平台适配（R40）：核心合成流水线完整可用；实时声卡播放为上游 linuxplay 驱动（OHOS 无 /dev/dsp），文件输出路径不依赖声卡，为实质性可用适配。
3. `--enable-static/--disable-shared` 对该 1994 configure 虽可接受但无意义（不产库），配方未使用。
4. L2/L4/L5 门禁本环境跳过（无 cache 路径）；二进制已确认 PIE/RELRO/AArch64。
---

**编译结束**: 2026-10-06 15:27
**最终状态**: published
