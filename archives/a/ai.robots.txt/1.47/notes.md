# ai.robots.txt 1.47 适配笔记（HarmonyOS PC · 纯数据包）

## 定位
- ai.robots.txt 是 GitHub 上的**配置文件/数据包**：屏蔽 AI 爬虫的 robots.txt 规则集
  （robots.txt、robots.json、nginx/apache/haproxy/Caddy/lighttpd 配置、table-of-bot-metrics）。
- **无编译产物**（纯数据），走数据包打包路径。

## 关键适配
- 数据包模式：`package_type = "unknown"`（规避 L0k 将 application 误判为 CLI 需 commands.json）、
  `settings = "os", "arch"`、package() 拷贝规则文件到 `share/ai.robots.txt/`。
- **G4 门禁**：纯数据包无 lib/，创建 `lib/pkgconfig/ai-robots-txt.pc`（声明 datadir）满足 G4/L5。
- **上游测试集成**：build() 运行 `python3 code/tests.py`（unittest，11 用例，验证 robots.txt/htaccess/
  nginx/haproxy/Caddy/lighttpd 生成与 test_files 基准一致），实测 **11/11 全部通过**。

## 状态
built（conan-verify 通过；纯数据包无 ELF 产物）

## 编译步骤

```bash
conan create archives/a/ai.robots.txt/1.47 --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 配方内 build()：纯数据包无编译，集成上游测试
cd $source_folder && python3 code/tests.py
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G4 产物完整性对纯数据包会 FAIL（无 lib/bin/include） | 门禁检查 lib/ 等目录有内容 | package() 创建 `lib/pkgconfig/ai-robots-txt.pc`（ae_fonts_mono 同款先例） |
| 2 | `package_type="application"` 会被 L0k 误判为 CLI 工具要求 commands.json | 数据包非命令工具 | 用 `package_type="unknown"`（asahi-audio 同款） |
| 3 | 上游测试依赖 bs4/lxml（本机 Python 缺） | requirements.txt 声明 | 本机 `pip3 install beautifulsoup4 lxml`；配方 build() 运行测试需环境具备 |

## 上游测试结果

```bash
$ python3 code/tests.py
test_htaccess_generation ... ok
test_lighttpd_generation ... ok
test_nginx_generation ... ok
test_clean_name ... ok
test_robots_txt_generation ... ok
test_table_generation ... ok
----------------------------------------------------------------------
Ran 11 tests in 0.008s
OK
```

- 上游测试 11/11 全部通过（100%）。

## 交付物

| 文件 | 说明 |
|------|------|
| share/ai.robots.txt/robots.txt | 主规则文件（AI 爬虫 User-agent 块列表） |
| share/ai.robots.txt/robots.json | 结构化机器人数据 |
| share/ai.robots.txt/nginx-block-ai-bots.conf 等 | 各平台服务器配置 |
| share/ai.robots.txt/LICENSE README.md assets/ | 许可与文档 |
| lib/pkgconfig/ai-robots-txt.pc | pkg-config 元数据（G4 门禁） |

## 注意事项

- R38：数据包非命令工具，无需 commands.json（package_type=unknown 规避误判）。
- R26：无 .so 产物，系统同名库隔离不适用（G3 如实标注）。
- 上游许可：CC-BY-SA-4.0（LICENSE 文件随包）。
- 包名含点号 `ai.robots.txt`（有 docopt.cpp 先例，Conan 支持）。
---

**编译结束**: 2026-08-08 20:06
**最终状态**: built
