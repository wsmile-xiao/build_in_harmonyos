# bwa

Burrows-Wheeler Aligner (BWA) is a software package for mapping low-divergent sequences against a large reference genome, such as the human genome. It consists of three algorithms: BWA-backtrack, BWA-SW, and BWA-MEM. The first algorithm is designed for Illumina sequence reads up to 100bp, while the other two are for longer reads ranging from 70bp to 1Mbp.

## Key Features
- BWA-MEM algorithm for long reads (70bp-1Mbp)
- BWA-backtrack for short Illumina reads (up to 100bp)  
- BWA-SW for long query sequences (deprecated, use MEM)
- Support for paired-end mapping
- Shared memory index management (shm command)

## Version
- 0.7.19-r1273

## License
- GPL-3.0-or-later AND MIT

## Build System
- Makefile (custom, no autotools/configure/install targets)
