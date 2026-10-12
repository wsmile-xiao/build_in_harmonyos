# yubico 2.27 适配笔记

> 说明：任务 "yubico 2.27" 对应上游项目 **Yubico PAM 模块（pam_yubico，仓库 yubico-pam）2.27**（Arch/Debian 包名 yubico-pam，版本 2.27；并非 libyubikey/yubico-c 1.13）。

## 编译环境
- 构建系统: autotools（官方 release 源树含预生成 configure，免 automake）
- 编译日期: 2026-10-02
- 编译器: clang 15.0.4（OHOS aarch64）
- 状态: built（本地 conan create 验证通过后可标 published）

## 依赖（W0 已确认全部发布制品仓 ohpcd）
- linux-pam/1.7.2（提供 security/pam_appl.h、pam_modules.h、libpam.so）
- json-c/0.18（注意：ykpers 依赖 json-c/0.18，不能用 0.17，否则版本冲突）
- ykclient/2.15（yubico-c-client，静态 libykclient.a）
- ykpers/1.20.0（yubikey-personalization，静态 libykpers-1.a + libyubikey.a + libusb-1.0.a）

## 编译步骤
```bash
# 1) 安装依赖（ohos-aarch64 profile）
conan install --requires=json-c/0.18 --requires=linux-pam/1.7.2 \
  --requires=ykclient/2.15 --requires=ykpers/1.20.0 \
  -r=ohpcd -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=never -of=<deps-dir>

# 2) configure（缓存变量覆盖链接探测 + 显式注入依赖路径）
./configure --prefix=<prefix> CC=clang CXX=clang++ \
  CPPFLAGS="-I<json-c>/include -I<linux-pam>/include -I<ykclient>/include -I<ykpers>/include" \
  LDFLAGS="-L<json-c>/lib -L<linux-pam>/lib -L<ykclient>/lib -L<ykpers>/lib -L<curl>/lib" \
  LIBS="-ljson-c -lcurl" \
  ac_cv_libykclient=yes ac_cv_libyubikey=yes \
  YKPERS_CFLAGS="-I<ykpers>/include/ykpers-1" YKPERS_LIBS="-L<ykpers>/lib -lykpers-1 -lusb-1.0"
# 3) make
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot guess build type | tarball 自带 config.guess(2018) 不识别 aarch64:OHOS | 补丁 config.guess 增加 `aarch64:OHOS:* \| aarch64:HarmonyOS:*` → `aarch64-unknown-linux-ohos` |
| 2 | config.sub: Invalid configuration 'aarch64-unknown-linux-ohos' | 旧 config.sub 不识别 linux-ohos OS | 补丁 config.sub 两处加 `linux-ohos*`（kernel-os 列表 + os 列表） |
| 3 | config.status: can't create ./confXXX/subs1.awk: Permission denied | config.status 硬编码 `(umask 077 && mktemp -d ./confXXXXXX)` 建 0700 临时目录，HMDFS 上 0700 目录所有者亦不可写（librrd 先例） | 补丁 configure 两处 `umask 077`→`umask 022` |
| 4 | configure: Libykclient v2.15+ required | ykclient 为静态库，AC_LIB_HAVE_LINKFLAGS 链接探测失败（缺传递依赖） | configure 传 `ac_cv_libykclient=yes ac_cv_libyubikey=yes` 跳过探测 + LIBS 注入 -ljson-c -lcurl |
| 5 | pkg-config: No package 'ykpers-1' found | ykpers 依赖的 .pc 未在 PKG_CONFIG_PATH；且 ykpers-1.pc 的 prefix 指向构建期 staging 路径（不存在） | PKG_CONFIG_PATH 指向 ykpers lib/pkgconfig；显式传 YKPERS_CFLAGS/YKPERS_LIBS 指向真实包路径 |
| 6 | libtool: cannot find .../staging/lib/libyubikey.la | 依赖包 .la 烘焙构建期 staging 路径；libtool 链接中间 .la 时解析失败（ideviceinstaller #6853 先例） | 消费者侧把依赖包 lib/*.la 改名 *.la.bak，libtool 回退 -L+-l 解析真实 .a/.so |
| 7 | ykpamcfg: undefined symbol libusb_* | libykpers-1.a 依赖 libusb-1.0，但 ykpers-1.pc 未声明 | LIBS 追加 -lusb-1.0（tests/Makefile 同样追加） |
| 8 | make -j2: jobserver mkfifo Operation not permitted | OHOS 沙箱禁止 mkfifo | 单任务 make（不用 -j） |

## 源码修改
- `build-aux/config.guess`：识别 aarch64:OHOS/HarmonyOS → aarch64-unknown-linux-ohos
- `build-aux/config.sub`：两处加 linux-ohos* 识别
- `configure`：config.status 临时目录 umask 077→022（OHOS 沙箱可写临时目录）
- `tests/util_test.c`：两处 `/tmp/pamtest.XXXXXX` 模板改为 `$TMPDIR/pamtest.XXXXXX`（OHOS /tmp 只读，E002）

## 依赖版本
linux-pam/1.7.2、json-c/0.18、ykclient/2.15、ykpers/1.20.0（+传递 curl/8.15.0.1、zlib/1.3.1.1）

## 验证结果（上游测试，R51 如实回填）

**上游测试清点**：`tests/` 下 2 个测试二进制（util_test、pam_test）。
- `util_test.c`：5 个用例（test_get_user_cfgfile_path / test_check_user_token / test_load_chalresp_state / test_check_user_challenge_file / test_filter_printf）
- `pam_test.c`：5 个核心场景（test_authenticate1-5；LDAP/MySQL 场景因未启用 HAVE_LIBLDAP/RUN_MYSQL_TESTS 未编译）

**适配后实测**：
| 测试 | 结果 | 说明 |
|------|------|------|
| util_test | 未完整通过 | test_filter_printf 通过；test_check_user_token 在 OHOS 沙箱 SIGABRT（Signal 6，退出码 134，直接捕获非管道误读）——崩溃点位于 check_user_token 的 token 匹配循环（util.c:362 附近），疑似 musl libc 交互/上游缺陷，待进一步调查；test_check_user_token 之后用例未执行。已按 AI 检视恢复 mkstemp/fdopen 返回值检查（assert fd != -1 / assert handle != NULL） |
| pam_test | 0/5（场景1失败） | `ykclient return value (109): Error performing curl`——沙箱 socket 限制，mock ykval server(localhost:17502) 不可达；场景1失败即中止，后续未执行；进程收尾被 SIGKILL(137) |

**测试通过率**：util_test 未完整通过（test_filter_printf 通过，test_check_user_token SIGABRT——环境/平台问题待查，此前误报 5/5 系管道退出码误读，已更正）；pam_test 场景1因沙箱 socket 限制失败（环境性 expected_fail，与 dovecot 沙箱 socket 先例一致），PR 中如实说明。

**产物冒烟**：`./ykpamcfg -v` 正常运行（输出 "YubiKey core error: no yubikey present"，无硬件属正常）；`pam_yubico.so` 链接依赖完整。

## 交付物
| 文件 | 说明 |
|------|------|
| .libs/pam_yubico.so | PAM 模块（约 150KB，动态库） |
| ykpamcfg | 命令行工具（YubiKey 配置） |

## 注意事项
- ykpers 依赖 **json-c/0.18**（非 0.17），版本冲突会导致 conan install 失败
- 依赖包（linux-pam/json-c/ykclient/ykpers）的 .la 文件烘焙构建期 staging 路径，消费者需 `.la → .la.bak` 回退 -L+-l（工具已实现于 conanfile build()）
- 产物为 PAM 模块（动态库），需 linux-pam 提供 security/pam_*.h；模块安装到 lib/security/
- 命令工具 ykpamcfg 需声明 commands.json（R38）
- OHOS 沙箱无 PAM 运行时权限语义（setuid/drop_priv），pam_test 中依赖真实 PAM 会话的 socket 类场景无法在沙箱运行
---

**编译结束**: 2026-10-02 19:44
**最终状态**: built
