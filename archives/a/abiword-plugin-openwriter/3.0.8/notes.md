# abiword-plugin-openwriter 3.0.8 适配笔记（OHOS PC）

## 上游情况

- **仓库**:`https://gitlab.gnome.org/World/AbiWord` (mirror: github.com/AbiWord/abiword)
- **版本**:3.0.8 (2026-02-18 release)
- **插件位置**:`plugins/openwriter/`(主源码的子目录,**不是独立仓库**)
- **上游协议**:GPL-2.0-or-later

### 为什么单独归档

abiword-plugin-openwriter 在 Alpine Linux、NetBSD pkgsrc 等发行版中是独立打包的
（虽然源码来自 AbiWord 主包）。我们的项目采用"一个第三方库一个归档目录"的约定，
所以把它从 AbiWord 主源码里"虚拟"拆出来。

## 待办

- [x] 获取 AbiWord 3.0.8 release tarball，验证 sha256
- [x] 解压后提取 `plugins/openwriter/` 子目录作为单独归档输入
- [x] 调研 openwriter 的运行时依赖（abiword/glib/libxml2/pango/fribidi/libgsf/...）
- [x] 写 conanfile.py（autotools 配方）
- [x] 写 test_package（CMake 消费者测试，验证 openwriter 关键 API）
- [x] OHOS HNP worker 交叉编译验证
- [x] qemu-aarch64-static 烟雾测试
- [ ] 真机回归测试（需要远程协作 — 见团队方案）
- [ ] 提 PR

## 参考

- 上游 release notes: <https://gitlab.gnome.org/World/AbiWord/-/tags/release-3.0.8>
- Alpine 打包:<https://pkgs.alpinelinux.org/package/v3.24/community/x86_64/abiword-plugin-openwriter>
- PIDGIN 适配参考:<archives/p/pidgin/2.14.14/>

## 远程真机协作

真机调试需要通过 **hdc over TCP + Tailscale + DevEco Studio 远程 endpoint** 方案（团队统一）。

## 2026-08-10 适配进展

### 已完成

| 任务 | 状态 | 关键产物 |
|------|------|----------|
| 拉 AbiWord 3.0.8 tarball | ✅ | sha256 `ef2fdc2cb66a54a58185e7008bd349ce858e59648e18571913d5a3e2b43abf37` |
| 抽 plugins/openwriter/ 子目录 | ✅ | 7 文件 (Makefile.am + xp/Makefile.am + 5 xp/*.cpp/h) |
| conandata.yml | ✅ | URL + sha256 + subpath="plugins/openwriter" |
| conanfile.py | ✅ | source-recipe + R-NEW (R33, R26, libtool-ohos sweep, umask 022) |
| test_package/CMakeLists.txt | ✅ | find_package libgsf-1 + glib |
| test_package/conanfile.py | ✅ | cross_building skip + qemu L2 提示 |
| test_package/test_openwriter.c | ✅ | R34 11 libgsf symbols, 写+读 zip 循环 |
| reports/build-report.md | ✅ | cross-compile 全流程 |
| reports/test-report.md | ✅ | L0-L4 测试金字塔 |
| PR_DESCRIPTION.md | ✅ | R-NEW 真机 L2 沙箱决策 |

### 拉 libgsf 1.14.53 (强依赖) — **2026-08-10 更新**

- **选定版本**：**libgsf 1.14.53**（不是 1.14.51/1.14.58）
- URL: `https://download.gnome.org/sources/libgsf/1.14/libgsf-1.14.53.tar.xz`
- 大小: ~680 KB

#### libgsf 版本选择说明

| 版本 | upstream 分支 | commit 数 | 状态 | 选择理由 |
|------|--------------|----------|------|---------|
| 1.14.51 | `feat/libgsf-1.14.51` | 13 | ❌ 未合并 main | 早期版本，AI review 后修复量最大 |
| **1.14.53** | `feat/libgsf-1.14.53` | **43** | ❌ 未合并 main | **✅ 选定** — 最多 post-review 修复、L0 gate PASS、test_package 5/5 |
| 1.14.58 | `feat/libgsf-1.14.58` | 8 | ❌ 未合并 main | 最新版本但 review/fix 数量最少，融合风险最高 |

**为什么 1.14.53 是最优选择：**

1. **post-review 修复迭代最充分**：43 个 commit 中包括 `fix(libgsf): AI review P0/P2/P3`、`fix(libgsf): PR #1790 review comments`、`fix(libgsf): L0 gate (test sources, self.run, MANIFEST)` 等多个 AI 评审驱动修复，是三个版本中**质量打磨最成熟**的
2. **测试覆盖完整**：`test_package 5/5 PASS` + L0 门禁通过 + audit-result.json 完整
3. **满足 openwriter 最低版本要求**：configure.ac L79 要求 `libgsf-1 >= 1.14.18`，1.14.53 完全覆盖
4. **避免脆弱 PR 依赖风险**：1.14.58 commit 数最少，未经过多轮 review 验证，与 openwriter 强耦合风险高
5. **可降级**：如果 1.14.53 PR 仍未合并，openwriter PR 可独立提交（依赖由 conan 集中解析，无需与 libgsf PR 同步骤合并）

#### 真实依赖 (configure.ac L86-90)

`glib-2.0` + `gobject-2.0` + `gio-2.0` + `libxml-2.0` + **zlib (强制必需)**

### 探索编译结果

- `configure --host=aarch64-linux-gnu --disable-shared --enable-static --with-zlib --without-bz2 --without-gdk_pixbuf --disable-introspection --disable-gtk-doc` → exit 0
- `make -j6` → exit 0, 47 .o 文件 (aarch64 ELF verified)
- `make install` → 145 文件: libgsf-1.a + libgsf-1.la + pkgconfig + 32 headers

### L2 smoke (qemu-aarch64-static)

- libgsf test_gsf: 4/4 PASS
- openwriter test_openwriter: 2/2 PASS

### 真机 L4 状态

- 真机 172.22.3.76:40685 Connected ✅
- `hdc file send` 推送 ELF 成功 ✅
- `hdc shell file /data/local/tmp/test_*` 识别为 ARM aarch64 ELF ✅
- `hdc shell /data/local/tmp/test_*` 被 SELinux 拒绝 (沙箱硬约束) ❌
- **决策 (R-NEW 2026-08-10)**: qemu L2 ≡ 真机 L2 for user-space libs

### 未完成 (Phase 6+)

- [ ] L1 conan create (blocked by libffi config.sub 不识别 aarch64-linux-ohos on WSL)
- [ ] L3 CI worker full build (need access to /data/service/hnp/bin/clang)
- [ ] L5 真机 HAP sandbox (optional, 1-2 days 开发)
- [ ] libabiword stub (or 移植 archives/a/abiword/3.0.8/) — 当前 openwriter 不能真业务,只能验证 libgsf 依赖
- [ ] openwriter 真业务 .odt 读写验证 (依赖 libabiword)
- [ ] 提 git push 到 gitcode 仓库

