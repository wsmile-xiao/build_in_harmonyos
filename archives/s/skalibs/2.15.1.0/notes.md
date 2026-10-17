# skalibs 2.15.1.0 适配笔记

## 编译环境
- 构建系统: skarnet 自有 configure+make（非标准 autotools/cmake/meson）
- 编译日期: 2026-08-24
- 编译器: clang/clang++ (OHOS 适配版 conan profile ohos-aarch64)
- 目标平台: OpenHarmony PC aarch64 (native)
- 状态: built (conan-verify 通过，未上传制品仓)

## 源码信息
- 上游: https://skarnet.org/software/skalibs/
- CI 源码包 URL (ghfast.top 镜像): https://ghfast.top/https://github.com/skarnet/skalibs/archive/refs/tags/v2.15.1.0.tar.gz
- SHA256: efa8b213fe341d57c8b7ad087d928b8d3296643a3a1583bf7e7675766bb68b06
- 许可证: ISC
- 无外部依赖 (仅依赖 C 标准库)

## 编译步骤

skalibs 使用 skarnet.org 自有的 configure+make 构建系统，**不是**标准 autotools，
因此 Conan 配方中不能使用 AutotoolsToolchain，而是直接 `self.run()` 调用：

```bash
./configure --prefix={prefix} --disable-shared
make -j1
make install
```

### 设备原生编译验证（已通过）
在设备上手动验证：
```bash
cd /storage/Users/currentUser/tmp/builds/skalibs-2.15.1.0.work
./configure --disable-shared
make -j2   # exit 0，编译成功
```

### sysdeps 自动检测
skarnet configure 会自动检测目标平台的 sysdeps。在 OHOS aarch64 (native) 上
自动检测结果正确，无需手动指定：
- devurandom=yes
- posixspawnearlyreturn=no
- procselfexe=/proc/self/exe
- selectinfinite=yes

conanfile.py 中未手动加 --with-sysdep-* 参数，依赖 configure 自动检测。
如未来出现交叉编译场景导致自动检测失败，可在 configure 参数中追加：
  --with-sysdep-devurandom=yes \
  --with-sysdep-posixspawnearlyreturn=no \
  --with-sysdep-procselfexe=/proc/self/exe \
  --with-sysdep-selectinfinite=yes

### Conan 配方构建
- configure 参数: `--prefix={package_folder} --disable-shared`
- make: `-j1`（遵循 R9，参考 s6 配方）
- make install: 安装到 package_folder
- 产物: lib/libskarnet.a + include/skalibs/*.h

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI 无法直连 skarnet.org / github.com | CI 网络限制 | conandata.yml 使用 ghfast.top 镜像 URL |
| 2 | conan-init 工具未生成配方文件（本地 file:// URL 不匹配） | manifest 中 source.url 为本地路径 | 手动编写 conanfile.py + conandata.yml + test_package/ |

## 依赖版本
- 无外部依赖（仅 C 标准库）

## 验证结果

### conan-verify
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify skalibs 2.15.1.0
```
- G1 配方完整性: ✅ PASS
- G0 预构建风险评估: ✅ PASS
- G2 conan create (干净构建): ✅ PASS
- G3 系统同名库隔离 (R26): ✅ PASS
- G4 产物完整性: ✅ PASS
- conan create: 通过（从干净源码构建成功）
- test_package: 通过（C 测试程序调用 stralloc + bytestr API，6 项断言全部通过）

### test_package 测试内容
测试程序 test.c 实质调用 skalibs API（R34 铁律）：
- stralloc_ready / stralloc_copys / stralloc_cats / stralloc_shrink / stralloc_free
- byte_chr / byte_diff
共 6 项断言，全部通过。

### finish (W3 本地 CI 模拟)
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finish skalibs 2.15.1.0 built
```
- W3 本地 CI 模拟: ✅ PASS (setup.sh + build_and_test.sh 均通过)
- W2 PR 原子性: ✅ PASS (8 文件，无框架文件)
- .ci-result.json: 已写入 (exit_code=0, integrity_hash=f0b7da12290baec2)
- 状态: built (conan-verify 通过，未上传制品仓)

### 踩坑记录
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create: `./configure: inaccessible or not found` | basic_layout 下 self.run() 的工作目录是 build 子目录，不在源码根 | build() 中用 `cd {self.source_folder} && ./configure ...` |
| 2 | conan create: `copy() 'src' and 'dst' arguments must have different values` | make install 已安装到 package_folder (prefix)，package() 中重复 copy 同一目录 | package() 改为 pass (make install 已完成安装) |
| 3 | CI L0d: `test() method has no self.run() call — likely a stub` | test_package 用 cmake.test() 无 self.run() | test() 改为 self.run("./test_skalibs", env="conanrun") |
| 4 | conan test: `IndexError: list index out of range` on self.cpp.build.bindirs[0] | test_package 未用 cmake_layout，bindirs 为空 | 用相对路径 "./test_skalibs" 代替 self.cpp.build.bindirs[0] |
| 5 | W3 junk_check: 其他包的 .orig/.ghfast-bak/.staging-verified 拦截 | junk_check full 模式扫描全仓已跟踪文件 | 提交 skalibs 变更后 junk_check 切换到 incremental 模式，只扫描本 PR 文件 |

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (skarnet configure+make, 静态库) |
| conandata.yml | 源码 URL + SHA256 (ghfast.top 镜像) |
| test_package/test.c | C 测试程序 (调用 stralloc/bytestr API) |
| test_package/CMakeLists.txt | CMake 测试构建 |
| test_package/conanfile.py | 测试包 Conan 配方 |
| test_package/MANIFEST.yml | 上游测试声明 |

## 注意事项
- skalibs 是 s6/execline 等 skarnet.org 软件的基础依赖库
- 构建系统为 skarnet 自有 configure，非 autotools，不能用 AutotoolsToolchain
- 默认静态编译 (R26: 危险库静态编译)
- sysdeps 在 native OHOS 上可自动检测，交叉编译时需手动提供
---

**编译结束**: 2026-08-24 09:49
**最终状态**: built
