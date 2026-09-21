# 上游源码树内的子库/绑定独立成包（libgmpxx ⊂ GMP）

> 草稿（DRAFT，编号 E585）。与同目录 `libgmpxx-6.3.0-subpackage-in-tree-static-bindings.kv` 成对。
> 取号说明：`knowledge_id.py --claim` 在本机假阴性报出已被上游占用的 E565，改用「上游主线 + 各本地 worktree + 主检出」
> 三面人工复核后定 E585（543–583 已被上游占用，E584 已被并行任务占用）。

## 现象

把「某个上游源码树里的子库/语言绑定」当成独立包适配时，配方会以三类形式失败：

```text
cxx/...cc: fatal error: 'gmp-impl.h' file not found        # 只解包/配置子目录
undefined reference to `__gmp_doprnt_integer'              # 子库与父库不同源配置
consumer: fatal error: 'gmp.h' file not found              # 父包头未对消费者可见
```

反过来也能"假绿"：子库装成了，但把父项目的 `libgmp.a` / `gmp.h` / `gmp.pc` 一起装进了同一个包，
与已发布的父包 `gmp/6.3.0` 双份安装（下游 `-lgmp` 命中两份、头文件来源不明）。

## 根因

1. **内部头依赖生成物**：子库实现 `#include` 父项目的内部头（`gmp-impl.h`），该头依赖
   `configure` 生成的 `config.h` 与内部符号声明——脱离父项目 configure 无法编译。
2. **内部符号 ABI 同源要求**：子库对象引用父库**非公开**符号（实测 `llvm-nm -u libgmpxx.a`：
   `__gmp_doprnt_*`、`__gmp_asprintf_*`、`__gmp_istream_*`、`__gmp_allocate_func`/`__gmp_free_func` 等
   18 个，**不含 `__gmpn_*`**），
   只有同 tarball、同 configure 选项（同 `config.h`）时才能链接成功。
3. **包边界**：父库本体属于父包，子包重复安装会造成双份产物与头文件冲突；
   而子库的公开头（`gmpxx.h`）又 `#include <gmp.h>`，因此父包头必须对消费者可见。

## 方案（libgmpxx 6.3.0 实测口径）

| 环节 | 做法 |
|---|---|
| source | 复用**父项目同一 tarball**（URL/sha256 与父包逐字一致） |
| requirements | 精确 pin 父包版本；父包头是公开依赖时 `visible=True`（CMakeDeps 才会为传递依赖生成 include 数据） |
| generate | 复制父包 configure 选项 + 追加子库开关（`--enable-cxx`）；**完整 configure 整树** |
| package | 完整 `make install` 后删除父包本体产物（`libgmp.a`/`gmp.h`/`gmp.pc`/全树 `*.la`） |
| package_info | `cpp_info.libs=[子库]`、`cpp_info.requires=["父包::父包"]` + cmake/pkgconfig 名字 |
| static-only | 声明 `shared` 选项（Conan 2 要求），`shared=True` 抛 `ConanInvalidConfiguration` 指向父包共享整包版本 |

## 验证（设备可直接执行）

```sh
PKG=$(conan cache path libgmpxx/6.3.0@ohpcd/stable:<package_id>)
find "$PKG" -type f | sort                       # 只应有子库产物 + 上游文档
for f in lib/libgmp.a include/gmp.h lib/pkgconfig/gmp.pc; do [ -e "$PKG/$f" ] && echo "PRESENT $f" || echo "absent $f"; done
find "$PKG" -name '*.la' | wc -l                 # 0
llvm-nm -u "$PKG/lib/libgmpxx.a" | grep '__gmp_' | head   # 子库确实引用父包内部符号
```

## 证据（libgmpxx 6.3.0，PR !11150）

- 父 tarball sha256 `a3c2b80201b89e68616f4ad30bc66aee4927c3ce50e33929ca819d5c43538898`（与 `archives/g/gmp/6.3.0` 一致）。
- 安装树 8 文件，父包本体三项全 absent、`*.la` 0 个；干净轮 `conan create` + `test_package` + W3 本地 CI 全通过。
- 上游 `tests/cxx` 22 个程序直接静态链接 harness 实跑 **22/22 PASS**（设备 HMDFS `getcwd(2)` 使 libtool 链接测试程序确定性失败，故不纳入 in-build check，见该包 `reports/upstream-tests-cxx-log.md`）。
- **上游 N 口径（返修实证：2026-09-20 外部审查 rule4 判“少报：实测 N=190 > 声明 N=22”）**：
  子包只报自己那一支的用例数会被判少报——N 必须取**父 tarball 的完整注册面**
  （`tests/**` 各 `Makefile.am` 的 `check_PROGRAMS` 总数 **200** = 190 个 `t-*` + 10 个具名项
  reuse/io/dive/dive_ui/convert/logic），再按交付面把未运行项记 **NOT_RUN** 并逐目录归因
  （本例 178 项测 libgmp C API，不在子包 install 面）；自洽式
  `TOTAL 200 = PASS 22 + FAIL 0 + SKIP 0 + NOT_RUN 178`，通过率按执行口径写 22/22（100%）
  并显式写明与 N=200 的换算。取数命令与逐目录表见该包 `notes.md` 与 `test_package/MANIFEST.yml`。

## 适用范围

包名对应"上游源码树内的子库/绑定"（子目录 Makefile 目标、`--enable-<x>` 开关、`<父项目><子模块>` 形式），
且父包已在本仓库单独发布、子包必须与父包同源链接。已能独立发行的子库按普通独立包适配，不套用本条。
