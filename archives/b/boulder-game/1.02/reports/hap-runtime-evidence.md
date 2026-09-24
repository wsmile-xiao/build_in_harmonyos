# HAP C++ 运行库故障与修复证据

## 失败实例（2026-09-15）

原始真机 hilog 摘录（PID 60096，应用 com.kasumizawamiyuu.boulderhost）：

```text
09-15 12:59:47.960 MUSL-LDSO: load libc++_shared.so failed, namespace=ndk no inherits, errno=2
09-15 12:59:47.960 MUSL-LDSO: load libc++_shared.so failed, namespace=moduleNs_default, errno=2
09-15 12:59:47.960 MUSL-LDSO: Error loading shared library libc++_shared.so: (needed by /data/storage/el1/bundle/libs/arm64/libboulderhost.so)
```

旧成品 HAP 只含 libboulderhost.so 和 libeditorhost.so。首页可打开，进入原生游戏失败。此前 Conan 通过不足以证明 HAP 运行环境可用。

## 修复与重建（2026-09-20）

CMake 从实际 C++ 编译器查询 libc++_shared.so，保留 SDK native NOTICE，安装到工程 entry/libs/arm64-v8a；消费者检查运行库与 NOTICE。干净 Conan 构建和消费者测试通过。

实测成品引用：`boulder-game/1.02@ohpcd/stable#503dd32c9e51e16cbfb1d828c9f149f5:3a4ed3ccc950041ac22b55893315c0cd87789c52#338825b7e094899ad9d16909681cb1a4`。

从此 Conan 包中的 harmony-project 复制构建工程，仅补用户私有调试签名，DevEco assembleHap 成功。HAP 最终包含：

```text
libs/arm64-v8a/libboulderhost.so
libs/arm64-v8a/libeditorhost.so
libs/arm64-v8a/libc++_shared.so
```

HAP SHA256：`958b53f17ebb0c4408e25d2deeee61a052fd4e55956f6600f9882e3cb6590a9e`。
Hvigor 执行 DoNativeStrip，因此完整 ELF 哈希不同。对比 Conan 原库/HAP 中库所有 SHF_ALLOC 节的名称、类型、地址、大小和内容哈希，boulderhost 23节、editorhost 23节、libc++ 24节全部一致。SHT_NOBITS 比较类型/地址/大小。明细见 hap-artifact-evidence.json，不将完整文件哈希描述为相等。

## 真机结果

安装成功；Enter 进入关卡；Right 后角色右移一格；游戏→首页→编辑器→首页→游戏后进程 PID 始终11637；编辑器仍显示之前保存的钻石。前期用户确认过背景音乐，本轮未重复听感断言。截图摘要与哈希随 JSON 留存，原图由操作者保留。

## 自动门禁与范围

官方 finish W3 本地 CI 返回0；L0/L1/L1e破坏性负例/L2/L5通过，L4提示为 JSON targets 字段误命中 gets 子串。官方日志把新增 CTest泛称“upstream tests”，实际为适配新增测试，上游用例数为0。独立 conan-verify 的 package ID解析导致L2/L4/L5跳过，与后来 W3 实际执行结果分别记录。

旧式 G0 检查错误地执行不存在的 ./configure，失败保留，不当作成功证据；实际构建为 CMake+Conan。知识整理 step5b 存量草稿完整性提示不代表当前功能失败；本次只提交一条完整 Boulder 草稿。
