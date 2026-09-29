# libradsec

RADIUS 协议客户端库，提供 RADIUS 数据包 / 属性值对（AVP）编解码与请求处理，
并原生支持 RadSec（RADIUS over TLS）传输协议。

- 官网: https://github.com/janetuk/libradsec
- 许可证: BSD-3-Clause
- 构建系统: autotools（configure + make + libtool）

## OHOS 适配要点

- `configure.ac` 中的 `AM_CFLAGS` 含 `-Werror`，在 clang 15 上会将众多告警升级为
  错误（E063），需在配方中通过 `extra_cflags` 注入 `-Wno-error=...` 关闭。
- 编译依赖 `libconfuse`（提供 `cfg_init`）与 `libevent`（提供
  `event_core`/`event_extra`）。TLS（RadSec）默认需要 `event_openssl` 组件，
  当前发布流程中该组件不可用，本配方采用 `--disable-tls` 进行基础适配，
  保留完整 RADIUS（UDP/TCP）功能。
- 上游自带单元测试套件 `tests/test-udp`（CUnit 框架，2 个注册用例），需要
  CUnit 测试框架与外部 RADIUS 服务器才能运行，详见 `0.0.5/test_package/MANIFEST.yml`。
