# yubico-c 2.15 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-18
- 编译器: clang/clang++ (OHOS aarch64)
- 状态: built

## 上游识别
- yubico-c 在本赛事中对应上游 **yubico-c-client** (libykclient)，不是 Yubico/yubico-c (libyubikey，已适配为 libyubikey/1.13)
- 上游 GitHub tag: `ykclient-2.15`
- 官方发布 tarball: https://developers.yubico.com/yubico-c-client/Releases/ykclient-2.15.tar.gz
- 产出: libykclient 静态库 + ykclient CLI 工具

## 编译步骤

```
configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
make -j1 MANS= man1_MANS=
make install -j1 MANS= man_MANS= man1_MANS= dist_man_MANS=
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI: config.sub 拒绝 ohos vendor | config.sub (2014) 只认 gnu vendor（Invalid configuration: machine 'aarch64-unknown-linux' not recognized） | --build/--host=aarch64-unknown-linux-gnu（实际编译器由 compiler_executables 指定） |
| 2 | configure 执行失败 exit 127 | profile 设置 CONFIG_SHELL=/data/service/hnp/bin/bash，本地 macOS 不存在 | self.buildenv.define("CONFIG_SHELL", "sh") 覆盖 |
| 3 | E114: config.status 临时目录失败 | configure 用 umask 077 + mktemp -d，HMDFS 上产生 drwx--S--- 不可写目录 | build() 中 strip "umask 077 &&"；mktemp wrapper exit 1 强制 mkdir fallback |
| 4 | conftest 程序运行失败 | OHOS loader 无默认搜索路径 | LD_LIBRARY_PATH 注入依赖 libdir |
| 5 | 并行 make 失败 | HMDFS jobserver fifo EPERM | make -j1；install() args 显式传 -j1 阻止 Conan 自动追加 -j20 |
| 6 | E289: make all 失败 (help2man 缺失) | automake 把 $(MANS) 加入 all-am；ykclient.1 规则依赖新编译的 ykclient 二进制，触发 help2man（OHOS 无此工具） | make 传 MANS= man1_MANS= 跳过 man page 生成 |
| 7 | E289: make install 仍触发 help2man | 该 automake 模板 install-man1 直接依赖 $(dist_man_MANS)，传 MANS=/man_MANS=/man1_MANS= 不够 | install 额外传 dist_man_MANS= 清空 |

## 源码修改

无补丁。所有适配在 conanfile.py 中完成（umask 修复 + mktemp wrapper + buildenv 覆盖）。

## 依赖版本

- libcurl/8.5.0 (ohpcd remote)

## 验证结果

G1 (配方完整性): PASS
G0 (知识图谱): PASS (E424 commands.json 已补充)
CI (PR #11092):
- 第 1 轮: config.sub 拒绝 aarch64-unknown-linux-ohos → 改 gnu vendor
- 第 2 轮: configure/编译/链接全部通过，make all 在 help2man 生成 ykclient.1 处失败（E289）→ make 传 MANS= man1_MANS=
- 第 3 轮: make all 通过；make install 仍触发 help2man（install-man1 依赖 $(dist_man_MANS)，且 Conan 自动加 -j20 报 jobserver EPERM）→ install 传 -j1 + dist_man_MANS=
- 第 4 轮: 待 CI 验证

## 注意事项

- 上游 tests/selftest.c 为单二进制自测，需 -DTEST_WITHOUT_INTERNET=1 跳过网络测试（鸿蒙 CI 无 api.yubico.com 访问）
- test_package.c 鸿蒙特有验证：ykclient_global_init() 在 OHOS 上初始化交叉编译的 libcurl
