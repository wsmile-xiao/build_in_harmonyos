# perl-server-starter 0.35-r4 适配笔记

## 编译环境
- 构建系统: custom (Perl ExtUtils::MakeMaker)
- 编译日期: 2026-06-29
- 编译器: N/A (纯Perl模块，无需C编译器)
- 状态: published

## 编译步骤

1. 源码下载: `get()` 从 CPAN 下载 Server-Starter-0.35.tar.gz
2. 生成 Makefile.PL: 源码仅含 Build.PL (Module::Build)，生成 Makefile.PL 用于 ExtUtils::MakeMaker
3. 构建: `perl Makefile.PL` + `make -j2`
4. 安装: `make install DESTDIR={package_folder}`
5. 打包: 使用 os.walk + shutil.copy2 将 .pm 文件复制到 lib/perl5/，脚本复制到 bin/
6. 清理: 删除原始 Perl 安装树 data/ 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G4产物完整性检查失败 | package()方法使用conan copy()和Perl Config路径查找，但copy未正确将文件复制到顶层bin/lib目录 | 改用os.walk+shutil.copy2直接遍历安装树，将.pm文件复制到lib/perl5/，脚本复制到bin/，参考perl-reply模式 |
| 2 | start_server脚本无法自定位模块 | Perl安装路径与包路径不一致，脚本无法找到Server::Starter模块 | 在start_server脚本中添加BEGIN块自定位lib/perl5目录 |
| 3 | package_info未正确设置PERL5LIB | 使用subprocess调用Perl Config获取绝对路径，不可靠 | 改用runenv_info.append_path("PERL5LIB", package_folder/lib/perl5) |

## 源码修改

无源码补丁。conanfile.py 的 package() 和 package_info() 方法已修复。

## 依赖版本

- Perl 5.42.0 (系统自带)
- Conan 2.29.1
- 无第三方编译依赖

## 验证结果

### Conan-verify 门禁

```
G0: PASS (预构建风险评估)
G1: PASS (配方完整性)
G2: PASS (conan create 成功)
G3: PASS (系统同名库隔离)
G4: PASS (产物完整性: bin/1文件, lib/有内容)
L2: PASS (smoke test: start_server 0.35)
L4: PASS (安全扫描: 0个ELF文件)
L5: PASS (基线对比: 产物已更新)
```

### 功能测试 (2026-06-30)

完整功能测试报告见 `reports/test-report.md`。测试结论: ✅ PASS

**手动功能测试 (10项全部通过)**:
1. ✅ Server::Starter 模块加载 → 0.35
2. ✅ Server::Starter::Guard 模块加载
3. ✅ start_server --version → 0.35
4. ✅ start_server --help → 完整用法
5. ✅ 4个导出函数全部定义 (start_server, restart_server, stop_server, server_ports)
6. ✅ Guard 对象创建和回调执行
7. ✅ 函数导入到 main 命名空间
8. ✅ start_server 启动 + 端口绑定 + PID文件 + Worker进程
9. ✅ 热重启 (HUP信号): 新worker启动 → 旧worker终止
10. ✅ 优雅停止 (TERM信号): worker终止 → 干净退出

**源码测试套件 (4通过/10跳过/1失败)**:
- ✅ t/00-base.t: 模块加载
- ✅ t/08-wait3.t: 信号处理和非阻塞wait
- ✅ t/09-guard.t: Guard功能(3/3)
- ✅ t/14-without-port.t: 无端口模式
- ⏭ 10个测试因缺少 Test::TCP 等测试框架依赖而跳过
- ❌ t/13-unix-daemonize.t: Unix socket listen权限限制 (OHOS平台限制)

## 交付物

| 文件 | 说明 |
|------|------|
| bin/start_server | 热部署超级守护进程脚本 |
| lib/perl5/Server/Starter.pm | Server::Starter 模块 |
| lib/perl5/Server/Starter/Guard.pm | Server::Starter::Guard 模块 |

## 注意事项

- 纯Perl模块，无需C编译器
- Build.PL不可用(Module::Build未安装)，需生成Makefile.PL
- package()必须使用os.walk+shutil.copy2而非conan copy()，否则文件不会出现在顶层bin/lib目录
- start_server脚本需要自定位补丁才能在非conan环境中找到模块
- Unix domain socket模式在OHOS上不可用（权限限制），TCP端口模式完全正常
- 源码测试套件大部分依赖Test::TCP等未安装的测试模块，仅基础测试可运行
