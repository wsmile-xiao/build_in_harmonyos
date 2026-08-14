#!/bin/bash
# Verify the packaged arno-iptables-firewall scripts and support files.

set -euo pipefail

PKG_ROOT="${1:-}"

if [ -z "$PKG_ROOT" ]; then
    echo "ERROR: package folder path is required"
    exit 1
fi

# --- 1. Main firewall script exists and is executable ---
AIF_SCRIPT="$PKG_ROOT/sbin/arno-iptables-firewall"
if [ ! -f "$AIF_SCRIPT" ]; then
    echo "ERROR: $AIF_SCRIPT not found"
    exit 1
fi
if [ ! -x "$AIF_SCRIPT" ]; then
    echo "ERROR: $AIF_SCRIPT not executable"
    exit 1
fi

# --- 2. Version string check ---
if ! grep -F "2.0.3" "$AIF_SCRIPT" >/dev/null 2>&1; then
    echo "ERROR: version string '2.0.3' not found in $AIF_SCRIPT"
    exit 1
fi

# --- 3. Script shebang check ---
SHEBANG=$(head -1 "$AIF_SCRIPT")
if [ "$SHEBANG" != "#!/bin/sh" ] && [ "$SHEBANG" != "#!/bin/bash" ]; then
    echo "ERROR: unexpected shebang: $SHEBANG"
    exit 1
fi

# --- 4. arno-fwfilter script exists and is executable ---
FWFILTER_SCRIPT="$PKG_ROOT/bin/arno-fwfilter"
if [ ! -f "$FWFILTER_SCRIPT" ]; then
    echo "ERROR: $FWFILTER_SCRIPT not found"
    exit 1
fi
if [ ! -x "$FWFILTER_SCRIPT" ]; then
    echo "ERROR: $FWFILTER_SCRIPT not executable"
    exit 1
fi

# --- 5. Environment file exists ---
ENV_FILE="$PKG_ROOT/share/arno-iptables-firewall/environment"
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: environment file not found at $ENV_FILE"
    exit 1
fi

# --- 6. Plugins directory exists and has content ---
PLUGINS_DIR="$PKG_ROOT/share/arno-iptables-firewall/plugins"
if [ ! -d "$PLUGINS_DIR" ]; then
    echo "ERROR: plugins directory not found at $PLUGINS_DIR"
    exit 1
fi
PLUGIN_COUNT=$(find "$PLUGINS_DIR" -name "*.plugin" 2>/dev/null | wc -l)
if [ "$PLUGIN_COUNT" -lt 1 ]; then
    echo "ERROR: no .plugin files found in $PLUGINS_DIR"
    exit 1
fi

# --- 7. Configuration file exists ---
CONF_FILE="$PKG_ROOT/etc/arno-iptables-firewall/firewall.conf"
if [ ! -f "$CONF_FILE" ]; then
    echo "ERROR: firewall.conf not found at $CONF_FILE"
    exit 1
fi

# --- 8. Man page exists ---
MAN_FILE="$PKG_ROOT/share/man/man8/arno-iptables-firewall.8"
if [ ! -f "$MAN_FILE" ]; then
    echo "ERROR: man page not found"
    exit 1
fi

echo "PASS: arno-iptables-firewall scripts, environment, plugins, config, and man pages are valid"
