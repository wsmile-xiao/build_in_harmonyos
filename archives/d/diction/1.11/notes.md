# diction 1.11 适配笔记

## 编译环境

- 平台: HarmonyOS PC（aarch64，设备原生 clang 工具链）
- Conan: 2.29.1（鸿蒙社区适配版），profile: `ci/conan/profiles/ohos-aarch64`
- 目标三元组: `aarch64-unknown-linux-ohos`
- 源码: `https://ftp.gnu.org/gnu/diction/diction-1.11.tar.gz`（GNU 官方 FTP）
- 构建系统: autotools（上游 Makefile 仅支持 in-source 构建）

## 编译步骤

1. `./configure --prefix=<prefix>`（短语库目录 `SHAREDIR` 在 configure 阶段确定）
2. `make -j1`
3. 上游测试逐个执行：`sh ./test/test01` … `sh ./test/test09`
4. `make install`（prefix 已指向安装目录，故不再叠加 Conan 的 `DESTDIR`）

## 遇到的问题与解决方案

1. **`config.guess` / `config.sub` 不识别 HarmonyOS**（知识库 E007）
   - 现象: `configure` 报 `invalid host type`，无法确定目标三元组。
   - 处理: 按 2006 年版语法定点补 `ohos` 分支（`echo ... ; exit ;;` 风格；新版 `GUESS=` 写法在该年代脚本中无效），最终得到 `aarch64-unknown-linux-ohos`。
2. **NLS/libintl 在干净 CI 中误启用**
   - 现象: `configure` 探测到可用 `libintl` 后生成 `-lintl` 链接参数，但 OHOS 环境缺少 `g_libintl_*` 实现，CI 链接报 `undefined symbol: g_libintl_bindtextdomain` / `g_libintl_gettext`。
   - 处理: 配方显式传 `--disable-nls`；diction 的核心短语检测功能不依赖 gettext，本地 W3 和消费者测试均覆盖。
3. **HMDFS 下 configure 无法写入 `config.status`**（知识库 E011）
   - 现象: `mktemp -d` 创建的临时目录权限受 `umask 077` 影响，configure 重执行时临时目录不可写。
   - 处理: 补丁把临时目录创建改为显式 `umask 022`。已对照验证：不加该补丁时原始 configure 在本平台 HMDFS 上必然失败，补丁为必需项。
4. **HMDFS 不支持硬链接**（知识库 E079）
   - 现象: `make install` 的 `(cd $(DESTDIR)@datarootdir@/diction; ln en C)` 直接失败。
   - 处理: 改源码 `Makefile.in`（而非生成的 `Makefile`），将硬链接改为 `rm -f C; cp en C`，保证重新 configure 后仍生效。
5. **运行期短语库目录不可迁移**（本次新发现）
   - 现象: diction 在 configure 阶段把短语库目录烧进二进制（`-DSHAREDIR=\"${prefix}/share\"`），安装到其它前缀后默认查找失败：
     `diction: Opening '<configure 前缀>/share/diction/en' failed (No such file or directory)`（exit 1）。
   - 处理: 改为**相对可执行文件查找**——由 `/proc/self/exe` 推导 `<bindir>/../share/diction/`，未命中再回退编译期 `SHAREDIR`；搬迁后默认查找可用（实测）。
   - 附带修复: `readlink` 不会补 NUL 终止符，静态缓冲区残留上次调用的字节会导致路径错误，已显式补 `'\0'`。
5. **Conan 2 配方加载失败**
   - 现象: `conan create` 报 `ImportError: cannot import name 'ConanException' from 'conan'`。
   - 处理: Conan 2 中异常类位于 `conan.errors`，改为 `from conan.errors import ConanException`。

## 源码修改

| 文件 | 修改 | 补丁 |
|------|------|------|
| `Makefile.in` | 硬链接 `ln en C` → `rm -f C; cp en C`（E079） | 0001-Makefile.in.patch |
| `config.guess` | 补 `ohos` 分支（E007） | 0002-config.guess.patch |
| `config.sub` | 补 `ohos` 三元组映射（E007） | 0003-config.sub.patch |
| `configure` | `mktemp -d` 临时目录显式 `umask 022`（E011） | 0004-configure.patch |
| `diction.c` | 短语库目录改为相对 exe 查找（`SHAREDIR` 回退）+ `readlink` NUL 终止 | 0005-diction.c.patch |

补丁中不含 `__OHOS__` 等平台宏（R8）：平台差异由 configure 阶段确定的目标三元组与运行期相对路径查找自然生效。

## 依赖版本

无外部依赖：仅使用设备自带 libc（clang / OHOS SDK），未引入第三方库；配方显式使用 `--disable-nls`，避免 OHOS 环境不完整 `libintl` 实现导致链接失败。

## 验证结果

- 上游测试: **9/9 通过**（test01..test09；`make check` 因 `for i in test/test*; do $$i || break; done` 吞错并恒返回 0，不可作为证据，故配方内逐个执行并检查退出码）
- 消费者测试: **5/5 通过**（`test_package/test_diction.sh`：版本输出 / 短语库随包安装 / 默认查找路径的真实短语标记与统计行 / `-f` 显式短语库与 `-q` 静默模式 / 鸿蒙安装目录迁移后相对路径查找）
- W3 本地 CI 模拟（`conan create`）: `exit_code=0`（见归档 `.ci-result.json`，含日志 SHA256）

## 交付物

- `bin/diction`、`bin/style`
- `share/diction/{C,de,en,en_GB,nl}` 短语库（运行时数据，随包安装）

## 注意事项

- diction 只支持 in-source 构建（2006 年 Makefile），Conan 配方采用 `basic_layout(self, src_folder=".")` + `self.folders.build = "."`。
- `make install` 不能叠加 Conan 默认的 `DESTDIR`（`--prefix` 已指向 `package_folder`），否则产物会写成 `package_folder/package_folder`。
- 软件级 `commands.json` 声明命令行工具（R38）。
---

**编译结束**: 2026-09-10 22:37
**最终状态**: built
