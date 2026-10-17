# DRAFT-7341 — hmdfs 无符号链接：版本化共享库软链必挂，运行期探测 + NO_VERSIONED_SONAME 条件化

> 状态：草稿（来自 libtiff 4.7.2.2 真机适配，task_id=7341）

## 问题

真机 `conan create` 首轮：源码编译 100% 通过、链接成功，止步于最后一步——CMake 按
libtiff 无条件设置的 VERSION/SOVERSION 创建版本化软链（libtiff.so.6 →
libtiff.so.6.0.1、libtiff.so → libtiff.so.6）时 hmdfs 报 `Operation not permitted`
（EPERM），构建终止。

取证：`/storage`（构建树与 conan 包目录所在）是 hmdfs 挂载，**完全不支持符号链接**，
直接 `ln -s x y` 即 EPERM；`/tmp` 是只读 tmpfs，不存在可建软链的落点。

## 根因

1. libtiff 在 cmake/AutotoolsVersion.cmake 里**无条件** set(VERSION/SOVERSION)
   （无平台门控），共享库构建必然产出版本化软链链。
2. 真机文件系统 hmdfs 不支持软链（EPERM）→ 任何"版本化共享库"配方在该文件系统上
   链接/安装后一步必挂。
3. 两端需求相反：Linux 农场要求与上游 4.7.2 一致的版本化布局；真机 hmdfs 上根本
   建不出软链。上游没有"只对一端生效"的开关。

## 方案

**运行期能力探测，而非平台分支**——build() 开头在构建目录尝试 `os.symlink()`：

- 失败（OSError）→ 追加 `-DCMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`：CMake 忽略
  VERSION/SOVERSION，产出裸 `libtiff.so`（SONAME 无版本），无任何软链；
- 成功（Linux 农场）→ 不追加，布局与上游 4.7.2 完全一致。

零源码补丁；同一配方在两端各自正确。探测代码见
`archives/l/libtiff/4.7.2.2/conanfile.py` build()。

## 验证

- 首轮（改前）：编译+链接 100% → 软链创建 EPERM 挂掉；
- 次轮（改后）：`conan create` 包建成（8 后端共享库、裸 libtiff.so XPM 自签），
  `conan test` 功能往返探针 83/83 断言全绿（exit 0）；
- 农场路径：探测不触发（软链可用），布局保持上游一致——由探测语义保证。

## 适用边界

- 仅影响"上游无条件设 VERSION/SOVERSION、且构建/安装目录在 hmdfs 上"的共享库配方；
- 静态库、上游本就不设 SOVERSION 的库不受此向量影响；
- 探测在软链可用的文件系统上恒不触发，农场行为不变。

## 查重差异

- DRAFT-libharu-2.3.0-missing-dt-soname：libharu 是**上游不设 VERSION/SOVERSION** +
  OHOS 无 CMake 平台模块致 SONAME 链接标志为空 → 产物**缺 DT_SONAME**、L5 门禁挂；
  修法是 generate() 静态设 CMAKE_PLATFORM_NO_VERSIONED_SONAME + SONAME 标志 + 上游补丁。
  本条是**上游无条件设** VERSION/SOVERSION → 版本化软链在 hmdfs 上**建不出来**
  （EPERM），修法是运行期探测 + 条件化开关，农场布局不变。两者互补（无 SONAME vs
  软链建不出），不是同一错误签名。
- DRAFT-6487-classads-hmdfs-getcwd / DRAFT-6507-cln-mktemp-0700-hmdfs：hmdfs 家族的
  getcwd / mktemp 权限向量，与软链能力无关。
