# norm 1.5.9 适配笔记

## 编译环境
- 构建系统: waf（上游 bundled waf 2.0.19；BUILD.TXT / wscript 为权威构建说明）
- 编译日期: 2026-09-04
- 编译器: clang/clang++（ohos-aarch64 profile，aarch64-linux-ohos）
- 状态: built（本地 conan-verify + W3 本地 CI 模拟通过）

## 源码信息
- 上游: NRL NORM（NACK-Oriented Reliable Multicast）
- 官方源码: https://github.com/USNavalResearchLaboratory/norm
- 版本: 1.5.9（v1.5.9 release asset: src-norm-1.5.9.tgz）
- sha256: ef6d7bbb7b278584e057acefe3bc764d30122e83fa41d41d8211e39f25b6e3fa
- 注意: 官方 .tgz 实为普通 tar（非 gzip）；conan get() 用 r:* 自动探测可解

## 编译步骤
1. init-build norm 1.5.9（官方 GitHub release URL）
2. 探索性编译（模式 B，AI 手动）:
   - wscript/protolib wscript 补 platform.system()=='harmonyos' → 'linux' 映射
   - `python3 waf configure --prefix=...` 成功（clang++ 探测、pthread/dl/rt 检查通过）
   - `python3 waf`（61/61 任务成功：libnorm.so.1.5.9 + libnorm.a + libprotokit + normApi.h + norm.pc）
   - OHOS 需 `-D__MUSL__`（E091：OHOS linux/socket.h 与 musl sys/socket.h 均定义
     sockaddr_storage；sys/socket.h 以 #ifndef __MUSL__ 包裹其定义）
3. conan-init 生成配方骨架后重写 conanfile.py 为 waf 驱动（参考 jack 1.9.22 配方）
4. conan create（conan-verify G0–G4 + L2/L4/L5 全过）
5. finish published → W3 本地 CI 模拟通过 → .ci-result.json exit_code=0

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 解压 .tgz 报 "not a gzip file" | 官方 GitHub release 的 src-norm-1.5.9.tgz 实为普通 tar | 本地 gzip 重打包供 init 解压；conan 侧 get() 的 r:* 自动探测原生可解，conandata 用官方 URL+真实 sha256 |
| 2 | waf 平台探测得到 'harmonyos'，未走 linux/unix 分支 | wscript 用 python platform.system().lower() | 两处 wscript（norm + protolib）将 harmonyos 映射为 linux（0001/0002 补丁） |
| 3 | linux/socket.h 与 sys/socket.h 重复定义 sockaddr_storage | OHOS 内核头文件与 musl libc 不一致（E091） | CFLAGS/CXXFLAGS 注入 -D__MUSL__（sys/socket.h 用 #ifndef __MUSL__ 包裹） |
| 4 | copytree 硬链/符号链接环失败 | 源码含 norp/norm -> .. 符号链接环，HMDFS 不支持 os.link | .work 用 `cp -a` 保留符号链接创建；refresh-patch 走 edit-tracker 精确模式 |
| 5 | waf 找不到编译目标版本宏 | - | 无（上游 VERSION 1.5.9 正常从 include/normVersion.h 读） |
| 6 | lang-preflight 判 mixed/env_unsupported（误报） | 仓库根目录有 pynorm 的 setup.py（辅助 python 打包），源统计 cpp 占 85% | 判定为 C/C++ 库继续适配；记录于此避免后续误判 |

## 源码修改（patches/）
- `0001-protolib-wscript.patch`: protolib wscript 平台名 harmonyos→linux 映射（portability，无 __OHOS__ 宏）
- `0002-wscript.patch`: norm wscript 平台名 harmonyos→linux 映射（portability，无 __OHOS__ 宏）

## 依赖版本
- 无外部 runtime 依赖（protolib 随上游 tar 内嵌，对象合入 libnorm）
- 工具链: OHOS clang 15 / llvm-ar / python3（运行 waf）/ conan 2.29.1

## 验证结果
```bash
# conan-verify（G0–G4 + L2/L4/L5）全通过
python3 scripts/ohc-run.py conan-verify norm 1.5.9

# W3 本地 CI 模拟（setup.sh + build_and_test.sh）通过，exit_code=0
# 上游离线自测：fecTest（RS16 FEC 编解码往返）通过
python3 waf build --targets=fecTest && ./build/fecTest   # rc=0，2 轮 erasure 往返 OK

# test_package（真实调用 NORM API）
test_norm  # NormGetVersion + NormCreateInstance + NormDestroyInstance → PASS
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | waf 构建配方（共享/静态均可；OHOS 注入 -D__MUSL__） |
| conandata.yml | 官方 URL + sha256 |
| test_package/test_norm.c | NORM API 消费者真实调用 |
| patches/0001-0002 | 平台名映射补丁 |

## 注意事项
- 该 .tgz 内容包含内嵌 protolib（.gitmodules 指向的 submodule 已随 release 打包）；
  CMakeLists 的 FetchContent 分支在非 git 工作树中不会触发。
- norm 的公开 API 头为 include/normApi.h（waf install 仅安装它），其余 norm*.h 为内部实现头。
- waf build 默认不构建 normapp/示例（posted=True），默认产物仅库 → R38 判为库类型，无 commands.json。
- 构建时通过 VirtualBuildEnv 暴露 profile [buildenv] PATH，CC/CXX/AR/RANLIB 取 profile conf。
---

**编译结束**: 2026-09-04 23:02
**最终状态**: built
