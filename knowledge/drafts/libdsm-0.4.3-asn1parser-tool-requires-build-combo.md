# 构建期需要 asn1Parser 的 meson/autotools 包：tool_requires 同包补齐工具缺口

> 草稿 ID：`libdsm-0.4.3-asn1parser-tool-requires-build-combo`
> 来源任务：libdsm 0.4.3 适配（SMB 客户端库，SPNEGO 认证需要 ASN.1 解析，meson 构建）

## 错误特征

```
meson.build:181:4: ERROR: Program or command 'asn1Parser' not found
```
或 autotools 系（./configure 阶段）：
```
checking for asn1Parser... no
configure: error: asn1Parser is required to build
```

## 触发条件

- 上游 tarball 只发布源码**不发布生成产物**（上游 `dist_generated.py` 之类的 dist 脚本
  本该把生成文件打进发行包，但 GitHub codeload tag tarball 是纯 `git archive` 产物，
  不跑 dist 脚本）；
- meson.build 用 `find_program('asn1Parser')` + `custom_target(... command: [asn1parser_prog, ...])`
  在构建期从 `contrib/spnego/spnego.asn1` 生成 `spnego_asn1.c`；
- 构建机（OHOS PC 本机 / CI clean 环境）没有系统级 libtasn1 工具（`which asn1Parser` 空）。

## 根因

asn1Parser 是"**既属依赖又属构建工具**"的双角色程序：运行期链接 libtasn1.so，
构建期用它的 CLI 生成 C 源。conan 生态把它当依赖管理（`requires`），但工具二进制
只在包的 bin/ 里，系统没装就在 PATH 上找不到——meson 的 find_program 不会去
conan cache 里找。

## 修复（构建系统组合方案）

conanfile.py 同时声明 requires + tool_requires **同一个包**：

```python
def requirements(self):
    # 运行期链接（SPNEGO/NTLM 认证的 ASN.1 解析）
    self.requires("libtasn1/4.21.0")

def build_requirements(self):
    # 构建期工具：spnego_asn1.c 未预生成，需 asn1Parser 从
    # contrib/spnego/spnego.asn1 生成（meson custom_target 原生流程）
    self.tool_requires("libtasn1/4.21.0")
    # meson 的 dependency('libtasn1') 走 pkg-config 查找：
    # CI clean 环境无系统 pkg-config，pkgconf 补齐
    # （ayatana-indicator-keyboard / burp2 / captagent 合入先例同款）
    self.tool_requires("pkgconf/3.0.5")
```

关键事实（实测验证）：
1. **libtasn1 制品仓包自带 bin/asn1Parser + lib/libtasn1.so.6**——不用自己造工具包；
2. conan 的 tool_requires 会把工具包的 bin/ 注入构建环境 PATH，lib/ 注入
   LD_LIBRARY_PATH（buildenv），meson 的 find_program 直接命中；
3. asn1Parser 动态链接 libtasn1.so.6，脱离包环境裸跑会
   `Error loading shared library libtasn1.so.6`（exit 127）——不要试图把
   二进制拷出去单跑，在 conan buildenv 里跑；
4. 生成命令（meson.build 内已有，无需改）：`asn1Parser -o spnego_asn1.c
   -n spnego_asn1_conf contrib/spnego/spnego.asn1`。

## 反例（不要这么做）

- ❌ 在 OHOS 上 apt/brew 装 libtasn1 工具——OHOS 无此类包管理器路径，且 CI
  clean 环境不复现；
- ❌ 预生成 spnego_asn1.c 提交进 patches/——可行但不如 tool_requires 干净
  （生成器版本与依赖库版本可能漂移；作为 fallback 保留）；
- ❌ 从 meson.build 里删掉 spnego 支持砍功能——SPNEGO 是 SMB 认证主路径。

## 验证

```bash
# 修复前（裸环境）：
$ which asn1Parser
asn1Parser not found

# 制品仓包内工具实测：
$ export LD_LIBRARY_PATH=$PKG/lib && $PKG/bin/asn1Parser --version
/storage/.../bin/asn1Parser (libtasn1) 4.21.0

# 修复后（conan create，tool_requires 注入 buildenv）：
$ conan create -pr:h=~/.conan2/profiles/ohos-aarch64 archives/l/libdsm/0.4.3
...
libdsm/0.4.3: Package created — test_package 8/8 断言通过
# spnego_asn1.c 由 meson custom_target 在构建期生成，产物进 spnego 认证路径
```

## 证据

- 本机实测：`~/.conan2/p/libtafabd0bb445031/p/bin/asn1Parser`（制品仓 libtasn1/4.21.0 包内）
- 生成实验：`asn1Parser -o spnego_asn1.c -n spnego_asn1_conf spnego.asn1` → 2228 字节产物
- 配方实现：`archives/l/libdsm/0.4.3/conanfile.py` → requirements()/build_requirements()
- 适配笔记：`archives/l/libdsm/0.4.3/notes.md`（上游事实节 + spnego 生成方案节）
- 上游对照：tarball 的 `meson.build:177-187`（fs_module.is_file('spnego_asn1.c') 分支
  + find_program('asn1Parser')）与 `dist_generated.py`
