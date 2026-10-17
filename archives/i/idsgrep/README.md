# idsgrep

Tsukurimashou IDSgrep：面向汉字结构数据的通用树匹配检索工具。

## OHOS adaptation

- Autotools 构建（`configure` 由上游预生成，无需 `autoreconf`），原生构建为 OHOS aarch64 二进制。
- PCRE 正则查询是核心功能：`requires pcre/8.45#d37e7bcdd1483105496deb82632f1b44`（RREV 钉 ohpcd Autotools 配方，防 preflight 命中 conancenter CMake 配方），`--with-pcre` 指向 Conan 包前缀做确定性探测。
- 字典生成（`cjkvi2eids`）与 `cooked`/`speed` 测试需要 perl：`tool_requires perl/5.42.2`。
- 复用仓库既有修复：bash 式 `mktemp` 包装（HMDFS 权限问题）、`--build=aarch64-unknown-linux-gnu`（旧 `config.guess` 不识别 OHOS）、`umask 022` 修复。
- 上游 `make check` 注册 25 个 automake 测试；缺 KanjiVG/Tsukurimashou 数据与 valgrind 时对应 4 项按退出码 77 跳过。

## Dependencies

- `pcre/8.45#d37e7bcdd1483105496deb82632f1b44`（运行期正则功能，静态链接）
- 构建期：`perl/5.42.2`（tool_requires）

## References

- https://tsukurimashou.org/idsgrep.php.en
- https://tsukurimashou.org/files/idsgrep-0.6.tar.gz
