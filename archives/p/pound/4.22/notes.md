# pound 4.22 编译笔记

## 软件信息
- **名称**: pound
- **版本**: 4.22
- **描述**: HTTP反向代理/负载均衡器
- **构建系统**: autotools

## 依赖
- openssl/1.1.1w（制品仓已发布）
- pcre2/10.45（制品仓已发布）

## 编译过程

### 遇到的问题与解决方案

#### 问题1: umask 077 导致 Permission denied (HMDFS)
- **现象**: configure/config.guess/config.status 使用 umask 077 创建临时目录，写入文件失败
- **原因**: HMDFS 中 umask 077 创建的目录有 setgid-without-execute 属性，即使 owner 也无法创建文件
- **解决**: patch 0002 将 configure 内建临时目录改为 `${TMPDIR:-/tmp}` 前缀并用 umask 022

#### 问题2: config.guess 不识别 HarmonyOS
- **现象**: config.guess (v2021-06-03) 无法识别 HarmonyOS 平台
- **解决**: OHOS 适配版 conan 的 AutotoolsToolchain 自动注入交叉配置，无需手工 patch config.guess

#### 问题6: pcre2-config 返回错误路径
- **现象**: conan pcre2 包的 pcre2-config 返回 `//lib/libpcre2-8.la`（错误路径），configure 检测失败
- **解决**: conanfile.py generate() 生成返回 conan cache 正确路径的 pcre2-config wrapper，并将 build folder 与 pcre2 bin prepend 到 PATH

#### 问题3: pthread_cancel 未实现
- **现象**: 链接错误 undefined reference to pthread_cancel
- **解决**: 协作式终止（patch 0001）：新增 `volatile sig_atomic_t shutting_down` 全局标志；dispatcher 主循环 `for(;;)` 改为 `while(!shutting_down)` 且 `poll` 超时从 `-1` 改为 `500ms`；server() 中 `pthread_cancel+pthread_join` 改为 `shutting_down=1; pthread_join`。dispatcher 在 500ms 内自行退出并经 cleanup handler 关闭 listener socket，join 保证其完全停止后才继续 shutdown——语义对齐上游 cancel+join（AI review P1 建议）

#### 问题4: pthread_mutexattr_settype
- **现象**: 上游 pound.c:1146 使用 PTHREAD_MUTEX_RECURSIVE
- **解决**: OHOS musl 提供 pthread_mutexattr_settype/PTHREAD_MUTEX_RECURSIVE，实测可直接编译，无需 patch

#### 问题5: makeinfo 缺失
- **现象**: make install 时文档构建失败
- **解决**: 传递 MAKEINFO=true 跳过文档生成

### 平台限制记录

| 功能 | 鸿蒙支持 | 替代方案 |
|------|---------|---------|
| pthread_cancel | 不支持 | 协作式终止（shutting_down 标志 + 500ms poll 超时 + join） |
| makeinfo(texinfo) | 未安装 | MAKEINFO=true |

### 补丁清单
- `0001-openharmony-pthread-cancel.patch`: 协作式 dispatcher 终止（见问题3）
- `0002-openharmony-tmpdir-fix.patch`: configure 临时目录改用 TMPDIR 且 umask 022（HMDFS 上 umask 077 创建的目录带 setgid-without-execute 属性导致不可写；同因 config.status 运行期写入失败一并解决）

---

**编译日期**: 2026-08-18
**最终状态**: built
**产物**: pound + poundctl 可执行文件
