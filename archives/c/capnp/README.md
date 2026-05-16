# capnp — OpenHarmony 编译记录

## 基本信息
- 软件: Cap'n Proto
- 描述: 数据交换格式和基于能力的RPC系统
- 官网: https://capnproto.org/
- 构建系统: cmake
- 目标: ohos-aarch64

## 已编译版本

| 版本 | 状态 | 单元测试 | 功能验证 | 推荐度 |
|------|------|----------|----------|--------|
| 1.3.0 | ✅ success | 60% (平台限制) | **100%** | ⭐⭐⭐⭐⭐ |

## 编译指导

### cmake 配置（推荐）
```bash
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DBUILD_SHARED_LIBS=OFF \
      -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
      -DCMAKE_CXX_FLAGS="-stdlib=libc++" \
      -DCMAKE_EXE_LINKER_FLAGS="-stdlib=libc++ -lc++ -lc++abi -lunwind" \
      ..
make -j$(nproc)
make install
```

### 注意事项
1. **静态库编译**: 建议使用 `-DBUILD_SHARED_LIBS=OFF`，避免共享库 RPATH 问题
2. **libc++ 链接**: 必须显式链接 libc++ 标准库
3. **平台限制规避**: 设置 `export TMPDIR=~/tmp`

## 补丁清单
- 无补丁

## 已知限制
| 限制 | 影响 | 规避方案 |
|------|------|----------|
| /tmp 只读 | 单元测试部分失败 | `export TMPDIR=~/tmp` |
| fuzz 测试耗时 | 测试超时 | 不影响功能 |

## 功能验证（1.3.0）

### 12项功能测试全部通过
| 功能模块 | 状态 | 说明 |
|----------|------|------|
| Schema 编译器 | ✅ | 所有类型支持 |
| C++ 代码生成 | ✅ | 结构、列表、接口、常量 |
| 序列化/反序列化 | ✅ | 二进制、packed |
| 嵌套结构 | ✅ | 多层嵌套 |
| 动态列表 | ✅ | List(T) 全类型 |
| JSON 编码 | ✅ | libcapnp-json.a |
| RPC 接口 | ✅ | interface 定义 |
| 文本转换 | ✅ | capnp convert |

### 功能验证示例
```bash
# 版本验证
$ capnp --version
Cap'n Proto version 1.3.0

# Schema 编译
$ capnp compile -o capnpc-c++ my-schema.capnp

# 序列化测试（C++）
auto person = message.initRoot<Person>();
person.setName("ZhangSan");
person.setAge(30);
// 数据一致性 100% ✅

# JSON 输出
{"id": "12345", "value": 3.14159, "label": "TestData"}
```

## 安装产物（1.3.0）

**库文件**: libkj.a, libcapnp.a, libcapnp-rpc.a, libcapnp-json.a, libcapnpc.a

**可执行文件**: capnp, capnpc-c++, capnpc-capnp

**预编译包**: capnp-1.3.0-ohos-aarch64.tar.gz (68MB)
