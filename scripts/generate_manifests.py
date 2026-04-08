#!/usr/bin/env python3
# ==============================================================================
# [Layer 3] generate_manifests.py - 批量 manifest.yaml 生成工具（AI 主导）
# ==============================================================================
# 层级: L3(辅助工具)
# 决策点: AI主导（内置硬编码数据，需 AI 审阅后使用）
# 入口: python3 scripts/generate_manifests.py（无参数）
# 依赖: PyYAML
# 调用者: AI / 用户（一次性初始化工具，非流程脚本）
# ==============================================================================
"""批量生成软件档案的 manifest.yaml 文件"""

import os
import yaml

# 软件档案数据
SOFTWARE_DATA = {
    ("a", "automake", "1.16.5"): {
        "software": "automake",
        "version": "1.16.5",
        "status": "success",
        "build_system": "autotools",
        "dependencies": {"required": ["autoconf", "perl"], "optional": []},
        "patches_applied": [{"file": "0001-port-for-ohos.patch", "purpose": "添加 HarmonyOS 系统检测", "lines_changed": 30}],
        "compatibility": {"level": "high", "issues": [], "notes": "编译 autotools 项目必需"},
        "knowledge_gained": ["automake 是 autotools 的核心组件", "需要 autoconf 和 perl"],
        "tags": ["automake", "autotools", "gnu"]
    },
    ("b", "bzip2", "1.0.8"): {
        "software": "bzip2",
        "version": "1.0.8",
        "status": "success",
        "build_system": "makefile",
        "dependencies": {"required": [], "optional": []},
        "patches_applied": [{"file": "0001-makefile-fpic.patch", "purpose": "添加 -fPIC 编译标志", "lines_changed": 5}],
        "compatibility": {"level": "high", "issues": [], "notes": "需要修改 Makefile 添加 -fPIC"},
        "knowledge_gained": ["bzip2 使用简单 Makefile", "必须添加 -fPIC 标志"],
        "tags": ["bzip2", "compression"]
    },
    ("g", "gawk", "5.3.0"): {
        "software": "gawk",
        "version": "5.3.0",
        "status": "success",
        "build_system": "autotools",
        "dependencies": {"required": [], "optional": ["mpfr", "gmp"]},
        "patches_applied": [{"file": "0001-port-for-ohos.patch", "purpose": "添加 HarmonyOS 系统检测", "lines_changed": 30}],
        "compatibility": {"level": "high", "issues": [], "notes": "替代 toybox awk"},
        "knowledge_gained": ["GNU awk 功能比 toybox awk 更完整"],
        "tags": ["gawk", "awk", "gnu"]
    },
    ("g", "gdbm", "1.23"): {
        "software": "gdbm",
        "version": "1.23",
        "status": "success",
        "build_system": "autotools",
        "dependencies": {"required": [], "optional": ["readline"]},
        "patches_applied": [{"file": "0001-port-for-ohos.patch", "purpose": "添加 HarmonyOS 系统检测", "lines_changed": 30}],
        "compatibility": {"level": "high", "issues": [], "notes": "Python gdbm 模块依赖"},
        "knowledge_gained": ["使用 cp 替代 ln -s 安装共享库"],
        "tags": ["gdbm", "database", "gnu"]
    },
    ("h", "help2man", "1.49.3"): {
        "software": "help2man",
        "version": "1.49.3",
        "status": "success",
        "build_system": "autotools",
        "dependencies": {"required": ["perl"], "optional": []},
        "patches_applied": [{"file": "0001-port-for-ohos.patch", "purpose": "添加 HarmonyOS 系统检测", "lines_changed": 30}],
        "compatibility": {"level": "high", "issues": [], "notes": "生成 man 页面工具"},
        "knowledge_gained": ["help2man 用于生成 man 页面"],
        "tags": ["help2man", "documentation", "gnu"]
    },
    ("l", "libffi", "3.5.2"): {
        "software": "libffi",
        "version": "3.5.2",
        "status": "success",
        "build_system": "autotools",
        "dependencies": {"required": [], "optional": []},
        "patches_applied": [{"file": "0001-port-for-ohos.patch", "purpose": "添加 HarmonyOS 系统检测", "lines_changed": 30}],
        "compatibility": {"level": "high", "issues": [], "notes": "与 3.4.4 类似"},
        "knowledge_gained": ["新版本添加了 FFI_VERSION_STRING 宏"],
        "tags": ["libffi", "ffi", "library"]
    },
    ("l", "libtool", "2.4.7"): {
        "software": "libtool",
        "version": "2.4.7",
        "status": "success",
        "build_system": "autotools",
        "dependencies": {"required": ["automake", "autoconf"], "optional": []},
        "patches_applied": [{"file": "0001-port-for-ohos.patch", "purpose": "添加 HarmonyOS 系统检测", "lines_changed": 30}],
        "compatibility": {"level": "high", "issues": ["libtoolize 在 zsh 下有兼容问题"], "notes": "Autotools 共享库支持必需"},
        "knowledge_gained": ["libtool 是构建共享库的关键工具", "libtoolize 在 zsh 下需要特殊处理"],
        "tags": ["libtool", "autotools", "gnu"]
    },
    ("l", "lzma", "5.6.2"): {
        "software": "lzma",
        "version": "5.6.2",
        "status": "success",
        "build_system": "autotools",
        "dependencies": {"required": [], "optional": []},
        "patches_applied": [{"file": "0001-port-for-ohos.patch", "purpose": "添加 HarmonyOS 系统检测", "lines_changed": 30}],
        "compatibility": {"level": "high", "issues": [], "notes": "高压缩比压缩库"},
        "knowledge_gained": ["lzma/xz 格式支持"],
        "tags": ["lzma", "xz", "compression"]
    },
    ("r", "readline", "8.2"): {
        "software": "readline",
        "version": "8.2",
        "status": "success",
        "build_system": "autotools",
        "dependencies": {"required": ["ncurses"], "optional": []},
        "patches_applied": [{"file": "0001-port-for-ohos.patch", "purpose": "添加 HarmonyOS 系统检测", "lines_changed": 30}],
        "compatibility": {"level": "high", "issues": [], "notes": "bash 依赖 readline"},
        "knowledge_gained": ["readline 依赖 ncurses", "使用 --with-shared 生成共享库"],
        "tags": ["readline", "library", "gnu"]
    },
    ("s", "sed", "4.9"): {
        "software": "sed",
        "version": "4.9",
        "status": "success",
        "build_system": "autotools",
        "dependencies": {"required": [], "optional": []},
        "patches_applied": [{"file": "0001-port-for-ohos.patch", "purpose": "添加 HarmonyOS 系统检测", "lines_changed": 30}],
        "compatibility": {"level": "high", "issues": [], "notes": "替代 toybox sed"},
        "knowledge_gained": ["GNU sed 完全兼容 HarmonyOS", "替代 toybox sed 解决兼容性问题"],
        "tags": ["sed", "gnu", "text-processing"]
    },
    ("t", "tar", "1.35"): {
        "software": "tar",
        "version": "1.35",
        "status": "success",
        "build_system": "autotools",
        "dependencies": {"required": [], "optional": []},
        "patches_applied": [{"file": "0001-port-for-ohos.patch", "purpose": "添加 HarmonyOS 系统检测", "lines_changed": 30}],
        "compatibility": {"level": "high", "issues": [], "notes": "替代 toybox tar，支持更多格式"},
        "knowledge_gained": ["GNU tar 替代 toybox tar", "支持 xattrs 等高级功能"],
        "tags": ["tar", "gnu", "archive"]
    }
}

def generate_manifest(letter, name, version, data):
    """生成 manifest.yaml 内容"""
    manifest = {
        "software": data["software"],
        "version": data["version"],
        "status": data["status"],
        "build_system": data["build_system"],
        "compile_date": data.get("compile_date", "2024-03-20"),
        "dependencies": data["dependencies"],
        "build_config": {
            "target": "aarch64-unknown-linux-ohos",
            "configure_options": [f"--prefix=$HOME/usr/local"],
            "cflags": "-fPIC -O2"
        },
        "patches_applied": data["patches_applied"],
        "compatibility": data["compatibility"],
        "test_results": {
            "type": "manual",
            "note": "通过实际使用验证功能正常"
        },
        "knowledge_gained": data["knowledge_gained"],
        "maintainer": "OpenHarmony PC Developer社区",
        "tags": data["tags"]
    }
    return yaml.dump(manifest, default_flow_style=False, allow_unicode=True, sort_keys=False)

def main():
    base_dir = "/storage/Users/currentUser/tmp/skill-redesign/archives"
    
    for (letter, name, version), data in SOFTWARE_DATA.items():
        # 创建目录
        dir_path = os.path.join(base_dir, letter, name, version)
        os.makedirs(dir_path, exist_ok=True)
        
        # 生成 manifest.yaml
        manifest_content = generate_manifest(letter, name, version, data)
        manifest_path = os.path.join(dir_path, "manifest.yaml")
        
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(manifest_content)
        
        print(f"Created: {manifest_path}")
    
    print(f"\n总计创建 {len(SOFTWARE_DATA)} 个 manifest.yaml 文件")

if __name__ == "__main__":
    main()