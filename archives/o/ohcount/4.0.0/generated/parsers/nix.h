
#line 1 "nix.rl.tmp"
/************************* Required for every parser *************************/
#ifndef OHCOUNT_NIX_PARSER_H
#define OHCOUNT_NIX_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *NIX_LANG = LANG_NIX;

// the languages entities
const char *nix_entities[] = {
  "space", "comment", "any"
};

// constants associated with the entities
enum {
  NIX_SPACE = 0, NIX_COMMENT, NIX_ANY
};

/*****************************************************************************/

#include "shell.h"


#line 28 "nix.h"
static const char _nix_actions[] = {
	0, 1, 2, 1, 3, 1, 10, 1, 
	11, 1, 13, 1, 14, 1, 18, 1, 
	19, 1, 22, 1, 23, 1, 29, 1, 
	30, 1, 31, 1, 33, 1, 34, 1, 
	36, 1, 37, 1, 38, 1, 39, 1, 
	40, 1, 41, 1, 46, 1, 47, 1, 
	48, 1, 49, 1, 50, 1, 51, 1, 
	52, 1, 53, 1, 57, 1, 58, 1, 
	59, 1, 60, 1, 61, 1, 62, 1, 
	63, 1, 68, 1, 69, 1, 70, 1, 
	71, 1, 72, 1, 75, 1, 78, 1, 
	79, 1, 80, 1, 81, 1, 82, 1, 
	84, 1, 85, 1, 86, 1, 88, 1, 
	89, 1, 90, 1, 91, 1, 92, 1, 
	93, 1, 95, 1, 96, 1, 97, 1, 
	98, 1, 99, 2, 1, 43, 2, 1, 
	54, 2, 1, 65, 2, 3, 12, 2, 
	3, 20, 2, 3, 24, 2, 3, 31, 
	2, 6, 5, 2, 7, 5, 2, 8, 
	5, 2, 9, 5, 2, 11, 44, 2, 
	12, 45, 2, 16, 15, 2, 19, 55, 
	2, 20, 56, 2, 23, 66, 2, 24, 
	67, 2, 30, 76, 2, 31, 77, 2, 
	32, 83, 2, 35, 87, 2, 39, 94, 
	2, 42, 31, 2, 42, 39, 3, 6, 
	5, 2, 3, 6, 5, 7, 3, 7, 
	5, 2, 3, 8, 5, 2, 3, 8, 
	5, 9, 3, 9, 5, 2, 3, 16, 
	15, 3, 4, 6, 5, 1, 43, 4, 
	6, 5, 1, 54, 4, 6, 5, 1, 
	65, 4, 6, 5, 7, 2, 4, 7, 
	5, 1, 43, 4, 7, 5, 1, 54, 
	4, 7, 5, 1, 65, 4, 8, 5, 
	1, 43, 4, 8, 5, 1, 54, 4, 
	8, 5, 1, 65, 4, 8, 5, 9, 
	2, 4, 9, 5, 1, 43, 4, 9, 
	5, 1, 54, 4, 9, 5, 1, 65, 
	4, 42, 0, 2, 12, 4, 42, 0, 
	2, 20, 4, 42, 0, 2, 24, 5, 
	2, 27, 15, 28, 74, 5, 4, 2, 
	21, 64, 1, 5, 6, 5, 7, 1, 
	43, 5, 6, 5, 7, 1, 54, 5, 
	6, 5, 7, 1, 65, 5, 8, 5, 
	9, 1, 43, 5, 8, 5, 9, 1, 
	54, 5, 8, 5, 9, 1, 65, 6, 
	2, 25, 15, 26, 73, 31, 6, 42, 
	4, 2, 17, 0, 20
};

static const char _nix_cond_offsets[] = {
	0, 0, 0, 0, 1, 2, 3, 4, 
	4, 4, 5, 6, 7, 8, 9, 10, 
	10, 10, 11, 12, 12, 13, 14, 15, 
	16, 16, 16, 17, 18, 19, 20, 21, 
	22, 22, 22, 23, 24, 24, 25, 26, 
	27, 28, 28, 28, 29, 30, 31, 32, 
	33, 34, 34, 34, 35, 36, 36, 37, 
	38, 39, 39, 39, 39, 39, 39, 39, 
	39, 40, 40, 41, 41, 42, 42, 42, 
	42, 42, 43, 43, 44, 44, 45, 45, 
	46, 46, 47, 47, 48, 48, 49, 49, 
	49, 49, 49, 49, 49, 49, 49, 49, 
	49, 49
};

static const char _nix_cond_lengths[] = {
	0, 0, 0, 1, 1, 1, 1, 0, 
	0, 1, 1, 1, 1, 1, 1, 0, 
	0, 1, 1, 0, 1, 1, 1, 1, 
	0, 0, 1, 1, 1, 1, 1, 1, 
	0, 0, 1, 1, 0, 1, 1, 1, 
	1, 0, 0, 1, 1, 1, 1, 1, 
	1, 0, 0, 1, 1, 0, 1, 1, 
	1, 0, 0, 0, 0, 0, 0, 0, 
	1, 0, 1, 0, 1, 0, 0, 0, 
	0, 1, 0, 1, 0, 1, 0, 1, 
	0, 1, 0, 1, 0, 1, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0
};

static const short _nix_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 0
};

static const char _nix_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0
};

static const short _nix_key_offsets[] = {
	0, 0, 1, 3, 15, 27, 35, 47, 
	48, 49, 61, 73, 85, 97, 105, 117, 
	118, 119, 131, 143, 144, 156, 168, 176, 
	188, 189, 190, 202, 214, 226, 238, 246, 
	258, 259, 260, 272, 284, 285, 297, 309, 
	317, 329, 330, 331, 343, 355, 367, 379, 
	387, 399, 400, 401, 413, 425, 426, 437, 
	448, 460, 461, 462, 469, 472, 475, 476, 
	477, 490, 492, 504, 507, 519, 520, 524, 
	527, 530, 543, 545, 557, 560, 572, 573, 
	586, 588, 600, 603, 615, 616, 630, 632, 
	635, 636, 637, 638, 643, 646, 649, 654, 
	657, 660
};

static const short _nix_trans_keys[] = {
	42, 42, 47, 9, 10, 12, 32, 34, 
	92, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 34, 92, 269, 525, 0, 
	11, 14, 255, 10, 12, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 34, 
	92, 269, 525, 0, 11, 14, 255, 10, 
	10, 9, 10, 12, 32, 34, 92, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 34, 92, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 39, 92, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 39, 92, 269, 525, 0, 11, 14, 
	255, 10, 12, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 39, 92, 269, 
	525, 0, 11, 14, 255, 10, 10, 9, 
	10, 12, 32, 39, 92, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 39, 
	92, 269, 525, 0, 11, 14, 255, 10, 
	9, 10, 12, 32, 34, 92, 269, 525, 
	0, 11, 14, 255, 9, 10, 12, 32, 
	34, 92, 269, 525, 0, 11, 14, 255, 
	10, 12, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 34, 92, 269, 525, 
	0, 11, 14, 255, 10, 10, 9, 10, 
	12, 32, 34, 92, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 34, 92, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 39, 92, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 39, 92, 
	269, 525, 0, 11, 14, 255, 10, 12, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 39, 92, 269, 525, 0, 11, 
	14, 255, 10, 10, 9, 10, 12, 32, 
	39, 92, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 39, 92, 269, 525, 
	0, 11, 14, 255, 10, 9, 10, 12, 
	32, 34, 92, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 34, 92, 269, 
	525, 0, 11, 14, 255, 10, 12, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 34, 92, 269, 525, 0, 11, 14, 
	255, 10, 10, 9, 10, 12, 32, 34, 
	92, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 34, 92, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 39, 
	92, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 39, 92, 269, 525, 0, 
	11, 14, 255, 10, 12, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 39, 
	92, 269, 525, 0, 11, 14, 255, 10, 
	10, 9, 10, 12, 32, 39, 92, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 39, 92, 269, 525, 0, 11, 14, 
	255, 10, 9, 10, 12, 32, 42, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 42, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 42, 47, 269, 525, 
	0, 11, 14, 255, 10, 10, 32, 34, 
	35, 39, 47, 9, 13, 32, 9, 13, 
	10, 12, 13, 39, 42, 9, 10, 12, 
	32, 34, 35, 39, 269, 525, 0, 8, 
	14, 255, 9, 32, 9, 10, 12, 32, 
	34, 92, 269, 525, 0, 11, 14, 255, 
	10, 12, 13, 9, 10, 12, 32, 39, 
	92, 269, 525, 0, 11, 14, 255, 10, 
	32, 35, 9, 13, 32, 9, 13, 10, 
	12, 13, 9, 10, 12, 32, 34, 35, 
	39, 269, 525, 0, 8, 14, 255, 9, 
	32, 9, 10, 12, 32, 34, 92, 269, 
	525, 0, 11, 14, 255, 10, 12, 13, 
	9, 10, 12, 32, 39, 92, 269, 525, 
	0, 11, 14, 255, 10, 9, 10, 12, 
	32, 34, 35, 39, 269, 525, 0, 8, 
	14, 255, 9, 32, 9, 10, 12, 32, 
	34, 92, 269, 525, 0, 11, 14, 255, 
	10, 12, 13, 9, 10, 12, 32, 39, 
	92, 269, 525, 0, 11, 14, 255, 10, 
	9, 10, 12, 32, 34, 35, 39, 47, 
	269, 525, 0, 8, 14, 255, 9, 32, 
	10, 12, 13, 39, 42, 10, 32, 34, 
	35, 9, 13, 32, 9, 13, 10, 12, 
	13, 32, 35, 39, 9, 13, 32, 9, 
	13, 10, 12, 13, 39, 0
};

static const char _nix_single_lengths[] = {
	0, 1, 2, 8, 8, 4, 8, 1, 
	1, 8, 8, 8, 8, 4, 8, 1, 
	1, 8, 8, 1, 8, 8, 4, 8, 
	1, 1, 8, 8, 8, 8, 4, 8, 
	1, 1, 8, 8, 1, 8, 8, 4, 
	8, 1, 1, 8, 8, 8, 8, 4, 
	8, 1, 1, 8, 8, 1, 7, 7, 
	8, 1, 1, 5, 1, 1, 1, 1, 
	9, 2, 8, 1, 8, 1, 2, 1, 
	1, 9, 2, 8, 1, 8, 1, 9, 
	2, 8, 1, 8, 1, 10, 2, 1, 
	1, 1, 1, 3, 1, 1, 3, 1, 
	1, 1
};

static const char _nix_range_lengths[] = {
	0, 0, 0, 2, 2, 2, 2, 0, 
	0, 2, 2, 2, 2, 2, 2, 0, 
	0, 2, 2, 0, 2, 2, 2, 2, 
	0, 0, 2, 2, 2, 2, 2, 2, 
	0, 0, 2, 2, 0, 2, 2, 2, 
	2, 0, 0, 2, 2, 2, 2, 2, 
	2, 0, 0, 2, 2, 0, 2, 2, 
	2, 0, 0, 1, 1, 1, 0, 0, 
	2, 0, 2, 1, 2, 0, 1, 1, 
	1, 2, 0, 2, 1, 2, 0, 2, 
	0, 2, 1, 2, 0, 2, 0, 1, 
	0, 0, 0, 1, 1, 1, 1, 1, 
	1, 0
};

static const short _nix_index_offsets[] = {
	0, 0, 2, 5, 16, 27, 34, 45, 
	47, 49, 60, 71, 82, 93, 100, 111, 
	113, 115, 126, 137, 139, 150, 161, 168, 
	179, 181, 183, 194, 205, 216, 227, 234, 
	245, 247, 249, 260, 271, 273, 284, 295, 
	302, 313, 315, 317, 328, 339, 350, 361, 
	368, 379, 381, 383, 394, 405, 407, 417, 
	427, 438, 440, 442, 449, 452, 455, 457, 
	459, 471, 474, 485, 488, 499, 501, 505, 
	508, 511, 523, 526, 537, 540, 551, 553, 
	565, 568, 579, 582, 593, 595, 608, 611, 
	614, 616, 618, 620, 625, 628, 631, 636, 
	639, 642
};

static const char _nix_trans_targs[] = {
	2, 1, 2, 59, 1, 3, 4, 4, 
	3, 64, 5, 7, 4, 3, 3, 64, 
	3, 4, 4, 3, 64, 5, 7, 4, 
	3, 3, 64, 6, 6, 8, 9, 3, 
	3, 64, 3, 4, 4, 3, 64, 5, 
	7, 4, 3, 3, 64, 4, 64, 6, 
	64, 3, 10, 4, 3, 64, 5, 7, 
	4, 3, 3, 64, 3, 4, 4, 3, 
	64, 5, 7, 4, 3, 3, 64, 11, 
	12, 12, 11, 64, 13, 15, 12, 11, 
	11, 64, 11, 12, 12, 11, 64, 13, 
	15, 12, 11, 11, 64, 14, 14, 16, 
	17, 11, 11, 64, 11, 12, 12, 11, 
	64, 13, 15, 12, 11, 11, 64, 12, 
	64, 14, 64, 11, 18, 12, 11, 64, 
	13, 15, 12, 11, 11, 64, 11, 12, 
	12, 11, 64, 13, 15, 12, 11, 11, 
	64, 64, 0, 20, 21, 21, 20, 73, 
	22, 24, 21, 20, 20, 73, 20, 21, 
	21, 20, 73, 22, 24, 21, 20, 20, 
	73, 23, 23, 25, 26, 20, 20, 73, 
	20, 21, 21, 20, 73, 22, 24, 21, 
	20, 20, 73, 21, 73, 23, 73, 20, 
	27, 21, 20, 73, 22, 24, 21, 20, 
	20, 73, 20, 21, 21, 20, 73, 22, 
	24, 21, 20, 20, 73, 28, 29, 29, 
	28, 73, 30, 32, 29, 28, 28, 73, 
	28, 29, 29, 28, 73, 30, 32, 29, 
	28, 28, 73, 31, 31, 33, 34, 28, 
	28, 73, 28, 29, 29, 28, 73, 30, 
	32, 29, 28, 28, 73, 29, 73, 31, 
	73, 28, 35, 29, 28, 73, 30, 32, 
	29, 28, 28, 73, 28, 29, 29, 28, 
	73, 30, 32, 29, 28, 28, 73, 73, 
	0, 37, 38, 38, 37, 79, 39, 41, 
	38, 37, 37, 79, 37, 38, 38, 37, 
	79, 39, 41, 38, 37, 37, 79, 40, 
	40, 42, 43, 37, 37, 79, 37, 38, 
	38, 37, 79, 39, 41, 38, 37, 37, 
	79, 38, 79, 40, 79, 37, 44, 38, 
	37, 79, 39, 41, 38, 37, 37, 79, 
	37, 38, 38, 37, 79, 39, 41, 38, 
	37, 37, 79, 45, 46, 46, 45, 79, 
	47, 49, 46, 45, 45, 79, 45, 46, 
	46, 45, 79, 47, 49, 46, 45, 45, 
	79, 48, 48, 50, 51, 45, 45, 79, 
	45, 46, 46, 45, 79, 47, 49, 46, 
	45, 45, 79, 46, 79, 48, 79, 45, 
	52, 46, 45, 79, 47, 49, 46, 45, 
	45, 79, 45, 46, 46, 45, 79, 47, 
	49, 46, 45, 45, 79, 79, 0, 54, 
	55, 55, 54, 56, 57, 55, 54, 54, 
	85, 54, 55, 55, 54, 56, 57, 55, 
	54, 54, 85, 54, 55, 55, 54, 56, 
	85, 57, 55, 54, 54, 85, 55, 85, 
	85, 0, 60, 59, 61, 62, 63, 60, 
	59, 60, 60, 59, 59, 59, 61, 59, 
	59, 1, 59, 65, 64, 64, 65, 66, 
	67, 68, 19, 69, 64, 64, 0, 65, 
	65, 64, 3, 4, 4, 3, 64, 5, 
	7, 4, 3, 3, 64, 64, 64, 67, 
	11, 12, 12, 11, 64, 13, 15, 12, 
	11, 11, 64, 64, 64, 71, 72, 71, 
	70, 71, 71, 70, 70, 70, 72, 74, 
	73, 73, 74, 75, 76, 77, 36, 78, 
	73, 73, 0, 74, 74, 73, 20, 21, 
	21, 20, 73, 22, 24, 21, 20, 20, 
	73, 73, 73, 76, 28, 29, 29, 28, 
	73, 30, 32, 29, 28, 28, 73, 73, 
	73, 80, 79, 79, 80, 81, 82, 83, 
	53, 84, 79, 79, 0, 80, 80, 79, 
	37, 38, 38, 37, 79, 39, 41, 38, 
	37, 37, 79, 79, 79, 82, 45, 46, 
	46, 45, 79, 47, 49, 46, 45, 45, 
	79, 79, 79, 86, 85, 85, 86, 85, 
	87, 88, 89, 58, 90, 85, 85, 0, 
	86, 86, 85, 85, 85, 87, 85, 85, 
	54, 85, 85, 85, 92, 91, 93, 92, 
	91, 92, 92, 91, 91, 91, 93, 95, 
	96, 97, 95, 94, 95, 95, 94, 94, 
	94, 96, 94, 94, 59, 59, 64, 64, 
	64, 64, 64, 64, 64, 64, 64, 64, 
	64, 64, 64, 64, 64, 64, 73, 73, 
	73, 73, 73, 73, 73, 73, 73, 73, 
	73, 73, 73, 73, 73, 73, 79, 79, 
	79, 79, 79, 79, 79, 79, 79, 79, 
	79, 79, 79, 79, 79, 79, 85, 85, 
	85, 85, 59, 59, 59, 59, 64, 64, 
	64, 64, 64, 70, 70, 73, 73, 73, 
	73, 73, 79, 79, 79, 79, 79, 85, 
	85, 85, 85, 85, 91, 91, 94, 94, 
	94, 0
};

static const short _nix_trans_actions[] = {
	37, 37, 37, 189, 37, 0, 0, 0, 
	0, 123, 0, 0, 0, 1, 1, 51, 
	150, 150, 150, 150, 261, 150, 150, 150, 
	210, 210, 51, 0, 0, 0, 0, 1, 
	1, 51, 153, 153, 153, 153, 281, 153, 
	153, 153, 218, 218, 51, 0, 51, 0, 
	51, 153, 153, 153, 153, 281, 153, 153, 
	153, 218, 218, 51, 214, 214, 214, 214, 
	341, 214, 214, 214, 276, 276, 51, 0, 
	0, 0, 0, 123, 0, 0, 0, 1, 
	1, 51, 144, 144, 144, 144, 226, 144, 
	144, 144, 198, 198, 51, 0, 0, 0, 
	0, 1, 1, 51, 147, 147, 147, 147, 
	246, 147, 147, 147, 206, 206, 51, 0, 
	51, 0, 51, 147, 147, 147, 147, 246, 
	147, 147, 147, 206, 206, 51, 202, 202, 
	202, 202, 323, 202, 202, 202, 241, 241, 
	51, 156, 0, 0, 0, 0, 0, 126, 
	0, 0, 0, 1, 1, 69, 150, 150, 
	150, 150, 266, 150, 150, 150, 210, 210, 
	69, 0, 0, 0, 0, 1, 1, 69, 
	153, 153, 153, 153, 286, 153, 153, 153, 
	218, 218, 69, 0, 69, 0, 69, 153, 
	153, 153, 153, 286, 153, 153, 153, 218, 
	218, 69, 214, 214, 214, 214, 347, 214, 
	214, 214, 276, 276, 69, 0, 0, 0, 
	0, 126, 0, 0, 0, 1, 1, 71, 
	144, 144, 144, 144, 231, 144, 144, 144, 
	198, 198, 71, 0, 0, 0, 0, 1, 
	1, 71, 147, 147, 147, 147, 251, 147, 
	147, 147, 206, 206, 71, 0, 71, 0, 
	71, 147, 147, 147, 147, 251, 147, 147, 
	147, 206, 206, 71, 202, 202, 202, 202, 
	329, 202, 202, 202, 241, 241, 71, 165, 
	0, 0, 0, 0, 0, 129, 0, 0, 
	0, 1, 1, 81, 150, 150, 150, 150, 
	271, 150, 150, 150, 210, 210, 81, 0, 
	0, 0, 0, 1, 1, 81, 153, 153, 
	153, 153, 291, 153, 153, 153, 218, 218, 
	81, 0, 81, 0, 81, 153, 153, 153, 
	153, 291, 153, 153, 153, 218, 218, 81, 
	214, 214, 214, 214, 353, 214, 214, 214, 
	276, 276, 81, 0, 0, 0, 0, 129, 
	0, 0, 0, 1, 1, 81, 144, 144, 
	144, 144, 236, 144, 144, 144, 198, 198, 
	81, 0, 0, 0, 0, 1, 1, 81, 
	147, 147, 147, 147, 256, 147, 147, 147, 
	206, 206, 81, 0, 81, 0, 81, 147, 
	147, 147, 147, 256, 147, 147, 147, 206, 
	206, 81, 202, 202, 202, 202, 335, 202, 
	202, 202, 241, 241, 81, 171, 0, 0, 
	0, 0, 0, 3, 0, 0, 3, 3, 
	93, 162, 162, 162, 162, 222, 162, 162, 
	222, 222, 93, 0, 0, 0, 0, 3, 
	83, 0, 0, 3, 3, 93, 0, 93, 
	177, 0, 35, 109, 37, 0, 195, 35, 
	113, 35, 35, 115, 117, 117, 37, 111, 
	119, 37, 119, 5, 156, 156, 5, 296, 
	132, 296, 7, 7, 159, 159, 0, 5, 
	5, 43, 0, 0, 0, 0, 123, 0, 
	0, 0, 1, 1, 49, 45, 45, 0, 
	0, 0, 0, 0, 123, 0, 0, 0, 
	1, 1, 49, 156, 47, 9, 11, 9, 
	53, 9, 9, 55, 57, 57, 11, 13, 
	165, 165, 13, 366, 135, 301, 15, 15, 
	168, 168, 0, 13, 13, 61, 0, 0, 
	0, 0, 126, 0, 0, 0, 1, 1, 
	59, 63, 63, 0, 0, 0, 0, 0, 
	126, 0, 0, 0, 1, 1, 67, 165, 
	65, 17, 171, 171, 17, 306, 138, 306, 
	19, 19, 174, 174, 0, 17, 17, 73, 
	0, 0, 0, 0, 129, 0, 0, 0, 
	1, 1, 79, 75, 75, 0, 0, 0, 
	0, 0, 317, 0, 0, 0, 1, 1, 
	79, 171, 77, 21, 177, 177, 21, 359, 
	141, 25, 192, 23, 23, 180, 180, 0, 
	21, 21, 85, 87, 87, 0, 311, 91, 
	3, 91, 177, 89, 27, 183, 29, 27, 
	95, 27, 27, 97, 99, 99, 29, 31, 
	33, 0, 31, 101, 31, 31, 103, 105, 
	105, 33, 186, 107, 121, 121, 51, 51, 
	51, 51, 51, 51, 51, 51, 51, 51, 
	51, 51, 51, 51, 51, 51, 69, 69, 
	69, 69, 69, 69, 69, 69, 71, 71, 
	71, 71, 71, 71, 71, 71, 81, 81, 
	81, 81, 81, 81, 81, 81, 81, 81, 
	81, 81, 81, 81, 81, 81, 93, 93, 
	93, 93, 115, 117, 119, 119, 43, 49, 
	45, 49, 47, 55, 57, 61, 59, 63, 
	67, 65, 73, 79, 75, 79, 77, 85, 
	87, 91, 91, 89, 97, 99, 103, 105, 
	107, 0
};

static const short _nix_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 39, 0, 0, 0, 0, 
	39, 0, 0, 0, 0, 0, 39, 0, 
	0, 39, 0, 0, 0, 0, 0, 39, 
	0, 0, 0, 0, 0, 39, 0, 0, 
	0, 0, 0, 39, 0, 0, 39, 0, 
	0, 0
};

static const short _nix_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 41, 0, 0, 0, 0, 
	41, 0, 0, 0, 0, 0, 41, 0, 
	0, 41, 0, 0, 0, 0, 0, 41, 
	0, 0, 0, 0, 0, 41, 0, 0, 
	0, 0, 0, 41, 0, 0, 41, 0, 
	0, 0
};

static const short _nix_eof_trans[] = {
	0, 646, 646, 662, 662, 662, 662, 662, 
	662, 662, 662, 662, 662, 662, 662, 662, 
	662, 662, 662, 0, 670, 670, 670, 670, 
	670, 670, 670, 670, 678, 678, 678, 678, 
	678, 678, 678, 678, 0, 694, 694, 694, 
	694, 694, 694, 694, 694, 694, 694, 694, 
	694, 694, 694, 694, 694, 0, 698, 698, 
	698, 698, 0, 0, 699, 700, 702, 702, 
	0, 703, 706, 705, 706, 707, 0, 708, 
	709, 0, 710, 711, 712, 713, 714, 0, 
	715, 718, 717, 718, 719, 0, 720, 721, 
	723, 723, 724, 0, 725, 726, 0, 727, 
	728, 729
};

static const int nix_start = 59;
static const int nix_first_final = 59;
static const int nix_error = 0;

static const int nix_en_shell_line = 64;
static const int nix_en_shell_entity = 70;
static const int nix_en_nix_dq_shell_line = 73;
static const int nix_en_nix_dsq_shell_line = 79;
static const int nix_en_nix_line = 85;
static const int nix_en_nix_dq_shell_entity = 91;
static const int nix_en_nix_dsq_shell_entity = 94;
static const int nix_en_nix_entity = 59;


#line 29 "nix.rl.tmp"


#line 222 "nix.rl.tmp"


/************************* Required for every parser *************************/

/* Parses a string buffer with Nix code.
 *
 * @param *buffer The string to parse.
 * @param length The length of the string to parse.
 * @param count Integer flag specifying whether or not to count lines. If yes,
 *   uses the Ragel machine optimized for counting. Otherwise uses the Ragel
 *   machine optimized for returning entity positions.
 * @param *callback Callback function. If count is set, callback is called for
 *   every line of code, comment, or blank with 'lcode', 'lcomment', and
 *   'lblank' respectively. Otherwise callback is called for each entity found.
 */
void parse_nix(char *buffer, int length, int count,
               void (*callback) (const char *lang, const char *entity, int s,
                                 int e, void *udata),
               void *userdata
  ) {
  init

  
#line 566 "nix.h"
	{
	cs = nix_start;
	top = 0;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 245 "nix.rl.tmp"
  cs = (count) ? nix_en_nix_line : nix_en_nix_entity;
  
#line 578 "nix.h"
	{
	int _klen;
	unsigned int _trans;
	short _widec;
	const char *_acts;
	unsigned int _nacts;
	const short *_keys;

	if ( p == pe )
		goto _test_eof;
	if ( cs == 0 )
		goto _out;
_resume:
	_acts = _nix_actions + _nix_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 41:
#line 1 "NONE"
	{ts = p;}
	break;
#line 600 "nix.h"
		}
	}

	_widec = (*p);
	_klen = _nix_cond_lengths[cs];
	_keys = _nix_cond_keys + (_nix_cond_offsets[cs]*2);
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + (_klen<<1) - 2;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + (((_upper-_lower) >> 1) & ~1);
			if ( _widec < _mid[0] )
				_upper = _mid - 2;
			else if ( _widec > _mid[1] )
				_lower = _mid + 2;
			else {
				switch ( _nix_cond_spaces[_nix_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
	case 0: {
		_widec = (short)(256 + ((*p) - 0));
		if ( 
#line 9 "common.rl"
 p+1 < pe && *(p+1) != '\n'  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _nix_trans_keys + _nix_key_offsets[cs];
	_trans = _nix_index_offsets[cs];

	_klen = _nix_single_lengths[cs];
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + _klen - 1;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + ((_upper-_lower) >> 1);
			if ( _widec < *_mid )
				_upper = _mid - 1;
			else if ( _widec > *_mid )
				_lower = _mid + 1;
			else {
				_trans += (unsigned int)(_mid - _keys);
				goto _match;
			}
		}
		_keys += _klen;
		_trans += _klen;
	}

	_klen = _nix_range_lengths[cs];
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + (_klen<<1) - 2;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + (((_upper-_lower) >> 1) & ~1);
			if ( _widec < _mid[0] )
				_upper = _mid - 2;
			else if ( _widec > _mid[1] )
				_lower = _mid + 2;
			else {
				_trans += (unsigned int)((_mid - _keys)>>1);
				goto _match;
			}
		}
		_trans += _klen;
	}

_match:
_eof_trans:
	cs = _nix_trans_targs[_trans];

	if ( _nix_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _nix_actions + _nix_trans_actions[_trans];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 )
	{
		switch ( *_acts++ )
		{
	case 0:
#line 30 "common.rl"
	{
  inqueue = 1;
  if (callback_list_head) free_queue(); // free the current queue
  callback_list_head = NULL;
  callback_list_tail = NULL;
  // set backup variables
  last_line_start = line_start;
  last_line_contains_code = line_contains_code;
  last_whole_line_comment = whole_line_comment;
}
	break;
	case 1:
#line 41 "common.rl"
	{
  if (inqueue) {
    Callback *item;
    for (item = callback_list_head; item != NULL; item = item->next)
      callback(item->lang, item->entity, item->s, item->e, item->udata);
    free_queue();
    inqueue = 0;
  }
}
	break;
	case 2:
#line 53 "common.rl"
	{
  if (!line_contains_code && !line_start) line_start = ts;
  line_contains_code = 1;
}
	break;
	case 3:
#line 58 "common.rl"
	{
  if (!line_contains_code) {
    whole_line_comment = 1;
    if (!line_start) line_start = ts;
  }
}
	break;
	case 4:
#line 65 "common.rl"
	{
  if (!line_contains_code && !whole_line_comment) seen = 0;
}
	break;
	case 5:
#line 38 "nix.rl.tmp"
	{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }
	break;
	case 6:
#line 58 "nix.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 60 "nix.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 8:
#line 70 "nix.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 9:
#line 72 "nix.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 10:
#line 84 "nix.rl.tmp"
	{ entity = SHELL_SPACE; }
	break;
	case 11:
#line 87 "nix.rl.tmp"
	{ entity = NEWLINE;     }
	break;
	case 12:
#line 88 "nix.rl.tmp"
	{ entity = SHELL_ANY;   }
	break;
	case 13:
#line 100 "nix.rl.tmp"
	{ entity = SHELL_SPACE;   }
	break;
	case 14:
#line 101 "nix.rl.tmp"
	{ entity = SHELL_COMMENT; }
	break;
	case 15:
#line 109 "nix.rl.tmp"
	{
    switch(entity) {
    case NIX_SPACE:
      ls
      break;
    case NIX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(NIX_LANG)
      break;
    case NEWLINE:
      std_newline(NIX_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(NIX_LANG)
    }
  }
	break;
	case 16:
#line 132 "nix.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 17:
#line 144 "nix.rl.tmp"
	{ p = ts; {cs = stack[--top]; goto _again;} }
	break;
	case 18:
#line 147 "nix.rl.tmp"
	{ entity = SHELL_SPACE; }
	break;
	case 19:
#line 150 "nix.rl.tmp"
	{ entity = NEWLINE;     }
	break;
	case 20:
#line 151 "nix.rl.tmp"
	{ entity = SHELL_ANY;   }
	break;
	case 21:
#line 157 "nix.rl.tmp"
	{ p = ts; {cs = stack[--top]; goto _again;} }
	break;
	case 22:
#line 160 "nix.rl.tmp"
	{ entity = SHELL_SPACE; }
	break;
	case 23:
#line 163 "nix.rl.tmp"
	{ entity = NEWLINE;     }
	break;
	case 24:
#line 164 "nix.rl.tmp"
	{ entity = SHELL_ANY;   }
	break;
	case 25:
#line 168 "nix.rl.tmp"
	{ entity = CHECK_BLANK_ENTRY; }
	break;
	case 26:
#line 169 "nix.rl.tmp"
	{ saw(SHELL_LANG); }
	break;
	case 27:
#line 170 "nix.rl.tmp"
	{ entity = CHECK_BLANK_ENTRY; }
	break;
	case 28:
#line 171 "nix.rl.tmp"
	{ saw(SHELL_LANG); }
	break;
	case 29:
#line 173 "nix.rl.tmp"
	{ entity = NIX_SPACE; }
	break;
	case 30:
#line 175 "nix.rl.tmp"
	{ entity = NEWLINE; }
	break;
	case 31:
#line 176 "nix.rl.tmp"
	{ entity = NIX_ANY;   }
	break;
	case 32:
#line 193 "nix.rl.tmp"
	{ {cs = stack[--top]; goto _again;} }
	break;
	case 33:
#line 196 "nix.rl.tmp"
	{ entity = SHELL_SPACE;   }
	break;
	case 34:
#line 197 "nix.rl.tmp"
	{ entity = SHELL_COMMENT; }
	break;
	case 35:
#line 205 "nix.rl.tmp"
	{ {cs = stack[--top]; goto _again;} }
	break;
	case 36:
#line 208 "nix.rl.tmp"
	{ entity = SHELL_SPACE;   }
	break;
	case 37:
#line 209 "nix.rl.tmp"
	{ entity = SHELL_COMMENT; }
	break;
	case 38:
#line 217 "nix.rl.tmp"
	{ entity = NIX_SPACE;   }
	break;
	case 39:
#line 218 "nix.rl.tmp"
	{ entity = NIX_COMMENT; }
	break;
	case 42:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 43:
#line 86 "nix.rl.tmp"
	{te = p+1;}
	break;
	case 44:
#line 38 "nix.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 45:
#line 38 "nix.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 46:
#line 38 "nix.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 47:
#line 85 "nix.rl.tmp"
	{te = p;p--;}
	break;
	case 48:
#line 38 "nix.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 49:
#line 38 "nix.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 50:
#line 38 "nix.rl.tmp"
	{{p = ((te))-1;}{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 51:
#line 103 "nix.rl.tmp"
	{te = p+1;}
	break;
	case 52:
#line 93 "nix.rl.tmp"
	{te = p;p--;{
    callback(SHELL_LANG, shell_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 53:
#line 93 "nix.rl.tmp"
	{te = p;p--;{
    callback(SHELL_LANG, shell_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 54:
#line 149 "nix.rl.tmp"
	{te = p+1;}
	break;
	case 55:
#line 38 "nix.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 56:
#line 38 "nix.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 57:
#line 144 "nix.rl.tmp"
	{te = p;p--;}
	break;
	case 58:
#line 38 "nix.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 59:
#line 148 "nix.rl.tmp"
	{te = p;p--;}
	break;
	case 60:
#line 38 "nix.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 61:
#line 38 "nix.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 62:
#line 144 "nix.rl.tmp"
	{{p = ((te))-1;}}
	break;
	case 63:
#line 38 "nix.rl.tmp"
	{{p = ((te))-1;}{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 64:
#line 157 "nix.rl.tmp"
	{te = p+1;}
	break;
	case 65:
#line 162 "nix.rl.tmp"
	{te = p+1;}
	break;
	case 66:
#line 38 "nix.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 67:
#line 38 "nix.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 68:
#line 38 "nix.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 69:
#line 161 "nix.rl.tmp"
	{te = p;p--;}
	break;
	case 70:
#line 38 "nix.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 71:
#line 38 "nix.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 72:
#line 38 "nix.rl.tmp"
	{{p = ((te))-1;}{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 73:
#line 169 "nix.rl.tmp"
	{te = p+1;{ {stack[top++] = cs; cs = 73;goto _again;} }}
	break;
	case 74:
#line 171 "nix.rl.tmp"
	{te = p+1;{ {stack[top++] = cs; cs = 79;goto _again;} }}
	break;
	case 75:
#line 174 "nix.rl.tmp"
	{te = p+1;}
	break;
	case 76:
#line 109 "nix.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case NIX_SPACE:
      ls
      break;
    case NIX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(NIX_LANG)
      break;
    case NEWLINE:
      std_newline(NIX_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(NIX_LANG)
    }
  }}
	break;
	case 77:
#line 109 "nix.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case NIX_SPACE:
      ls
      break;
    case NIX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(NIX_LANG)
      break;
    case NEWLINE:
      std_newline(NIX_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(NIX_LANG)
    }
  }}
	break;
	case 78:
#line 109 "nix.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case NIX_SPACE:
      ls
      break;
    case NIX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(NIX_LANG)
      break;
    case NEWLINE:
      std_newline(NIX_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(NIX_LANG)
    }
  }}
	break;
	case 79:
#line 174 "nix.rl.tmp"
	{te = p;p--;}
	break;
	case 80:
#line 109 "nix.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case NIX_SPACE:
      ls
      break;
    case NIX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(NIX_LANG)
      break;
    case NEWLINE:
      std_newline(NIX_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(NIX_LANG)
    }
  }}
	break;
	case 81:
#line 109 "nix.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case NIX_SPACE:
      ls
      break;
    case NIX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(NIX_LANG)
      break;
    case NEWLINE:
      std_newline(NIX_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(NIX_LANG)
    }
  }}
	break;
	case 82:
#line 109 "nix.rl.tmp"
	{{p = ((te))-1;}{
    switch(entity) {
    case NIX_SPACE:
      ls
      break;
    case NIX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(NIX_LANG)
      break;
    case NEWLINE:
      std_newline(NIX_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(NIX_LANG)
    }
  }}
	break;
	case 83:
#line 193 "nix.rl.tmp"
	{te = p+1;}
	break;
	case 84:
#line 199 "nix.rl.tmp"
	{te = p+1;}
	break;
	case 85:
#line 93 "nix.rl.tmp"
	{te = p;p--;{
    callback(SHELL_LANG, shell_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 86:
#line 93 "nix.rl.tmp"
	{te = p;p--;{
    callback(SHELL_LANG, shell_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 87:
#line 205 "nix.rl.tmp"
	{te = p+1;}
	break;
	case 88:
#line 211 "nix.rl.tmp"
	{te = p+1;}
	break;
	case 89:
#line 93 "nix.rl.tmp"
	{te = p;p--;{
    callback(SHELL_LANG, shell_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 90:
#line 93 "nix.rl.tmp"
	{te = p;p--;{
    callback(SHELL_LANG, shell_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 91:
#line 211 "nix.rl.tmp"
	{te = p;p--;}
	break;
	case 92:
#line 215 "nix.rl.tmp"
	{te = p+1;{ {stack[top++] = cs; cs = 91;goto _again;}  }}
	break;
	case 93:
#line 216 "nix.rl.tmp"
	{te = p+1;{ {stack[top++] = cs; cs = 94;goto _again;} }}
	break;
	case 94:
#line 181 "nix.rl.tmp"
	{te = p+1;{
    callback(NIX_LANG, nix_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 95:
#line 220 "nix.rl.tmp"
	{te = p+1;}
	break;
	case 96:
#line 181 "nix.rl.tmp"
	{te = p;p--;{
    callback(NIX_LANG, nix_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 97:
#line 181 "nix.rl.tmp"
	{te = p;p--;{
    callback(NIX_LANG, nix_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 98:
#line 220 "nix.rl.tmp"
	{te = p;p--;}
	break;
	case 99:
#line 220 "nix.rl.tmp"
	{{p = ((te))-1;}}
	break;
#line 1518 "nix.h"
		}
	}

_again:
	_acts = _nix_actions + _nix_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 40:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 1531 "nix.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _nix_eof_trans[cs] > 0 ) {
		_trans = _nix_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 247 "nix.rl.tmp"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(NIX_LANG) }
}

#endif

/*****************************************************************************/
