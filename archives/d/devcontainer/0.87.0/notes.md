# devcontainers/cli 0.87.0 编译笔记

## 项目信息
- **软件**: devcontainers/cli (开发容器CLI)
- **版本**: 0.87.0
- **构建系统**: npm (Node.js/TypeScript)
- **目标平台**: HarmonyOS NEXT (musl libc, aarch64)

## 编译环境
- **Node.js**: v24.13.0
- **npm**: 11.6.2
- **Python**: 3.12.9 (用于 node-gyp 编译原生模块)
- **esbuild**: v0.27.3 (打包/压缩工具)

## 源码修改
无源码修改。编译过程为标准 npm build 流程。

## 编译命令
```bash
# 安装依赖 (跳过原生模块编译脚本)
npm install --ignore-scripts

# 编译 node-pty 原生模块 (需要设置 LD_LIBRARY_PATH 以便 Python 可执行)
export LD_LIBRARY_PATH=/data/service/hnp/python.org/python_3.12/lib:/data/service/hnp/lib:$LD_LIBRARY_PATH
cd node_modules/node-pty
npx node-gyp rebuild --nodedir=/data/service/hnp/node.org/node_v24.13.0

# 编译 TypeScript/JavaScript
npm run compile
```

## 安装
```bash
# 安装到 TEST_PREFIX
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/lib/devcontainer/dist/spec-node
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/lib/devcontainer/scripts

cp devcontainer.js package.json CHANGELOG.md LICENSE.txt README.md ThirdPartyNotices.txt $TEST_PREFIX/$DEFAULT_PREFIX/lib/devcontainer/
cp dist/spec-node/devContainersSpecCLI.js $TEST_PREFIX/$DEFAULT_PREFIX/lib/devcontainer/dist/spec-node/
cp -r node_modules $TEST_PREFIX/$DEFAULT_PREFIX/lib/devcontainer/
cp scripts/updateUID.Dockerfile $TEST_PREFIX/$DEFAULT_PREFIX/lib/devcontainer/scripts/

# 创建运行 wrapper
cat > $TEST_PREFIX/$DEFAULT_PREFIX/bin/devcontainer << 'EOF'
#!/bin/sh
exec node /usr/local/lib/devcontainer/devcontainer.js "$@"
EOF
chmod +x $TEST_PREFIX/$DEFAULT_PREFIX/bin/devcontainer
```

## 签名验证
- node-pty/build/Release/pty.node (ELF 原生模块) 已签名
- devcontainer CLI 版本验证: 0.87.0 ✅

## Conan 适配
- **package_type**: application (CLI tool)
- **build system**: custom (npm)
- **conandata.yml**: sha256 verified, mirror fallback URLs added by CI
- **test_package**: shell-based test (test_devcontainer.sh) verifies --version and --help
- **commands.json**: declared as tool type
- **conan-verify**: G1-G4 + L2/L4/L5 all passed
- **W3 local CI**: passed (setup.sh + build_and_test.sh)

## 注意事项
- node-pty 原生模块需要 Python 环境来通过 node-gyp 编译
- LD_LIBRARY_PATH 需要包含 Python 库路径，否则 Python 无法运行
- npm install --ignore-scripts 需要先执行，然后手动编译 node-pty
- devcontainer CLI 是 Node.js 应用，需要 Node.js 运行环境
- nodedir 需通过 `os.path.realpath(shutil.which("node"))` 解析符号链接

## npm registry 陷阱（2026-09-18 修复）
- **现象**: `npm install --ignore-scripts` 报 `ETARGET No matching version found for esbuild@0.27.3`
- **根因**: 部分构建环境（如 OpenDesk 沙箱注入的 `npm_config_registry` 环境变量）指向社区镜像
  `npm.cnb.cool/OpenHarmonyPCDeveloper/npm`，该镜像的 packument 是人工同步的子集，esbuild
  只有 0.27.0/0.28.1，而 devcontainers/cli 0.87.0 的 devDependencies 固定 `esbuild: ^0.27.3`
  （语义化范围 `>=0.27.3 <0.28.0`），镜像中无匹配版本
- **修复**: conanfile.py 的 `npm install` 与 `npx node-gyp` 命令显式追加
  `--registry=https://registry.npmjs.org`（CLI 参数优先级高于环境变量），公网官方源可达且版本完整
  （实测设备侧 registry.npmjs.org 响应 ~0.8s）；CI worker 的 buildbot 环境无该注入变量、默认即公网源
- **验证**: 本地 build_and_test.sh 两种环境（镜像 env 注入 / 干净环境）均通过

## CI 失败修复记录（PR #4218 重试）
- 2026-08-17 CI: L0 报 `missing_setting_compiler missing_setting_build_type` → 已由
  c9e986cb 补齐 settings 四项修复
- 2026-09-04 CI #37996: G0e 根目录白名单拦截 `.ci-branch-marker-v6`/`.ci-marker-v7b` ——
  属 CI checkout/base 环境内容（同批 loom #37976/#37979 同样被拦），main 侧已在 .gitignore
  放行 `.ci-branch-marker-*`/`.ci-marker-*` 并将 BUILD.gn/oh-package.json 加入 G0e 白名单；
  本分支合并最新 main 后自然解决
- 分支基点残留 `.ci-result.json`/`libfuse-3.18.2-PR.md`（!2877 批次误入 main，现已在 main 删除），
  合并 origin/main 后随删除消失，根目录白名单复验通过

## nodedir 解析陷阱（2026-09-18 修复，CI #49878）
- **现象**: CI worker（CI-020）上 `npx node-gyp rebuild` 报
  `gyp: /storage/Users/currentUser/usr/local/common.gypi not found` → `gyp failed with exit code: 1`
- **根因**: 部分 worker 装有用户级 node（`~/usr/local/bin/node`，无开发头文件），它先于
  `/data/service/hnp/bin` 出现在 profile buildenv PATH 中，`realpath(which("node"))` 推导的
  nodedir=`~/usr/local` 下没有 `include/node/config.gypi`（node-gyp 必需）
- **修复**: conanfile.py 在推导 nodedir 后探测 `include/node/config.gypi` 是否存在，缺失时
  回退到 `/data/service/hnp/node.org/node_v*`（倒序取最新含头文件者；worker 的用户级 node 与
  HNP node 同为 v24.13.0，ABI 一致）
- **验证**: 本地 W3 复验通过（主路径不受影响）；回退路径以无头文件 nodedir 单元验证
  正确解析到 `/data/service/hnp/node.org/node_v24.13.0`
- 另: 该 CI 上 `npm install --registry=https://registry.npmjs.org` 12s 完成（472 包），
  registry 钉扎在 CI 环境验证有效；CI worker 的 pre-download 步骤因机器无 curl 仅告警，
  conan 自身下载源码正常

## 第 3 次尝试（2026-09-20）：结果回执 SHA 对齐修复
- **现象**: 任务被派发方拒绝，报 `PR rejected (sha mismatch: got 09b9101b)`。PR #4218 本身
  CI 已通过（#49984，CI-020）且状态 open，检视意见全部闭环
- **根因**: 前序尝试在写 result.json（commit_hash=0a1a19356）之后，`feedback --resume`
  的完成入仓机制（R45）又自动提交并推送了 SKILL_FEEDBACK 报告（09b9101b1），PR head
  移动导致 result.json 记录的 commit hash 与 PR 实际 head 不一致
- **修复**: 本次无配方变更。在全新环境检出分支后本地 W3 复验（conan create，
  ohos-aarch64 profile，exit 0，test_package PASS：wrapper/--version=0.87.0/--help 全过），
  并将本轮记录提交推送，使 PR head 与最终 result.json 的 commit_hash 重新对齐；
  终态回执在所有推送完成之后写入
- **验证**: 本地 `conan create archives/d/devcontainer/0.87.0 -pr:h/-pr:b
  ci/conan/profiles/ohos-aarch64 --build=missing --build="devcontainer/*"` exit 0

## 结束

COMPLETED — devcontainer 0.87.0 conan 适配完成
