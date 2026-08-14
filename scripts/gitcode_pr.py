#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitCode PR 管理工具 — 创建PR、获取评论、监控CI状态、回复评论。

通过 GitCode API v5 实现 PR 全生命周期管理，供 OpenDesk AI Agent
在适配编译流程中自动创建 PR、跟踪审查意见和 CI 结果、回复评论并
推送修复。

首次使用前，运行 setup 命令配置 access_token:
    python3 scripts/gitcode_pr.py setup

用法:
    # 创建 PR
    python3 scripts/gitcode_pr.py create-pr \
        --repo OpenHarmonyPCDeveloper/build_in_harmonyos \
        --source feat/sqlite3-verify --target main \
        --title "feat: sqlite3 3.49.1 Conan 配方适配" \
        --description "PR 描述内容..."

    # 获取 PR 详情
    python3 scripts/gitcode_pr.py get-pr \
        --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 1862

    # 获取机器人评论（默认只看 bot 评论）
    python3 scripts/gitcode_pr.py get-comments \
        --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 1862

    # 获取最新 CI 状态
    python3 scripts/gitcode_pr.py ci-status \
        --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 1862

    # 回复评论
    python3 scripts/gitcode_pr.py reply-comment \
        --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 1862 \
        --discussion-id 12345 --body "已修复，见最新提交"

    # 获取 PR 的所有 commit
    python3 scripts/gitcode_pr.py get-commits \
        --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 1862

    # 检查 PR 是否已合并
    python3 scripts/gitcode_pr.py is-merged \
        --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 1862

首次使用:
    # 交互式配置 token
    python3 scripts/gitcode_pr.py setup

认证: 从 ~/.gitcode-token 读取 access_token，或通过 --token 参数指定。
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone

# ── 常量 ──────────────────────────────────────────────────────────

API_BASE = "https://api.gitcode.com/api/v5"
TOKEN_FILE = os.path.expanduser("~/.gitcode-token")

# 被监控的机器人用户名前缀
BOT_PREFIXES = ("gitcode-bot", "ohpcd-robot", "ohpcd-bot", "atomgit-bot")

# ── 工具函数 ──────────────────────────────────────────────────────

def load_token():
    """从文件或环境变量加载 access_token。"""
    token = os.environ.get("GITCODE_TOKEN", "")
    if token:
        return token
    if os.path.isfile(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return f.read().strip()
    print("ERROR: 未找到 GitCode access_token。", file=sys.stderr)
    print(f"请将 token 写入 {TOKEN_FILE} 或设置 GITCODE_TOKEN 环境变量。", file=sys.stderr)
    sys.exit(1)


def api_request(method, path, params=None, body=None):
    """发送 GitCode API v5 请求。

    Args:
        method: HTTP 方法 (GET/POST/PATCH/PUT/DELETE)
        path: API 路径 (不含 /api/v5 前缀)
        params: query 参数 dict
        body: POST/PATCH 请求体 dict

    Returns:
        解析后的 JSON 数据 (dict 或 list)
    """
    token = load_token()
    if params is None:
        params = {}
    # access_token 总是作为 query 参数
    params["access_token"] = token

    query = urllib.parse.urlencode(params)
    url = f"{API_BASE}{path}?{query}"

    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            if not raw:
                return {}
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")[:500]
        print(f"API 错误 {e.code}: {error_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"网络错误: {e}", file=sys.stderr)
        sys.exit(1)


def is_bot_user(username):
    """判断用户名是否为机器人。"""
    if not username:
        return False
    username_lower = username.lower()
    return any(username_lower.startswith(bp) for bp in BOT_PREFIXES)


def format_time(ts):
    """格式化时间戳为可读字符串。"""
    if not ts:
        return "N/A"
    try:
        # 解析 ISO 8601
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        # 转为本地时间
        local_dt = dt.astimezone()
        return local_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts[:19]


def truncate(text, max_len=500):
    """截断文本，保留开头和结尾。"""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    half = max_len // 2
    return text[:half] + f"\n... [{len(text) - max_len} chars omitted] ...\n" + text[-half:]


# ── 子命令实现 ────────────────────────────────────────────────────

def cmd_setup(args):
    """引导用户创建 GitCode access_token 并保存到本地。"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           GitCode Access Token 配置引导                           ║
╚══════════════════════════════════════════════════════════════════╝

本工具通过 GitCode API v5 管理PR，需要 access_token 认证。
请按以下步骤创建 token：

  1. 打开浏览器访问:
     https://gitcode.com/setting/token-classic/create

  2. 填写令牌名称 (如: opendesk-ai)

  3. 权限选择 — 只勾选以下 4 项为「读写」，其余全部「禁止」:

     ┌────────────────┬────────┐
     │ 权限项         │ 设置   │
     ├────────────────┼────────┤
     │ 项目           │ 读写   │
     │ PR             │ 读写   │
     │ Issue          │ 读写   │
     │ Notes          │ 读写   │
     └────────────────┴────────┘
     ⚠️  其他权限项一律设为「禁止」，最小权限原则。

  4. 点击「创建令牌」，复制生成的 token

  5. 将 token 粘贴到下方 (或直接写入 ~/.gitcode-token 文件)

""")

    # 检查是否已有 token
    if os.path.isfile(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            existing = f.read().strip()
        if existing and not args.force:
            print(f"⚠️  已检测到现有 token: {existing[:8]}...{existing[-4:]}")
            print("   使用 --force 覆盖，或直接编辑 ~/.gitcode-token")
            return

    # 交互式输入 token
    try:
        token = input("请粘贴你的 access_token (或按 Ctrl+C 跳过): ").strip()
    except KeyboardInterrupt:
        print("\n已跳过。可稍后手动写入 ~/.gitcode-token")
        return

    if not token:
        print("未输入 token，可稍后手动写入 ~/.gitcode-token")
        return

    # 保存 token
    with open(TOKEN_FILE, "w") as f:
        f.write(token)
    os.chmod(TOKEN_FILE, 0o600)

    print(f"\n✅ Token 已保存到 {TOKEN_FILE} (权限 600)")
    print(f"   Token: {token[:8]}...{token[-4:]}")

    # 验证 token
    print("\n正在验证 token...")
    try:
        old_token = os.environ.get("GITCODE_TOKEN", "")
        os.environ["GITCODE_TOKEN"] = token
        result = api_request("GET", "/user")
        print(f"✅ 验证成功! 当前用户: {result.get('login', 'N/A')} ({result.get('name', 'N/A')})")
    except SystemExit:
        print("❌ Token 验证失败，请检查 token 是否正确")
    finally:
        if old_token:
            os.environ["GITCODE_TOKEN"] = old_token


def cmd_create_pr(args):
    """创建 Pull Request。"""
    body = {
        "title": args.title,
        "head": args.source,
        "base": args.target,
        "body": args.description or "",
    }
    if args.milestone:
        body["milestone_number"] = args.milestone

    path = f"/repos/{args.repo}/pulls"
    result = api_request("POST", path, body=body)

    print("✅ PR 创建成功")
    print(f"   编号: #{result.get('number', 'N/A')}")
    print(f"   标题: {result.get('title', 'N/A')}")
    print(f"   分支: {args.source} → {args.target}")
    print(f"   URL:  {result.get('html_url', 'N/A')}")
    # 输出 JSON 供 AI 解析
    print("\n--- JSON ---")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def cmd_get_pr(args):
    """获取单个 PR 详情。"""
    path = f"/repos/{args.repo}/pulls/{args.number}"
    result = api_request("GET", path)

    print(f"PR #{result.get('number', 'N/A')}: {result.get('title', 'N/A')}")
    print(f"  状态: {result.get('state', 'N/A')}")
    print(f"  分支: {result.get('head', {}).get('ref', 'N/A')} → {result.get('base', {}).get('ref', 'N/A')}")
    print(f"  创建: {format_time(result.get('created_at'))}")
    print(f"  更新: {format_time(result.get('updated_at'))}")
    print(f"  URL:  {result.get('html_url', 'N/A')}")
    labels = [l.get("name", "") for l in result.get("labels", [])]
    if labels:
        print(f"  标签: {', '.join(labels)}")
    print(f"\n描述:\n{truncate(result.get('body', ''), 1000)}")

    if args.json:
        print("\n--- JSON ---")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def cmd_get_comments(args):
    """获取 PR 评论，默认只显示机器人评论。"""
    path = f"/repos/{args.repo}/pulls/{args.number}/comments"
    params = {"per_page": 100, "page": 1}

    all_comments = []
    while True:
        result = api_request("GET", path, params=params)
        if not result:
            break
        all_comments.extend(result)
        if len(result) < params["per_page"]:
            break
        params["page"] += 1

    # 过滤
    if not args.all_comments:
        comments = [c for c in all_comments if is_bot_user(c.get("user", {}).get("login", ""))]
    else:
        comments = all_comments

    print(f"PR #{args.number} 评论 ({len(comments)}/{len(all_comments)} 条{', 仅机器人' if not args.all_comments else ''})")
    print("=" * 80)

    for i, c in enumerate(comments):
        user = c.get("user", {}).get("login", "unknown")
        created = format_time(c.get("created_at"))
        cid = c.get("id", "")
        body = c.get("body", "")
        discussion_id = c.get("discussion_id", c.get("in_reply_to", ""))

        bot_marker = "🤖" if is_bot_user(user) else "👤"
        print(f"\n[{i+1}] {bot_marker} {user} ({created})")
        print(f"    comment_id: {cid}")
        if discussion_id:
            print(f"    discussion_id: {discussion_id}")
        print(f"    {truncate(body, args.max_length)}")

    if args.json:
        print("\n--- JSON ---")
        print(json.dumps(comments, ensure_ascii=False, indent=2))
    return comments


def cmd_ci_status(args):
    """从评论中提取最新 CI 构建状态。"""
    path = f"/repos/{args.repo}/pulls/{args.number}/comments"
    params = {"per_page": 100, "page": 1}

    all_comments = []
    while True:
        result = api_request("GET", path, params=params)
        if not result:
            break
        all_comments.extend(result)
        if len(result) < params["per_page"]:
            break
        params["page"] += 1

    # 筛选 CI 相关评论 (ohpcd-robot)
    ci_comments = [
        c for c in all_comments
        if is_bot_user(c.get("user", {}).get("login", ""))
        and ("CI" in c.get("body", "") or "校验" in c.get("body", ""))
    ]

    if not ci_comments:
        print("未找到 CI 评论。")
        return

    # 取最后一条 CI 评论
    latest = ci_comments[-1]
    user = latest.get("user", {}).get("login", "unknown")
    created = format_time(latest.get("created_at"))
    body = latest.get("body", "")

    # 解析 CI 状态
    if "校验通过" in body:
        status = "✅ PASSED"
    elif "校验失败" in body:
        status = "❌ FAILED"
    elif "构建已启动" in body:
        status = "🔄 RUNNING"
    elif "排队中" in body:
        status = "⏳ QUEUED"
    else:
        status = "❓ UNKNOWN"

    print(f"CI 最新状态: {status}")
    print(f"  机器人: {user}")
    print(f"  时间: {created}")
    print(f"  评论数: {len(ci_comments)} 条 CI 相关")
    print(f"\n评论内容:\n{truncate(body, 2000)}")

    # 列出所有 CI 构建历史
    print("\n--- CI 历史摘要 ---")
    for c in ci_comments:
        t = format_time(c.get("created_at"))
        b = c.get("body", "")
        if "校验通过" in b:
            s = "✅"
        elif "校验失败" in b:
            s = "❌"
        elif "构建已启动" in b:
            s = "🔄"
        elif "排队中" in b:
            s = "⏳"
        else:
            s = "❓"
        # 提取构建号
        build_num = ""
        for line in b.split("\n"):
            if "PR #" in line and "|" in line:
                parts = line.split("|")
                if len(parts) >= 3:
                    build_num = parts[1].strip()
                    break
        print(f"  {t} {s} {build_num}")

    if args.json:
        print("\n--- JSON ---")
        print(json.dumps(ci_comments, ensure_ascii=False, indent=2))
    return ci_comments


def cmd_trigger_ci(args):
    """主动评论 /rebuild 触发 CI 构建。

    平台变更后 CI 不再自动触发，需要主动评论才能启动构建。
    API: POST /repos/{repo}/pulls/{number}/comments (body=/rebuild)
    """
    body = {"body": "/rebuild"}
    path = f"/repos/{args.repo}/pulls/{args.number}/comments"
    result = api_request("POST", path, body=body)

    print("✅ 已评论 /rebuild 触发 CI 构建")
    print(f"   PR: {args.repo}#{args.number}")
    print(f"   note_id: {result.get('note_id', 'N/A')}")

    if args.json:
        print("\n--- JSON ---")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def cmd_reply_comment(args):
    """回复 PR 评论。

    使用简单评论 API (POST /repos/{repo}/pulls/{number}/comments) 配合
    in_reply_to 参数回复指定讨论。discussions API 需要额外权限，
    简单评论 API 兼容性更好。
    """
    body = {"body": args.body, "in_reply_to": args.discussion_id}
    path = f"/repos/{args.repo}/pulls/{args.number}/comments"
    result = api_request("POST", path, body=body)

    print("✅ 回复成功")
    print(f"   note_id: {result.get('note_id', 'N/A')}")
    print(f"   discussion_id: {args.discussion_id}")

    if args.json:
        print("\n--- JSON ---")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def cmd_resolve_comment(args):
    """修改检视意见解决状态（标记为已解决/未解决）。

    API: PUT /repos/{owner}/{repo}/pulls/{number}/comments/{discussion_id}
    Body: {"resolved": true/false}
    """
    resolved = not args.unresolved if args.unresolved else True
    body = {"resolved": resolved}
    path = f"/repos/{args.repo}/pulls/{args.number}/comments/{args.discussion_id}"
    result = api_request("PUT", path, body=body)

    status_text = "已解决" if resolved else "未解决"
    print(f"✅ 检视意见标记为{status_text}")
    print(f"   discussion_id: {args.discussion_id}")

    if args.json:
        print("\n--- JSON ---")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def cmd_handle_review_opinion(args):
    """处理单条检视意见：回复 + （接纳时）标记已解决。

    封装检视意见处理流程，确保规则一致性：
    - accept: 回复"已修复: {reason}" + 标记已解决
    - reject: 回复"不接纳: {reason}。请审核人员评估..."（不标记已解决）

    AI 只需传入 action 和 reason，脚本保证流程正确。
    ID 优先级: --comment-id（评论 ID，始终存在，in_reply_to 首选）
              > --discussion-id（讨论 ID，旧参数，可能为空导致回复变成独立评论）
    """
    reply_to = getattr(args, "comment_id", None) or args.discussion_id
    if not reply_to:
        print("❌ 错误: 需要 --comment-id 或 --discussion-id（可从 monitor-review 获取）")
        import sys
        sys.exit(2)

    if args.action == "accept":
        reply_body = f"✅ 已修复: {args.reason}"
    else:
        reply_body = (f"❌ 不接纳: {args.reason}\n\n"
                       "请审核人员评估是否无需解决，"
                       "如无需解决，由审核人员标记已解决。")

    # Step 1: 在检视意见讨论串内回复
    reply_data = {"body": reply_body, "in_reply_to": reply_to}
    reply_path = f"/repos/{args.repo}/pulls/{args.number}/comments"
    reply_result = api_request("POST", reply_path, body=reply_data) or {}

    # 校验回复是否真正挂到讨论串（响应未回显 in_reply_to 则可能变成独立评论）
    echo_id = str(reply_result.get("in_reply_to", ""))
    if echo_id and echo_id != str(reply_to):
        print(f"⚠️  回复未挂到原讨论串 (echo={echo_id}, expect={reply_to})，"
              f"请在 PR 页面确认回复位置")

    print(f"✅ 已回复检视意见 ({args.action})")
    print(f"   reply_to: {reply_to}")
    print(f"   回复内容: {reply_body[:100]}")

    # Step 2: 标记已解决（仅接纳时），校验结果
    if args.action == "accept":
        resolve_target = args.discussion_id or reply_to
        resolve_data = {"resolved": True}
        resolve_path = f"/repos/{args.repo}/pulls/{args.number}/comments/{resolve_target}"
        resolve_result = api_request("PUT", resolve_path, body=resolve_data)

        if resolve_result is None:
            print(f"⚠️  标记已解决失败（API 无响应），请到 PR 页面手动标记: {resolve_target}")
        else:
            print(f"✅ 已标记为已解决")
    else:
        print(f"⏸️  未标记已解决（拒绝意见，留待审核人员评估）")

    if args.json:
        output = {
            "action": args.action,
            "discussion_id": args.discussion_id,
            "reply_body": reply_body,
            "resolved": args.action == "accept",
        }
        print("\n--- JSON ---")
        print(json.dumps(output, ensure_ascii=False, indent=2))
    return {"action": args.action, "resolved": args.action == "accept"}


def cmd_update_pr(args):
    """更新 PR 信息（标题/描述/状态）。"""
    body = {}
    if args.title:
        body["title"] = args.title
    if args.description is not None:
        body["body"] = args.description
    if args.state:
        body["state"] = args.state

    if not body:
        print("ERROR: 至少指定 --title, --description 或 --state 之一", file=sys.stderr)
        sys.exit(1)

    path = f"/repos/{args.repo}/pulls/{args.number}"
    result = api_request("PATCH", path, body=body)

    print("✅ PR 更新成功")
    print(f"   编号: #{result.get('number', 'N/A')}")
    print(f"   标题: {result.get('title', 'N/A')}")
    print(f"   状态: {result.get('state', 'N/A')}")

    if args.json:
        print("\n--- JSON ---")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def cmd_get_commits(args):
    """获取 PR 的所有 commit。"""
    path = f"/repos/{args.repo}/pulls/{args.number}/commits"
    params = {"per_page": 100, "page": 1}

    all_commits = []
    while True:
        result = api_request("GET", path, params=params)
        if not result:
            break
        all_commits.extend(result)
        if len(result) < params["per_page"]:
            break
        params["page"] += 1

    print(f"PR #{args.number} Commits ({len(all_commits)} 个)")
    print("=" * 80)
    for i, c in enumerate(all_commits):
        sha = c.get("sha", "")[:8]
        msg = c.get("commit", {}).get("message", "").split("\n")[0]
        author = c.get("commit", {}).get("author", {}).get("name", "unknown")
        date = format_time(c.get("commit", {}).get("author", {}).get("date"))
        print(f"  [{i+1}] {sha} - {msg}")
        print(f"      作者: {author}  日期: {date}")

    if args.json:
        print("\n--- JSON ---")
        print(json.dumps(all_commits, ensure_ascii=False, indent=2))
    return all_commits


def cmd_is_merged(args):
    """检查 PR 是否已合并。"""
    path = f"/repos/{args.repo}/pulls/{args.number}/merge"
    try:
        result = api_request("GET", path)
        merged = result.get("merged", False)
    except SystemExit:
        # 404 表示未合并
        merged = False

    if merged:
        print(f"✅ PR #{args.number} 已合并")
        print(f"   合并 SHA: {result.get('sha', 'N/A')}")
        print(f"   合并时间: {format_time(result.get('merged_at'))}")
    else:
        print(f"❌ PR #{args.number} 未合并")

    if args.json:
        print("\n--- JSON ---")
        print(json.dumps({"merged": merged}, ensure_ascii=False))
    return {"merged": merged}


def cmd_list_prs(args):
    """列出项目的 PR。"""
    params = {"state": args.state, "per_page": args.per_page}
    if args.source_branch:
        params["head"] = args.source_branch

    path = f"/repos/{args.repo}/pulls"
    result = api_request("GET", path, params=params)

    print(f"PR 列表 ({len(result)} 条, state={args.state})")
    print("=" * 80)
    for pr in result:
        num = pr.get("number", "?")
        title = pr.get("title", "N/A")
        state = pr.get("state", "N/A")
        source = pr.get("head", {}).get("ref", "N/A")
        target = pr.get("base", {}).get("ref", "N/A")
        updated = format_time(pr.get("updated_at"))
        print(f"  #{num} [{state}] {title}")
        print(f"      {source} → {target}  更新: {updated}")

    if args.json:
        print("\n--- JSON ---")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def cmd_get_review_comments(args):
    """获取代码审查意见（检视意见），筛选 gitcode-bot 的审查评论。"""
    path = f"/repos/{args.repo}/pulls/{args.number}/comments"
    params = {"per_page": 100, "page": 1, "comment_type": "review"}

    all_comments = []
    while True:
        result = api_request("GET", path, params=params)
        if not result:
            break
        all_comments.extend(result)
        if len(result) < params["per_page"]:
            break
        params["page"] += 1

    # 筛选审查意见
    review_comments = []
    for c in all_comments:
        user = c.get("user", {}).get("login", "")
        body = c.get("body", "")
        if is_bot_user(user) and ("Priority" in body or "检视" in body or "审查" in body):
            review_comments.append(c)

    print(f"PR #{args.number} 代码审查意见 ({len(review_comments)} 条)")
    print("=" * 80)

    unresolved = []
    for i, c in enumerate(review_comments):
        user = c.get("user", {}).get("login", "unknown")
        created = format_time(c.get("created_at"))
        cid = c.get("id", "")
        body = c.get("body", "")

        # 解析优先级
        if "🔴" in body or "Critical" in body:
            priority = "🔴 Critical"
        elif "🟠" in body or "High" in body:
            priority = "🟠 High"
        elif "🟡" in body or "Medium" in body:
            priority = "🟡 Medium"
        elif "🔵" in body or "Low" in body:
            priority = "🔵 Low"
        else:
            priority = "⚪ Info"

        print(f"\n[{i+1}] {priority} — {user} ({created})")
        print(f"    comment_id: {cid}")
        print(f"    {truncate(body, args.max_length)}")
        unresolved.append({"index": i+1, "priority": priority, "comment_id": cid, "body": body})

    if unresolved:
        print(f"\n--- 待处理审查意见: {len(unresolved)} 条 ---")
        for u in unresolved:
            print(f"  [{u['index']}] {u['priority']} (comment_id: {u['comment_id']})")

    if args.json:
        print("\n--- JSON ---")
        print(json.dumps(review_comments, ensure_ascii=False, indent=2))
    return review_comments


# ── AI Review 监控 ────────────────────────────────────────────────

# atomgit-bot 评论分类关键词
SUMMARY_GENERATING_MARKERS = ["正在生成合并请求摘要", "正在生成合并请求摘要，请稍候"]
REVIEW_IN_PROGRESS_MARKERS = ["AI 代码检视正在进行中", "AI 代码检视正在进行中，请稍候"]
SUMMARY_READY_MARKERS = ["变更摘要"]
# CI 状态评论关键词（ohpcd-robot 等，非检视意见，不需要回复）
CI_STATUS_MARKERS = ["CI 校验", "CI 构建", "CI 检验", "CI 自动", "CI流水线",
                     "校验排队", "校验通过", "校验失败",
                     "构建已启动", "构建成功", "构建失败"]


def classify_comment(body: str) -> str:
    """将 bot 评论内容分类。

    Returns:
        "summary_generating" — 正在生成摘要
        "review_in_progress" — AI 检视进行中
        "summary_ready"      — 变更摘要已生成
        "ci_status"          — CI 状态通知（非检视意见，不需要回复）
        "review_opinion"     — 检视意见（需处理）
        "unknown"            — 未知类型
    """
    if not body:
        return "unknown"
    for marker in SUMMARY_GENERATING_MARKERS:
        if marker in body:
            return "summary_generating"
    for marker in REVIEW_IN_PROGRESS_MARKERS:
        if marker in body:
            return "review_in_progress"
    for marker in SUMMARY_READY_MARKERS:
        if marker in body:
            return "summary_ready"
    # CI 状态通知（非检视意见）
    for marker in CI_STATUS_MARKERS:
        if marker in body:
            return "ci_status"
    return "review_opinion"


def cmd_monitor_review(args):
    """监控 atomgit-bot AI 检视状态，返回结构化 JSON。

    检视状态 (state):
        no_bot_comments    — 尚无 atomgit-bot 评论
        generating         — 仅含"正在生成"和"检视进行中"，尚未出摘要
        summary_ready      — 变更摘要已生成，无检视意见
        has_opinions       — 已出现检视意见，需 AI 评估处理

    输出 JSON 字段:
        state              — 上述状态之一
        phase              — 数字阶段 (0=未开始, 1=等待摘要, 2=摘要就绪, 3=有检视意见)
        summary_content    — 变更摘要评论全文 (state=summary_ready/has_opinions 时)
        review_opinions    — 检视意见列表 [{comment_id, body, created_at, discussion_id}]
        bot_comment_count  — atomgit-bot 评论总数
        all_comments_count — 全部评论数 (含人工)
    """
    path = f"/repos/{args.repo}/pulls/{args.number}/comments"
    params = {"per_page": 100, "page": 1}

    all_comments = []
    while True:
        result = api_request("GET", path, params=params)
        if not result:
            break
        all_comments.extend(result)
        if len(result) < params["per_page"]:
            break
        params["page"] += 1

    # 筛选 atomgit-bot 评论（按时间排序）
    bot_comments = [
        c for c in all_comments
        if is_bot_user(c.get("user", {}).get("login", ""))
    ]
    # 按创建时间排序
    bot_comments.sort(key=lambda c: c.get("created_at", ""))

    # 分类每条评论
    classified = []
    summary_content = None
    review_opinions = []

    for c in bot_comments:
        body = c.get("body", "")
        category = classify_comment(body)
        entry = {
            "comment_id": c.get("id", ""),
            "discussion_id": c.get("discussion_id", c.get("in_reply_to", "")),
            "created_at": c.get("created_at", ""),
            "category": category,
            "body": body,
        }
        classified.append(entry)

        if category == "summary_ready":
            summary_content = body
        elif category == "review_opinion":
            review_opinions.append({
                "comment_id": c.get("id", ""),
                "discussion_id": c.get("discussion_id", c.get("in_reply_to", "")),
                "created_at": c.get("created_at", ""),
                "body": body,
            })

    # 判断整体状态
    categories = [c["category"] for c in classified]
    has_summary = "summary_ready" in categories
    has_opinions = len(review_opinions) > 0

    if not bot_comments:
        state = "no_bot_comments"
        phase = 0
    elif not has_summary and not has_opinions:
        # 只有"正在生成"和"检视进行中"
        state = "generating"
        phase = 1
    elif has_summary and not has_opinions:
        state = "summary_ready"
        phase = 2
    elif has_opinions:
        state = "has_opinions"
        phase = 3
    else:
        state = "unknown"
        phase = 0

    output = {
        "state": state,
        "phase": phase,
        "summary_content": summary_content,
        "review_opinions": review_opinions,
        "unreplied_opinions": unreplied_opinions,
        "bot_comment_count": len(bot_comments),
        "all_comments_count": len(all_comments),
        "classified_comments": classified,
    }

    # 人类可读输出
    state_desc = {
        "no_bot_comments": "尚无 atomgit-bot 评论",
        "generating": "⏳ AI 检视进行中（摘要尚未生成）",
        "summary_ready": "📋 变更摘要已生成，等待检视意见",
        "has_opinions": "🔍 已有检视意见，需评估处理",
        "unknown": "❓ 未知状态",
    }
    print(f"AI Review 状态: {state_desc.get(state, state)}")
    print(f"  Phase: {phase}")
    print(f"  atomgit-bot 评论数: {len(bot_comments)}")
    print(f"  全部评论数: {len(all_comments)}")
    if summary_content:
        print(f"\n--- 变更摘要 ---")
        print(truncate(summary_content, 2000))
    if review_opinions:
        print(f"\n--- 检视意见 ({len(review_opinions)} 条) ---")
        for i, op in enumerate(review_opinions):
            print(f"\n[{i+1}] comment_id: {op['comment_id']}")
            if op.get("discussion_id"):
                print(f"    discussion_id: {op['discussion_id']}")
            print(f"    {truncate(op['body'], 800)}")
    if unreplied_opinions:
        print(f"\n--- ⚠️ 未回复检视意见 ({len(unreplied_opinions)} 条，闭环未完成) ---")
        for op in unreplied_opinions:
            print(f"  comment_id: {op['comment_id']}: {truncate(op['body'], 100)}")

    if args.json:
        print("\n--- JSON ---")
        print(json.dumps(output, ensure_ascii=False, indent=2))
    return output


# ── CLI ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="GitCode PR 管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--token", help="GitCode access_token (默认从 ~/.gitcode-token 读取)")
    parser.add_argument("--json", action="store_true", help="输出原始 JSON")
    sub = parser.add_subparsers(dest="command", help="子命令")

    # setup
    p = sub.add_parser("setup", help="引导创建 GitCode access_token")
    p.add_argument("--force", action="store_true", help="覆盖已有 token")
    p.set_defaults(func=cmd_setup)

    # create-pr
    p = sub.add_parser("create-pr", help="创建 PR")
    p.add_argument("--repo", required=True, help="owner/repo 格式的仓库路径")
    p.add_argument("--source", required=True, help="源分支名")
    p.add_argument("--target", required=True, help="目标分支名")
    p.add_argument("--title", required=True, help="PR 标题")
    p.add_argument("--description", help="PR 描述")
    p.add_argument("--milestone", type=int, help="里程碑编号")
    p.set_defaults(func=cmd_create_pr)

    # get-pr
    p = sub.add_parser("get-pr", help="获取单个 PR 详情")
    p.add_argument("--repo", required=True)
    p.add_argument("--number", type=int, required=True, help="PR 编号")
    p.set_defaults(func=cmd_get_pr)

    # get-comments
    p = sub.add_parser("get-comments", help="获取 PR 评论")
    p.add_argument("--repo", required=True)
    p.add_argument("--number", type=int, required=True)
    p.add_argument("--all-comments", action="store_true", help="显示所有评论 (默认只显示机器人评论)")
    p.add_argument("--max-length", type=int, default=800, help="每条评论最大显示长度")
    p.set_defaults(func=cmd_get_comments)

    # ci-status
    p = sub.add_parser("ci-status", help="获取最新 CI 状态")
    p.add_argument("--repo", required=True)
    p.add_argument("--number", type=int, required=True)
    p.set_defaults(func=cmd_ci_status)

    # trigger-ci
    p = sub.add_parser("trigger-ci", help="评论 /rebuild 主动触发 CI 构建")
    p.add_argument("--repo", required=True)
    p.add_argument("--number", type=int, required=True)
    p.add_argument("--json", action="store_true", help="输出原始 JSON")
    p.set_defaults(func=cmd_trigger_ci)

    # reply-comment
    p = sub.add_parser("reply-comment", help="回复 PR 评论")
    p.add_argument("--repo", required=True)
    p.add_argument("--number", type=int, required=True)
    p.add_argument("--discussion-id", required=True, help="讨论 ID")
    p.add_argument("--body", required=True, help="回复内容")
    p.set_defaults(func=cmd_reply_comment)

    # resolve-comment
    p = sub.add_parser("resolve-comment", help="修改检视意见解决状态 (标记为已解决/未解决)")
    p.add_argument("--repo", required=True)
    p.add_argument("--number", type=int, required=True)
    p.add_argument("--discussion-id", required=True, help="讨论 ID")
    p.add_argument("--unresolved", action="store_true", help="标记为未解决 (默认标记为已解决)")
    p.set_defaults(func=cmd_resolve_comment)

    # handle-review-opinion
    p = sub.add_parser("handle-review-opinion", help="处理单条检视意见 (在讨论串内回复+标记已解决)")
    p.add_argument("--repo", required=True)
    p.add_argument("--number", type=int, required=True)
    p.add_argument("--comment-id", required=False, help="检视意见评论 ID (首选, monitor-review 的 comment_id)")
    p.add_argument("--discussion-id", required=False, help="检视意见讨论 ID (旧参数, 可能为空)")
    p.add_argument("--action", required=True, choices=["accept", "reject"],
                   help="accept=接纳并修复(回复+标记已解决), reject=拒绝(仅回复)")
    p.add_argument("--reason", required=True, help="修复说明或拒绝原因")
    p.set_defaults(func=cmd_handle_review_opinion)

    # update-pr
    p = sub.add_parser("update-pr", help="更新 PR 信息")
    p.add_argument("--repo", required=True)
    p.add_argument("--number", type=int, required=True)
    p.add_argument("--title", help="新标题")
    p.add_argument("--description", help="新描述 (传空字符串清除)")
    p.add_argument("--state", choices=["open", "closed"], help="PR 状态")
    p.set_defaults(func=cmd_update_pr)

    # get-commits
    p = sub.add_parser("get-commits", help="获取 PR 的所有 commit")
    p.add_argument("--repo", required=True)
    p.add_argument("--number", type=int, required=True)
    p.set_defaults(func=cmd_get_commits)

    # is-merged
    p = sub.add_parser("is-merged", help="检查 PR 是否已合并")
    p.add_argument("--repo", required=True)
    p.add_argument("--number", type=int, required=True)
    p.set_defaults(func=cmd_is_merged)

    # list-prs
    p = sub.add_parser("list-prs", help="列出项目 PR")
    p.add_argument("--repo", required=True)
    p.add_argument("--state", default="open", choices=["open", "closed", "all", "merged"])
    p.add_argument("--source-branch", help="按源分支筛选")
    p.add_argument("--per-page", type=int, default=20)
    p.set_defaults(func=cmd_list_prs)

    # get-review-comments
    p = sub.add_parser("get-review-comments", help="获取代码审查意见")
    p.add_argument("--repo", required=True)
    p.add_argument("--number", type=int, required=True)
    p.add_argument("--max-length", type=int, default=800)
    p.set_defaults(func=cmd_get_review_comments)

    # monitor-review
    p = sub.add_parser("monitor-review", help="监控 atomgit-bot AI 检视状态")
    p.add_argument("--repo", required=True)
    p.add_argument("--number", type=int, required=True)
    p.add_argument("--json", action="store_true", help="输出结构化 JSON")
    p.set_defaults(func=cmd_monitor_review)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 如果通过 --token 传入了 token，设置环境变量
    if args.token:
        os.environ["GITCODE_TOKEN"] = args.token

    args.func(args)


if __name__ == "__main__":
    main()
