#!/bin/sh
# liblangtag 补丁应用后需要运行 autoreconf 生成 configure
# 因为补丁修改了 configure.ac,需要重新生成构建脚本

set -e

echo "Running autoreconf to regenerate configure script..."

# 设置 AUTOM4TE 环境变量(如果需要)
if [ -z "$AUTOM4TE" ]; then
    AUTOM4TE="/storage/Users/currentUser/usr/local/bin/autom4te"
    export AUTOM4TE
fi

# 运行 autoreconf
autoreconf -fi

# 复制必要的辅助文件(如果 autoreconf 未生成)
for file in config.guess config.sub install-sh missing compile ar-lib; do
    if [ ! -f "$file" ]; then
        src="/storage/Users/currentUser/usr/local/share/automake-1.17/$file"
        if [ -f "$src" ]; then
            cp "$src" "$file"
            chmod +x "$file"
        fi
    fi
done

# 创建 gtk-doc.make (如果不存在)
if [ ! -f "gtk-doc.make" ]; then
    touch gtk-doc.make
fi

echo "Autoreconf completed successfully."
