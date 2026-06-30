#!/data/service/hnp/bin/bash

pkgname="taskflow"
pkgver="4.0.0"
url=""
pkgtype="cc"
buildsystem="cmake"
depends=()
makedepends=()
source="https://github.com/taskflow/taskflow/archive/refs/tags/v4.0.0.tar.gz"
builddir="taskflow-4.0.0"

download_and_extract() {
    local url=$source
    local filename=$(basename $url)

    # 检查压缩包是否存在
    if [[ -f $filename ]]; then
        echo "$filename压缩包已存在，跳过下载: $filename"
    else
        echo "$filename不存在，下载源码: $url"
        curl -L -o $filename $url
    fi

    # 解压,hmdfs 不支持硬链接，忽略硬链接错误
    echo "解压: $filename"
    tar -xf $filename 2>/dev/null
}

prepare() {
    # header-only库，外部目录构建
    mkdir -p $builddir/ohos-build
}

config() {
    cd $builddir/ohos-build
    # header-only库，关闭examples/tests，仅生成cmake config文件
    cmake -S../ \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
        -DTF_BUILD_EXAMPLES=OFF \
        -DTF_BUILD_TESTS=OFF \
        -DTF_BUILD_BENCHMARKS=OFF \
        -DTF_BUILD_PROFILER=OFF \
        -DTF_BUILD_CUDA=OFF
}

build() {
    cd $builddir/ohos-build
    # header-only库无实际编译，仅生成cmake config
    make --jobserver-style=pipe -j$(nproc)
}

# 调试阶段的安装函数，防止污染正式目录
test_install() {
    cd $builddir/ohos-build
    local staging_root="$HOME/tmp/test-install-${pkgname}-${pkgver}"
    rm -rf "$staging_root"
    make install DESTDIR="$staging_root"
}

# 正式的安装函数
install() {
    cd $builddir/ohos-build
    make install
}

check() {
    cd $builddir/ohos-build
    # header-only库，测试已关闭
    echo "header-only库无测试套件"
}

# Main logic
ACTION=${1:-print}
case $ACTION in
    prepare)
        prepare
        ;;
    config)
        config
        ;;
    build)
        build
        ;;
    test_install)
        test_install
        ;;
    install)
        install
        ;;
    check)
        check
        ;;
    *)
        echo "Unknown action: $ACTION"
        ;;
esac