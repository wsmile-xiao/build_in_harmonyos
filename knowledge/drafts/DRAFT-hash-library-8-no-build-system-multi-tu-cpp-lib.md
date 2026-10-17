# DRAFT-hash-library-8-no-build-system-multi-tu-cpp-lib — 无构建系统多 TU C++ 库（多个 .cpp 实现 + .h + CLI 示例）custom 配方：逐 TU 循环编译 + 静态库 + CLI 双产物 + R38 commands.json

- 触发事件：hash-library 8（stbrumme/hash-library，tag hash_library_v8）首轮适配。
  上游为纯 C++ 源码库：6 个算法实现（crc32/md5/sha1/sha256/sha3/keccak 各
  .cpp+.h 配对）+ hmac.h/hash.h 模板头 + digest.cpp CLI 示例工具 + tests/，
  **无任何构建系统**（无 configure/make/CMake/meson）。
- 路径：Path B（知识库扩展）
- 编号：DRAFT-hash-library-8-no-build-system-multi-tu-cpp-lib

## 现象

conan-init 按 autotools 模板生成配方（configure + make），但上游没有 configure
脚本和 Makefile。与 DRAFT-hashmap-0.8.1（单 TU C 源库）不同，本库是**多翻译单元
（6 个 .cpp）C++ 库**且附带 **CLI 示例工具**（digest.cpp，R38 要求 commands.json
声明）——hashmap 草稿的 affected_scope 明确排除多 TU 形态，且无 CLI 交付维度。

## 根因

1. 无构建系统的多 TU C++ 库被 conan-init 误判为 autotools → configure 阶段必败。
2. 与单 TU（hashmap）形态差异：需要**循环编译多个 .cpp 实现**并归档，而非单文件直编。
3. 与纯 header-only（E257）形态差异：实现体在 .cpp（不在头文件），不能 no-op build，
   必须编译实现 TU，否则下游链接缺符号。
4. 附带 CLI 示例工具时，库+工具双产物需分别处理：库进 lib/，工具进 bin/ 并声明
   commands.json（R38），"文件仅存在于 worktree 而未进入 PR 是交付失败"。

## 修复（已在本轮验证）

conanfile.py 四要素（多 TU custom 配方）：

```python
package_type = "library"
settings = "os", "compiler", "build_type", "arch"
options = {"shared": [True, False]}
default_options = {"shared": False}

def build(self):
    comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
    cxx = comp.get("cpp", "clang++") if comp else "clang++"
    ar, ranlib = "llvm-ar", "llvm-ranlib"
    workdir = self.source_folder   # R392/E392: 源码在 source_folder，self.run 必须 cwd
    for impl in ["crc32", "md5", "sha1", "sha256", "sha3", "keccak"]:  # 逐 TU 循环编译
        self.run(f"{cxx} -fPIC -O2 -std=c++17 -c {impl}.cpp -o {impl}.o", cwd=workdir)
    self.run(f"{ar} rcs libhash-library.a crc32.o md5.o sha1.o sha256.o sha3.o keccak.o", cwd=workdir)
    self.run(f"{ranlib} libhash-library.a", cwd=workdir)
    # CLI 双产物
    self.run(f"{cxx} -fPIC -O2 -std=c++17 digest.cpp crc32.cpp md5.cpp sha1.cpp "
             f"sha256.cpp keccak.cpp sha3.cpp -o digest", cwd=workdir)

def package(self):
    copy(self, "libhash-library.a", src=self.source_folder,
         dst=os.path.join(self.package_folder, "lib"))     # 绝对路径（DRAFT-cmrc）
    copy(self, "*.h", src=self.source_folder,
         dst=os.path.join(self.package_folder, "include"))
    copy(self, "digest", src=self.source_folder,
         dst=os.path.join(self.package_folder, "bin"))
    copy(self, "LICENSE", src=self.source_folder,
         dst=os.path.join(self.package_folder, "licenses"))

def package_info(self):
    self.cpp_info.libs = ["hash-library"]
    self.cpp_info.bindirs = ["bin"]     # CLI 交付 → R38 commands.json 必须声明
```

配套（软件级目录 `archives/h/hash-library/commands.json`，R38）：

```json
{
  "name": "hash-library",
  "type": "tool",
  "versions": { "8": { "ref": "hash-library/8", "binary": false } }
}
```

## 验证（已在本轮实测）

- conan-verify hash-library 8：G0-G4 + L2/L4/L5 全 PASS；conan create 干净构建成功。
- test_package 消费者（test_consumer.cpp 调用 SHA256/MD5/SHA1/CRC32/SHA3/Keccak/
  HMAC 已知向量 + 流式 API）：1/1 Passed。
- 上游测试 3/3：tests.cpp 主套件（100 组向量 + SHA/HMAC 系列）all tests ok；
  github-issue2/issue6 rc=0。
- OHOS 专项 tests-ohos/ohos_test.cpp：14 项断言全 PASS（含 1MB NIST 向量、流式分块、
  HMAC RFC2202/4231、getHash 幂等）。
- digest CLI：`./digest readme.md --sha256` 与 sha256sum 一致。

## 边界/反例

- 适用：无构建系统、多翻译单元（>1 个 .cpp）C++ 库，可附带 CLI 示例；OHOS/aarch64 +
  Conan 2.29.1 + clang 15。
- 反例：单 TU C 库走 DRAFT-hashmap-0.8.1；纯 header-only 走 E257；有 Makefile 走
  E392 raw-makefile；stb 单头实现走 DRAFT-enet。
- 单字符版本（"8"→set_version "v8"）等通用问题复用 DRAFT-strong_type-9 草稿，不在
  本条重复。

## 关系

- similar_to: DRAFT-hashmap-0.8.1-no-build-system-single-tu-lib（同族 custom 直编，
  差异：TU 数量、语言、CLI 双产物 + commands.json）
- similar_to: E392 raw-makefile-conan-recipe-pattern（compiler dict / cwd / copy 共享）
- similar_to: DRAFT-cmrc-2.0.1（copy 绝对路径）
- conflicts_with: 无；prerequisite_of: 无