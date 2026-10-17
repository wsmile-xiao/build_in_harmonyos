# isoquery 3.4.0

- 任务：OHPCD MAIN #7535，分支 `feat/isoquery-3.4.0`
- 上游：https://codeberg.org/toddy/isoquery tag v3.4.0
- 归档：Debian `isoquery_3.4.0.orig.tar.gz` 与 codeberg `archive/v3.4.0.tar.gz` 同为 97204 字节
- SHA-256：`606f21ee3051c9fb9e180e6deaf3ac10f231e644adeed310d56ba98a905051be`
- 真机：HarmonyOS aarch64，独立 `CONAN_HOME=/storage/Users/currentUser/work/psj/ch-isoquery7535`
- `conan create` 退出码 0，包 id `63aab31a4c856332923dc1244457d59fa400548d`

## 上游测试

命令：`meson test -C build --print-errorlogs --no-rebuild -v`

- `isoquery:options`：16 subtests passed
- `isoquery:integration`：39 subtests passed
- meson 汇总：`Ok: 2`，`Fail: 0`（日志未另印 Skipped 行；55 个子测试均标 passed）
- 消费者：`OHOS_RESULT 12/12`

## 配置日志（文档工具）

```
Program asciidoctor found: NO
Program po4a found: NO
Program msgfmt found: YES (/storage/Users/currentUser/.harmonybrew/bin/msgfmt)
Build targets in project: 24
```

man/nls 为 feature `auto`。本机没有 asciidoctor 与 po4a，手册页被跳过。msgfmt 存在，所以编了 po。

## 运行期

- 制品仓里的 json-glib 1.10.8 共享库 `dlopen` 返回 `Permission denied`（文件带 `.codesign`，去掉该段后仍拒绝）。glib 2.88.3 共享库可以加载。OHOS 上改为静态链接 json-glib。
- 集成测试用 `execvpe` 把环境收成只有 `LC_ALL=en_GB.UTF-8`。设备上 `setlocale(LC_ALL, "en_GB.UTF-8")` 失败。补丁在失败时改用 `C.UTF-8`。
- `g_libintl_dgettext` 不读 iso-codes 的法语目录。补丁按 `ISOQUERY_LIBINTL` 绝对路径 `dlopen` GNU libintl。对照探针：`Tibetan -> Tibétain`。
