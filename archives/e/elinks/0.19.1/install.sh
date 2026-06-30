#!/bin/sh
# elinks 0.19.1 安装脚本 (鸿蒙 PC 版)
PREFIX="${PREFIX:-$HOME/usr/local}"

mkdir -p "$PREFIX/bin" "$PREFIX/share/doc/elinks"

tar -xzf elinks-0.19.1-ohos-aarch64.tar.gz -C "$PREFIX"

# SSL certificate path fix for HTTPS
# OpenSSL was compiled with a temporary test path, not /etc/ssl
# Create wrapper script to set correct certificate path
if [ -f "$PREFIX/bin/elinks" ] && [ ! -f "$PREFIX/bin/elinks.real" ]; then
    mv "$PREFIX/bin/elinks" "$PREFIX/bin/elinks.real"
    cat > "$PREFIX/bin/elinks" << 'WRAPPER'
#!/bin/sh
# elinks wrapper - set SSL certificate path for HTTPS support
export SSL_CERT_FILE="/etc/ssl/certs/cacert.pem"
exec "${0}.real" "$@"
WRAPPER
    chmod +x "$PREFIX/bin/elinks"
fi

echo "elinks 0.19.1 安装完成"
echo "HTTPS SSL 证书路径已配置"
echo ""
echo "运行: $PREFIX/bin/elinks --version"
echo "HTTPS 测试: $PREFIX/bin/elinks -dump https://example.com"