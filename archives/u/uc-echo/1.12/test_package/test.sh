#!/data/service/hnp/bin/bash
# uc-echo 1.12 consumer test — runs the installed binaries the way a real user would.
# Pipeline: hashing x2 -> HashMerge -> NeighborJoin x2 (kmer ranges) ->
#           NeighborMerge -> Voting, then byte-exact golden comparison.
set -eu

echo "[test] K0: --version / --help (rc=0) for all six binaries"
for b in hashing HashMerge NeighborJoin NeighborJoinParam NeighborMerge Voting; do
  "$b" --version > /dev/null
  "$b" --help > /dev/null
  echo "  $b ok"
done

W="$PWD/work"
rm -rf "$W"
mkdir -p "$W"
base64 -d revdata.b64 > "$W/revdata.bin"
cd "$W"

P="-read revdata.bin -K 8 -h 16 -e 0.05"
hashing $P -st 0 -ed 6 -nhash 1 -ihash_st 0 -ihash_ed 1 -fpre "$W/" -fsuf 0
hashing $P -st 6 -ed 12 -nhash 1 -ihash_st 0 -ihash_ed 1 -fpre "$W/" -fsuf 3
HashMerge -fpre "$W/" -fsuf all -input "$W/0.hash" -input "$W/0.index" -input "$W/3.hash" -input "$W/3.index"
NK=$(od -An -tu4 -N4 "$W/all.index" | tr -d " ")
NK2=$((NK / 2))
NeighborJoinParam $P -st 0 -ed 12 -st2 0 -ed2 12 -nhash 1 -ihash_st 0 -ihash_ed 1 -fpre "$W/" -fsuf np -input "$W/all.hash" -input "$W/all.index"
NeighborJoin $P -st 0 -ed 12 -st2 0 -ed2 12 -nhash 2 -ihash_st 0 -ihash_ed $NK2 -max_cov 0 -fpre "$W/" -fsuf 0_0_0 -input "$W/all.hash" -input "$W/all.index"
NeighborJoin $P -st 0 -ed 12 -st2 0 -ed2 12 -nhash 2 -ihash_st $NK2 -ihash_ed $NK -max_cov 0 -fpre "$W/" -fsuf 1_0_0 -input "$W/all.hash" -input "$W/all.index"
NeighborMerge $P -st 0 -ed 12 -fpre "$W/" -fsuf mrg -input "$W/neighbors_0_0_0.list" -input "$W/neighbors_1_0_0.list"
Voting $P -st 0 -ed 12 -fpre "$W/" -fsuf final -input "$W/neighbors_mrg.list"

cmp output_final.txt ../expected_output.txt
echo "[test] PASS: corrected output matches golden (2 sequencing errors corrected)"
