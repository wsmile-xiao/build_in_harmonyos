"""Pre-analysis: 鸿蒙PC平台适配静态分析

在编译前静态分析软件源码，识别鸿蒙PC平台适配需求。
鸿蒙PC是独立OS（同等级于macOS/Linux/Windows），不能用Linux伪装。

分析维度:
  1. 构建系统检测（cmake/autotools/meson/makefile/python）
  2. 平台API使用（syscall/dlopen/X11/Wayland/PulseAudio等）
  3. 图形依赖（X11/OpenGL/Vulkan/Wayland/Qt/GTK）
  4. 系统集成（open命令/文件关联/D-Bus/通知/托盘）
  5. 音视频依赖（ALSA/PulseAudio/Pipewire/ffmpeg）
  6. 已知限制检查（对照需求图谱 knowledge/requirements/）

输出: archives/{software}/{version}/pre-analysis.md
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# ── 鸿蒙PC平台能力清单 ──
HARMONYOS_PC_CAPABILITIES = {
    "libc": "musl libc (非glibc)，缺部分GNU扩展",
    "toolchain": "LLVM/Clang only (无gcc)",
    "filesystem": "HMDFS (不支持symlink/hardlink/FIFO)",
    "graphics": "无X11/Wayland，有ArkUI渲染框架",
    "audio": "无ALSA/PulseAudio/Pipewire，有OHAudio",
    "video": "有多媒体框架但API不同于ffmpeg CLI",
    "ipc": "无D-Bus，有SoftBus/Ashmem",
    "shell": "/data/service/hnp/bin/bash (非标准/bin/bash)",
    "signing": "ELF签名必须匹配运行环境",
    "syscall": "部分syscall行为与Linux不同(fstat/lseek/setreuid等)",
}

# ── 关键检测模式 ──
DETECTION_PATTERNS = {
    "build_system": {
        "cmake": [r"CMakeLists\.txt", r"\.cmake$"],
        "autotools": [r"configure\.ac", r"Makefile\.am", r"configure\b"],
        "meson": [r"meson\.build"],
        "makefile": [r"^Makefile$", r"^makefile$", r"\.mk$"],
        "python": [r"setup\.py", r"pyproject\.toml", r"setup\.cfg"],
        "rust": [r"Cargo\.toml"],
        "go": [r"go\.mod"],
    },
    "graphics": {
        "X11": [r"#include.*<X11/", r"-lX11", r"XOpenDisplay", r"XCreateWindow"],
        "Wayland": [r"#include.*<wayland", r"wl_display_connect"],
        "OpenGL": [r"#include.*<GL/gl", r"glBegin", r"glGenTextures", r"-lGL"],
        "Vulkan": [r"#include.*<vulkan", r"vkCreateInstance"],
        "Qt": [r"#include.*<Q", r"QApplication", r"-lQt"],
        "GTK": [r"#include.*<gtk", r"gtk_init", r"-lgtk"],
        "SDL": [r"#include.*<SDL", r"SDL_Init", r"-lSDL"],
    },
    "audio_video": {
        "ALSA": [r"#include.*<alsa/", r"snd_pcm_", r"-lasound"],
        "PulseAudio": [r"#include.*<pulse", r"pa_simple_new", r"-lpulse"],
        "Pipewire": [r"#include.*<pipewire", r"pw_loop"],
        "ffmpeg": [r"#include.*<libav", r"avcodec_", r"-lavcodec"],
        "GStreamer": [r"#include.*<gst/", r"gst_init", r"-lgst"],
    },
    "system_integration": {
        "open_cmd": [r"\bopen\s+", r"xdg-open", r"system\(\s*\".*open"],
        "dbus": [r"#include.*<dbus", r"dbus_", r"-ldbus"],
        "notify": [r"notify-send", r"libnotify", r"NotifyNotification"],
        "tray": [r"AppIndicator", r"gtk_status", r"systray"],
        "file_assoc": [r"xdg-mime", r"shared-mime"],
    },
    "platform_specific": {
        "linux_only": [r"__linux__", r"#ifdef\s+__linux", r"/proc/", r"/sys/"],
        "glibc_only": [r"__GLIBC__", r"gnu_get_libc", r"getauxval"],
        "posix_ext": [r"_GNU_SOURCE", r"_POSIX_C_SOURCE", r"_DEFAULT_SOURCE"],
        "syscall_direct": [r"syscall\(", r"__NR_", r"SYS_"],
        "dlopen": [r"dlopen\(", r"dlsym\(", r"lt_dlopen"],
    },
}

# ── 需求图谱条目结构 ──
REQUIREMENT_TEMPLATE = """id:                     R{NNN}
title:                  {title}
category:               {category}
severity:               {severity}
status:                 open
affected_software:      {software}
description:            {description}
needed_capability:      {needed}
current_workaround:     {workaround}
created_date:           {date}
closed_in_version:      
closed_date:            
contributors:           {contributor}
"""


def detect_build_system(src_dir: Path) -> list[str]:
    """检测构建系统类型"""
    found = []
    for system, patterns in DETECTION_PATTERNS["build_system"].items():
        for pat in patterns:
            try:
                result = list(src_dir.rglob("*"))
                for f in result:
                    if re.search(pat, str(f.name)):
                        if system not in found:
                            found.append(system)
                        break
            except Exception:
                continue
    return found


def scan_patterns(src_dir: Path, category: str) -> dict[str, list[str]]:
    """扫描源码中的平台依赖模式"""
    results = {}
    patterns = DETECTION_PATTERNS.get(category, {})

    # 限制扫描深度避免过慢
    for dep, pats in patterns.items():
        hits = []
        for pat in pats:
            try:
                for f in src_dir.rglob("*"):
                    if not f.is_file():
                        continue
                    # 只扫描文本文件
                    ext = f.suffix.lower()
                    if ext not in ('.c', '.h', '.cpp', '.cc', '.hpp', '.py',
                                   '.sh', '.cmake', '.txt', '.md', '.in',
                                   '.am', '.ac', '.build', '.rs', '.go',
                                   '.vala', '.ui', '.glade', '.xml', '.yaml',
                                   '.yml', '.json', '.toml', '.cfg', '', '.mk'):
                        continue
                    try:
                        content = f.read_text(encoding='utf-8', errors='ignore')
                        if re.search(pat, content, re.MULTILINE):
                            rel = str(f.relative_to(src_dir))
                            if rel not in hits:
                                hits.append(rel)
                    except Exception:
                        continue
            except Exception:
                continue
        if hits:
            results[dep] = hits[:5]  # 每个依赖最多5个文件示例
    return results


def check_requirements_graph(pdir: Path, software: str) -> list[dict]:
    """检查需求图谱中是否有与当前软件相关的未关闭需求"""
    req_dir = pdir / "knowledge" / "requirements"
    if not req_dir.exists():
        return []

    related = []
    for f in sorted(req_dir.glob("R*.kv")):
        try:
            content = f.read_text(encoding='utf-8')
            fields = {}
            for line in content.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                m = re.match(r'^(\w+):\s*(.*)', line)
                if m and m.group(1) not in fields:
                    fields[m.group(1)] = m.group(2).strip()

            if fields.get('status', '') == 'closed':
                continue
            affected = fields.get('affected_software', '')
            if software in affected or '*' in affected:
                related.append(fields)
        except Exception:
            continue
    return related


def generate_report(
    software: str,
    version: str,
    src_dir: Path,
    pdir: Path,
) -> str:
    """生成预分析报告"""
    import datetime

    build_systems = detect_build_system(src_dir)
    graphics = scan_patterns(src_dir, "graphics")
    audio_video = scan_patterns(src_dir, "audio_video")
    sys_integration = scan_patterns(src_dir, "system_integration")
    platform = scan_patterns(src_dir, "platform_specific")
    related_reqs = check_requirements_graph(pdir, software)

    # 生成报告
    lines = [
        f"# 预分析报告: {software} {version}",
        f"",
        f"> 生成日期: {datetime.date.today()}",
        f"> 源码目录: {src_dir}",
        f"",
        f"## 1. 构建系统",
        f"",
    ]

    if build_systems:
        for bs in build_systems:
            lines.append(f"- ✅ **{bs}**")
    else:
        lines.append("- ⚠️ 未检测到标准构建系统")

    lines.extend([
        f"",
        f"## 2. 图形依赖",
        f"",
    ])
    if graphics:
        for dep, files in graphics.items():
            impact = HARMONYOS_PC_CAPABILITIES.get("graphics", "")
            lines.append(f"- ⚠️ **{dep}**: 鸿蒙PC无此依赖。{impact}")
            for f in files:
                lines.append(f"  - `{f}`")
    else:
        lines.append("- ✅ 未检测到图形依赖")

    lines.extend([
        f"",
        f"## 3. 音视频依赖",
        f"",
    ])
    if audio_video:
        for dep, files in audio_video.items():
            lines.append(f"- ⚠️ **{dep}**: 鸿蒙PC音视频API不同。{HARMONYOS_PC_CAPABILITIES.get('audio', '')}")
            for f in files:
                lines.append(f"  - `{f}`")
    else:
        lines.append("- ✅ 未检测到音视频依赖")

    lines.extend([
        f"",
        f"## 4. 系统集成",
        f"",
    ])
    if sys_integration:
        for dep, files in sys_integration.items():
            lines.append(f"- ⚠️ **{dep}**: 鸿蒙PC可能不支持此功能")
            for f in files:
                lines.append(f"  - `{f}`")
    else:
        lines.append("- ✅ 未检测到系统集成依赖")

    lines.extend([
        f"",
        f"## 5. 平台特定代码",
        f"",
    ])
    if platform:
        for dep, files in platform.items():
            risk = {
                "linux_only": "高: 鸿蒙不是Linux，__linux__未定义",
                "glibc_only": "高: 鸿蒙用musl，无__GLIBC__",
                "posix_ext": "中: 需确认_POSIX_C_SOURCE在musl下的行为",
                "syscall_direct": "高: 鸿蒙syscall行为可能与Linux不同",
                "dlopen": "中: dlopen可用但需注意ELF签名",
            }.get(dep, "需评估")
            lines.append(f"- ⚠️ **{dep}**: {risk}")
            for f in files:
                lines.append(f"  - `{f}`")
    else:
        lines.append("- ✅ 未检测到平台特定代码")

    lines.extend([
        f"",
        f"## 6. 关联未关闭需求",
        f"",
    ])
    if related_reqs:
        for req in related_reqs:
            lines.append(f"- 🔴 **{req.get('id', '?')}**: {req.get('title', '')} (严重度: {req.get('severity', '?')})")
            lines.append(f"  - 需要能力: {req.get('needed_capability', '未描述')}")
            lines.append(f"  - 当前变通: {req.get('current_workaround', '无')}")
    else:
        lines.append("- ✅ 需求图谱中无关联未关闭需求")

    # 适配建议
    lines.extend([
        f"",
        f"## 7. 适配建议",
        f"",
    ])

    has_issues = bool(graphics or audio_video or sys_integration or platform)
    if has_issues:
        lines.append("⚠️ 本软件需要平台适配，不能仅编译通过。重点关注:")
        if graphics:
            lines.append(f"- 图形: 需替换为ArkUI兼容方案或条件编译跳过")
        if audio_video:
            lines.append(f"- 音视频: 需使用OHAudio或多媒体框架替代")
        if sys_integration:
            lines.append(f"- 系统集成: 需用鸿蒙等价API或降级处理")
        if platform:
            lines.append(f"- 平台代码: 需用#ifdef __OHOS__守卫做兼容")
        lines.append("")
        lines.append("**如遇系统能力缺失，提交需求图谱条目:**")
        lines.append(f"```bash")
        lines.append(f"python3 $SKILL_ROOT/scripts/ohc-run.py req add \\")
        lines.append(f"  --title \"{software}需要XXX能力\" \\")
        lines.append(f"  --category graphics \\")
        lines.append(f"  --severity 2 \\")
        lines.append(f"  --software {software} \\")
        lines.append(f"  --description \"详细描述\" \\")
        lines.append(f"  --needed \"需要的API/能力\"")
        lines.append(f"```")
    else:
        lines.append("✅ 未检测到明显的平台适配障碍，可继续编译流程。")

    return '\n'.join(lines)


def run_pre_analysis(
    software: str,
    version: str,
    pdir: str | None = None,
) -> int:
    """执行预分析并生成报告"""
    from .utils import find_project_dir, log_info, log_ok, log_fail

    project = Path(pdir) if pdir else Path(find_project_dir())
    archive_dir = project / "archives" / software[:1].lower() / f"{software}-{version}"
    src_dir = archive_dir / "src"

    if not src_dir.exists():
        # 尝试其他路径
        for p in archive_dir.iterdir() if archive_dir.exists() else []:
            if p.is_dir() and (p / "configure.ac").exists() or (p / "CMakeLists.txt").exists():
                src_dir = p
                break

    if not src_dir.exists():
        log_fail(f"源码目录不存在: {src_dir}")
        log_info("请先执行 init-build 下载源码")
        return 1

    log_info(f"🔍 预分析: {software} {version}")
    log_info(f"   源码: {src_dir.relative_to(project)}")

    report = generate_report(software, version, src_dir, project)

    report_path = archive_dir / "pre-analysis.md"
    report_path.write_text(report, encoding='utf-8')
    log_ok(f"✅ 预分析报告: {report_path.relative_to(project)}")

    # 简要输出
    has_issues = "⚠️" in report
    if has_issues:
        log_info("⚠️ 检测到平台适配需求，请查阅报告")
    else:
        log_info("✅ 未检测到明显适配障碍")

    return 0


def pre_analysis_cli(argv: list[str] | None = None) -> int:
    """CLI entry: ohc pre-analysis <software> <version> [--project-dir P]"""
    import argparse
    parser = argparse.ArgumentParser(prog="ohc pre-analysis", description="鸿蒙PC平台适配预分析")
    parser.add_argument("software", help="软件名 (e.g. zlib)")
    parser.add_argument("version", help="版本号 (e.g. 1.3.1)")
    parser.add_argument("--project-dir", default=None)
    args = parser.parse_args(argv)
    return run_pre_analysis(args.software, args.version, pdir=args.project_dir)
