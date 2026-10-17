# uhdm — OpenHarmony 编译记录

## 基本信息
- 软件: UHDM (Universal Hardware Data Model)
- 描述: C++17 VPI 硬件数据模型库与 CLI 工具集（chipsalliance，Apache-2.0）
- 官网: https://github.com/chipsalliance/UHDM
- 仓库: https://github.com/chipsalliance/UHDM
- 构建系统: cmake
- 目标: ohos-aarch64

## 已编译版本

| 版本 | 状态 | 备注 |
|------|------|------|
| 1.86 | 🔄 适配中 | CMake host 分支（UHDM_USE_HOST_CAPNP）+ 制品仓 capnproto/1.3.0 代码生成；上游 17 测试二进制/43 用例实测 43/43 |

## 补丁清单
- 无补丁（上游 CMake 在 OHOS 下原样编译，零源码修改）

## 已知限制
| 限制 | 影响 | 规避方案 |
|------|------|----------|
| /tmp 只读（E002） | 测试二进制创建临时文件 abort | TMPDIR 指向可写目录 |
| host 分支不定义 CAPNP_EXECUTABLE | capnp 代码生成命令为空 | 消费方显式注入制品仓 capnproto 包 bin/capnp、bin/capnpc-c++ |
| generate.py 依赖 pip orderedmultidict | CI clean 环境无 site-packages | build() 内 pip --no-deps 钉版安装至 build_folder 私有前缀（R49/E524） |
