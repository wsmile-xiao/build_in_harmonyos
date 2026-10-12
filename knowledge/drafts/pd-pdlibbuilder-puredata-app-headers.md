# DRAFT-PD-PDLIBBUILDER-PUREDATA-APP-HEADERS — 适配 Pure Data 外部对象库（pd-* / pd-libbuilder）到 OHOS

## 错误特征

适配 `archives/p/pd-*/` 这类走上游自带 `pd-lib-builder` 的包时，容易撞上：

```
error: m_pd.h: No such file or directory          # 找不到 Pd API 头
PDINCLUDEDIR=...                                  # 上游默认只探测 /usr/include/pd
uname -> HarmonyOS                                # 老版本 pd-lib-builder 用 uname，OHOS 无分支
ld.lld: error: undefined symbol: main             # 平台没选对 → 没 -shared，链接退化
no rule to make target ... .pd_linux               # extension 为空
permission denied: .../foo.pd_linux                # make install 落点问题
```

以及**编译安装全绿但功能静默缺失**：帮助补丁 Pd 打不开。

## 触发条件

- 阶段: source / build / package
- 前置: 上游用 `Makefile.pdlibbuilder`（pd-lib-builder）构建 Pure Data 外部对象库

## 根因分析

三个点叠在一起：

### 1. Pd API 头已经在制品仓里，不必再拉 pure-data 源码树

`puredata/0.54.1` 是 **application** 类型包，`package_info()` 不导出 `includedirs`，
但包内 `include/pd/` 确实装了 `m_pd.h` 与 `g_canvas.h`：

```
<pkg>/include/pd/m_pd.h
<pkg>/include/pd/g_canvas.h
```

旧先例（`pd-maxlib`）的注释断言「puredata 不装 m_pd.h」，并为此在 `source()` 里额外
下载整棵 pure-data 源码树。该断言已过时——多一次十几 MB 下载 + 一个硬编码 URL（R39 面）。

### 2. 平台判定信号是 `$(CC) -dumpmachine`，不是 uname

pd-lib-builder **v0.6.0**：

```make
target.triplet := $(subst -, ,$(shell $(CC) -dumpmachine))
ifneq ($(filter linux gnu% kfreebsd, $(target.triplet)),)
  system = Linux
endif
```

`aarch64-unknown-linux-ohos` / `aarch64-linux-ohos` 都含 `linux` → 命中 Linux 分支 →
`extension = pd_linux`、`-DUNIX`、`-fPIC -shared -rdynamic`、`-lc -lm`。

`target.arch` 取三元组首词 = `aarch64` → `arch.c.flags = -mcpu=cortex-a53`，
**OHOS clang 接受，不要清空**（只有 x86 构建机才需要 `arch.c.flags=`）。

更早版本的 pd-lib-builder 用 `uname`，那时 OHOS worker（`uname = HarmonyOS`）会失配，
所以配方里仍显式传 `system=Linux` 兜底最稳。

### 3. 帮助补丁必须拍平（最隐蔽的一条）

源码树里帮助补丁按类分目录：

```
control/ 17   experimental/ 4   filters/ 9   gui/ 9   other/ 1   signal/ 5   = 45
```

`datafiles` 用 `$(wildcard */*-help.pd)` 展开，而 `install-datafiles` 是：

```make
install-datafiles: all
	$(INSTALL_DIR) -v "$(installpath)"
	$(foreach v, $(datafiles), $(INSTALL_DATA) '$(v)' "$(installpath)";)
```

逐文件 install 到**同一个** installpath，**没有 `cp -R`**。用 `make -n install-datafiles`
实测即可确认——上游 `make install` 的结果本来就是扁平的。

Pd 侧（pure-data 0.54 `src/s_path.c`）：

```
open_via_helppath()  →  do_open_via_path(usedir, "<obj>-help.pd", "", …)
                     →  sys_trytoopenone(<每个已声明 path>, name, "", …)
```

`sys_trytoopenone()` 只做一次字面 `open(dir + "/" + name + ext)`，**不 opendir、不递归**。

⇒ conan 的 `copy()` 对帮助补丁必须 `keep_path=False`，否则 45 个帮助补丁 Pd 一个都找不到，
而「产物文件都装齐了」这类门禁完全查不出来。

### 4. 附带：`#include` 关系 ≠ 链接依赖

`gui/fatom.c` 在上游 Makefile 里被注释掉（不构建 `[fatom]` 类），但 `fatom.h` 仍被
`gui/slider.c`、`gui/sliderh.c`、`gui/ticker.c` include。这三个类只需要头文件里的声明与
内联辅助定义，不引用 `fatom.c` 的外部符号。判定依据是 undefined 符号，不是 include 图：

```bash
llvm-nm -D --undefined-only <ext_dir>/{slider,sliderh,ticker}.pd_linux | grep -i fatom   # 应为空
```

## 解决方案

### 推荐方案

配方零补丁，只做三件事：

1. **头文件**：声明依赖，从包目录探测

   ```python
   def requirements(self):
       self.requires("puredata/0.54.1")

   def _pd_include_dir(self):
       dep = self.dependencies["puredata"]
       for c in (os.path.join(dep.package_folder, "include", "pd"),
                 os.path.join(dep.package_folder, "include")):
           if os.path.isfile(os.path.join(c, "m_pd.h")):
               return c
       raise ConanInvalidConfiguration(...)
   ```

2. **构建**：`make -j1 system=Linux CC=<conf 里的编译器> PDINCLUDEDIR=<探测目录>`
   （R33：编译器取 `tools.build:compiler_executables`，不裸用 `${CC}`）

3. **打包**：外部对象与帮助补丁都拍平到 `lib/pd-externals/`；
   `LICENSE.txt` / `README.txt` 进 `licenses/`

### 测试（实测可用的形态）

用 puredata 包里的 OHOS `pd` 无头加载安装后的外部对象，print 出确定性数值再 grep：

```sh
timeout 40 "$PD_BIN" -nogui -nosound -path "$EXT_DIR" -open "$PATCH" > "$LOG" 2>&1 || true
grep -q "GGEE_CONSTANT: 3.14159" "$LOG"
```

三个要点：

- 启动 pd 前先断言外部对象**数量**正确，防止对残缺安装跑绿；
- `; pd quit;` 会与 `loadbang` 输出竞争、导致个别 print 丢失 → 用 `timeout` 收尾，不要在补丁里主动退出；
- 本地 WSL 是 x86_64，跑 aarch64/OHOS 产物要 binfmt+qemu 与 guest musl 的 `__fd_chk` 等 shim。
  那是**环境侧**设施，配方里不得出现 `LD_PRELOAD`/shim/运行期补丁。

## 验证

```bash
# 1. 头确实在包里
ls <puredata_pkg>/include/pd/m_pd.h

# 2. 上游 install 目标确实是拍平的（不是 cp -R）
cd <src> && make -n install-datafiles | head -5
grep -n 'cp -R' <src>/pd-lib-builder/Makefile.pdlibbuilder   # 应无匹配

# 3. 拍平后的包结构
ls <ext_dir>/*.pd_linux | wc -l            # = Makefile class.sources 条目数
find <ext_dir> -mindepth 1 -type d | wc -l # = 0
```

## 禁止做法

- ❌ 保留帮助补丁的类子目录（`keep_path=True`）：Pd 不可达，静默功能缺失。
- ❌ 相信「puredata 不装 m_pd.h」的旧注释并为此额外下载 pure-data 源码树。
- ❌ 在配方里塞 `LD_PRELOAD`/shim 让本地能跑——那是把环境问题伪装成产品行为。
- ❌ 只断言「产物数量 ≥ 下限」；用 `== len(class.sources)` 精确计数。
