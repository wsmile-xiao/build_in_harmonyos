# mtxclient 0.10.1 — HarmonyOS PC 适配可行性分析

> 任务类型：A 类（前置适配）；本报告按「阻塞点分析」口径产出，可直接用于任务记录 / PR 正文。
> 分析日期：2026-09-29
> 分支：`feat/mtxclient-0.10.1`
> 结论：**可适配（配方就绪，待设备构建）** —— 配方、补丁、test_package 与依赖声明已完成并通过本机静态验证；
> W0 依赖全部已发布；设备 `conan create` 待空闲窗口执行。

> ⚠️ **本报告已修订**。初版曾判定「W0 阻塞：coeurl 未发布」，该结论**错误**，根因是初次 W0 用了
> `conan download` 的**退出码**作为判据：该命令在打印 `No packages found for this revision` 时
> 仍可能 exit 0。改用 `conan graph info` 读 `binary` 字段后确认 coeurl/0.3.2 制品已在 ohpcd。
> 修订内容见 §2 阻塞点 1。

## 1. 目标与现状

| 项目 | 值 |
|------|-----|
| 库 | mtxclient（Matrix 客户端-服务器 API 库，Nheko 使用） |
| 版本 | 0.10.1（上游 2025-08-02） |
| 源码 | `https://github.com/Nheko-Reborn/mtxclient/archive/refs/tags/v0.10.1.tar.gz` |
| sha256 | `203be46a08e1dc6cfc068d0911f3b09976f48e4cc4302c3517b9c0f4e53631e3` |
| 构建系统 | CMake（C++20） |
| 产物类型 | 库（无 bin/ → R38 不需要 commands.json） |
| 归档状态 | `built`（验证配方就绪；设备构建待窗口） |

## 2. 阻塞点

### 阻塞点 1（已解决）：曾经以为 coeurl 未发布 —— 实为验证方法错误

**现象**：初次 W0 用 `conan download coeurl/0.3.2 -r=ohpcd --only-recipe` 判断，重试多次
仍失败，于是判定「coeurl 未发布 → 本库 blocked」。

**根因（两个叠加）**：

1. `conan download` 在远端只找到 recipe、没有匹配 binary 时会打印
   `packages: No packages found for this revision`，**但仍然 exit 0**；
   反过来，网络/网关抖动时会返回 `error:system acceleration policy not enabled` 并 exit≠0。
   即**退出码与输出文本都不是可用性判据**。
2. 仓库里的两个 preflight 工具（`ci/scripts/preflight_check.sh`、`scripts/ohc/preflight.py`）
   走制品仓 search API，而 R35 已明确指出该 API 对 binary 返回不完整。

**复测（R35 正确落地方式）**：

```sh
conan graph info --requires=coeurl/0.3.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<build-profile> -f=json
# → coeurl/0.3.2 ... binary: Cache
conan install --requires=coeurl/0.3.2 ...   # → Install finished successfully
```

**结论**：`coeurl/0.3.2` 的 recipe 与 OHOS aarch64 制品**都在 ohpcd**；
其归档目录尚未合入 main，但不影响本库构建（依赖按 ref 解析，不读 main 目录）。
本库不含任何 W0 阻塞。

**方法学教训（已写入 manifest.knowledge_gained）**：判断依赖是否可用必须读
`conan graph info` 的 `binary` 字段，不能用 `conan download` 的退出码，也不能依赖 search API。

### 阻塞点 2（真阻塞，已解决）：OHOS 镜像没有 pkg-config

**缺什么**：`pkg-config` / `pkgconf` 可执行文件。

**证据（设备实测）**：

```sh
command -v pkg-config   # → 未找到
command -v pkgconf      # → 未找到
ls /data/service/hnp/bin | grep -i pkg   # → 空
```

**为什么是硬阻塞**：mtxclient 的 `CMakeLists.txt` 有 5 处
`pkg_check_modules(... REQUIRED ...)`（re2 / libevent_core / libevent_pthreads / libcurl / coeurl），
补丁 0002 又新增 `pkg_check_modules(gtest_main ...)`。CMake 的 `FindPkgConfig` 模块找不到
可执行文件就 FATAL（`Could not find PkgConfig`），configure 直接失败。

**处置**：配方以 `tool_requires("pkgconf/3.0.6")` 引入实现（ohpcd 已发布，含 OHOS aarch64 制品
`bin/pkgconf`），并在 `generate()` 里把绝对路径写进 `PKG_CONFIG_EXECUTABLE`
（该包只装 `bin/pkgconf`，没有 `pkg-config` 这个名字，所以显式固定路径比依赖 PATH 更稳）。

### 阻塞点 3（运行期能力缺口，未解决，不在本 PR 范围）：ohpcd `libcurl/8.5.0` 无 TLS 后端

**缺什么**：带 TLS 后端（OpenSSL）的 libcurl 制品。

**证据**：

- `libcurl/8.5.0` 的 `conaninfo.txt` 只有 `[requires] zlib/1.3.1.1`，**没有 openssl**；
- 包内 `lib/libcurl.so` 的 DT_NEEDED 仅 `libc.so`；
- coeurl 适配会话独立记录了同一结论（`https 运行时返回 CURLE_UNSUPPORTED_PROTOCOL=1`）。

**影响**：mtxclient 可以正常编译、链接与通过全部离线 API 测试，但**任何真实 Matrix homeserver
通信都是 HTTPS**，运行期会得到 `CURLE_UNSUPPORTED_PROTOCOL`。即：本包可作为下游应用适配的
编译/链接基线，但端到端联网能力受该依赖限制。

**不处理的原因**：这是依赖库自身的制品能力问题。按工作流 §3.1「依赖缺失先拆依赖库单独适配」，
应作为 `libcurl` 的独立任务；在本库 PR 里绕过（例如内置一份 TLS curl）会掩盖依赖缺口。

### 非阻塞问题（已用补丁解决）

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| `find_package(Olm 3.2.7)` / `Olm::Olm` 找不到 | libolm 3.2.x 自身安装 `olm-config.cmake`；ConanDeps 按包名生成 `olm-config.cmake` + `olm::olm`，配方未声明 `cmake_target_name` | patch 0001 降为小写 |
| `GTest::GTest` / `GTest::Main` 找不到 | googleTest 1.13 改名、1.14 删除旧目标名；ohpcd gtest/1.17.0 只提供 `GTest::gtest` / `GTest::gtest_main` | patch 0002 改用包内 `gtest_main.pc`（pkg-config 单一导入目标） |

其余探测全部命中（`OpenSSLConfig.cmake`、`nlohmann_json-config.cmake`、`spdlog-config.cmake`、
`re2.pc`、`libevent_core.pc`、`libevent_pthreads.pc`、`libcurl.pc`、`coeurl-config.cmake`、`gtest-config.cmake`），
逐项对照见 `reports/local-validation.md` §5。

### 待设备确认的风险

| 风险 | 说明 |
|------|------|
| clang 15 / libc++ 对 C++20 的完整度 | 库需要 `std::strong_ordering` + `operator<=>`；profile 的 cppstd=17 已被配方覆盖为 20 |
| CMakeDeps 传递依赖数据缺口（E216 同族） | 配方已按 coeurl 的做法把各依赖 include/lib 目录补进 `cpp_info.includedirs`/`libdirs` 并补 `LD_LIBRARY_PATH` |
| 设备 conan 入口 | 无 console script，`python3 -m conan` 不可用；`import conan` = 2.31.1（文档基线 2.29.1） |
| 9 个 nonetwork 上游用例的通过率 | 需设备构建 |

## 3. 已验证方案与结果

| 验证项 | 命令 | 结果 |
|--------|------|------|
| 源码校验值 | `sha256(tar.gz)` | 与 conandata.yml 一致 |
| 配方语法 | `python -m py_compile conanfile.py test_package/conanfile.py` | pass |
| YAML 解析 | `yaml.safe_load(conandata.yml / MANIFEST.yml / manifest.yaml)` | pass |
| 依赖图无冲突 | `conan graph info ... -f=json` | 15 节点，`graph.error=None`，无节点 error |
| **依赖发布状态** | **`conan graph info --requires=<ref>` 读 `binary` 字段** | **11 个 ref 全部 Cache（含 coeurl/0.3.2、pkgconf/3.0.6）** |
| 补丁可复现 | `git apply --check` × 2（对全新下载源码，顺序） | 均 exit 0；合并 18 insertions / 33 deletions |
| CMakeDeps/PkgConfigDeps 产物名对齐 | 本机 `conan install` 生成实际产物核对 | 12 项探测逐项对齐 |
| 本机 CI 门禁复刻 | `python _w0probe/local_gates.py` | 48 项检查，0 失败 |
| test_package API 真实性 | 逐个核对上游头文件签名/命名空间 | 36 项断言，24 处 `mtx::` API 引用 |
| 设备连通性与工具链 | SSH + 上传探针脚本 | 可达；**系统无 pkg-config**（已由 pkgconf tool_requires 解决） |

**未验证**：`conan create`、上游 9 个 nonetwork 用例、产物 SONAME/RPATH/NEEDED、安装后 CMake 包可消费性
—— 全部依赖设备；设备在会话期间处于他人构建负载下（load ≈ 22、fork 失败），按错峰规则未抢占。

## 4. 下一步命令

前置条件已满足（W0 全部依赖在 ohpcd 有 OHOS 制品），只差设备空闲窗口。

```sh
# 0) 设备侧准备：把本分支同步到隔离 job
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user "$USER" --job mtxclient-010 \
  --package archives/m/mtxclient/0.10.1 \
  --repo-source "$HOME/validation/build_in_harmonyos"
. "$HOME/ohos-users/$USER/mtxclient-010/env.sh"
export PATH="$HOME/usr/local/bin:/data/service/hnp/bin:$PATH"

# 1) 单包 shadow CI（推荐，单包排队）
sh "$HOME/bin/run-ohos-shadow-ci.sh" "$CI_PACKAGES"

# 2) 等价的 CI 定向验证
CI_PACKAGES="archives/m/mtxclient/0.10.1" zsh ci/conan/build_and_test.sh

# 3) 手工 conan create
conan create archives/m/mtxclient/0.10.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

预期：`Build Summary` `Total: 1`、L0/L1 pass、ctest 执行 9 个 nonetwork 用例全通过（6 个 network 用例不执行）、
`ci-metadata.json` 与日志一致。

首次真机启动前的检查清单见 `notes.md` §六（`settings.yml` 认识 OHOS、编译器路径存在、
`TMPDIR`/`TMPPREFIX` 可写、PATH 与 conan 入口、pkgconf 由工具链提供）。

## 5. 结论

- 本库**可适配**：没有任何缺失的系统接口或不可实现的平台能力。
  三个"缺口"分别是——一个**验证方法错误**（误判 coeurl 未发布，实为已发布）、
  一个**环境缺失已解决**（系统无 pkg-config，改由 `tool_requires("pkgconf/3.0.6")` 提供）、
  一个**依赖制品能力限制**（libcurl 无 TLS，属依赖库自身任务，不影响编译与链接）。
- 配方层面该做的适配工作已经做完并通过离线可验证的全部门禁；
  剩余工作只有**设备构建验证**，不是重新设计适配方案。
- 状态标记 `built`（配方与静态门禁通过），**不标 `published`**（R29：`conan_verify` 通过才可标 `published`）。
