#!/data/service/hnp/bin/bash
# test_package/test.sh — verify lxc-templates-legacy template scripts are installed
set -eu

# Get the package root from environment (set by test_package/conanfile.py)
PKG_ROOT="${CONAN_PKG_ROOT:-}"
if [ -z "$PKG_ROOT" ]; then
    echo "ERROR: CONAN_PKG_ROOT not set"
    exit 1
fi

SHARE_DIR="$PKG_ROOT/usr/share/lxc"
TEMPLATES_DIR="$SHARE_DIR/templates"
CONFIG_DIR="$SHARE_DIR/config"

if [ ! -d "$TEMPLATES_DIR" ]; then
    echo "ERROR: Templates directory not found: $TEMPLATES_DIR"
    exit 1
fi

# Count template scripts
TEMPLATE_COUNT=$(ls "$TEMPLATES_DIR"/lxc-* 2>/dev/null | wc -l)
if [ "$TEMPLATE_COUNT" -lt 20 ]; then
    echo "ERROR: Expected >= 20 template scripts, found $TEMPLATE_COUNT"
    exit 1
fi

# Count config files
if [ -d "$CONFIG_DIR" ]; then
    CONFIG_COUNT=$(ls "$CONFIG_DIR"/*.conf 2>/dev/null | wc -l)
else
    CONFIG_COUNT=0
fi
if [ "$CONFIG_COUNT" -lt 30 ]; then
    echo "ERROR: Expected >= 30 config files, found $CONFIG_COUNT"
    exit 1
fi

# Verify a specific template script exists
if [ ! -f "$TEMPLATES_DIR/lxc-alpine" ]; then
    echo "ERROR: lxc-alpine template not found"
    exit 1
fi

# Verify template script is readable and contains expected content
if ! grep -q "usage" "$TEMPLATES_DIR/lxc-alpine"; then
    echo "ERROR: lxc-alpine template should contain usage info"
    exit 1
fi

echo "OK: Verified $TEMPLATE_COUNT templates and $CONFIG_COUNT config files"
