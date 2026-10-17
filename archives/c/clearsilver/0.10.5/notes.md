# clearsilver 0.10.5 — HarmonyOS PC Adaptation Notes

## 上游信息
- 仓库: https://github.com/blong42/clearsilver
- 版本: clearsilver-0.10.5 (tag eb9af71, 2007-07-12)
- 许可证: ClearSilver-1.0 (Apache-1.1 derived)
- 构建系统: Autotools (configure.in + Makefile + rules.mk.in)

## 适配改动
- **源码获取**: conandata.yml 使用 GitHub archive `refs/tags/clearsilver-0.10.5.tar.gz` (sha256 20ef815...) 并通过 gh-proxy 提供镜像回退，符合 CI build_and_test.sh 的 GitHub 镜像策略。
- **依赖**: 仅保留 `zlib/1.3.1` (HTML compression `--enable-compression` 默认开启，链接 -lz)。其余 wrapper (python/perl/ruby/java/csharp/apache/wdb) 通过 `--disable-*` 关闭，避免在 OHOS 上引入额外依赖链。
- **配置**: `AutotoolsToolchain` 设置 `--build/--host=aarch64-linux-ohos` (仅当 OS=OHOS 时)，配合补丁后的 config.sub/guess 识别 OHOS triplet。`CONFIG_SHELL` 默认取 env `CONFIG_SHELL`，回退到 `/data/service/hnp/bin/bash` 以兼容 OHOS 无 `/bin/sh`。
- **补丁**:
  - `0001-config-guess-ohos.patch`: 在 UNAME_MACHINE 处理中新增 `aarch64`/`aarch64_be` 映射为 `aarch64-unknown`，使 `config.guess` 在 aarch64 OHOS 上可自检。
  - `0002-config-sub-ohos.patch`: 在 `config.sub` 的 `*local*` 分支后插入 `aarch64-*-linux* | aarch64-*-ohos*` 直通规则，允许 `aarch64-linux-ohos` 通过校验 (旧版 2001 config.sub 不认识 aarch64)。
- **构建**: `autogen.sh` 在 configure 缺失时自动运行；`Autotools.configure()` → `make -j1` → `make -C cs test -j1` (上游回归套件 30+ .cs gold 对比)。采用单作业 `-j1` 满足 HMBS `tools.build:jobs=1` 注入与 OHOS 平台约束。
- **打包**: `Autotools.install()` 安装到 package_folder；静态库场景删除 `*.la/*.so*/*.dylib`，保留 `libneo_*.a` (neo_utl / neo_cs / neo_cgi)，由 Conan 管理静态依赖链 (系统同名库检查不适用，此库非系统同名)。
- **R32/R33 合规**: 平台判断使用 `in ("Linux", "OHOS")`，编译器通过 `self.conf.get("tools.build:compiler_executables")` 获取，不裸用 shell `$CC`。

## 测试
- **上游**: `make -C cs test` 运行 cstest 针对 `test.cs` 等 30+ 模板与对应 `.gold` 基准的 diff 回归 (全部通过则退出 0)。`manifest.yaml` 记录 `cases: 30`。
- **test_package**: CMake 构建 `test.c`，调用 `HDF` (hdf_init/set_value/get_value) 与 `CS` (cs_init/parse_string/render) 实测模板 `Hello <?cs var:Query.var ?>` 条件与变量，断言输出包含预期子串。`MANIFEST.yml` 中 `assertion_count: 12`。

## 验证
- 待 HMBS 真机 `conan create` 实测 (ohos-aarch64 profile, clang 15, libc++)；本地 Windows 无 OHOS 工具链，仅完成配方与补丁静态检查。
- 预期产物: `libneo_utl.a`, `libneo_cs.a`, `libneo_cgi.a` + 头文件 `ClearSilver.h`, `cs/cs.h`, `cgi/*.h`, `util/*.h`。

## 后续
- 若真机发现 `cs_config.h` 中缺 `HAVE_*` 宏 (如 regex/snprintf/mkstemp) 导致编译错误，需追加补丁在 configure 检测后修正。
- 若需共享库版本，可在 `conanfile.py` 增加 `--enable-shared` 并调整 `package()` 的 `*.so` 清理逻辑。
