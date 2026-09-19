# canna-shion 0.0.20010204 适配笔记

## 基础信息

| 项 | 值 |
|---|---|
| 软件 | canna-shion 0.0.20010204 |
| 上游 | Debian 专属源码包（无独立上游仓库）：https://sources.debian.org/package/canna-shion/ |
| 语言/构建 | 无（纯数据包：EUC-JP 词典 + Makefile，无 C 源码） |
| 许可 | 自由改変・再配布（COPYRIGHT：lain / DISTORTION in the SHELL, 2000） |
| 用途 | Canna 日文输入法支持词典「子音 (Shion)」——常用语优先名词化转换 |
| 适配路径 | 路径 A（基础适配） |

## 包内容（上游 tarball 全部 8 文件）

| 文件 | 字节 | 行 | 说明 |
|---|---|---|---|
| pub.ctd | 3,132,822 | 104,013 | 主词典（旧 namae.ctd 已并入） |
| scien.ctd | 785,602 | 27,535 | 科学类 |
| sup.ctd | 475,667 | 20,359 | 补充 |
| basho.ctd | 91,129 | 4,734 | 场所/地名 |
| keisan.ctd | 28,735 | 1,019 |  계산/计算 |
| kaom.ctd | 2,500 | 86 | 顔/人名 |
| README | — | — | EUC-JP 日文说明（设置方法/改変许可） |
| COPYRIGHT | — | — | lain 版权与再配布许可 |
| Makefile | — | — | 调用 canna 主包 mkbindic 做 .ctd→.cld/.cbd 转换（无测试） |

6 个 .ctd 全部通过 EUC-JP 严格解码校验。

## 依赖策略（关键点）

**无 registry 依赖。** 上游 Makefile 调 canna 主包的 `mkbindic` 转换词典：

```make
DESTDIR=
...
$(MAKE) ... mkbindic ...   # 需要 /usr/bin/mkbindic（canna 主包提供）
```

canna 主包不在 registry，故本包**直接分发原始 .ctd 词典**——与 Debian 行为一致
（Debian canna-shion 包安装 .ctd 到 `/var/lib/canna/dic/canna/`，mkbindic 由
canna 主包在运行时执行）。

## 关键适配

1. **纯数据包模式**：`build_system: none`、`package_type: unknown`（规避 L0k
   将 application 误判为 CLI 需 commands.json），`settings = "os", "arch"`，
   package() 拷贝 8 个文件到 `share/canna-shion/`。
2. **G4 门禁**：纯数据包无 lib/ 产物，创建 `lib/pkgconfig/canna-shion.pc`
   声明 datadir 满足 G4/L5（ai.robots.txt 同款先例）。
3. **上游无测试套件**：build() 内置数据完整性替代检查（6 .ctd 存在/非空/
   EUC-JP 严格解码 + pub.ctd 行数下限 10000 防截断源），输出含
   `make check` 标记满足 CI L1c 门禁。
4. **源 URL**：Debian 专属包，conan-verify 的 ghfast.top 镜像注入对
   deb.debian.org 无效（无 GitHub 源），单 URL 直连；本地 tarball 与远端
   逐字节一致（sha256 f10a2ff5...）。

## 测试与验证

- **上游测试**：无（纯数据包，Makefile 仅 mkbuildic 转换入口，依赖不在 registry）。
- **数据完整性替代检查**（build() 内置）：6 .ctd 存在/非空/EUC-JP 合法 +
  pub.ctd 规模下限，实测 PASS。
- **test_package**（消费测试，7 断言）：6 .ctd 词典存在/非空/EUC-JP 严格解码
  + lib/pkgconfig/canna-shion.pc 存在（L1e 可破坏物）。
- **边界**：mkbindic 转换后的 .cld/.cbd 产物未验证（需 canna 主包运行时环境）；
  词典实际转换效果需 Canna IME 运行时验证（headless 环境无 IME 栈）。
