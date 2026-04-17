# notcurses 3.0.17 编译进度

**日期**: 2026-04-16 (更新: 2026-04-17)
**状态**: ✅ success (补丁更新 v2)

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | CMake 配置完成 |
| Step 2 patches | ✅ | 8 个补丁（新增 0008-termdesc.c） |
| Step 3 configure | ✅ | cmake 成功 |
| Step 4 make | ✅ | make -j$(nproc) 成功 |
| Step 5 install | ✅ | make install → ~/usr/local/ |
| Step 6 safety | ✅ | 安全弹窗已通过 |
| Step 7 check | ✅ | 验证程序 timeout 5 EXIT=0 |
| Step 8 staging | ✅ | 预编译包制作完成 |
| Step 9 package | ✅ | tar.gz + install.sh |
| Step 10 deploy | ✅ | 本地安装验证 |
| Step 11 finish | ✅ | 归档完成 |

## 发现与知识

### v2 更新（2026-04-17）：终端查询细化

**问题**：v1 版本完全跳过了 `send_initial_queries()`，导致 SMCUP（进入备选屏幕）和 KKBDENTER（键盘初始化）都没有发送，终端没有进入备选屏幕模式，键盘无法正常工作（不能输入/回车）。

**修复**：细化 `send_initial_queries()` 补丁，只跳过需要响应的查询（DA1/DA2/DSRCPR/DIRECTIVES），保留不需要响应的初始化序列（SMCUP/KKBDENTER）。

### 关键经验

1. **SMCUP 必须发送**：否则终端不进入备选屏幕模式
2. **KKBDENTER 应该发送**：初始化键盘协议，否则键盘可能不响应
3. **DA1/DA2/DSRCPR 必须跳过**：OHOS 终端不响应，会导致 `pthread_cond_wait` 永久阻塞
4. **`pthread_cancel` 不可用**：OHOS 内核不支持，`cancel_and_join` 会永久阻塞在 `pthread_join`，需要 `pthread_detach` 替代
5. **`ppoll` 不可用**：用 `poll` 替代

---

**编译结束**: 2026-04-16 17:57
**补丁更新**: 2026-04-17 00:24
**最终状态**: success
