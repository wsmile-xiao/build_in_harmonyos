# pangene

Construct a pangenome gene graph in GFA format from miniprot
protein-to-genome PAF alignments.

- Upstream: https://github.com/lh3/pangene (Heng Li, MIT)
- Version: 1.1 (r231, 2024-02-22)
- Build: plain Makefile, single `pangene` executable, pure C99
- Dependencies: zlib (via Conan zlib/1.3.2)

## Usage

```sh
# Align proteins to each genome first (miniprot, separate tool):
miniprot --outs=0.97 --no-cs -Iut16 genome1.fna proteins.faa > genome1.paf

# Construct a pangene graph (GFA on stdout):
pangene -a2 genome1.paf genome2.paf > graph.gfa
```

## OHOS adaptation notes

See [1.1/notes.md](1.1/notes.md). Zero patches; recipe mirrors the
sibling miniprot/0.18 package (same author, same Makefile + klib + zlib
pattern).
