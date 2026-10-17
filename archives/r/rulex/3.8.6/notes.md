# rulex 3.8.6 HarmonyOS PC 适配笔记

## 源码与构建

- 官方源码：`poretsky/rulex` 标签 `r3.8.6`（提交 `67fad229c4a394b1082a358c35fcfa5179c81ff9`）。
- 源码 SHA-256：`7d29bfb632bdb3e779fbca81889abf544efb482d66ff918d4a6fa7778ea8a226`。
- 构建系统：Autotools；GitHub 标签包不含生成的 `configure`，构建时使用
  Autoconf、Automake、Libtool 和 Autoconf Archive 自举。
- 依赖：已发布的 `berkeley-db5/5.3.28`，通过 `--with-libdb` 显式注入。

## 适配问题与解决方案

上游两个命令行程序在启动时强制设置 `ru_RU.KOI8-R`，系统没有该 locale
时立即退出。HarmonyOS PC 的 libc 会接受这一 locale 名称，但 POSIX 正则
引擎随后会把词典中的单字节 KOI8-R 规则当作无效多字节输入。RuLex 的数据库
格式固定为 KOI8-R，其俄文字母大小写映射是确定的。

两个补丁均采用平台中立修复：将字符分类固定为字节语义的 `C` locale，并对
KOI8-R 大写块及特殊字母 Ё 实施显式小写映射；ASCII 仍使用标准 `tolower()`。
这样正则规则和查询键始终使用同一单字节编码。修复不依赖平台宏，不修改
数据库格式、不删除功能，也不更改上游测试数据。

HarmonyOS Worker 构建显式使用 `aarch64-unknown-linux-gnu` build triplet 和
`aarch64-unknown-linux-ohos` host triplet，既避免 `config.guess` 在受限临时
目录执行探测程序，也强制 Autoconf 采用交叉编译模式而不运行目标产物；Conan
交叉 profile 继续使用其自动生成的 triplet。

`autoreconf` 生成的 `configure` 默认以 `umask 077` 创建 `config.status` 临时
目录；HarmonyOS HMFS 会继承 setgid 组并映射目录属主，导致构建进程无法创建
`subs1.awk`。配方在 `autoreconf` 后将该临时目录掩码调整为 `022`，避免临时
目录被限制为仅映射后的属主可遍历，不改变安装文件权限或上游功能。

共享版 `librulexdb` 运行时依赖 Berkeley DB；配方通过 Conan `runenv_info`
公布其库目录，确保安装后消费者使用 `conanrun` 时能加载 `libdb-5.3.so`。

Libtool 生成的 `lexholder` 启动脚本依赖 `pwd` 定位 `.libs/lexholder`；HMFS 在
Conan 缓存子目录中可能拒绝 `getcwd()`，使启动脚本误报真实 ELF 不存在。配方
仍执行上游正式 `make test` 目标，仅将该目标中的测试命令改为直接调用已链接的
`.libs/lexholder`，并显式提供 `librulexdb` 与 Berkeley DB 的运行库目录。

## 上游测试审计

上游正式入口为 `make test`，它先由六份数据源构建 Berkeley DB 词典，再用
`data/lexicon.test` 的 430,015 条记录逐条查询并比较发音结果。配方验证：

- 精确检查测试输入为 430,015 行；
- 完整执行 `make test`；
- 要求输出完成且 `data/lexicon.dump` 存在并为 0 字节，任何不匹配均失败；
- 实测结果：430,015/430,015 通过，`No mismatches found`。

## 适配后消费者测试

- C 消费者链接打包后的 `librulexdb`，执行 18 个数据库创建、写入、读取、
  查询、遍历、重复写入、删除和错误路径断言。
- HarmonyOS 专项测试在 `LANG=C`、`LC_ALL=C` 下执行打包后的
  `lexholder-ru`，验证字节 locale 下帮助入口和 KOI8-R 大写查询仍可用
  （4 个断言）。
- 从最终 Conan 包重新执行 430,015 条词典测试，确认安装后的工具、共享库、
  Berkeley DB 依赖、词典数据库和测试夹具共同工作。

适配后有效断言总数为 430,037（上游 430,015 + 消费者 22），全部通过。

## 验证命令

```bash
conan create archives/r/rulex/3.8.6 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
CI_PACKAGES="archives/r/rulex/3.8.6" \
  CONAN_PROFILE=ohos-aarch64 zsh ci/conan/build_and_test.sh
python3 scripts/ohc-run.py graph validate
```

---

**编译结束**: 2026-09-27
**最终状态**: built
