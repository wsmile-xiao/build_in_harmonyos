# slurm 0.4.4 适配笔记

## 软件识别
- 上游：github.com/mattthias/slurm（ncurses 终端网络流量监控器，非 HPC 调度器 Slurm）
- 上游 tag：`upstream/0.4.4`（2022-04-29，GPG 签名验证）
- 源码 sha256：`2f846c9aa16f86cc0d3832c5cd1122b9d322a189f9e6acf8e9646dee12f9ac02`

## 编译环境
- 构建系统: meson（上游 0.4.4 已从 autotools 迁移到 meson，根目录 meson.build）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，ld.lld 15.0.4）
- Conan: 2.29.1（OHOS 适配版），profile ci/conan/profiles/ohos-aarch64
- 状态: published

## 编译步骤
1. W0 依赖检查：`conan download ncurses/6.{4,5,6} -r=ohpcd --only-recipe` 全部 rc=0；
   `conan download 'ncurses/6.6:*' -r=ohpcd -p 'os=OHOS AND arch=armv8'` 二进制下载 rc=0（R35/R36 闭环）。
2. meson 不在真机/CI PATH、ohpcd 无 meson 工具包 → 沿用 astroterm/1.0.9 与
   libdvdnav/7.0.0 已验证的 **vendored meson 1.11.2** 方案（source() 解压到
   meson-vendor/，`python3 -c` 进程内 sys.path 注入调 mesonmain.main()）。
3. generate()：MesonToolchain + ar/ranlib 注入 native file；将 host 依赖
   ncurses/6.6 的 include/lib 路径持久化到 generators/ncurses_paths.json。
4. build()：将上游 `curses_dep = dependency('curses', version: '>=5')` 替换为
   `declare_dependency(include_directories=…, link_args=[…/libncursesw.a])`；
   `meson setup --prefix=/ --native-file=conan_meson_native.ini` → `ninja -j1`。
5. package()：`meson install --no-rebuild --destdir <package_folder>`。

## 首个错误 → 根因 → 修复 → 复验
- 首个错误（create1，日志 /data/storage/el2/base/cache/slurm-0.4.4-create.log）：
  `ld.lld: error: undefined symbol: ethtool_cmd_speed`（src/if_media.c:332，
  编译期 -Wimplicit-function-declaration 告警）
- 根因：`ethtool_cmd_speed()` 是 glibc 私有 `linux/ethtool.h` 的 static inline
  辅助函数；OHOS sysroot（ohos-sdk_26.0.0.18）的 `linux/ethtool.h` 不含它
  （grep rc=1）。字段 `speed`/`speed_hi` 与 `SPEED_*` 常量 OHOS 均有。
- 修复：patches/0001-src-if_media.c.patch——以
  `((__u32) edata.speed_hi << 16) | edata.speed` 直接计算（与 glibc inline
  等价，平台中立，无 `__OHOS__` 宏，R8 合规）。
- 复验（create2，日志 /data/storage/el2/base/cache/slurm-0.4.4-create2.log）：
  conan create RC=0，产物 bin/slurm（aarch64 musl ELF）+ 4 个 .theme + slurm.1。

## HMDFS 硬链接陷阱（工具链级发现）
init-build 解包时 .orig 与 .work 同 inode（硬链接，link count 2），直改
.work 源码会同步"修改" .orig，refresh-patch 的 difflib 恒判无差异、静默
产出 0 补丁。解法：从源码 tarball 重新提取原始文件，以 `os.replace` 换新
inode 打断硬链接后再跑 `refresh-patch --auto`（生成 0001 补丁 +1/-1）。
后续适配类似问题可直接检查 `ls -li orig work` 的 inode 是否相同。

## 上游测试（R51 申报）
- **上游 0.4.4 无自动化测试**。清点证据：
  - `grep -rn "test" meson.build` → 零命中（exit 1），无 test() 条目；
  - `find . -iname "*test*" -o -iname "*.suite*"` → 计数 0，无 tests/ 目录；
  - build() 输出 `HMBS_UPSTREAM_TEST_RESULT={"status":"no_upstream_tests",...}`。
- test_package 不替代上游测试统计；本包新增 **鸿蒙消费者可行性用例**：
  test.c 真实执行打包产物 `slurm -h`（上游 slurm.c `case 'h': usage(0)` 语义，
  无需 TTY），2 项检查：退出码 0 + usage 横幅文本。create2 实测 2/2 通过，
  `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"discovered":2,"passedCount":2}`。

## 依赖版本
- ncurses/6.6（ohpcd 静态 widec 构建，conan 包，libncursesw.a 直连）

## 验证结果
```bash
# conan create（复验）
conan create archives/s/slurm/0.4.4 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64   # RC=0
# conan-verify（G0-G4 + L2/L4/L5 全过）
python3 scripts/ohc-run.py conan-verify slurm 0.4.4   # RC=0, 可标记 published
```

## 注意事项
- 上游 `dependency('curses')` 在 meson 下会走 pkg-config 查找；本配方改为
  declare_dependency 直连，避免 pkg-config 路径注入的不确定性。
- 软件级 commands.json 已提供（R38，可执行文件类型）。
---

**编译结束**: 2026-09-21 14:48
**最终状态**: published
