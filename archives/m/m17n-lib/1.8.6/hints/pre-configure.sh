#!/bin/sh
# 修复源码包缺少 bison 生成的 plural.h 文件问题
# m17n-lib 1.8.6 发布包中缺少 intl/plural.h，需要从 plural.y 生成
# 方案：优先使用预置的 plural.h，如果预置文件不存在则尝试 bison 生成

cd intl

if [ -f plural.y ] && [ ! -f plural.h ]; then
    echo "Generating or copying plural.h..."

    # 方案 1：优先使用预置文件（从 hints 目录）
    if [ -f "../hints/plural.h" ]; then
        echo "Using pre-generated plural.h from hints directory..."
        cp "../hints/plural.h" plural.h

        if [ -f plural.h ]; then
            echo "✓ plural.h copied successfully"
        else
            echo "✗ Failed to copy plural.h"
            exit 1
        fi
    else
        # 方案 2：尝试 bison 生成（如果预置文件不存在）
        echo "Generating plural.h from plural.y using bison..."
        bison -d plural.y --header=plural.h 2>&1 | grep -v "warning: deprecated directive" || true

        if [ -f plural.h ]; then
            echo "✓ plural.h generated successfully"
        else
            echo "✗ Failed to generate plural.h"
            echo "Note: Please ensure bison is installed or provide pre-generated plural.h in hints directory"
            exit 1
        fi
    fi
fi