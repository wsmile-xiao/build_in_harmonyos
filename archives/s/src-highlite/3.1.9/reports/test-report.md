# src-highlite 3.1.9 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15.0.4 (OHOS SDK 26.0.0.18)
- Conan 2.29.1 (CONAN_HOME=~/tmp/ch/home-ds12-srchighlite)

## Verification

- `conan-verify src-highlite 3.1.9`: exit 0（G0/G1/G2/G3 + L2/L4/L5 全 PASS）
- 探索构建（真机 -j1）：CONFIGURE_RC=0 / MAKE_RC=0 / INSTALL_RC=0 / CHECK_RC=0
- W3 本地 CI 模拟（finish step [5/10]）：通过
- 源码: sha256=3a7fd28378cb5416f8de2c9e77196ec915145d44e30ff4e0ee8beb3fe6211c91
  （https://ftp.gnu.org/gnu/src-highlite/source-highlight-3.1.9.tar.gz）

## 上游测试（make -C tests check，配方 build() 内真实执行）

| 维度 | 数量 | 说明 |
|---|---|---|
| N_static | 170 | 默认 check 目标（check-produced-output，98 子目标）展开为 168 组 diff 对比 + output_dir 2 组（tests/Makefile.am 注册入口计数） |
| N_registered | 170 | 与 N_static 同口径 |
| N_executed | 170 | CHECK_RC=0，全过 |
| 未执行 | 3 类 | 错误类 5 目标 = MAINTAINER_MODE 条件注册（上游默认亦不执行）；src/ 的 ~25 个 .lang 合法性自检（无断言）；doc/ 的 11 个示例文档生成（无断言） |
| N_consumer | 1 | consumer_test（断言 4 项），编译+链接静态库+签名+运行，"highlighted 478 bytes OK" |

## test_package

消费者程序 `consumer_test` 以库使用者身份链接 `libsource-highlight.a`（+
`libboost_regex.a`），调用 `srchilite::SourceHighlight::highlight()` 将 C++
源码高亮为 HTML，断言产物含 main/comment 正文与 `<font`/`<pre>` 高亮标记，
退出码 0 判定通过。

- Test cases: 1
- Passed: 1
- Failed: 0
- Skipped: 0

## Result

PASS — 可进入提交流程（当前 HEAD 绑定的 conan create 与测试证据）。
