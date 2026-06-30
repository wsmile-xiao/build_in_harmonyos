# repo

**Repo is a tool built on top of Git.**

Repo helps manage many Git repositories, does the uploads to revision control
systems, and automates parts of the development workflow. Repo is not meant to
replace Git, only to make it easier to work with Git.

## 安装

### 预编译包安装

```bash
tar -xzf repo-2-ohos-aarch64.tar.gz -C $HOME/usr/local
export PATH=$HOME/usr/local/bin:$PATH
repo --version
```

### 使用镜像源

如果官方源网络受限，可以使用镜像：

```bash
export REPO_URL=https://mirrors.tuna.tsinghua.edu.cn/git/git-repo/
repo init -u <manifest-url>
```

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2 | built | 最新版本 |

## 依赖

- git (>= 2.0)
- python (>= 3.6)

## 使用

```bash
# 初始化项目
repo init -u https://android.googlesource.com/platform/manifest

# 同步代码
repo sync

# 查看状态
repo status

# 更多命令
repo help
```

## 链接

- 官方主页: https://gerrit.googlesource.com/git-repo/
- GitHub 镜像: https://github.com/GerritCodeReview/git-repo
- 文档: https://source.android.com/source/using-repo.html