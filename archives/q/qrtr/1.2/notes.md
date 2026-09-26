# qrtr 1.2 适配笔记

## 构建环境

- 构建系统：Meson（上游仓库自带 `meson.build`）
- 设备：HarmonyOS 6.1 aarch64（OpenDesk）
- Conan：2.30.0
- 编译器：OHOS clang 15.0.4
- 外部依赖：无（`libqrtr` 只链接 libc）

## 适配过程

1. 从上游 GitHub tag `v1.2` 获取源码，校验 SHA256。
2. `systemd-service` 特性显式设为 `disabled`：鸿蒙 PC 没有 systemd，
   保持默认 `auto` 会让 Meson 去探测 systemd 依赖。
3. `qrtr-ns` 上游默认 `auto`（不编译），本配方显式 `enabled`，
   与 `qrtr-cfg`、`qrtr-lookup` 一起交付。
4. Conan 的 `MesonToolchain` 不写 `ar`/`ranlib`，Meson 按裸名探测
   `llvm-ar` 会失败（OHOS clang 目录不在 PATH 上）。`generate()` 从
   `tools.build:compiler_executables` 的 c 编译器目录推导
   `llvm-ar`/`llvm-ranlib` 全路径写入 `conan_meson_native.ini`。
5. 打包时执行 `meson install`，并单独收集 `LICENSE`。
6. OHOS 的 `sys/socket.h` 与 `linux/socket.h` 都定义了 `struct sockaddr_storage`：
   `libqrtr.h` 直接包含 `linux/qrtr.h`，`src/ns.c`、`src/addr.c`、`src/cfg.c` 还包含
   `linux/netlink.h`、`linux/rtnetlink.h`，它们都会间接拉入 `linux/socket.h`，于是和
   `sys/socket.h` 的定义撞车，报 `error: redefinition of 'sockaddr_storage'`。
7. 补丁只覆盖项目内的 `linux/qrtr.h`，`socket.h` 仍由系统提供。QRTR 头直接包含
   `<linux/types.h>`，并用 `unsigned short` 声明 family 字段；不会 shadow 或占用系统
   `linux/socket.h` 的 include guard，也没有使用平台条件分支。
8. `struct qrtr_ctrl_pkt` 使用 `__attribute__((packed))` 保持与内核 UAPI 相同的线格式，
   避免 OHOS 工具链缺失裸 `__packed` 宏时把后续 token 解析成全局变量。

## 上游测试

上游 1.2 发布包内**没有测试套件**：

- 仓库中不存在 `tests/` 目录；
- `.github/workflows/ci.yml` 与 `ci/*.sh` 只做构建（`meson setup` + 编译）；
- 因此不存在可集成的 `make check` / `meson test` 目标。

`test_package/` 因此提供消费者视角的功能测试（见下）。

## 验证结果

- 上游测试：上游无测试套件（已在 `test_package/MANIFEST.yml` 声明）
- 消费者测试：`test_package/test_qrtr.c` 链接安装后的 `libqrtr`（20 条 C 断言全部通过），
  覆盖 QMI 报文编码、报文头解析、双 TLV 往返解码，以及五类异常路径（错误 type、错误 id、NULL 结构体、NULL 输出、报文长度不一致）；
  另含 5 条 UAPI ABI 检查（AF_QIPCRTR、sockaddr_qrtr 尺寸/偏移、packed 控制包尺寸）；
  另校验 `qrtr-cfg`、`qrtr-lookup`、`qrtr-ns` 已安装且可启动
- 源码补丁：1 个（`patches/001-libqrtr-ohos-sockaddr-storage.patch`，`patch_type: portability`），
  提供项目内最小 Linux UAPI 兼容头，解决 `sockaddr_storage` 重定义与 `__packed` 可移植性问题

- QMI 解码是按 `tlv_type` 反查描述符（`find_ei`）：上游 `qmi_response_type_v01_ei` 的两个字段共用 `QMI_COMMON_TLV_TYPE`，编码后合成同一个 TLV，解码时 `find_ei` 永远命中第一个元素，因此该结构体无法按字段往返。这是上游对公共响应头的既定行为；消费者测试改用各自独立 `tlv_type`(0x01/0x02) 的描述符来验证往返，而不是改库。

## 交付物

- `lib/libqrtr.so.1`（含 `libqrtr.so` 开发链接）
- `include/libqrtr.h`
- `lib/pkgconfig/qrtr.pc`
- `bin/qrtr-cfg`、`bin/qrtr-lookup`、`bin/qrtr-ns`
