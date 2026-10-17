#!/bin/sh
# Consumer CLI test: c2p must turn the unit square's constraint matrix into the
# expected 2-dimensional polyhedron with four facets and the vertices (0,0)
# and (1,1).  Usage: test_c2p.sh <c2p binary> <matrix input>
set -e

c2p="$1"
input="$2"

out=$("$c2p" < "$input")

case "$out" in
  *"POLYHEDRON Dimension:2"*) ;;
  *) echo "FAIL: c2p did not report a 2-dimensional polyhedron"; echo "$out"; exit 1 ;;
esac
case "$out" in
  *"Constraints:4  Equations:0  Rays:4  Lines:0"*) ;;
  *) echo "FAIL: c2p facet/ray counts differ from the unit square"; echo "$out"; exit 1 ;;
esac
case "$out" in
  *"Vertex: [   0    0  ]/1"*) ;;
  *) echo "FAIL: vertex (0,0) missing from c2p output"; echo "$out"; exit 1 ;;
esac
case "$out" in
  *"Vertex: [   1    1  ]/1"*) ;;
  *) echo "FAIL: vertex (1,1) missing from c2p output"; echo "$out"; exit 1 ;;
esac

echo "OK: c2p produced the expected unit-square polyhedron"
