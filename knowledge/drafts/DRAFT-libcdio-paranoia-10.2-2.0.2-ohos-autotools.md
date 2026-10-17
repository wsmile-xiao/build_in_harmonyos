# DRAFT-libcdio-paranoia-10.2-2.0.2-ohos-autotools

## 问题

`libcdio-paranoia` 10.2-2.0.2 在 HarmonyOS PC aarch64 上使用 Conan 2 + Autotools 构建时，源码归档中的旧版 GNU helper 和测试夹具会阻塞配置或回归测试；其 `libcdio/2.3.0` 静态依赖还带有指向构建机 `/lib` 的历史 `.la` 元数据。

## 根因

1. `config.guess`/`config.sub` 不认识 `HarmonyOS` 和 `linux-ohos`，不能稳定产出 `aarch64-unknown-linux-ohos`。
2. HMDFS 上 configure 的 `umask 077` 临时目录不能继续创建配置文件；仅设置外部 `TMPDIR` 不会修正 configure 自己创建的目录权限。
3. 发布 tarball 的 `cdda*.cue` 引用不存在的 `BOING.BIN`，而同一归档实际提供 `cdda*.bin`；这是测试数据引用错误，不是光盘设备限制。
4. endian 测试复制 CUE 文件后仍指向原始 BIN；生成的 CUE 必须指向 `cdda-be.bin`/`cdda-le.bin`。
5. libcdio 2.3.0 的 BIN/CUE 驱动从 image entry 1 开始重新编号。单纯把 CUE 写成 `TRACK 07` 不会得到 7/8/9 音频轨道；需要先放六个 one-sector data entry，再放三个音频 entry。
6. 依赖 `.la` 中的历史绝对路径会把 libtool 链接导向 `//lib`。不应修改 Conan 缓存；应在当前 Conan build folder 建立只含静态归档和头文件的私有依赖前缀，并生成对应的 `libcdio.pc`。

## 推荐方案

- 对旧版 `config.guess`、`config.sub` 和 configure 临时目录做最小补丁。
- 修复测试夹具引用，不删除断言，也不放宽测试条件。
- 保留非 1 音频轨道测试的 7/8/9 断言，用六个 data track entry 模拟依赖驱动的实际编号。
- 在 Conan `generate()` 中把依赖静态归档、头文件和 pkg-config 描述复制到 `self.build_folder` 下的私有前缀；在 OHOS build 环境中仅引用该前缀。
- package() 删除包含构建机绝对路径的 `.la`，对消费者只导出静态库、头文件、pkg-config 文件和 `cd-paranoia`。

## 验证

在 HarmonyOS PC `aarch64-unknown-linux-ohos` 上实测：

- 上游 `make check`：9 项，6 PASS、3 SKIP、0 FAIL；3 个 SKIP 均为物理音频 CD 依赖，离线 BIN/CUE 测试全部通过。
- `conan-verify`：G1/G2/G3 通过，`conan create` 的 upstream checks 和 test_package 均执行。
- `ci/conan/build_and_test.sh`：L0/L1/L2/L5 通过，1/1 package 成功；`cd-paranoia --version` 通过。
- CMake 消费者实际链接并调用 `cdio_cddap_version()` 与 `cdio_paranoia_version()`，输出 `10.2+2.0.2 aarch64-unknown-linux-ohos`。

## 适用范围与边界

适用于带旧版 Autotools helper、BIN/CUE 离线测试，并依赖 libcdio 2.3.0 静态包的 OHOS 适配。物理光盘测试仍需真实光驱和音频 CD，不能用离线镜像测试替代该硬件场景；不得通过修改断言将物理设备缺失伪装为通过。

与 E007/E129 的 config.guess/HMDFS 经验、E544 的 `.la` 私有依赖路由经验互补；本条增加 libcdio BIN/CUE track renumbering 和发布测试夹具缺失文件的具体证据。

## 交付边界

本条为本地知识草稿，未创建知识 Issue、未宣称已合入正式知识编号；关联交付为 `archives/l/libcdio-paranoia/10.2-2.0.2`。
