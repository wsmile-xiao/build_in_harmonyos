# open-jtalk

Open JTalk — HMM 统计参数合成的日语文本到语音（TTS）系统，由名古屋工业大学
HTS Working Group 开发，语音合成后端为 hts_engine_API。

- 上游项目：SourceForge `open-jtalk`（<https://open-jtalk.sourceforge.net/>）
- 许可证：BSD-3-Clause（modified BSD，见包内 `licenses/COPYING`）
- 版本目录：`archives/o/open-jtalk/1.11/`（conanfile.py + conandata.yml + patches/ +
  test_package/ + manifest.yaml + notes.md）
- 任务分支：`feat/open-jtalk-1.11`

## 说明

- 包类型为 `application`：产物是命令行程序 `bin/open_jtalk`，并随包装出
  MeCab NAIST-JDic 词典数据目录 `dic/`（`sys.dic` 约 98 MB）。
- **构建只支持 in-tree**：`bin/Makefile.am` 的链接行用 `@top_srcdir@` 绝对路径引用
  各子目录静态库，automake 的 out-of-tree（VPATH）构建会找不到这些 `.a`。
  配方通过 `basic_layout(src_folder=".", build_folder=".")` 固定
  `build_folder == source_folder`。
- **hts_engine_API 1.10 为私有内建依赖**：open_jtalk 的 configure 强制要求它的
  头文件与静态库，但它没有发布到 ohpcd Conan 制品仓，也不在 cmd-pkgs 预编译索引中，
  因此由 `conandata.yml` 的 `private_sources` 在配方内下载并构建，静态链接进
  `open_jtalk` 可执行文件（不产生独立的 hts_engine 包）。
- 上游 tarball 自带的 2013 版 `config.guess`/`config.sub` 是旧式脚本（无 `GUESS=` 变量，
  `patch-autotools-ohos.pl` 的锚点不适用）；包内补丁按最小锚点方式补上
  `aarch64:HarmonyOS` 运行时分支与 `linux-ohos*` 双锚点（不使用 `__OHOS__` 平台宏），
  同一补丁也作用于私有内建的 hts_engine_API。`configure` 自身因 HMDFS 上
  `umask 077` 临时目录不可写而失败，另有补丁把该处的 `umask 077` 改为 `022`。
- 内置的 MeCab 0.996 是 C++98 代码，使用 C++17 已删除的 `register` 关键字，
  配方注入 `-Wno-register`。

## 使用

```bash
# 合成日语语音需要外部 .htsvoice 声学模型（源码包/本包都不含）
open_jtalk -x <prefix>/dic -m /path/to/voice.htsvoice -ow out.wav <<< "こんにちは"
```

## 已知限制

- **不随包分发 `.htsvoice` 声学模型**：这是上游设计（模型单独发布），没有模型时
  `open_jtalk` 会在加载词典之后报
  `Error: Dictionary or HTS voice cannot be loaded.` 并退出 1。
  因此 `test_package/test.sh` 的端到端范围止于「词典加载成功 + 到达声学模型加载阶段」，
  未覆盖真实合成（见 `test_package/MANIFEST.yml`）。
- 上游没有任何自动化测试目标（各 `Makefile.am` 未定义 `check_PROGRAMS`/`TESTS`，
  `make check` 全为 no-op）。
- 运行期动态依赖为 OHOS 系统的 `libc++_shared.so` / `libc.so`；hts_engine 为静态链接。
- 与仓库内历史纯归档目录 `archives/o/open_jtalk/1.11`（ARCHIVE-SPEC v2.0 时代产物，
  无 conanfile.py）并存：两者互不影响，本包是任务卡分支对应的 Conan 化制品
  （CI 的 L0n 门禁要求「分支名去前缀 == 包目录名-版本」，故目录名为 `open-jtalk`）。
