# DRAFT-boost-headeronly-vendor-meson-boostroot-staging：ohpcd boost 裁剪缺 header-only 组件的补齐三步法

> Contributor: sea_crab | Status: Draft | Updated: 2026-08-29
> Source: bali-phy 4.1 HarmonyOS PC adaptation（patch 0001 + patches/boost-extra 183 头）
> 对应：knowledge/drafts/DRAFT-boost-headeronly-vendor-meson-boostroot-staging.kv

## 现象

ohpcd/OHOS curated boost 配方用 `BOOST_INCLUDE_LIBRARIES` 只安装精选头文件子集，
**未安装 `boost/json`、`boost/uuid`、`boost/convert`、`boost/rational`、`boost/compute`
任何 header-only 组件**，也没有配方导出 `Boost::json`。bali-phy 硬依赖
`<boost/json.hpp>`（src/util/json.hh、src/mcon/mcon.H），还含 `<boost/convert.hpp>`、
`<boost/rational.hpp>`、`<boost/compute/detail/sha1.hpp>`。缺头直接编译失败：

```text
fatal error: 'boost/json.hpp' file not found
```

meson 还要能解析 program_options/random/system/chrono/json 五个 boost 模块，
缺 `version.hpp` 所在的 boost 根会报 `Dependency ... not found`。

## 与现有知识的关系（确认去重证据）

检查范围：knowledge/graph + knowledge/drafts（本分支 HEAD 423 文件）+ 经验仓
ophs_ci_review（HEAD=1715154b，工作树干净）。
检索词：boost / boost.json / boost/json / header-only / vendor / boost_root /
boost-bundle / src.hpp / uuid / convert / rational / compute。
graph 面 E035/E099/E153 为 b2/bjam 检测，不相关；**E217-draft-4AC2** 最相近但
机制不同：它面向 boost **编译库**裁剪模块补全（interprocess/locale/asio/charconv，
手工编译 libboost_locale.a + .pc prefix=/ + meson 平台映射），本条目面向
**header-only 组件**（json/uuid/convert/rational/compute 逐字 vendor + 单 TU
src.hpp + meson boost_root staging bundle）；drafts 面 E331-draft-C898
（epoll-shim header-only INTERFACE）非 boost；全树 boost_root/boost-bundle/
boost/json = 0 命中。无覆盖。

## 知识库沉淀价值

- 可复用问题类别：ohpcd/OHOS curated boost 只装精选头，库硬依赖 header-only
  boost 组件（json 等）时如何不污染上游配方地补齐。
- 适用对象：任何需要 `boost/json`（或其它 header-only boost 组件）的 OHOS 库
  （现代 C++ 项目常用 Boost.JSON）。
- 决策价值：给出标准三步（逐字 vendor + 官方单 TU `src.hpp` + meson
  `boost_root` staging），与既有 E217（编译库裁剪补全）形成互补；"恰一个 TU
  包含 src.hpp"可避免重复定义陷阱。

## 方案

1. **逐字 vendor**：在配方 `patches/boost-extra` 内 vendor Boost 1.91 缺失的
   header-only 头（json+uuid+convert+rational+compute，183 个文件，BSL-1.0，
   注明无 OHOS/musl 修改；不改任何 boost 配方）。
2. **官方单 TU 实例化**：新增 `src/util/boost-json-src.cc`（`#include
   <boost/json/src.hpp>`），注册进 `libutil_sources`——所有可执行文件与 builtins
   模块都链 libutil，json 符号全局可解析。
3. **meson boost_root staging**：`generate()` 搭最小 meson boost 根
   （boost-bundle：真实 boost 的 version.hpp + vendor 头 + header-only boost/system
   + 编译件 .so 拷贝），经 `tc.properties['boost_root']` 注入，使 meson 五个模块
   全部解析；真实 boost include 目录经 `cpp_args -I` 提供。

## 验证证据

- 最小探针（json+chrono+random+program_options 编译/链接/运行）设备实测通过。
- round-2~round-6 多轮全量构建通过；权威 round-6 CI 218/218 + test_package
  10/10 + create_exit_code=0；29 个 builtins .so 签名成功。
- `git ls-files patches/boost-extra` = 183，头文件逐字（BSL-1.0）。

## 禁止做法

- 修改共享 boost 配方 / 打 boost 补丁（污染其他依赖库，违反不污染上游纪律）。
- 构建期外网 `curl` 下载缺失头（破坏离线可复现，设备直连 github 超时）。
- 在多个 TU 里包含 `<boost/json/src.hpp>`（官方模式 = 恰一个 TU）。
