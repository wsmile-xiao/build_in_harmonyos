# DRAFT: Qt 子模块无独立源码：provider 配方复用已发布父模块制品（Qt6LinguistTools 案例）

## 场景

Qt6LinguistTools 6.11.1 适配任务。消费者 kdnssd 6.29.0 的 ECM
`ECMPoQmTools.cmake:155` 需要 `find_package(Qt6 COMPONENTS LinguistTools)`，
并曾因 `Qt6LinguistToolsConfig.cmake` 缺失失败。核验发现：Qt6LinguistTools
在 Qt 6 中**不是独立源码模块**，其实体（lrelease/lupdate/lconvert/lcheck/
ltext2id 等工具 + Qt6LinguistToolsConfig.cmake）由 **qttools** 构建产生，
且 qttools/6.11.1.1 已发布到 ohpcd registry（revision e6b700c0...）并实际
产出这些工具与 CMake 配置。

## 问题

1. 已经存在完整提供 Qt6LinguistTools 的已发布包（qttools），若再下载
   qttools 源码重新编译一份独立 Qt6LinguistTools，既重复制品又浪费构建，
   且 KDE 库此前因 "Qt6LinguistTools not published to ohpcd" 把
   `ecm_install_po_files_as_qm(poqm)` 注释掉。
2. 归档目录名 `Qt6LinguistTools` 含大写，不是 conan slug —— W3 本地 CI
   门禁 L0m-5 直接拦截（`conan create` 报 must be all lowercase）。HMDFS
   文件系统大小写不敏感，直接 `mv Qt6LinguistTools qt6linguisttools` 是
   同名 no-op，必须两步 mv（先改临时名再改 slug 名）。

## 方案

写 provider 配方（不重复编译父模块）：

```python
# conanfile.py (name = "qt6linguisttools", 归档目录 slug 同名)
def requirements(self):
    self.requires("qttools/6.11.1.1", transitive_headers=True, transitive_libs=True)
    self.requires("qtbase/6.11.1", transitive_headers=True, transitive_libs=True)

def build(self):
    apply_conandata_patches(self)      # 无补丁，仅满足 G1 结构检查

def package(self):
    # 从已发布的 qttools 依赖包复制 LinguistTools CMake 模块与 bin 工具
    copy(self, "Qt6LinguistTools/*", src=qttools/lib/cmake, dst=lib/cmake)
    for tool in ("lrelease","lrelease-pro","lupdate","lupdate-pro",
                 "lconvert","lcheck","ltext2id"):
        copy(self, tool, src=qttools/bin, dst=bin)

def package_info(self):
    self.cpp_info.set_property("cmake_find_mode", "none")
    linguisttools = self.cpp_info.components["linguisttools"]
    linguisttools.set_property("cmake_target_name", "Qt6::LinguistTools")
    linguisttools.builddirs = ["lib/cmake/Qt6LinguistTools"]
    self.env_info.PATH.append(bin)     # lrelease 等运行期依赖 libQt6Core.so.6（qtbase）
```

conandata 仍指向官方 qttools 子模块 tarball（SHA-256 与 download.qt.io
mirrorlist 一致），`source()` 下载作来源留证，不参与编译。

## 验证

- `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64` → 通过
  （test_package CMake `find_package(Qt6 COMPONENTS Core LinguistTools)` +
  build/test 中**实际调用 lrelease** 把 TS 编译为 QM，exit 0，非空壳）
- `ohc-run.py conan-verify` → G1/G2/G3/G4/L2/L4/L5 全 PASS，可标记 published
- 逐入口实测（aarch64 主机跑 arm64 ELF，LD_LIBRARY_PATH=qtbase/lib）：
  lrelease -version rc=0、lupdate -version rc=0、lconvert rc=0、
  lcheck/ltext2id usage rc=0；lrelease TS→QM 产出 81B .qm、lconvert TS→TS
  均 rc=0
- W3 本地 CI 被预存在无关 junk 文件 `archives/g/goaccess/1.10.2/
  ncurses-headers.tar.gz`（仓库基线，非本包引入）拦截 → 按 R41 外部首错
  回报不掩盖

## 适用边界

- 仅适用于"独立归档库 = 已发布父模块的子组件"的情形（本案例：LinguistTools
  归属 qttools，非 qtbase——qtbase 已安装包不含 Qt6LinguistTools cmake 目录）
- 若父模块未发布或制品缺目标组件，仍须按 R36 先发布父模块
- 归档目录名必须为 conan slug 全小写（L0m-5 门禁）

## 查重差异

knowledge/graph/index.tsv（322 条）与 knowledge/drafts/ 均无 linguist/
qttools/ECMPoQmTools/provider 复用相关条目——新增知识价值成立。