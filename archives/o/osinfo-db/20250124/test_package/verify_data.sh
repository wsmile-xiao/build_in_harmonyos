#!/bin/bash
# verify_data.sh — verify osinfo-db data files are correctly installed
# Called from test_package/conanfile.py via self.run()
set -eu

OSINFO_DIR="$1"

if [ -z "$OSINFO_DIR" ]; then
    echo "ERROR: OSINFO_DIR argument is empty"
    exit 1
fi

# Verify VERSION file exists and contains expected version
VERSION_FILE="$OSINFO_DIR/VERSION"
if [ ! -f "$VERSION_FILE" ]; then
    echo "ERROR: VERSION file not found at $VERSION_FILE"
    exit 1
fi

VERSION=$(tr -d '[:space:]' < "$VERSION_FILE")
if [ "$VERSION" != "20250124" ]; then
    echo "ERROR: Expected version 20250124, got '$VERSION'"
    exit 1
fi

# Verify LICENSE file exists
if [ ! -f "$OSINFO_DIR/LICENSE" ]; then
    echo "ERROR: LICENSE file not found"
    exit 1
fi

# Verify data directories exist
for dir in os device platform schema datamap install-script; do
    if [ ! -d "$OSINFO_DIR/$dir" ]; then
        echo "ERROR: Data directory '$dir/' not found at $OSINFO_DIR/$dir"
        exit 1
    fi
done

# Count XML files in os/ directory (should have hundreds)
XML_COUNT=$(find "$OSINFO_DIR/os" -name "*.xml" 2>/dev/null | wc -l)
if [ "$XML_COUNT" -lt 100 ]; then
    echo "ERROR: Expected at least 100 XML files in os/, got $XML_COUNT"
    exit 1
fi

# Count schema files (RNG/XSD)
SCHEMA_COUNT=$(find "$OSINFO_DIR/schema" -type f 2>/dev/null | wc -l)
if [ "$SCHEMA_COUNT" -lt 1 ]; then
    echo "ERROR: No schema files found"
    exit 1
fi

# Verify a sample XML file is valid (basic well-formedness check)
SAMPLE_XML=$(find "$OSINFO_DIR/os" -name "*.xml" -print -quit 2>/dev/null)
if [ -n "$SAMPLE_XML" ]; then
    HEAD=$(head -1 "$SAMPLE_XML")
    if ! echo "$HEAD" | grep -qE '<\?xml|<!'; then
        echo "ERROR: Sample XML file $SAMPLE_XML doesn't look like valid XML"
        exit 1
    fi
fi

TOTAL_FILES=$(find "$OSINFO_DIR" -type f 2>/dev/null | wc -l)
echo "OK: osinfo-db verified - version=$VERSION, os_xml=$XML_COUNT, total_files=$TOTAL_FILES"
