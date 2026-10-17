# libotf

[libotf](https://savannah.nongnu.org/projects/m17n) — GNU m17n 项目的
OpenType 字体处理库（C 库 + 命令行工具）：OTF 表遍历（GDEF/GSUB/GPOS）、
cmap 驱动、字形串处理，以及 OTF → BDF 转换。

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 0.9.16 | 已适配 OHOS | 见 [0.9.16/notes.md](0.9.16/notes.md) |

## 许可证

LGPL-2.1-or-later（上游 `COPYING`，包内 `licenses/COPYING`）。

## OHOS 适配要点（0.9.16）

- **构建系统**：autotools（上游发布含预生成 `configure`，无需 autoreconf）。
  4 个补丁均为 `portability` 类型，详见 [0.9.16/notes.md](0.9.16/notes.md)。
- **freetype 探测（核心修复）**：上游 `configure` 依赖 FreeType 2.10 起已移除的
  `freetype-config`；探测失败时上游**静默**置 `HAVE_FREETYPE=no` —— 库仍能编译，
  但 `FT_Load_Sfnt_Table` 等符号悬空、OTF 表读取链路全部失效。补丁改为
  `pkg-config`（先 `freetype2`、后 Conan `PkgConfigDeps` 的 `freetype`）回退，
  并保证 `-lfreetype` 进入链接行（E572）。
- **临时目录权限**：autotools 的 `confXXXXXX` 临时目录以 `umask 077` 创建，
  HMDFS 下权限 2700 导致目录不可写（E011），补丁改为 `umask 022`。
- **三元组**：上游 2014 年的 `config.guess`/`config.sub` 不认识 HarmonyOS，
  补丁补齐 `aarch64-unknown-linux-ohos`（先于 `-linux*` 归一化命中）。
- **VPATH 构建**：Conan 采用 out-of-tree 构建；上游 `example/Makefile.in` 只有
  `-I$(top_builddir)/src`，示例程序找不到 `<otf.h>`；补丁补 `-I$(top_srcdir)/src`。
- **依赖**：`freetype/2.14.3`。`otf.h` 公开头文件包含 `<ft2build.h>`/
  `FT_FREETYPE_H`，配方以 `transitive_headers` + `transitive_libs` 传递，
  消费者无需显式配置 freetype 头文件路径。
- **产物**：`libotf.so.1`（SONAME）+ 三个命令行工具 `otfdump`/`otflist`/
  `otftobdf`（上游 `bin_PROGRAMS`，随 `make install` 安装；按 R38 在软件级
  目录声明 [commands.json](commands.json)）。

## 使用

```conan
requires = "libotf/0.9.16"
```

```c
#include <otf.h>

OTF *otf = OTF_open("/system/fonts/HarmonyOS_Sans_SC.ttf");
if (otf) {
    if (OTF_check_table(otf, "GSUB") == 0)   /* 0 = 表存在，-1 = 不存在 */
        printf("GSUB present\n");
    OTF_close(otf);
}
```

命令行工具：

```sh
otfdump /system/fonts/HarmonyOS_Sans_SC.ttf | head   # OTF 表转储
otflist /system/fonts                                # 目录字体枚举
otftobdf /system/fonts/FTChariSans.ttf > out.bdf     # OTF → BDF
```
