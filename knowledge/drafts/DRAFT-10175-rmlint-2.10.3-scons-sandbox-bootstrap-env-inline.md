# DRAFT-10175：SCons 包在 OHOS 的沙箱自举 + 三个内联环境变量坑（rmlint 2.10.3）

- **触发实例**：rmlint 2.10.3 适配（2026-09-25，任务 10175，分支 feat/rmlint-2.10.3，B 机真机 G2 五轮）
- **错误签名**：`No module named SCons` / `Checking for glib-2.0 >= 2.64 ... Error: not found` / `AttributeError: 'VirtualBuildEnv' object has no attribute 'buildenv_info'`
- **类别**：build-system（SCons）/ conan 环境注入
- **严重度**：1（G2 阻塞级）
- **同构先例**：`archives/g/gpsd/3.26`、`archives/d/dxx-rebirth/0.6`、`archives/v/vixl/5.1.0`（均已合并 main）

## 症状（三轮 G2 实测，各为一次首错）

1. `AttributeError`：把 `buildenv_info` 当 `VirtualBuildEnv` 实例的属性用——它是 **ConanFile 属性**。
2. `No module named SCons`：`Environment().save_script("scons_env")` 写的是独立脚本，**不会**被聚合进
   `conanbuild.sh`，SCons 前缀的 PYTHONPATH 根本到不了 `python3 -m SCons`。
3. `Checking for glib-2.0 >= 2.64 ... Error: not found`：`PkgConfigDeps` 把 `glib-2.0.pc` 等写进了
   `generators_folder`，但聚合 `conanbuild.sh` 在本 Conan/平台组合上**不带**这个目录的
   `PKG_CONFIG_PATH`。

## 根因（三个事实叠加）

1. **SCons 无处可拿**：设备镜像无 scons 二进制/模块，ohpcd 制品仓无配方（`conan download scons/x
   --only-recipe` 报 acceleration policy 错），Conan 官方不分发 SCons 配方 ⇒ `tool_requires` 不可行。
   家法 = pip `--target=<build_folder>/_scons_env` 私有前缀自举（构建目录内生成、随沙箱销毁）。
2. **save_script 与聚合环境是两回事**：内联 `PYTHONPATH=<prefix>` 写进 `python3 -m SCons` 命令行才可靠。
3. **pkg-config 发现只有 PKG_CONFIG_PATH 一条路**：`SConstruct` 的 `options['ENV']` 白名单只放行
   `PATH/TERM/HOME/PKG_CONFIG_PATH` 四个变量 ⇒ CFLAGS/LDFLAGS 注入静默无效；
   `buildenv_info.append_path("PKG_CONFIG_PATH", generators_folder)` 必须在
   `VirtualBuildEnv(self).generate()` **之前**设置（顺序错即注入丢失）。

## 最小修复（最终方案，全部在 conanfile.py，零上游改动）

```python
# generate() 顺序：
self._install_scons()            # pip --target=build_folder/_scons_env scons==4.10.1
self._patch_scons_shell()        # SCons.Platform.posix SHELL 'sh'->'/system/bin/sh'（无则 noop）
PkgConfigDeps(self).generate()
self._ensure_gio_unix_pc()       # 缺失 component 的 .pc 派生（见 notes.md §1.5）
self.buildenv_info.append_path("PKG_CONFIG_PATH", self.generators_folder)
VirtualBuildEnv(self).generate()

# build()：
PYTHONPATH=<build_folder>/_scons_env PKG_CONFIG_PATH=<generators_folder> \
  python3 -m SCons -j1 CC=<conf c> AR=<ar> RANLIB=<ranlib> --without-<可选面...>
```

CC/AR/RANLIB 一律取自 `self.conf["tools.build:compiler_executables"]`（R33，禁裸 shell 变量）。

## 适用边界

- 适用于一切 SCons 工程；`--target` 私有前缀是 R49 合规形态，`--user`/site-packages/PF6 前缀是禁区。
- 构建期依赖 PyPI 社区源可达（gpsd/dxx-rebirth/vixl 同形，CI 已证明可行）。
- OHOS 无 `/bin/sh`，只有 `/system/bin/sh`；SCons posix 平台的 `SHELL='sh'` patch 必须保留
  "目标串不存在即 noop" 写法，防上游版本变动。

## 关联

- 配方：`archives/r/rmlint/2.10.3/conanfile.py`；笔记 §1.1/§1.3/§2
- 兄弟知识：DRAFT-10175-RMLINT-GETPWUID-NULL-NO-PASSWD-DB-SEGFAULT（同包实测的运行期拦路虎）
