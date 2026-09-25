# outils 0.14 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 Makefile，无 configure）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18，aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤
1. 下载官方 tag 归档（GitHub archive v0.14，sha256 e4dcbd92…91eb）
2. 应用 6 个补丁（见下）
3. `make CC=clang -j1`（Makefile 默认 PREFIX=/usr 仅影响 calendar 的 _PATH_INCLUDE 宏）
4. 上游无测试套件（R51 清点：无 tests/ 目录、Makefile 无 test/check 目标）
5. test_package 20 条消费者回归断言（含鸿蒙特有 calendar #include 展开场景）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lam 链接失败：undefined symbol: explicit_bzero | 上游 Makefile 在 glibc 上依赖 libc 提供 explicit_bzero；musl 无，而 lam 目标漏链 explicit_bzero.o | 补丁 0001 补链 src/liboutils/explicit_bzero.o |
| 2 | ts 链接失败：undefined symbol: reallocarray | 同上（glibc 自带 reallocarray，musl 无；ts 目标漏链） | 补丁 0001 补链 src/liboutils/reallocarray.o |
| 3 | rdate 链接失败：undefined symbol: adjtime | musl 不实现 adjtime(3)（glibc 有）；rdate -a 滑动校时需要 | 补丁 0002/0003 新增 adjtime 兼容实现（clock_adjtime）+ 原型；0001 补链 |
| 4 | calendar 无法打开任何日历文件 | calendar 通过 execl("/usr/bin/cpp", …) 展开 #include；HarmonyOS 无 /usr/bin/cpp | 补丁 0004/0005/0006：内置 #include 展开（pipe+fork 流式），保留 -I. + _PATH_INCLUDE 搜索语义 |
| 5 | 内置展开曾尝试内存流方案失败 | OHOS musl 上 open_memstream 不累积输出（buflen=0）、fmemopen 读取 SIGILL；tmpfile() 因 /tmp 只读失败（errno 13） | 改用与上游一致的 pipe+fork 流式方案（只用已验证可用的 stdio/pipe） |

## 源码修改
| 文件 | 修改内容 | 补丁 |
|------|----------|------|
| Makefile | lam/ts/rdate 补链对象；calendar 补 preprocess.o | 0001 |
| src/liboutils/adjtime.c | 新增 adjtime(3)（clock_adjtime 实现） | 0002 |
| src/liboutils/outils.h | adjtime 原型声明 | 0003 |
| src/usr.bin/calendar/calendar.h | expand_calendar 原型 | 0004 |
| src/usr.bin/calendar/io.c | calin 输入流 + 无 cpp 时内置展开 | 0005 |
| src/usr.bin/calendar/preprocess.c | 新增 #include 展开器 | 0006 |

## 依赖版本
- 无外部依赖（LIBS=-lm；加密代码随源码内嵌：ed25519 / bcrypt_pbkdf / blowfish / sha2）

## 验证结果
```bash
make CC=clang -j1            # 13 个二进制全部构建成功
# test_package/test.sh：20/20 断言通过（含 calendar #include 展开、随包数据）
# conan-verify G0-G4 与本地 CI gate 结果见 reports/
```

## 注意事项
- calendar 的 `-a`（cron 邮件模式）需要 sendmail，HarmonyOS 无此程序；普通用法（-f/-t/CALENDAR_DIR）不受影响
- 数据文件安装到包内 share/calendar；可用 `CALENDAR_DIR=<prefix>/share/calendar calendar …` 加载随包日历
- md5 别名（cksum/sha1/sha256/sha512）以真实副本安装（argv[0] 分派，行为与上游 ln -s 一致）
---

**编译结束**: 2026-09-21 20:24
**最终状态**: built
