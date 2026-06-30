# devcontainers/cli 0.87.0 编译笔记

## 项目信息
- **软件**: devcontainers/cli (开发容器CLI)
- **版本**: 0.87.0
- **构建系统**: npm (Node.js/TypeScript)
- **目标平台**: HarmonyOS NEXT (musl libc, aarch64)

## 编译环境
- **Node.js**: v24.13.0
- **npm**: 11.6.2
- **Python**: 3.12.8 (用于 node-gyp 编译原生模块)
- **esbuild**: v0.27.3 (打包/压缩工具)

## 源码修改
无源码修改。编译过程为标准 npm build 流程。

## 编译命令
```bash
# 安装依赖 (跳过原生模块编译脚本)
npm install --ignore-scripts

# 编译 node-pty 原生模块 (需要设置 LD_LIBRARY_PATH 以便 Python 可执行)
export LD_LIBRARY_PATH=/data/service/hnp/python.org/python_3.12/lib:/data/service/hnp/lib:/storage/Users/currentUser/usr/local/lib:$LD_LIBRARY_PATH
cd node_modules/node-pty
node-gyp rebuild --nodedir=/data/service/hnp/node.org/node_v24.13.0

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

## 注意事项
- node-pty 原生模块需要 Python 环境来通过 node-gyp 编译
- LD_LIBRARY_PATH 需要包含 Python 库路径，否则 Python 无法运行
- npm install --ignore-scripts 需要先执行，然后手动编译 node-pty
- devcontainer CLI 是 Node.js 应用，需要 Node.js 运行环境
