#!/bin/bash
# test_package smoke test for bamutil
set -euo pipefail

echo "Testing bamutil executable..."
bam help > /dev/null 2>&1 && echo "✓ bam help works" || { echo "✗ bam help failed"; exit 1; }

# Create minimal SAM input
cat > test.sam <<'EOF'
@HD	VN:1.0	SO:coordinate
@SQ	SN:chr1	LN:1000
read1	0	chr1	100	60	10M	*	0	0	AAAAAAAAAA	IIIIIIIIII
EOF

# Test SAM→BAM conversion
echo "Testing SAM→BAM conversion..."
bam convert --in test.sam --out test.bam --noph || { echo "✗ convert SAM→BAM failed"; exit 1; }
test -f test.bam || { echo "✗ test.bam not created"; exit 1; }
echo "✓ SAM→BAM works"

# Test BAM→SAM round-trip
echo "Testing BAM→SAM conversion..."
bam convert --in test.bam --out test_out.sam --noph || { echo "✗ convert BAM→SAM failed"; exit 1; }
test -f test_out.sam || { echo "✗ test_out.sam not created"; exit 1; }
echo "✓ BAM→SAM works"

echo "All tests passed!"
