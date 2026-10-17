# meson 把 asciidoctor 和 po4a 标成 required 时用 feature auto 跳过

## 问题

isoquery 3.4.0 的 `meson.build` 写着 `find_program('asciidoctor', required: true)` 和 `find_program('po4a', required: true)`。HarmonyOS 真机没有这两个程序。打上 feature 选项补丁后，同一次 `conan create` 的配置日志原样是：

```
Program asciidoctor found: NO
Program po4a found: NO
Program msgfmt found: YES (/storage/Users/currentUser/.harmonybrew/bin/msgfmt)
Build targets in project: 24
```

随后 `isoquery:options` 16 subtests passed，`isoquery:integration` 39 subtests passed，meson 汇总 `Ok: 2`、`Fail: 0`。本轮没有再跑未打补丁的配置，所以没有「Program asciidoctor not found」那一行失败日志。

## 根因

手册页依赖 asciidoctor 与 po4a，翻译目录依赖 msgfmt。上游把前两个写成 `required: true`，工具不在 `PATH` 时 meson 会在配置阶段停止。编译和 `tests/` 并不需要手册页。msgfmt 在这台设备的 harmonybrew 里存在，所以 nls 的 auto 实际编了 `po/`。

证据是上面的 found NO 与 `Build targets in project: 24`。若 required 仍为 true，配置不会进入「Build targets」。

## 最小解决与边界

新增 `meson_options.txt`，`man` 与 `nls` 都是 `feature`，默认 `auto`。`find_program` 的 `required` 改为 `get_option('man')` 或 `get_option('nls')`。只有 `.found()` 才 `subdir('man')` 或 `subdir('po')`。配方传入 `-Dman=auto -Dnls=auto`。

边界：选项设为 `enabled` 时，工具缺失必须仍然失败。不要用 `__OHOS__` 包住这段逻辑。若上游已经有 `meson.options`，再添加一份不同的 `meson_options.txt` 会撞上 E258（双文件且不是同一 inode）。isoquery 3.4.0 原来没有这两个文件，本轮只新增 `meson_options.txt`，配置已通过。

反例：项目的测试或安装包必须带 man 页时，不能把 `man` 设成 auto 后当作成功。

## 验证

`CONAN_HOME=/storage/Users/currentUser/work/psj/ch-isoquery7535`，`conan create` 退出码 0。上游 55/55，消费者 `OHOS_RESULT 12/12`。

## 七轴查重

对 `origin/main` 的 `knowledge/doc`、`knowledge/graph`、`knowledge/drafts` 检索。

| 轴 | 结果 | 证据 |
| --- | --- | --- |
| exact_duplicate | 否 | `po4a` 在 doc 与 graph 零命中 |
| causal_duplicate | 否 | E258 的报错是 meson.options 与 meson_options.txt 不是同一文件 |
| trigger_overlap | 弱 | `asciidoctor` 只命中无关的 DRAFT-12609 Java Maven 草稿 |
| solution_overlap | 否 | doc/graph 没有 `find_program` 的命中 |
| combination_novelty | 是 | asciidoctor、po4a、msgfmt 三条 required 一起改成 feature auto |
| boundary_novelty | 是 | auto 跳过，enabled 仍失败；与 E258 的双文件问题方向相反 |
| test_migration_novelty | 否 | 不改上游测试，只跳过手册子目录 |

决定：写成这一对草稿。json-glib 共享库的 `Permission denied` 与 libintl 运行时加载另有 E077 和多条 libintl 条目，本轮不另写草稿。

## 适用边界

适用于「文档或翻译工具被 meson 标成 required，但编译和测试可以没有它们」的项目。不适用于必须产出 man 页的发布物，也不适用于已经同时存在 `meson.options` 与 `meson_options.txt` 的源码树。
