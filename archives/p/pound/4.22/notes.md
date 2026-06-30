# pound 4.22 编译笔记

## 软件信息
- **名称**: pound
- **版本**: 4.22
- **描述**: HTTP反向代理/负载均衡器
- **下载源**: 本地已有源码包
- **构建系统**: autotools

## 依赖
- openssl 1.1.1w（已预编译）
- pcre2 10.42（已预编译）

## 编译过程

### 遇到的问题与解决方案

#### 问题1: configure脚本临时目录权限问题
- **现象**: `mktemp -d "./confXXXXXX"`创建的目录无法创建文件
- **原因**: HMDFS文件系统中mktemp创建的目录有setuid属性(S)
- **解决**: 修改configure/config.status脚本，使用mkdir替代mktemp，使用TMPDIR环境变量

#### 问题2: pthread_mutexattr_settype未实现
- **现象**: 编译错误 `pthread_mutexattr_settype undeclared`
- **原因**: 鸿蒙系统不支持pthread_mutexattr_settype函数（PTHREAD_MUTEX_RECURSIVE）
- **解决**:
  - 移除`pthread_mutexattr_settype`调用
  - 使用默认mutex属性（PTHREAD_MUTEX_DEFAULT）
  - 在pound.c第1145-1146行注释掉该调用

#### 问题3: pthread_cancel未实现
- **现象**: 链接错误 `undefined reference to pthread_cancel`
- **原因**: 鸿蒙系统不支持pthread_cancel函数
- **解决**:
  - 在server函数中用`pthread_detach`替代`pthread_cancel`
  - 移除`pthread_join`调用（detach的线程不能join）
  - 修改probe_pthread_cancel函数为空操作
  - 在pound.c第784行、670-677行修改

#### 问题4: ELF签名
- **现象**: 编译后的ELF需要重新签名才能在鸿蒙上执行
- **解决**:
  - llvm-objcopy --remove-section .codesign移除旧签名段
  - binary-sign-tool sign -selfSign 1重新签名

### 编译参数
```bash
./configure --prefix=/storage/Users/currentUser/usr/local CFLAGS="-I/storage/Users/currentUser/usr/local/include" LDFLAGS="-L/storage/Users/currentUser/usr/local/lib"
make -j2
make install DESTDIR=/storage/Users/currentUser/test-install-pound-4.22
```

### 关键修改文件
- `configure`: 修改临时目录创建方式
- `config.status`: 修改临时目录创建方式
- `src/pound.c`:
  - 移除pthread_mutexattr_settype调用
  - 用pthread_detach替代pthread_cancel
  - 修改probe_pthread_cancel函数

### 平台限制记录

| 功能 | 鸿蒙支持 | 替代方案 |
|------|---------|---------|
| pthread_mutexattr_settype | ❌ 不支持 | 使用默认mutex |
| pthread_cancel | ❌ 不支持 | pthread_detach |
| makeinfo(texinfo) | ❌ 未安装 | 跳过文档生成 |

---

**编译开始**: 2026-05-21 14:47
**编译结束**: 2026-05-21 15:04
**最终状态**: published
**产物**: pound-4.22-ohos-aarch64.tar.gz (577KB)

## 知识提取

### E051扩展: pthread_cancel不支持
- **现象**: undefined reference to pthread_cancel
- **解决方案**: pthread_detach替代 + 移除pthread_join
- **适用场景**: 所有使用pthread_cancel的软件

### E052新增: pthread_mutexattr_settype不支持
- **现象**: pthread_mutexattr_settype undeclared
- **解决方案**: 使用默认mutex属性
- **适用场景**: 需要递归锁的软件