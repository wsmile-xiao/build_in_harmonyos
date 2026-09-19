# osip (libosip2) 5.3.2 — HarmonyOS PC 适配

GNU oSIP 是 RFC 3261（SIP）协议的实现库，包含 libosip2（事务/状态机）与
libosipparser2（SIP 报文解析）两个库，是 eXosip、SIP 网络组件的基础依赖。

## 本归档

- 上游：https://ftp.gnu.org/gnu/osip/libosip2-5.3.2.tar.gz
- 适配版本：5.3.2（首次适配）
- 构建系统：autotools
- 产物：`libosip2.a/.so`、`libosipparser2.a/.so`
- Conan 引用：`osip/5.3.2`（`cpp_info.libs = ["osip2", "osipparser2"]`）

## 适配要点

1. 升级 config.guess/config.sub 并加入 ohos triplet（配合交叉参数）
2. configure 的 umask 077 临时目录在 HMDFS 上改为 022
3. src/test 的 check 目标修复 out-of-source 路径拼接
4. `--enable-test` 构建上游 torture 测试工具并在配方 build() 中真实执行
   （122 条 sip 语料 + 42 条 hgs + 93 条 msgs2，共 257 条全部通过）

## 版本

- 5.3.2：首次适配（详见 5.3.2/notes.md）
