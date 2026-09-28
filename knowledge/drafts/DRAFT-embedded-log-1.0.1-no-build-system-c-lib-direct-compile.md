# DRAFT-embedded-log-1.0.1-no-build-system-c-lib-direct-compile：零构建系统裸 C 库的 Conan 直接编译配方模式

> Contributor: pc7-18 | Status: Draft | Updated: 2026-09-23
> Source: embedded-log 1.0.1 适配（零构建系统裸 C 库，HarmonyOS PC）
> 对应：`knowledge/drafts/DRAFT-embedded-log-1.0.1-no-build-system-c-lib-direct-compile.kv`

## 问题

上游只给出 `src/log.c` + `src/log.h` + `src/log_cfg.h` 三个文件，**没有任何构建系统**
（无 Makefile / configure / CMake / meson），这类"裸 C 库"在 Conan 适配时踩三个连环坑：

1. **构建系统误判**：`ohc-run.py conan-init` 按 URL 猜测构建系统，把这类库误判为
   autotools，生成 `AutotoolsToolchain`/`Autotools` 模板配方——但上游根本没有
   configure/Makefile，模板在 build() 直接失败。
2. **包类型契约**：模板默认 `package_type = "library"`，Conan 2 对 library 类型
   强制要求声明 `shared` 选项（`Package type is 'library', but no 'shared' option
   declared`），纯静态小库引入 shared 分支没有意义。
3. **手写编译与安装**：无构建系统意味着 build() 必须直接调用编译器
   （`clang -c` + `llvm-ar rcs`），package() 必须平铺拷贝头文件与 .a；
   头文件互 include（`log.h` → `#include "log_cfg.h"`）时还必须保持同目录层级，
   否则消费者编译找不到。

## 识别：什么算"零构建系统裸 C 库"

```sh
# ① 解压后顶层是否只有源码与文档，无任何构建文件？
tar -tzf <lib>.tar.gz | grep -iE 'makefile|configure|cmakelists|meson|\.mk$' || echo "无构建系统"
# ② 是否仅 .c/.h 且头文件互相包含？
find . -name '*.c' -o -name '*.h' | sort
```

满足"无构建文件 + 有需编译的 .c"即本模式；若连 .c 都没有（纯单头文件）走 E257
header-only 模式；若有 Makefile 走 E392 raw-makefile 模式；有 configure/CMake 走对应模式。

## 配方写法（三要素）

```python
package_type = "static-library"          # ① 绕开 library 的 shared 契约（纯静态库）

def build(self):
    cc = conf_or_fallback("c", "clang")  # ② conf 子键不可用时回退 PATH（R33 合规）
    ar = conf_or_fallback("ar", "llvm-ar")
    self.run(f"{cc} -c -O2 -fPIC -std=c99 -I{src_dir} {src_dir}/log.c -o log.o")
    self.run(f"{ar} rcs libembedded-log.a log.o")

def package(self):
    copy(self, "log.h",     src=src_dir, dst=include, keep_path=False)  # ③ 平铺
    copy(self, "log_cfg.h", src=src_dir, dst=include, keep_path=False)  #    互包含头同层
    copy(self, "libembedded-log.a", src=build_dir, dst=lib, keep_path=False)
    copy(self, "LICENSE", src=source_folder, dst=licenses, keep_path=False)

def package_info(self):
    self.cpp_info.libs = ["embedded-log"]
```

> `conf_or_fallback`：`self.conf.get("tools.build:compiler_executables:<k>", ...)`
> 在 OHOS 适配版 Conan 2.29.1 上抛 `ConanException: does not exist in
> configuration list`（E392 同源：该 conf 是字典），用 try/except 回退到 PATH 上的
> clang/llvm-ar（与 AutotoolsToolchain 发射的工具名一致）。

## 验证

- `conan create`（G2 干净构建）通过；conan-verify G0-G4 + L2/L4/L5 8 道门禁全过；
- test_package 消费者用例（log_init + LOG_INF 断言 hook 回调）与鸿蒙专项用例
  （LOG_ERR/WRN/INF + printk_hex 多断言）ctest 2/2 通过；
- L1e sabotage 反向验证通过（移走 lib/ 与 include/ 后测试失败，证明真实依赖被测包）。

## 适用边界

- ✅ 适用：上游仅 .c/.h、无任何构建系统的纯 C 库（嵌入式/单片式小库、单文件 C 程序）。
- ❌ 反例：有 Makefile（走 E392）、有 configure/CMake/meson（走对应模式）、
  纯单头文件无需编译（走 E257）、需要生成配置头或消费上游 CMake target 的库（走 E307 直编边界）。

## 与既有知识的差异

| 条目 | 覆盖 | 本候选新增 |
|------|------|-----------|
| E283 declare-shared-contract | library 类型需 shared 契约（方案=声明 shared 选项） | **static-library 替代解法**：纯静态库直接换包类型绕开契约 |
| E392 raw-makefile-conan-recipe-pattern | 有 Makefile 的 raw makefile 三陷阱（BadZipFile/conf 字典/make cwd） | 边界扩展：**完全无 Makefile** 时的直接编译路径与平铺头安装 |
| E257 header-only | 单头文件库 build() 空操作 | 本模式有真实 .c 编译，不适用 |

## 关系

- `similar_to`: E283, E392, E257
- `caused_by` / `prerequisite_of` / `conflicts_with`: 无
