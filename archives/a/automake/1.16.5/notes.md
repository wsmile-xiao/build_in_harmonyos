# automake 1.16.5 适配笔记

## 编译环境
- 构建系统: autotools (configure) + gen-all.pl (手动生成)
- 编译日期: 2026-03-19 首次适配，2026-04-09 重新编译
- 编译器: clang + musl libc (HarmonyOS NDK)
- Perl: /data/service/hnp/bin/perl v5.42.0
- 状态: success

## 编译步骤
1. 下载解压 automake-1.16.5.tar.xz
2. 应用补丁 0001-port-for-ohos.patch（config.guess + config.sub）
3. 手动修复 config.sub（3处 linux-ohos 识别，原补丁遗漏）
4. `./configure --prefix=$HOME/usr/local`
5. 使用 gen-all.pl 手动生成 Config.pm / automake / aclocal / amversion.m4
6. 修补残留变量 @am_AUTOCONF@ → autoconf, @PACKAGE_URL@ → URL
7. 手动安装 Perl 库/脚本/M4 宏/辅助脚本

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 鸡生蛋问题导致 make 失败 | automake 脚本依赖 Config.pm，而 Config.pm 由 configure 生成 | gen-all.pl 手动生成替代 |
| 2 | config.sub 不识别 linux-ohos | 原补丁只改了 config.guess | 补充 config.sub 3处修改 |
| 3 | 残留 @am_AUTOCONF@ 变量 | gen-all.pl 的 do_subst 不完整 | sed 后处理替换 |
| 4 | 符号链接受限 | HMDFS 不支持 ln -sf | 用 cp 创建版本化副本 |
| 5 | 官方测试套件不可用 | make check 触发 automake 重新生成 | 手动全链路功能测试替代 |

## 源码修改
- `lib/config.guess` — HarmonyOS 内核检测 + aarch64 输出 + 上游同步
- `lib/config.sub` — linux-ohos OS 识别 (3处)
- `bin/automake` — 残留 @am_AUTOCONF@ sed 替换
- `bin/aclocal`, `bin/automake` — 残留 @PACKAGE_URL@ sed 替换

## 验证结果
- automake --version → GNU automake 1.16.5 ✅
- aclocal --version → GNU aclocal 1.16.5 ✅
- autoreconf --install --force → PASS
- 完整工作链: configure.ac → autoreconf → configure → make → run → PASS
- Staging 隔离目录全链路测试 → PASS
- 质量门禁 G1-G3 通过

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| automake-1.16.5-ohos-aarch64.tar.gz | 1.2MB | 主包（105 文件） |

## 注意事项
- gen-all.pl 是核心脚本，必须保留
- 产物包含：bin/automake, bin/aclocal, Perl 模块, M4 宏, 辅助脚本
- 官方 make check/make install 不可用，需手动安装
