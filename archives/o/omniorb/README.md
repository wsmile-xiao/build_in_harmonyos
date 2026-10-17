# omniORB

高性能 CORBA 2.6 ORB（C++）：ORB 运行时库、omniidl IDL 编译器与 omniNames 命名服务。

## 版本
- 4.3.4 (2026-01-05 上游发布)

## 用途
- CORBA 分布式对象通信（C++ 语言映射）
- IDL 编译（omniidl 生成 C++ stub/skeleton）
- COS 命名服务（omniNames）

## 产物
- 库：libomniORB4、libomnithread、libomniDynamic4、libomniCodeSets4、libCOS4、libCOSDynamic4（各含 static + shared）
- 工具：omniidl、omniNames、catior/convertior/genior、nameclt
- 头文件：omniORB4/、omnithread/；IDL 文件：share/idl

## OHOS 适配
- 自带 config.sub 为 2001 版，不识别 aarch64/ohos，已打补丁接受 `aarch64-unknown-linux-ohos`（E007 模式）
- 构建需要 Python 3（omniidl 后端），其余零 conan 依赖；OpenSSL 缺席时 SSL 传输自动关闭
- 上游无测试套件（无 tests/ 目录、无 check 目标），适配测试为消费者视角：omniidl 代码生成 + 同进程 Echo 调用

## 安装
curl install.sh | sh -s -- omniorb 4.3.4

## 验证
omniidl -bcxx echo.idl && ./test_echo

## 参考
- 官网: https://omniorb.sourceforge.io/
- 源码: https://sourceforge.net/projects/omniorb/files/omniORB/omniORB-4.3.4/
