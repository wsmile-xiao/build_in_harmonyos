# E725: OHOS/CI 无 protoc-c：protobuf-c 代码生成的预生成交付套路（含 ohpcd protobuf 的 zlib::zlib shim）

> Draft: DRAFT-E725-ohos-protoc-c-pregenerated-pb-c
> 来源：riemann-c-client/1.10.4 适配（2026-09-25，contrib-14160）；同族先例 ocserv 1.5.0

## 现象

上游 autotools 项目在 `.proto` 变更时用 `protoc-c … --c_out` 生成 `*.pb-c.[ch]`，
在 OHOS 构建主机与 CI 上两类失败依次出现：

1. configure 阶段：`You need protoc-c installed and on your path to proceed`
   （`AC_CHECK_PROG([HAS_PROTOC_C], [protoc-c])` 硬错误）；
   或 make 阶段 `protoc-c: command not found`。
   **`conan list -r=ohpcd` 实查：无任何包导出 protoc-c / protoc-gen-c 二进制**
   （protobuf-c/1.5.1 的配方 `package()` 明确 `rmtree(bin/)`，protoc-gen-c 只在
   其自身构建期用于测试夹具）。

2. 试图按 ocserv 1.5.0 先例本机构建 protoc-gen-c 时，CMake configure 报：

```text
CMake Error at .../protobuf/3.17.3/lib/cmake/protobuf/protobuf-targets.cmake:69 (set_target_properties):
  The link interface of target "protobuf::libprotobuf" contains:
    zlib::zlib
  but the target was not found.
```

   根因：**ohpcd protobuf 包的 `protobuf-targets.cmake` 在
   `INTERFACE_LINK_LIBRARIES` 里写了 `zlib::zlib`，但 `protobuf-config.cmake`
   从不 `find_dependency(zlib)`**（包级元数据缺陷，grep 该 config 全文 0 命中）。

## 判定方法（可机器匹配）

1. `command -v protoc-c protoc-gen-c protoc` 三者皆空 + `conan list -r=ohpcd "*protoc*"`
   无导出二进制 → 命中「预生成」分支。
2. `grep -c 'zlib::zlib' <protobuf-config-dir>/protobuf-targets.cmake` ≥1 且
   `grep -c 'find_dependency' <protobuf-config-dir>/protobuf-config.cmake` == 0
   → 命中 zlib::zlib shim 分支。
3. 构建日志出现 `Error relocating … gnutls_*: symbol not found` 或
   `conftest … Error loading shared library libgnutls.so.30`，
   而 `conaninfo.txt` 却写着 `shared=False`
   → 命中「registry 声明与实物不符」分支（gnutls/libgcrypt 实测只打包 .so）。

## 处置建议（完整可复现链）

一次性 bootstrap（落 `$TASK_DIR/pbgen/`，全部命令可在设备直接执行）：

```sh
# 1) 工具环境（protoc + libprotoc + zlib 头库）
cd "$HOME/tmp/riemann-c-client-1.10.4/pbgen"
cat > conanfile.py <<'EOF'
from conan import ConanFile
class Gen(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    def build_requirements(self):
        self.tool_requires("protobuf/3.17.3")
        self.tool_requires("zlib/1.3.1")
EOF
conan install . -pr:h="$HOST_PROFILE" -pr:b="$HOST_PROFILE" -g VirtualBuildEnv -of .
PB=/storage/Users/currentUser/.conan2/p/protoca95317637dbb/p   # conan cache path protobuf/3.17.3:<pkgid>
ZB=/storage/Users/currentUser/.conan2/p/zlib56af09fbb4346/p    # conan cache path zlib/1.3.1:<pkgid>

# 2) zlib::zlib shim（绕过 ohpcd protobuf 包缺陷）
cat > zlibshim.cmake <<EOF
if(NOT TARGET zlib::zlib)
  add_library(zlib::zlib STATIC IMPORTED)
  set_target_properties(zlib::zlib PROPERTIES
    IMPORTED_LOCATION "$ZB/lib/libz.a"
    INTERFACE_INCLUDE_DIRECTORIES "$ZB/include")
endif()
EOF

# 3) 只构建插件（protobuf-c 官方源码 build-cmake，BUILD_PROTOC 默认 ON）
curl -sSL -o protobuf-c-1.5.1.tar.gz \
  https://codeload.github.com/protobuf-c/protobuf-c/tar.gz/refs/tags/v1.5.1
tar -xzf protobuf-c-1.5.1.tar.gz
export PATH="$PB/bin:$PATH"
cmake -S protobuf-c-1.5.1/build-cmake -B build3 \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_CXX_FLAGS="-stdlib=libc++" -DBUILD_PROTOC=ON -DBUILD_TESTS=OFF \
  -DProtobuf_DIR="$PB/lib/cmake/protobuf" \
  -DCMAKE_PROJECT_INCLUDE="$PWD/zlibshim.cmake"
cmake --build build3 --target protoc-gen-c -j4

# 4) 生成 pb-c 源（版本配对：protoc 3.17.3 ↔ protobuf-c 1.5.1）
SRC="$HOME/tmp/riemann-c-client-1.10.4/w0-src"   # 上游 tag 1.10.4 检出树
"$PB/bin/protoc" riemann.proto -I"$SRC/lib/riemann/proto" \
  --plugin=protoc-gen-c="$PWD/build3/protoc-gen-c" --c_out="$PWD/gen"
```

消费方（autotools 项目）三补丁形态（riemann-c-client 1.10.4 实装）：

1. `configure.ac`：protoc-c 硬错误降级 `AC_MSG_WARN`；
2. `Makefile.am`：生成规则改 `cp -f` 随包预生成文件到构建树（保持显式规则，
   out-of-source 也成立）；
3. 补丁新增 `*.pb-c.[ch]`（**patch 新增文件头必须 `--- /dev/null`**；
   conan `strip=1` 对 /dev/null 源补丁会额外吃掉一层路径，此类补丁要
   `strip: 0` 且路径写成根相对——patch_ng 实测 2026-09-25）。

配套（同任务实测的相邻坑，判据见 notes.md 问题表）：

- registry `shared=False` 实为 .so → 构建期给 configure/make/check 注入依赖
  lib 目录 LD_LIBRARY_PATH；test_package 扫描含 .so 的依赖目录补
  `extrasharedlibs` 脚本，且 conan `self.run(env=...)` 逗号字符串是**单文件名**，
  必须传 list：`env=["conanrun", "extrasharedlibs"]`。
- .la 带 `//lib` 残留（E236 族）→ 消费者侧改写（cattle-1.0 先例）。
- mock 拦截型 Check 套件静态链接必 duplicate symbol → 双态构建 + 打包留单态。

## 实例数据

- riemann-c-client/1.10.4：补丁 0001–0005，`make check` 37+2 用例全过，
  安装树 11/11，test_package ctest 1/1，CLI `--help/--version` 目标机 rc=0。
- protoc-gen-c 构建：cmake 目标 100% Built target protoc-gen-c（约 90s，armv8）。
- 生成物：riemann.pb-c.c 725 行 / riemann.pb-c.h 245 行（protobuf-c ≥1.3 兼容窗）。

## 降级方案（fallback）

- 无法本机构建插件时：改走 ocserv 形态——从任何可生成的机器取预生成文件打进
  补丁（本条目第 4 步的生成机可以是 x86 Linux，protobuf-c 生成物与宿主无关）。
- 项目本身放弃 codegen：部分项目（meson fs.exists fallback，ocserv）可在
  `meson.build`/CMake 层加「预生成文件已存在则不调 protoc」分支，补丁面更小。
