# DRAFT-kodi-pvr-iptvsimple-21.11.0-cmake-install-rpath-rewrite-ohos-loader-integrity：cmake --install 的隐式 RPATH 改写使 ELF 与链接期完整性值不符，OHOS 加载器 dlopen 报 Permission denied

> Contributor: OpenDesk Agent | Status: Draft | Updated: 2026-10-10
> Source: kodi-pvr-iptvsimple 21.11.0（Kodi IPTV Simple PVR client，CMake MODULE 插件）适配
> 对应：`knowledge/drafts/DRAFT-kodi-pvr-iptvsimple-21.11.0-cmake-install-rpath-rewrite-ohos-loader-integrity.kv`

## 现象

conan test_package 中 `dlopen` 打包后的共享模块失败；链接该模块的测试二进制在**进程启动**时即失败：

```console
Error loading shared library /…/p/lib/pvr.iptvsimple.so: Permission denied
```

同一次构建、同一 `.o`、同一条链接命令，输出到 `build/Release/pvr.iptvsimple.so`
（链接器输出）可正常 `dlopen`；`cmake --install` 后的同名文件（conan 包内那个）失败。

## 根因（因果链）

1. CMake 为 `target_link_libraries` 里用完整路径链接的静态/共享库记录**构建期 DT_RUNPATH**
   （本模块：指向 pugixml/lzma 的 conan 目录；即使那两者是静态库也会记录）。
2. `cmake --install` 发现 install RPATH（空）≠ build RPATH，于是**原地改写 ELF**：
   把 DT_RUNPATH 字符串清零、删除该动态项，并重写若干路径字符串（本例共 230 字节差异）。
3. OHOS（musl）加载器对可 `dlopen` 的 ELF 做**整文件内容校验**（链接期记录的完整性/签名，
   产物带 `.note.ohos.ident` / `.codesign`）。文件被改写后校验不符 → `dlopen` 返回 EACCES
   「Permission denied」。
4. 失败点在链接/运行阶段而非编译阶段，且报错指向主库路径 → 易误判为权限/依赖/16K 对齐/rpath 语义问题。

**关键取证（证伪单因子解释）**：

- 差异仅 230 字节（`cmp -l`），全在 RUNPATH 字符串与若干路径字符串；ELF 头/段/动态表结构一致（无 RUNPATH 的新链产物可载）。
- 对可加载副本在**任意偏移**（含加载器不读取的 `.debug_*` 节）翻转 1 字节 → 立即 EACCES。
- 把安装产物的全部差异字节还原 → 恢复可加载。
  ⇒ 是整文件完整性校验，而非「权限/noexec/依赖缺失/对齐/rpath 语义」。

## 方案（配方层预防，零事后签名）

```python
# conanfile.py generate()
tc = CMakeToolchain(self)
tc.variables["CMAKE_SKIP_RPATH"] = True   # 链接器不植入 RUNPATH → cmake --install 不改写 ELF
```

验证：安装文件与链接器输出 `sha256sum` 相同，`dlopen` 成功（本库 test_package 25/25 断言通过）。

**退路**：确需安装后改写 RPATH 时，按 E077 的四步（`llvm-objcopy --remove-section .codesign`
→ 改 ELF → `binary-sign-tool sign -selfSign 1` → `chmod a+x`）处理；或在 `package()` 内直接用
`tools.files.copy` 打包 build 产物（不经 `cmake --install`），同样零修改。

## 判别（三行定位）

```sh
# 1) 同一 .so 链接器输出 vs install 后，加载行为是否不同
/path/to/dlt build/Release/x.so   # ok
/path/to/dlt "$PKG/lib/x.so"      # Error loading shared library …: Permission denied → 命中
# 2) 逐字节差异是否局限于 rpath/debug 字符串
python3 - <<'PY'
a=open('build/Release/x.so','rb').read(); b=open('x.so','rb').read()
d=[i for i in range(len(a)) if a[i]!=b[i]]; print(len(d), d[:5], d[-5:] if d else None)
PY
# 3) 改后是否只剩结构/权限差异（install 前后 ELF 头/段一致即非结构问题）
llvm-readobj -l -d x.so | head
```

## 关系

- `E077`（patchelf/strip/objcopy 显式改 ELF → 签名失效 → 四步重签名）：同族；本条补充
  **CMake install 的隐式 RPATH 改写**这一触发源与**构建期预防**（CMAKE_SKIP_RPATH）这一修法。
- `E653`（OHOS dlopen 内容级拒载 NDK 产物）：同现象不同机理（那条是 NDK 产物固有内容）。
- `E135`/`E083`（ELF 签名 / .codesign 与 dlopen Permission denied）：背景同域。
- 原则：P012（部署不污染系统路径）、P013（平台限制诚实降级）。

## 查重（Curator 确认审计）

检索范围：`knowledge/graph/index.tsv`（全文关键词 dlopen/rpath/runpath/EACCES/loader/install）、
`knowledge/drafts/` 全列表。

- 命中相近：E077（ELF 签名失效，显式改 ELF 工具 + 四步重签名）、E135、E083、E212、E653、E331、E088、E019、E186。
- 差异：E077 的触发是**显式**改 ELF 工具、修法是**事后重签名**；本条触发是 **cmake --install 隐式
  RPATH 改写**、修法是**构建期零修改预防**（CMAKE_SKIP_RPATH），并以「单字节翻转即 EACCES」
  的实验把机理收敛到整文件完整性校验。
- **相似度自评：与 E077 同族、覆盖度较高**——是否作为独立正式条目由主编判定（见 PR 说明）。
