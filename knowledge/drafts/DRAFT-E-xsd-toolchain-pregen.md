# DRAFT-E-xsd-toolchain-pregen: CodeSynthesis XSD 工具链预生成方案

## 场景

依赖 CodeSynthesis XSD 代码生成器的库（libkolabxml 等）在交叉编译 CI 上：

```
-- Could NOT find XSDCXX (missing: XSDCXX XSDCXX_INCLUDE_DIRS)
```

xsdcxx（xsd → C++ bindings 生成器）和 xsdbin（schema → grammar 数组编译器）
是 host 工具：制品仓没有 xsd 包、官方预编译二进制只有 x86_64、CodeSynthesis
已于 2014 年停止维护（4.0.0 末版）。

## 方案（三步）

### 1. 本机编译 xsdcxx/xsdbin（OHOS arm64）

```bash
# xsd-4.0.0+dep.tar.bz2（官方一体包，含 libcutl/libxsd-frontend/build2）
# 两个坑先修：
#  a) 组件目录无扩展名 version 文件 ↔ libc++ <version> 头冲突
#     （新版 libc++ 无条件 include <version>）→ mv version version.txt
#  b) libxsd-frontend/.../elements.cxx 的 operator<<(wostream&, Path)：
#     path.string() 是 char 串，逐字符 widen：
#     std::string const& s(path.string());
#     std::wstring ws(s.begin(), s.end()); return os << ws;

make CXX=clang++ CC=clang \
  CXXFLAGS="-O2 -std=c++14 -I<conan-xerces>/include" \
  LDFLAGS="-L<conan-xerces>/lib" \
  LIBS="-lxerces-c -lc++ -lc++abi -ldl -lpthread" -j4

# 运行时 LD_LIBRARY_PATH 指向 SDK libc++_shared.so
```

### 2. 预生成（命令对齐上游 CMakeLists + --std c++11）

```bash
xsdcxx cxx-tree --std c++11 --generate-polymorphic \
  --generate-serialization --namespace-map http://kolab.org=KolabXSD \
  --root-element icalendar --root-element vcards --root-element note \
  --root-element configuration --root-element file \
  --output-dir bindings/ <7 个 .xsd>

xsdbin --array-name iCalendar_schema --output-dir . <7 个 .xsd>
```

**--std c++11 必加**：默认（c++03）生成的代码 `using dom::auto_ptr`，
与 XSD_CXX11 模式的 libxsd 头不匹配（编译错 no member named 'auto_ptr'）。

### 3. 配方集成

- patches/bindings/（14 个生成文件）+ patches/kolabformat-xcal-schema.cxx
  + patches/libxsd/（header-only runtime，106 个 .hxx）
- conanfile build()：copy 进源码树
- CMakeLists patch：XSDCXX 不可用时 copy 预生成文件（保留原命令 fallback）
- 编译宏：`-DXSD_CXX11 -DXSD_CXX11_TEMPLATE_ALIAS -DXSD_CXX11_NULLPTR`
  （clang-on-OHOS 伪装 GCC 4.2，TEMPLATE_ALIAS 不自动推导）

## 验证

- libkolabxml 1.2.1 OHOS arm64 conan create 全绿
- 上游测试 84/84（bindingstest 27 + conversiontest 39 +
  kolabconversationtest 4 + parsingtest 3 + validationtest 11）

## 兜底

无 OHOS 本机环境时在任意 Linux x86_64 编译 xsdcxx——预生成产物是纯 C++
源码，平台无关。
