# DRAFT-cute_tiled-1.0.0-pf0-path-typed-repository-dir

> 草稿（Path B 知识库扩展候选），由受控共享 PR 客户端 PF0 类型边界缺陷及其验证过的恢复协议产生。
> 本文与同名 `.kv` 配对，逐字段一致。仅为本地知识草稿，不代表任何 PR/Issue/commit/push/CI/review/merge/score 或共享客户端安装/远端成功。

## topic

PF0 shared PR client repository-directory Path type boundary

## error_signature

正常 `create-pr` 的 PF0 在任何 PR 写入之前即失败，错误为：
`unsupported operand type(s) for /: 'str' and 'str'`
当 `preflight.py` 的 `repo_dir / d` 收到 `_git_toplevel()` 返回的 `str` 时触发。

## root_cause

Git helper 输出（`_git_toplevel()` 返回 `str`）与 pathlib 路径运算（`repo_dir / d`）之间的类型边界缺少显式的 `pathlib.Path` 转换；缺陷位于实际的 `cmd_create_pr -> run_preflight` 调用点，属共享 PR 客户端的通用问题，而非任何单一库的源码问题。

## durable_solution

1. 在该调用点使用最小显式 Path 转换：`run_preflight(Path(_git_toplevel() or "."), args.target, args.source)`，并配套所需 import（`from pathlib import Path`）。
2. 证明精确的、已获批准整文件值（baseline `e7d899d8…` 到 fixed `e9602421…`，实际回归验证通过）。
3. 通过实际调用路径运行本地回归（真实 `cmd_create_pr -> run_preflight` 收到 `pathlib.Path` 参数，原始 `str` 对照复现 TypeError，修复后消除）。
4. 运行正常非绕过的 PF0-PF4（零 finding，期间零网络/API/凭据访问）。
5. 任何后续交付前，将临时验证字节逐字节恢复为基准（`e7d899d8…`），绝不将临时补丁留在发行物中。

## impact

该缺陷会阻断所有使用该受控客户端的仓库通过正常 preflight 创建 PR；因此该修复是可复用的共享客户端知识，而不是 cute_tiled 源码变更。任何遇到 `str/str` PF0 的仓库均可套用同样恢复协议。

## evidence_references

- R21 PR-delivery first-error log SHA: `fb25420be4f080007a686d05dfc237a9599e38989f1551e1bdd22f9d99354251`
- R22 exact-patch log SHA: `28b19031c8314719d06d5100a88174766fa4872421f466762552be21484742cf`
- Actual-callpath regression SHA: `d069fd93be7949f91512da353e248fdb96941abf757125ba413f86e61dc02576`
- PF0-PF4 nonwrite validation SHA: `1e24eff485ddbed0a16a4fae239e320b6d90e1d0ee09f5c98f565f4c00cc40e3`
- Restore/atomicity SHA: `2913a752f03f3aa5f6498a42dc8f2bb4e5474a4c50b27e365ae75333823168cc`

## recovery_condition

后续、另行授权的交付只能使用已知的精确修复并保持正常 preflight；交付后必须恢复基准字节。任何与指定修复值不匹配、PF0 再次出现或任何请求 `--no-preflight` 的情况，都会冻结交付；不得降级为 curl/原始 HTTP/浏览器自动化，也不得留下客户端字节补丁。

## status

draft_pending_review