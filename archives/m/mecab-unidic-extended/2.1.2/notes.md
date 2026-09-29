# mecab-unidic-extended 2.1.2 适配笔记

## 任务身份

- 平台库名: mecab-unidic-extended
- 平台版本: 2.1.2
- 分支: feat/mecab-unidic-extended-2.1.2
- 路径: 词典数据 + 预编译二进制索引包（构建期 mecab-dict-index 编译）

## 上游身份

- 项目: UniDic（kana-accent 仮名アクセント付き变体，MeCab 用日语音韵重音词典）
- 上游主页: https://clrd.ninjal.ac.jp/unidic/
- 上游版本: unidic-mecab_kana-accent-2.1.2_src.zip
- 许可证: GPL-2.0-or-later, LGPL-2.1-or-later, BSD-3-Clause（源内 COPYING/GPL/LGPL/BSD/AUTHORS/ChangeLog）
- 源码: canonical 主机 clrd.ninjal.ac.jp 在中国大陆常不可达
  - 主 URL: https://mirrors.dotsrc.org/osdn/unidic/58338/unidic-mecab_kana-accent-2.1.2_src.zip（OSDN 镜像，字节一致）
  - 备用 URL: https://clrd.ninjal.ac.jp/unidic_archive/cwj/2.1.2/unidic-mecab_kana-accent-2.1.2_src.zip
  - SHA256: 70793cacda81b403eda71736cc180f3144303623755a612b13e1dffeb6554591
  - 下载缓存已 seed: ~/.conan2/d/s/70793cac…（conan 按 sha256 命中，免网络下载）

## 归档身份

- Conan name/version: mecab-unidic-extended/2.1.2
- 归档路径: archives/m/mecab-unidic-extended/2.1.2/
- 软件类型: 词典数据 + 预编译二进制索引包（settings 参与 package_id，无本包 C/C++ 编译）
- 区别于 mecab-ipadic / mecab-ko-dic（纯源数据包）: 构建期用 tool_requires mecab/0.996
  的 mecab-dict-index 把 lex.csv + matrix.def 编译为 MeCab 二进制索引

## 数据统计

- lex.csv: 756,463 条目（179,234,466 B，UTF-8）
- matrix.def: 5981x5981 连接代价矩阵（514,489,873 B）
- DEF 文件: char.def, unk.def, rewrite.def, feature.def, left-id.def, right-id.def
- dicrc: 26 特征列 f[0]-f[25]，cost-factor=700，output-format-type=unidic
- 上游 zip 不含 pos-id.def 与 model.def（mecab-dict-index 回退最小 pos-id 表，可用）
- 生成的二进制索引（真机验证值）:
  - sys.dic 187,716,561 B (~179MB)
  - matrix.bin 71,544,726 B (~68MB)
  - char.bin 262,496 B
  - unk.dic 5,492 B

## 包布局

- res/unidic/      可加载词典（char.bin, matrix.bin, sys.dic, unk.dic, dicrc）
- res/unidic-src/  原始 UTF-8 源数据（*.csv, *.def, dicrc，用于复现/重索引）
- licenses/        COPYING, GPL, LGPL, BSD, AUTHORS, ChangeLog
- 消费接口: runenv UNIDIC_EXT_DICDIR=<pkg>/res/unidic
  （package_info 清空 includedirs/libdirs/bindirs，纯数据包）

## 外部工具依赖

- mecab/0.996（tool_requires）: 构建期 mecab-dict-index 索引编译；test_package 期 libmecab 消费
- HarmonyOS PC 同机构建（pr:b = pr:h = ohos-aarch64）: mecab-dict-index 原生运行，
  产物即 OHOS aarch64 可加载索引（同字节序/词典格式）

## 验证结果

- 源完整性: dotsrc 镜像下载 + SHA256 校验通过（COMPLETE 70793cac…）
- 本地预验证（上一次会话，真机产物）:
  - test_consumer（mecab C API 加载词典、统计 feature 逗号数）: PRE-VALIDATION PASSED
  - -r 空 rcfile 探针: R-FLAG-CONSUMER-PASSED
  - golden 字节级捕获（すもももももももものうち，8 行，与 test_package kGolden 三方一致）
- conan create (ohos-aarch64): PASSED（2026-09-23，pr:b = pr:h = ohos-aarch64 同机构建；
  package_id 6b129b068851896169fae42d399fa922d239ce8a 已入缓存；
  res/unidic 248M + res/unidic-src 663M + licenses 96K；
  日志: unidic-ext-work/conan-create.log 与 conan-create2.log）
- test_package consumption verification: PASSED（真机执行，二进制 conan 可执行文件链接
  libmecab + UNIDIC_EXT_DICDIR runenv 加载词典）:
  - golden 8/8 行字节级一致（すもももももももものうち）
  - 第二句切分为 形態/素/解析/は/面白い 共 5 词素 + EOS——UniDic 2.1.2 lex.csv 无
    单一「形態素」词条（形態、素 为独立条目），初次断言按连续「形態素」字符串写错，
    已按真实词典切分修正
  - 输出末行 MECAB-UNIDIC-EXTENDED CONSUMER TEST PASSED
- smoke: golden 与 SMOKE-TEST-DESIGN.md 已归档（smoke/golden/）
- 2026-09-28 重跑（新增 HarmonyOS 专项测试）: conan create (ohos-aarch64, pr:b=pr:h) PASSED，
  test_package 两组测试均真机执行通过:
  - [1/2] 普通消费者测试 PASSED（golden 8/8 行 + 第二句 5 词素 + UNIDIC_EXT_DICDIR 契约）
  - [2/2] HarmonyOS 专项测试 PASSED（15 断言: __OHOS__/__OHOS_FAMILY__/__aarch64__ 宏、
    uname=HarmonyOS、自身 ELF64/EM_AARCH64(183)/小端/PT_INTERP=/lib/ld-musl-aarch64.so.1、
    OHOS libmecab 加载包内索引、charset=utf8/size=756463/lsize=rsize=5981、すもも分词+EOS；
    __MUSL__ 不断言——OHOS Clang 不定义该宏，T1c 仅 info 诊断，musl 判据为 T4 PT_INTERP）
- 上游正式测试核实（2026-09-28）: N=0 — zip 全 27 文件枚举无 test/tests/spec/CI/脚本；
  configure.ac 仅 MECAB_CONFIG 检测与 --with-dicdir 选项（无测试发现）；Makefile.am 仅
  dic_DATA 安装 + mecab-dict-index 编译规则（无 TESTS/check_PROGRAMS）；Makefile.in check-am
  为空 automake 样板——无上游测试可执行

## 已知限制 / 注意事项

- HarmonyOS 无系统 mecabrc（/usr/local/etc/mecabrc 不存在）: 消费者必须
  mecab_new2("-d <dicdir> -r <rcfile>") 显式指定；词典目录 dicrc 携带输出格式配置
- mecab-dict-index 不复制 dicrc 到输出目录，recipe 手动补齐
- unidic 输出 8 列（表層,pron,lForm,lemma,pos,cType,cForm,aType）；助词行尾三字段为空（行尾制表符）
- 软件包体积 ~954MB（res/ 未压缩），sys.dic 187MB 为最大单文件
- 上游 zip 内含 configure/Makefile（autotools 安装路径），本 recipe 不走 autotools，
  直接调 mecab-dict-index，避免上游 configure 的 host 检测问题
- OHOS Clang（aarch64-unknown-linux-ohos）不定义 __MUSL__（不同于 musl-gcc）：
  musl 判据须用 T4 ELF PT_INTERP==/lib/ld-musl-aarch64.so.1；__MUSL__ 仅作 T1c info 诊断，
  不得作硬失败条件，也不得用 -D__MUSL__ 伪造
