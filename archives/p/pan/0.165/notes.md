# pan 0.165 适配笔记

- 日期：2026-09-03
- 状态：**配方先行开发**（gmime 3.0.5 PR #7971 在 CI，等合入间隙）
- 分支：feat/pan-0.165（worktree ../pan-wt，基于 origin/main 17f38c6e19）

## 1. 软件概况

- GNOME Usenet 新闻组阅读器，C++17（107 .cc + 15 .c），GTK3 GUI + nzb 批处理
- 上游：https://gitlab.gnome.org/GNOME/pan，tag **v0.165**（注意 v 前缀）
- 0.165 已迁移到 CMake（`cmake_minimum_required(VERSION 3.25)`）

## 2. 源码

- GitLab archive：`https://gitlab.gnome.org/GNOME/pan/-/archive/v0.165/pan-v0.165.tar.gz`
- sha256（本地实算）：`c9eeeff363908bb4c7f2d305e651b618d729a5ea3b9e5756525ce9dd0da118e4`
- 与 gmime 3.0.5 同款下载通道，实测可达（2.7MB）

## 3. 依赖确认（W0 实测）

| 依赖 | 版本 | 制品仓（conan download 实测） | 说明 |
|---|---|---|---|
| gtk | 3.24.43 | ✅ 已发布 | 传递依赖 glib/2.84.0.1(**shared**) 等 20 包全可解析 |
| gmime | 3.0.5 | ❌ **未发布（PR #7971 在途）** | 本地缓存有完整 OHOS 包（见 §5） |
| zlib | 1.3.1.1 | ✅ 已发布 | PIC 修正版；cmake_file_name=ZLIB 满足 find_package(ZLIB) |
| glib2 | 2.88.0 | ✅（gmime 的依赖） | static |
| gspell | — | ❌ 无任何版本 | **WANT_GSPELL 必须关**（上游默认开） |
| gnutls | 3.8.10 | ✅ 已发布 | 本次先关（WANT_GNUTLS=OFF），可作后续增强 |
| libnotify/libsecret/gcr/webkitgtk | — | ❌ | 上游默认关，保持关 |

## 4. 关键技术决策

### 4.1 CMake 版本：不 tool_requires

- pan 0.165 要求 CMake ≥ 3.25；hnp 工具链 cmake 为 **4.1.2** ✅
- **不使用 tool_requires("cmake/...")**：ohpcd 制品仓无任何 cmake 配方
  （conan list 实测 0 条），且 CI setup.sh 明确**禁用 conancenter**
  （`ci/conan/setup.sh:130-133`），L0i 依赖闸会硬拦
  （fastdds/2.1.0 的 tool_requires("cmake/3.16.3") 是制品仓有该配方的历史场景，不适用）

### 4.2 glib 双树统一（本配方最大风险点，已实测验证）

- gmime/3.0.5 依赖 **glib2/2.88.0（static）**；gtk/3.24.43 依赖 **glib/2.84.0.1（shared）**
- 两包 `pkg_config_name` 同为 `glib-2.0`，共图时实测（conan install gmime+gtk --build=missing）：
  - 图中两个 glib 变体**共存**（29 节点图，无版本冲突报错）
  - PkgConfigDeps 输出**单一 glib-2.0.pc**，指向 gtk 树的 shared glib（prefix=glibcad7259522c98）
  - gmime 的静态 libgmime-3.0.a 在链接期按 glib-2.0 符号解析，运行时绑定 shared libglib
  - 兼容性依据：pan 编译策略 `GLIB_VERSION_MAX_ALLOWED=2.36`、`GLIB_VERSION_MIN_REQUIRED=2.26`，2.84/2.88 均满足
- **W3 终验时需复验**：gmime 从制品仓解析后此结论是否仍成立（同一配方 revision 则成立）

### 4.3 可选功能开关

- `WANT_GSPELL` 上游默认 **ON** → 强制 OFF（gspell 未发布）
- `WANT_GNUTLS` 上游默认 **ON** → 本次 OFF：
  - 上游 `pan/data/cert-store.h:166` 提供完整 `#else` 空壳降级（无 TLS 时 CertStore 为空实现，socket-impl-main.cc 走 GIOChannelSocket），**非 stub 注入，上游原生支持**
  - gnutls/3.8.10 制品仓已有，后续版本可开（需验证 gcr-3 证书路径在 OHOS 的行为）
- `ENABLE_MANUAL` OFF（需 itstool，纯文档）
- `BUILD_TESTING` OFF（上游无活动测试，见 §6）

### 4.4 po/ 翻译处理

- po/CMakeLists.txt `find_package(Gettext)` + `GETTEXT_PROCESS_PO_FILES`（53 语言）
- msgfmt/xgettext/msgmerge 由 hnp 工具链提供（/data/service/hnp/bin），profile PATH 已注入
- CMake FindGettext 找系统工具，无需 conan gettext 包

### 4.5 其他

- `CMAKE_SYSTEM_NAME=Linux`（OHOS 无 CMake 平台模块，设备原生编译，同 abcmidi 模式）
- `SOURCE_DATE_EPOCH=1`：跳过嵌入 git rev（tarball 无 .git）与 uname（可复现构建）
- try_run(strftime %l/%k 检测) 需要 cmake 3.25+，hnp cmake 4.1.2 下正常运行
- Iconv：find_package(Iconv) 无 REQUIRED，musl 提供 iconv（ld-musl 符号表实测 T iconv），HAVE_ICONV 真实可用

## 5. 本地预验证（gmime 用本地缓存）

- 本地 .conan2 缓存有 gmime/3.0.5 完整 OHOS 包（rrev 4ce219a364ce9dc3e6f9683ff0574e7a，package aa42aa5300...，static，os=OHOS armv8 clang15）
- `conan install --requires=gmime/3.0.5 --build=never` 本地解析通过（gmime+glib2+pcre2+zlib 全 Cache）
- 本地 conan create 预验证结果：见本文件附录 A（执行后回填）

## 6. 上游测试情况（R34 分析）

- CMakeLists include(CTest) 但**全工程零 add_test()**
- 唯一候选 `pan/data/article-test.cc` 被上游注释（"this test is broken"，pan/data/CMakeLists.txt 尾部）
- uulib 无测试
- → test_package 补全真实测试（R34）：
  1. **执行打包产物 pan 二进制**：`pan --version`（参数解析阶段 return，先于 gtk_init，headless 安全）+ `pan --help`
  2. **消费侧链接证明**：test_pan.cxx 以与 pan 完全相同的方式（pkg_check_modules gmime-3.0 + gtk+-3.0）链接两库并调用 g_mime_init/g_mime_version_string + gtk_get_*_version
- assertion_count = 5（版本串非空、GTK major=3、两个二进制 smoke、test_pan 退出码）

## 7. ⚠️ 卡点清单（等 gmime PR #7971 合入后执行）

| # | 卡点步骤 | 阻塞原因 | 解除后动作 |
|---|---|---|---|
| 1 | **W3 终验**（finish step 5：R36 依赖闸 + conan create 从制品仓解析 gmime） | gmime/3.0.5 未合入 ohpcd | `conan download gmime/3.0.5 -r=ohpcd --only-recipe` 验证 → `ohc-run.py finish pan 0.165 built` |
| 2 | **CI 通过**（L0i 依赖闸对 gmime/3.0.5 探测） | 同上 | submit 建 PR 走 CI |
| 3 | **PF4 依赖闸**（create-pr 前置探测） | 同上 | #7971 合入后 create-pr 不再拦 |

### 非卡点（已闭环）

- ✅ 源码下载 + sha256 实算
- ✅ W0：gtk/zlib/glib2 制品仓实测在仓；gspell 无（已规避）；gnutls 在仓（本次不用）
- ✅ lang-preflight：detected=cpp（107 cc vs 15 c，主体 87%）
- ✅ 配方三件套 + commands.json + manifest + notes 全套开发
- ✅ 本地 conan create 预验证（gmime 本地缓存解析）——结果见附录

## 8. 后续任务（W3 终验任务交接清单）

gmime PR #7971 合入后，在 feat/pan-0.165 分支（worktree ../pan-wt）执行：

```bash
cd /storage/Users/currentUser/huawei/pan-wt
# 1. W0 复验
conan download "gmime/3.0.5" -r=ohpcd --only-recipe
# 2. 本地干净 W3（清掉本地 gmime 缓存或用 --build=never 从远端拉）
SKILL_ROOT=/data/storage/el2/base/files/apps/skills/resources/openharmony-compile-agent
python3 $SKILL_ROOT/scripts/ohc-run.py finish pan 0.165 built
# 3. W4 审计 + submit（PF4 依赖闸此时应放行）
python3 $SKILL_ROOT/scripts/ohc-run.py submit pan 0.165
```

注意事项：
- 若 #7971 合入的 gmime 配方 rrev 与本地缓存（4ce219a...）不同，glib-2.0.pc 指向结论（§4.2）需重验
- pan 无上游测试，CI L1 的 upstream_check_command 已按 test_package/MANIFEST.yml 说明 disabled

---

## 附录 A：本地 conan create 预验证记录（2026-09-03）

**结果：✅ 完整通过（编译 + 链接 + test_package 三 smoke 全绿）**

命令：
```bash
conan create archives/p/pan/0.165 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=default \
  --build=pan/0.165
# 复验（缓存包）：--build=never 同样通过
```

- pan/0.165 recipe rrev `fdd95c6f7350a6084074f9e84b250bfe`，package_id `f3e58f0ff6a3ea0770f1b8745d783cb7542fc0ff`
- 依赖图 28 包全部从本地缓存解析（**gmime/3.0.5 走本地缓存**：rrev 4ce219a3…，package aa42aa5300…）
- test_package 输出：
  - `pan --version` → **`Pan 0.165`** ✅
  - `pan --help` → exit 0 ✅
  - `./test_pan` → `gmime version: 3.0.5` / `gtk version: 3.24.43` / `test_pan: gmime+gtk link OK` ✅
- 产物：`bin/pan`（2.5MB，PIE DYN，GNU_RELRO + NX GNU_STACK RW，`.codesign` 签名段 1 个）
  + share/{applications,icons,locale(53 语言)}；licenses/COPYING

### 调参过程记录（8 次 conan create 迭代，供 W3 终验参考）

| # | 失败点 | 修复 |
|---|---|---|
| 1 | zlib/1.3.1 vs 1.3.1.1 版本冲突（glib2 树 pin 1.3.1） | `self.requires("zlib/1.3.1.1", override=True)`（同 gmime 配方） |
| 2 | `--build=never` 找不到 pan 预编译包 | 首次构建用 `--build=pan/0.165` |
| 3 | `CMakeToolchain` 无 `.environment()` 方法 | SOURCE_DATE_EPOCH/msgfmt 走 `Environment().vars().save_script()` |
| 4 | `try_run(HAVE_LKSTRFTIME)` 交叉编译模式报错 | 预填 cache `HAVE_LKSTRFTIME=0`（上游有 %l→%I/%k→%H 安全 fallback） |
| 4b | FindGettext 找不到 msgmerge | prepend `/data/service/hnp/gettext.org/gettext_0.26/bin` 到 PATH（msgmerge 无 hnp/bin 链接） |
| 5 | test_package 找不到 gmime-3.0.pc | pan 是 application 无 cpp_info 传递 → test_package 显式 requires gmime/gtk |
| 6 | `g_mime_init(0)`/`g_mime_version_string()` API 签名错 | gmime-3.0.5 是 `g_mime_init(void)` + `gmime_major_version` 常量 |
| 7 | `pan --version` → Operation not permitted（SDK 自动签名无效） | package() 加 E077 四步重签（remove .codesign → binary-sign-tool selfSign → chmod 755） |
| 8 | `libc++_shared.so`/`libc++.so` not found | test() 的 LD_LIBRARY_PATH 追加 `/system/lib64`（date/3.0.5 同款修复） |

### E077 签名发现（重要知识）

OHOS SDK 链接器**自动生成**的 `.codesign` 段**无效**（内核仍拒执行），必须：
1. `llvm-objcopy --remove-section .codesign $BIN`
2. `binary-sign-tool sign -inFile $BIN -outFile $BIN.signed -selfSign 1`
3. `os.replace($BIN.signed, $BIN)` + `chmod 755`

实测：未重签的 pan 报 `Operation not permitted`；四步重签后正常输出 `Pan 0.165`。

### 运行时库路径发现

pan 二进制 NEEDED 含 `libc++.so`/`libc++_shared.so`（OHOS 系统 C++ 运行库，在 `/system/lib64`，
非 conan 包）；musl loader 对这些不自动搜索 → test 时 LD_LIBRARY_PATH 必须补 `/system/lib64`。
gtk 树 23 个 conan libdir + gmime/glib2/pcre2/zlib 4 个 + /system/lib64 全量注入后 `Pan 0.165` 输出正常。

### 与 W3 终验的差异声明

本次验证的 gmime/3.0.5 来自**本地缓存**（子任务 gmime conan create 的产物）。
W3 终验时 gmime/3.0.5 需从 ohpcd 制品仓解析（PR #7971 合入后）。若合入的 rrev 与本地
（4ce219a364ce9dc3e6f9683ff0574e7a）一致，本附录结论直接有效；若不同，需复验 §4.2 的
glib-2.0.pc 指向与 test 三 smoke。
---

**编译结束**: 2026-09-07 01:13
**最终状态**: built
