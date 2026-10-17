# libidn2 2.3.8 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
- 产出 libidn2.so 等 1 个库，供链接与 dlopen。

## 关键适配
- 删除 lib/*.la：其中烤死 libdir 绝对路径，会把下游 libtool 引到 //lib/ 死路
- 修 configure 的 umask 077→022（HMDFS E011）
- 依赖接制品仓 libunistring/1.0 + libiconv/1.17（均 static），产物 .so 静态并入二者，
  DT_NEEDED 仅 libc.so，SONAME libidn2.so.0

## 状态
pending —— **mac 交叉编译验证通过，真机验证待补**（验证时测试机被占用）。

已验证面（mac + DevEco SDK clang 15 交叉，aarch64-linux-ohos，接制品仓 libunistring/libiconv armv8 包）：
- configure/make/install 全绿：config.sub 原生认 ohos 三元组，libunistring 1.0.0 / libiconv 均从 conan 制品接上（未落到内嵌裁剪版）
- 产物 `libidn2.so.0.4.0`：aarch64 ELF、SONAME=libidn2.so.0、DT_NEEDED 仅 libc.so、23 个导出符号（含 test.c 断言用的全部 5 个 API，带 IDN2_0.0.0 版本标记）
- test_package/test.c（真实 IDNA 断言）交叉编译+链接通过

真机待补：`conan create <本目录> -pr:h ohos -pr:b ohos_build -r ohpcd`（test_package 运行断言）。
- ⚠️ 必须 `-r ohpcd`：conancenter 的 libiconv/1.17 旧修订会抢占制品仓修订 → Missing binary（已实撞）
- ⚠️ 设备本地 cache 若已有旧修订 libiconv，先 `conan remove "libiconv/1.17" -c`

<details>
<summary>历史记录：2026-05-20 源码构建（cmd-pkgs 静态链接路线，非 conan）</summary>

本目录早先存有源码构建笔记与 manifest（status: published、build_type: static_linked）。
本次新增的 conan 配方走独立动态库路线（.so + conan 制品仓），不基于该次构建；旧记录原文保留备查。

### 旧 notes.md

````markdown
# libidn2 2.3.8 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-20
- 编译器: clang/clang++
- 状态: published

## 编译步骤

标准 autotools 构建流程：

```bash
# 1. 配置
./configure --prefix=/data/data/com.example.harmonyapp/files/usr/local

# 2. 编译
make -j2

# 3. 安装
make install DESTDIR=/path/to/staging

# 4. 打包预编译包
# 生成 libidn2-2.3.8-ohos-aarch64.tar.gz
```

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| libunistring | 1.4.2 | Unicode 字符串处理库（cmd-pkgs 预编译包） |

## 重新编译记录（2026-05-20）

### 问题：动态库无法加载
- OpenHarmony 的 musl 动态链接器有安全限制
- musl 只从预配置的系统目录加载动态库
- 用户目录 ~/usr/local/lib 不在 musl 搜索路径中
- LD_LIBRARY_PATH、RUNPATH/RPATH、LD_PRELOAD 都不起作用

### 解决方案：完全静态链接
1. 安装 libunistring 1.4.2 预编译包（cmd-pkgs）
   ```bash
   curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libunistring 1.4.2
   ```
2. 创建 rpl_free.c 提供 gnulib 替换符号
   ```c
   void rpl_free(void *ptr) { free(ptr); }
   void libunistring_rpl_free(void *ptr) { free(ptr); }
   ```
3. 静态链接编译 idn2-static：
   ```bash
   clang -o idn2-static -I~/usr/local/include -static \
       simple_idn2.c rpl_free.o \
       ~/usr/local/lib/libidn2.a \
       ~/usr/local/lib/libunistring.a
   ```

### 功能验证：✓ PASS
```bash
$ ~/usr/local/bin/idn2 --version
idn2 (libidn2) 2.3.8

$ echo "测试.中国" | ~/usr/local/bin/idn2
xn--0zwm56d.xn--fiqs8s

$ echo "日本.jp" | ~/usr/local/bin/idn2
xn--wgv71a.jp
```

### 最终产物
- `~/usr/local/bin/idn2-static` (1.4MB) - 静态链接可执行文件
- `~/usr/local/bin/idn2` → idn2-static (符号链接)

### 限制说明
- 动态库只能从系统目录加载（用户环境下不可用）
- 静态链接是用户环境下唯一可行的方案
- 其他需要使用 libidn2 的程序也需要静态链接

## 知识提取记录

### 新发现的平台限制：musl 动态链接器安全限制
- **分类**: platform-limitation
- **严重级别**: 🔴 4（影响所有动态链接的软件）
- **现象**: LD_LIBRARY_PATH/RUNPATH/LD_PRELOAD 不生效
- **根因**: musl 只从预配置的系统目录加载动态库
- **解决方案**: 采用静态链接方式编译可执行文件
````

### 旧 manifest.yaml

````yaml
# 版本级 manifest
# 文件位置: archives/l/libidn2/2.3.8/manifest.yaml
# 遵循 ARCHIVE-SPEC v2.0

# ============================================================
# 必须字段
# ============================================================

# 软件名称（继承自软件级）
software: libidn2

# 版本号
version: "2.3.8"

# 编译状态
# published | built | failed | archived
status: published
build_type: static_linked  # 动态库在用户环境下不可用，采用静态链接

# 编译日期（YYYY-MM-DD）
build_date: "2026-05-20"

# 构建系统（继承自软件级）
build_system: autotools

# ============================================================
# 源码信息
# ============================================================

source:
  # 源码下载 URL
  url: "https://ftp.gnu.org/gnu/libidn/libidn2-2.3.8.tar.gz"

  # 源码校验和
  sha256: ""

  # 压缩格式
  # tar.gz | tar.xz | tar.bz2 | zip
  tar_format: tar.gz

# ============================================================
# 构建配置
# ============================================================

build:
  # 构建系统类型
  # cmake | autotools | makefile | meson | custom
  system: autotools

  # 配置选项列表
  configure_options:
    - "--prefix=/data/data/com.example.harmonyapp/files/usr/local"

  # 编译依赖列表（格式: name/version）
  dependencies:
    - libunistring/1.4.2

  # 编译器
  cc: clang
  cxx: clang++

# ============================================================
# 补丁信息
# ============================================================

# 应用的补丁列表
patches_applied: []

# ============================================================
# 知识沉淀
# ============================================================

# 编译中学到的知识
knowledge_gained:
  - "标准 autotools 构建系统"
  - "依赖 libunistring 1.4.2 库"
  - "musl 动态链接器限制：LD_LIBRARY_PATH/RUNPATH 不生效，需静态链接"
  - "静态链接 idn2-static 成功运行，功能验证通过"
````

</details>

