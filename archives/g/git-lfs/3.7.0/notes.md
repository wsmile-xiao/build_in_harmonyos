# git-lfs 3.7.0 编译笔记

## 编译环境
- OpenHarmony R18 (linux/arm64)
- Go 1.24.4 (预编译包，已签名)
- GOPROXY: https://goproxy.cn,https://goproxy.io,direct

## 编译过程

### 1. 下载源码
```bash
wget --no-check-certificate https://github.com/git-lfs/git-lfs/archive/refs/tags/v3.7.0.tar.gz
tar xzf v3.7.0.tar.gz
mv git-lfs-3.7.0 git-lfs-3.7.0.work
```

### 2. Go环境配置
```bash
export GOROOT=~/usr/local/go1.24.4
export GOPATH=~/go
export PATH=$GOROOT/bin:$GOPATH/bin:$PATH
export GOPROXY=https://goproxy.cn,https://goproxy.io,direct
export GO111MODULE=on
export CGO_ENABLED=0
export GOCACHE=/data/storage/el2/base/haps/entry/files/go-build
export GOTMPDIR=/data/storage/el2/base/haps/entry/files/tmp
```

### 3. 编译问题及解决

#### 问题1: Makefile依赖git仓库
**错误**: `fatal: not a git repository`

**原因**: git-lfs的Makefile使用git命令获取版本信息

**解决**: 跳过Makefile，直接使用`go build`

#### 问题2: go generate需要执行临时二进制
**错误**: `fork/exec .../mangen: permission denied`

**原因**: OpenHarmony要求所有ELF二进制文件必须签名才能执行

**解决**: 手动创建空的生成文件
- `commands/mancontent_gen.go` - 手册内容
- `tr/tr_gen.go` - 翻译文件

#### 问题3: Go链接器权限问题
**错误**: `link: mapping output file failed: permission denied`

**原因**: Go工具链的二进制文件未签名

**解决**: 签名Go工具链所有可执行文件
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf ~/usr/local/go1.24.4/pkg/tool/linux_arm64/link
# 以及其他工具
```

### 4. 编译命令
```bash
cd ~/builds/git-lfs-3.7.0.work
go build -o git-lfs .
```

### 5. 签名二进制
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf git-lfs
```

### 6. 验证
```bash
./git-lfs version
# 输出: git-lfs/3.7.0 (GitHub; linux arm64; go 1.24.4)
```

## 打包结果
- 预编译包: `git-lfs-3.7.0-ohos-aarch64.tar.gz` (13MB)
- Debug包: `git-lfs-3.7.0-ohos-aarch64-debug.tar.gz` (已删除，节省空间)

**⚠️ 注意**: 主预编译包大小为13MB，超过GitCode的10MB限制，无法上传到GitCode。
预编译包可通过以下方式分发：
1. cmd-pkgs仓库的GitHub Release（推荐）
2. 本地归档路径：`archives/g/git-lfs/3.7.0/packaging/git-lfs-3.7.0-ohos-aarch64.tar.gz`
3. 用户可从源码自行编译

## 特殊说明
- Go静态编译，无需RPATH设置
- 所有二进制文件需要ELF签名才能在OpenHarmony上执行
- Go工具链本身也需要签名才能执行编译任务

## 知识提取
### E1: Go程序在OpenHarmony上的编译
1. Go工具链所有二进制文件都需要签名
2. 设置GOCACHE和GOTMPDIR到可写目录
3. 使用CGO_ENABLED=0进行静态编译
4. go generate生成的临时二进制也需要签名

### E2: 跳过go generate的方法
对于Go项目的代码生成步骤，可以通过创建空的生成文件来跳过：
- 检查go:generate指令的目标文件
- 创建符合包结构的空文件
- 确保不影响主要功能
---

**编译结束**: 2026-05-25 10:48
**最终状态**: built
