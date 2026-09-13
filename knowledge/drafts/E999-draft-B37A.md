# 纯数据包在 conan 生态的打包范式（noarch + 数据完整性测试）

> 实证来源：pari-elldata 20210301（500 文件，157MB）、pari-galdata 20080411（344 文件）。
> 仓库先例：wireless-regdb/2026.05.30、mbrola-hu1/1.002。

## 适用场景

三方库只发布**数据/资源文件**（数据库、字库、语音库、规则表……）：
tarball 解包后没有源码、没有 configure/CMakeLists、没有库和可执行文件。
pari 生态的 elldata/galdata/nftables/polis/seadata、内核 wireless-regdb、
MBROLA 语音库都是这个形态。对这类包，常规配方模板和测试形态全部失效。

## 怎么做（五件套）

### 1. conanfile.py 骨架

```python
class PariElldataConan(ConanFile):
    package_type = "unknown"                          # 数据包非 library/application
    settings = "os", "arch", "compiler", "build_type" # ⚠️ L0p 要求四项全声明
    def configure(self):
        self.settings.rm_safe("os.version")
        self.settings.rm_safe("compiler.cppstd")
    def package_id(self):
        self.info.clear()                              # → noarch，全平台一个包
```

**关键坑**：settings 只写 `("os", "arch")` 会被 CI L0p 门禁拦截
（missing_setting_compiler / missing_setting_build_type）——OHOS profile
要求四项全声明，再靠 `package_id().clear()` 折叠成 noarch，两者不冲突。

### 2. package()：数据安装布局

```python
def package(self):
    copy(self, "ell*", src=os.path.join(self.source_folder, "data", "elldata"),
         dst=os.path.join(self.package_folder, "share", "pari", "elldata"), keep_path=False)
    # README → share/doc/<pkg>/，许可 → licenses/（数据 tarball 常不带 COPYING，
    # README 内的许可声明可作为 licenses/ 交付）
```

### 3. package_info()：导出数据目录

```python
def package_info(self):
    self.cpp_info.libs = []           # 数据包全空
    self.cpp_info.includedirs = []
    self.cpp_info.libdirs = []
    self.cpp_info.bindirs = []
    self.cpp_info.resdirs = ["share"]
    data_dir = os.path.join(self.package_folder, "share", "pari", "elldata")
    self.buildenv_info.define_path("PARI_ELLDATA_DIR", data_dir)
    self.runenv_info.define_path("PARI_ELLDATA_DIR", data_dir)
```

### 4. build() 内嵌验证（损坏下载在 create 阶段即失败）

```python
def build(self):
    self.run(f'"{sys.executable}" "{self._validator}" --source-root "{self.source_folder}"')
```

### 5. test_package（R34 数据包豁免口径）

被测包无 API 可调用 → 常规 "编译 consumer 调 API" 形态不适用，**验证以数据
完整性为准**，test() 必须 `self.run` 真实执行验证脚本（--package-root 模式）：

| 断言层 | 内容 | 拦截能力 |
|---|---|---|
| 结构完整性 | 数据目录文件集合精确匹配（数量+命名） | 缺失/多余文件 |
| 载荷同一性 | 逐文件 sha256 与官方载荷 pin 表比对 | 截断/损坏/替换 |
| 内容健全性 | 抽验关键记录（如曲线 11a1 的系数） | 篡改后哈希凑巧不变等极端场景 |

- pin 表从**已校验的上游 tarball** 实算生成（`hashes_<pkg>.py`，随配方走）
- MANIFEST.yml 写明豁免理由："数据包无 API 可调用，验证以数据完整性为准"
- **export_sources() 必须拷贝验证脚本 import 的一切模块**（test 脚本 +
  hashes 表），只拷主脚本会 ModuleNotFoundError
- **故障注入自证**：截断一个数据文件、删一个文件，验证器必须 exit 1
  （elldata 实测：截断 ell5 → `sha256 mismatch`；删 ell250 → `found 499 entries`）

## 为什么这样（依据）

- `package_id().clear()` 是 conan 官方 noarch 语义；数据文件平台无关，
  折叠后全平台共享一个包，制品仓不用按 arch 重复上传
- 载荷同一性 pin 表把 test_package 从"存在性检查"升级为"身份检查"——
  数据包的全部价值就是数据本身，哈希逐文件对得上 = 包正确
- build() 内嵌验证器让 `conan create` 在装包前就完成源端校验，与
  test_package（包端校验）形成双端闭环

## 验证结果（pari-elldata 20210301 实测）

```
conan create ... --build=missing
  build()（source 模式）:  6/6 断言 PASS
  test_package（package 模式）: 6/6 断言 PASS
  W3 本地 CI 模拟: exit_code=0
  W4 Pre-PR 审计: verdict=pass（P0/P1=0，18 项检查，含 500 文件哈希独立重算）
故障注入: 截断 ell5 → exit 1（sha256 mismatch）；删 ell250 → exit 1（499 entries）
```

## 复用指引

后续 pari 系数据包（nftables/polis/seadata）及任何"数据/资源包"类三方库
直接套此范式；`recipe-search` 可用 elldata/galdata/wireless-regdb 作底稿。
