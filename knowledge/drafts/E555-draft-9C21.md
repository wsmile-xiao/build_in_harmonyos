# E555: CMake 定向 --target 构建绕过 ALL 生成目标，cmake --install 因安装清单引用的生成物缺失而失败

> **知识性质**：通用 CMake 构建闭包问题。标题、根因、算法均不绑定任何具体库；
> libzzip 0.13.80 仅作为首个真实成功案例（见"真实实例"章节）。
> **编号说明**：本条目原编号 E544，因 upstream/main 已存在其他贡献者的 E544 草稿（编号冲突），
> 于 2026-09-04 迁移为 E555，知识内容不变。

## 基本信息
- **ID**: E555
- **严重度**: 3
- **阶段**: installation（configure/build 全绿，install 阶段失败）
- **类别**: cmake, build-system, packaging, ohos, detection
- **触发工具**: cmake / cmake --install / conan create
- **推荐方案**: `restore-default-all-install-generation-closure`
- **状态**: 草稿（draft，待人工确认后 promote）

---

## 使用说明

当满足以下全部信号时使用本条目：

1. **构建日志里库目标全部编译成功**——`configure` 完成、`cmake --build` 到 `[100%] Built target <libs>` 无一失败；
2. **失败发生在 `cmake --install`**（或 Conan 的 `package()` 阶段执行 install 时），报错形如：
   ```
   CMake Error at zzip/CMakeLists.txt:321 (install):
     file INSTALL cannot find
     "/build-ohos/zzip/zziplib.pc".
   ```
3. 缺失对象**不是库本体**，而是安装元数据类生成物：`*.pc`（pkg-config）、compat 兼容头、`libfoo.so.N` 版本化软链（libtool 约定）、`.m4`、cmake config 等。

若你的失败发生在 configure 阶段（平台不识别/Unsupported platform），请转 **E532**；
若产物能安装但 `.so` 缺 SONAME，请转 **E383**。

---

## 适用范围

同时或单独满足以下任一条件的 CMake 工程移植（典型：HarmonyOS/OHOS Conan 适配）：

| 条件 | 上游形态特征 |
|---|---|
| A. 定向构建绕过 ALL 闭包 | 配方为规避 ALL 闭包中个别会失败的目标，显式 `cmake --build --target <lib> <bin> ...`；上游存在 `add_custom_target(<meta> ALL DEPENDS <产物>)`（如 pkgconfig/compat/libtool-links），其产物被 `install(FILES ${CMAKE_CURRENT_BINARY_DIR}/<产物>)` 引用 |
| B. 平台门控的元数据选项静默 OFF | 上游 `if(UNIX OR MINGW)` 包住 `option(<XXX>_PKGCONFIG "..." ON)` 等默认值；HarmonyOS 无 CMake 平台模块、`UNIX` 为假，落入 `else()` 的 OFF 默认（或根本不定义），configure 日志仅一行 `-- installing N pkgconfig files: OFF`，极易漏看 |

两种条件可叠加（libzzip 即叠加态），单独任一条件也可能独立触发同类 install 失败。

**通用抽象**：这是"CMake 安装清单闭包 ⊅ 实际构建闭包"的通用问题——`install()` 规则声明的输入集合，必须被构建阶段实际生成；任何缩小构建闭包（定向 target）或关闭生成选项（平台门控默认 OFF）的操作，都会让 install 清单引用悬空文件。

---

## 不适用范围

- **configure 期平台识别失败**（`if(WIN32) elseif(UNIX) else()` 落入 else 报 Unsupported platform / 编译宏全错）→ E532，发生在配置阶段，本条目发生在安装阶段；
- **共享库缺 SONAME**（链接成功、安装成功，`readelf -d` 无 SONAME）→ E383，是链接模板变量缺失，与 install 清单无关；
- **纯编译/链接错误**（编译器不认识宏、找不到头文件、undefined reference）——build 阶段即失败，本条目 build 全绿；
- **Autotools/Meson 的同类问题**（如 `make install` 缺 `.pc`）——诊断思想相通（"安装清单 ⊆ 构建闭包"不变式），但命令与选项名不同，本条目命令仅适用 CMake；
- **上游本来就不安装该文件**（install 规则被上游 `if()` 正当关闭）——此时清单不应引用该文件，属于上游 bug，不在本条目修复范围；
- **install 时目录权限/路径错误**（`file INSTALL cannot set permissions` 等）——是安装环境问题，不是生成物缺失。

---

## 输入定义

执行诊断算法前需收集的输入：

| 输入 | 来源 | 用途 |
|---|---|---|
| `install_fail.log` | CI 失败日志中 `cmake --install` 段 | 提取 `file INSTALL cannot find "<绝对路径>"` 的文件清单 |
| `configure.log` | 同一轮 CI 的 `cmake -B` 输出 | 检查 `-- installing N pkgconfig files: OFF`、`-- compat: OFF` 等元数据选项状态行 |
| `build_cmd` | recipe `build()` 中的 `cmake --build ... --target ...` 命令行 | 确认是否定向构建、绕过了哪些 ALL 目标 |
| `<src>/**/CMakeLists.txt` | 上游源码 | 定位 `add_custom_target(... ALL)`、`install(FILES ...)`、`if(UNIX OR MINGW)` 门控 |
| `conanfile.py` | 当前配方 | 确认 `conf`/`cache_variables` 中是否已显式 `-D` 元数据选项 |

---

## 输出定义

修复完成后必须产出的输出：

1. **修复后的 `conanfile.py`**：
   - `build()` 不再含 `--target` 列表（默认 ALL 构建）；
   - `generate()`/`configure()` 中显式 `-D<XXX>_PKGCONFIG=ON -D<XXX>_COMPAT=ON -D<XXX>_LIBTOOL=ON`（逐个对照上游被门控的选项）；
   - 若 ALL 闭包中个别目标失败，以环境变量（如 `LD_LIBRARY_PATH` 指向构建树库目录）修复，而非绕过。
2. **安装前生成物校验记录**：构建树中枚举出的全部 `.pc` / compat 头 / 软链清单（fail-closed：缺一即中止）。
3. **成功的 `cmake --install` 日志**：install 清单全部文件复制成功，包目录 `lib/pkgconfig/*.pc` 齐全。
4. **消费者测试结果**：`conan create` 的 test_package 阶段用**最终安装包**（非构建树）链接并运行通过。

---

## 通用诊断算法

```text
DIAG-INSTALL-CLOSURE(fail_log, src, recipe, configure_log):
1. 阶段定位:
   若 fail_log 显示 configure 或 compile 错误 → 不适用本条目（转对应编译类条目）。
   仅当错误为 "file INSTALL cannot find" 且发生于 install 阶段 → 继续。

2. 提取缺失文件清单:
   files = grep 'file INSTALL cannot find' fail_log 提取全部绝对路径
   按 类型分类: *.pc / 生成头 / lib*.so.N 软链 / 其他元数据

3. 反查生成目标 (对每个缺失文件):
   grep -n "add_custom_target.*ALL\|add_custom_command(OUTPUT <file>" src/**/CMakeLists.txt
   记录产出该文件的 custom target 名 T 及其是否挂 ALL。

4. 检查配方构建闭包:
   若 recipe.build() 含 "--target" 且 T 不在列表中
     → 确认根因①: 定向构建绕过 ALL 生成目标。

5. 检查选项平台门控:
   grep -n "if(UNIX OR MINGW)" src/**/CMakeLists.txt
   检查门控内 option(<XXX>_PKGCONFIG/COMPAT/LIBTOOL> ... ON) 的默认值;
   在 configure_log 中找对应 "-- ...: OFF" 状态行;
   若 HarmonyOS 环境下 UNIX 为假且配方未显式 -D 开启
     → 确认根因②: 元数据选项静默 OFF。

6. 双因素归因:
   根因①与②可独立或叠加成立; 输出诊断结论:
   "构建闭包未覆盖安装清单闭包, 缺失目标=[T...], 静默 OFF 选项=[...]"
```

---

## 推荐修复算法

```text
FIX-RESTORE-DEFAULT-ALL-INSTALL-GENERATION-CLOSURE(recipe, src):
1. 删除显式 --target 列表, 恢复默认 ALL 构建:
   cmake --build build -j N        # 不带 --target

2. 修复 ALL 闭包中原本会被绕过的失败目标 (而非继续绕过):
   例: custom target 在构建期 exec 交叉编译产物二进制 →
       设 LD_LIBRARY_PATH=<build>/<libdir> 使其找到刚链接的库;
   原则: 让 ALL 闭包完整可构建, 而不是挑目标。

3. 显式开启被平台门控静默关闭的元数据选项 (逐个对照上游 else() 分支):
   cmake -B build -S src \
     -D<XXX>_PKGCONFIG=ON \
     -D<XXX>_COMPAT=ON \
     -D<XXX>_LIBTOOL=ON

4. 安装前 fail-closed 校验生成物:
   枚举 install(FILES) 引用的全部生成文件, 逐一 test -f;
   任一缺失 → 立即中止, 回到第 3 步排查; 不许带病安装。

5. 执行安装:
   cmake --install build --prefix <pkg>

6. 消费者验证:
   用最终安装包 (lib/pkgconfig/*.pc, 头文件, 库, 软链) 跑
   test_package: 链接 + 运行 + (如适用) pkg-config 解析校验。

回退方案 (仅当 ALL 闭包中确有无法满足的目标):
   fallback: explicit-targets-plus-manual-generation-steps —
   保留 --target 列表, 但逐一显式追加被绕过的生成目标
   (pkgconfig/compat/<xxx>_links 等), 且第 4 步校验不可省略。
```

---

## fail-closed 安全边界

以下为**硬性禁止**，任何一条都不得以"让 CI 变绿"为由违反：

| 禁止操作 | 禁止理由 | 违反后果 |
|---|---|---|
| ❌ 手工伪造 `.pc`（`echo`/`printf`/`touch` 生成 `prefix=...` 文件） | 内容未经上游生成逻辑校准：libdir/includedir、`Requires:` 传递依赖（如 zlib）全靠手猜 | 包表面完整，下游 pkg-config 解析错、传递依赖丢失，问题延迟到消费者处爆发且难溯源 |
| ❌ 删除/注释上游 `install(FILES ...)` 规则 | 等于裁剪交付物，破坏上游安装契约 | CI 绿但包残缺：pkg-config 消费者、libtool 约定（找 `libfoo.so.N`）消费者全不可用 |
| ❌ 显式 `-D..._PKGCONFIG=OFF`（等）关闭交付功能来消除报错 | 反向修复：用降级交付换取构建通过 | 包永久缺元数据，下游 Meson/pkg-config 构建直接失败；交付完整性被静默阉割 |
| ❌ 跳过第 4 步安装前校验直接 install | 缺失会再次以 install 中断或更隐蔽方式暴露 | 失败在更晚、更贵的阶段出现 |

**fail-closed 原则**：安装前生成物校验必须"缺一即停"（缺失 → 中止并报错），而不是"缺了也继续"；消费者测试必须使用最终 Conan 安装包（不是构建树产物），否则校验形同虚设。

---

## 真实实例：libzzip 0.13.80（首个成功案例）

> 本节仅为实证记录；知识本身是通用 CMake 问题，后续任何库命中同模式均适用本条目。

**背景**：zziplib（libzzip）0.13.80 适配 HarmonyOS OHOS-AARCH64，CI 执行 `conan create`。

**失败现场**（真实 CI 安装失败）：
- 库目标全部编译成功：`[100%] Built target zzip`、`libzzip-0.so`、`zzipfseeko`、`zzipmmapped`、`zzipwrap` 链接完成，无任何编译错误；
- `cmake --install` 阶段失败，install 清单引用的生成文件不存在：
  - `zziplib.pc`
  - `zzipmmapped.pc`
  - `zzipfseeko.pc`
  - `zzipwrap.pc`
  - （同门控下的 compat 兼容头与 libtool 版本化 `.so` 软链也未生成）

**双因素根因实证**：
1. **定向构建绕过 ALL 闭包**：旧版配方 `build()` 用显式 `--target` 列表只编库与 bins（动机：全量 ALL 会跑 test/ 目录的 sfx ALL 目标，生成自解压 `zzipshowme` 需先 exec 交叉二进制）。上游 `zzip/CMakeLists.txt` 中 `add_custom_target(pkgconfig ALL ...)`、`compat ALL`、`libzzip_links ALL`（libtool 软链）等元数据目标不在 `--target` 列表内，四个 `.pc` 与软链从未生成；
2. **平台门控静默 OFF**：上游 `if(UNIX OR MINGW)` 内设置 `ZZIP_PKGCONFIG`、`ZZIP_COMPAT`、`ZZIP_LIBTOOL` 默认 ON；HarmonyOS 在当前 CMake 环境不满足 `UNIX`，落入 else() 静默默认 OFF——configure 日志仅一行 `-- installing N pkgconfig files: OFF`。

**真实修复**（对应推荐算法逐步落实）：
1. 删除显式 `--target` 列表，恢复默认 ALL 构建（sfx 目标的 exec 失败用 `LD_LIBRARY_PATH` 指向构建树库目录修复）；
2. configure 显式设置 `ZZIP_PKGCONFIG=ON`、`ZZIP_COMPAT=ON`、`ZZIP_LIBTOOL=ON`；
3. 安装前验证四个 `.pc` 文件及其他安装元数据（compat 头、软链）全部生成；
4. 执行 `cmake --install` 成功；
5. 用最终 Conan 安装包跑消费者测试：test_package 链接并运行通过，上游 229 项测试全绿（`failures=0`）。

修复遵守全部 fail-closed 边界：未手工伪造任何 `.pc`、未删除任何 `install()` 规则、未关闭任何交付功能。

---

## 与 E532 / E383 的本质区别

| 维度 | E532 | E383 | **E555（本条目）** |
|---|---|---|---|
| 失败阶段 | **configure（配置）** | **link（链接）**（产物缺陷，运行期/装载期暴露） | **install（安装）**：configure/build 全绿 |
| 失败本质 | 平台三分支 `if(WIN32) elseif(UNIX) else()` 不识别 HarmonyOS，落入 else() → **Unsupported platform** | 无 Platform/HarmonyOS.cmake 模块 → `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 为空 → **缺 SONAME flag** | 构建/安装**两个闭包不一致**：定向 `--target` + 平台门控默认 OFF → install 清单引用的**生成物缺失** |
| 关键症状 | configure 期报不支持的平台/宏全错 | `readelf -d` 无 SONAME 字段 | `file INSTALL cannot find "*.pc"` 等安装清单引用文件不存在 |
| 修复面 | 平台识别注入（OHOS 三元组/平台模块补齐） | recipe 注入 `-Wl,-soname,` 链接 flag | 恢复 ALL 构建闭包 + 显式开元数据选项 |

一句话区分：**E532 是"配置期平台不认识"，E383 是"链接期缺 SONAME flag"，E555 是"构建成功后因 target closure 不完整导致安装生成物缺失"**——三者阶段、症状、修复面完全不同，互不覆盖。

---

## 验证命令

```bash
# 1. 诊断：确认 install 失败与缺失文件清单
grep -E "file INSTALL cannot find" <ci_fail_log>

# 2. 反查上游生成目标与 install 规则（通用，替换 <src> 为上游源码根）
grep -R -nE 'add_custom_target\([a-zA-Z_]+ ALL|install\(FILES' <src> --include=CMakeLists.txt | head -30
# 平台门控检查
grep -R -n 'if(UNIX OR MINGW)' <src> --include=CMakeLists.txt

# 3. 修复后构建（libzzip 实例；通用场景替换 <XXX> 前缀选项）
cmake -B build-ohos -S <src> \
  -DZZIP_PKGCONFIG=ON -DZZIP_COMPAT=ON -DZZIP_LIBTOOL=ON
LD_LIBRARY_PATH=build-ohos/zzip cmake --build build-ohos -j$(nproc)

# 4. 安装前 fail-closed 校验（libzzip 实例：四个 .pc 必须全部存在）
ls -1 build-ohos/zzip/zziplib.pc build-ohos/zzip/zzipmmapped.pc \
      build-ohos/zzip/zzipfseeko.pc build-ohos/zwrap/zzipwrap.pc

# 5. 安装
cmake --install build-ohos --prefix <package_dir>

# 6. 最终包消费者验证（test_package 用安装包而非构建树）
conan create . -pr:h=<ohos-profile> -pr:b=<build-profile>

# 7. 包内元数据核验
ls <package_dir>/lib/pkgconfig/   # zziplib.pc zzipmmapped.pc zzipfseeko.pc zzipwrap.pc
```

---

## 关联条目
- 相似（对比区分）: E532（configure 期 Unsupported platform）、E383（缺 SONAME flag）、E309（install 阶段其他失败模式）、E278（CMake 内部目标缺失）、E289（HELP2MAN=true 未生成 man 但 Automake install-man 仍非空——同为"生成物缺失但安装清单仍引用"模式，但 E289 属 Automake/make 工具链且根因是替身命令静默成功，本条目属 CMake 且根因是 --target 绕过 ALL 闭包；draft-review 相似度 0.35 属人工复核灰区，经人工比对主题不同）
- 原则: P013（保持上游构建/安装闭包完整）、P014（不得伪造生成物规避失败）

---
*draft E555 — 待人工确认后 promote；由 contributor 9C21 创建（2026-09-02）；原编号 E544，因 upstream/main 编号冲突于 2026-09-04 迁移为 E555*
