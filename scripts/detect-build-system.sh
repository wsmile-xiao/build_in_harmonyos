#!/bin/sh
# detect-build-system.sh - 检测软件使用的构建系统类型
# 用法: ./detect-build-system.sh <源码目录>

set -e

SOURCE_DIR="${1:-.}"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "错误: 目录不存在: $SOURCE_DIR"
    exit 1
fi

cd "$SOURCE_DIR"

# 检测函数
detect() {
    # 优先级从高到低检测
    
    # 1. 自定义 Perl Configure (OpenSSL 风格)
    if [ -f "Configure" ] && [ -x "Configure" ] && head -1 Configure 2>/dev/null | grep -q "perl"; then
        echo "custom-perl"
        return 0
    fi
    
    # 2. Autotools
    if [ -f "configure" ] && [ -x "configure" ]; then
        echo "autotools"
        return 0
    fi
    
    # 3. CMake
    if [ -f "CMakeLists.txt" ]; then
        echo "cmake"
        return 0
    fi
    
    # 4. Meson
    if [ -f "meson.build" ]; then
        echo "meson"
        return 0
    fi
    
    # 5. QMake
    if ls *.pro 1>/dev/null 2>&1; then
        echo "qmake"
        return 0
    fi
    
    # 6. Autotools (需要生成)
    if [ -f "configure.ac" ] || [ -f "configure.in" ]; then
        echo "autotools-needs-bootstrap"
        return 0
    fi
    
    # 7. 简单 Makefile
    if [ -f "Makefile" ] || [ -f "makefile" ] || ls *.mk 1>/dev/null 2>&1; then
        echo "makefile"
        return 0
    fi
    
    # 8. 未知
    echo "unknown"
    return 1
}

# 输出详细信息
print_info() {
    local build_system=$(detect)
    
    echo "构建系统: $build_system"
    echo ""
    echo "检测到的文件:"
    
    case $build_system in
        custom-perl)
            echo "  - Configure (Perl 脚本)"
            [ -d "Configurations" ] && echo "  - Configurations/"
            ;;
        autotools)
            echo "  - configure"
            [ -f "Makefile.am" ] && echo "  - Makefile.am"
            [ -f "configure.ac" ] && echo "  - configure.ac"
            [ -f "config.guess" ] && echo "  - config.guess"
            [ -f "config.sub" ] && echo "  - config.sub"
            ;;
        cmake)
            echo "  - CMakeLists.txt"
            find . -name "*.cmake" -type f 2>/dev/null | head -5 | sed 's/^/  - /'
            ;;
        meson)
            echo "  - meson.build"
            [ -f "meson_options.txt" ] && echo "  - meson_options.txt"
            ;;
        makefile)
            echo "  - Makefile 或 *.mk"
            ;;
    esac
    
    echo ""
    echo "推荐的编译命令:"
    case $build_system in
        custom-perl)
            echo "  ./Configure --prefix=\$HOME/usr/local <选项>"
            echo "  make -j\$(nproc)"
            echo "  make install"
            ;;
        autotools)
            echo "  ./configure --prefix=\$HOME/usr/local"
            echo "  make -j\$(nproc)"
            echo "  make install"
            ;;
        cmake)
            echo "  cmake -DCMAKE_INSTALL_PREFIX=\$HOME/usr/local .."
            echo "  make -j\$(nproc)"
            echo "  make install"
            ;;
        meson)
            echo "  meson setup builddir --prefix=\$HOME/usr/local"
            echo "  meson compile -C builddir"
            echo "  meson install -C builddir"
            ;;
        makefile)
            echo "  make"
            echo "  make install PREFIX=\$HOME/usr/local"
            ;;
    esac
}

# 主逻辑
if [ "$2" = "--info" ]; then
    print_info
else
    detect
fi