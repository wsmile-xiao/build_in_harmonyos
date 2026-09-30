
#line 1 "rust.rl"
// rust.rl written by Sébastien Crozet <developer@crozet.re>
// Inpired by golang.rl

/************************* Required for every parser *************************/
#ifndef OHCOUNT_RUST_PARSER_H
#define OHCOUNT_RUST_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *RUST_LANG = LANG_RUST;

// the languages entities
const char *rust_entities[] = {
  "space", "comment", "string", "number",
  "keyword", "identifier", "operator", "any"
};

// constants associated with the entities
enum {
  RUST_SPACE = 0, RUST_COMMENT, RUST_STRING, RUST_NUMBER,
  RUST_KEYWORD, RUST_IDENTIFIER, RUST_OPERATOR, RUST_ANY
};

/*****************************************************************************/


#line 31 "rust.h"
static const char _rust_actions[] = {
	0, 1, 0, 1, 1, 1, 6, 1, 
	7, 1, 9, 1, 10, 1, 11, 1, 
	12, 1, 13, 1, 17, 1, 18, 1, 
	20, 1, 21, 1, 24, 1, 25, 1, 
	26, 1, 27, 1, 28, 1, 29, 1, 
	35, 1, 36, 1, 37, 1, 38, 1, 
	39, 1, 40, 1, 41, 1, 42, 1, 
	43, 1, 44, 2, 3, 2, 2, 4, 
	2, 2, 5, 2, 2, 7, 22, 2, 
	8, 23, 2, 10, 30, 2, 11, 31, 
	2, 12, 32, 2, 13, 14, 2, 13, 
	16, 2, 16, 34, 2, 19, 1, 2, 
	19, 8, 2, 19, 10, 2, 19, 12, 
	3, 3, 2, 1, 3, 3, 2, 25, 
	3, 4, 2, 1, 3, 5, 2, 0, 
	3, 5, 2, 21, 3, 13, 14, 16, 
	3, 15, 33, 16, 3, 19, 0, 8, 
	3, 19, 11, 16, 4, 19, 3, 2, 
	1, 4, 19, 10, 15, 16
};

static const char _rust_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 1, 1, 1, 1, 2, 3, 
	4, 4, 4, 4, 4, 4, 4, 4, 
	4, 5, 5, 5, 5, 5, 5, 5, 
	5, 5, 5, 5, 5, 5, 5, 5, 
	5, 5, 5, 5, 5, 5, 5, 5, 
	5, 5, 5, 5, 5, 5, 5, 5, 
	5, 5, 5, 5, 5, 5, 5, 5, 
	5, 5, 5, 5, 5, 5, 5, 5, 
	5, 5, 5, 5, 5, 5, 5, 5, 
	5, 5, 5, 5, 5, 5, 5, 5, 
	5, 5, 5, 5, 5, 5, 5, 5, 
	5, 5, 5, 5, 5, 5, 5, 5, 
	5, 5, 5, 5, 5, 5, 5, 5, 
	5, 5, 5, 5, 5, 6, 6, 6, 
	6, 6, 7, 7, 7
};

static const char _rust_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 1, 0, 0, 0, 1, 1, 1, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 1, 0, 0, 0, 
	0, 1, 0, 0, 0
};

static const short _rust_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 0
};

static const char _rust_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0
};

static const short _rust_key_offsets[] = {
	0, 0, 2, 2, 3, 5, 6, 9, 
	14, 17, 19, 20, 21, 22, 25, 28, 
	35, 39, 47, 51, 52, 57, 68, 79, 
	91, 92, 93, 94, 136, 139, 141, 143, 
	147, 154, 157, 169, 175, 179, 188, 192, 
	197, 202, 211, 218, 227, 235, 243, 251, 
	259, 267, 276, 284, 292, 300, 308, 316, 
	325, 333, 341, 349, 357, 365, 373, 383, 
	391, 399, 407, 415, 423, 431, 439, 449, 
	457, 465, 475, 483, 491, 500, 509, 517, 
	527, 535, 543, 551, 559, 568, 576, 584, 
	592, 600, 608, 617, 625, 633, 642, 650, 
	659, 667, 678, 686, 694, 702, 711, 719, 
	727, 735, 743, 751, 759, 767, 776, 785, 
	793, 801, 809, 818, 826, 834, 842, 850, 
	858, 866, 874, 882, 890, 902, 904, 908, 
	910, 916, 927, 933, 939
};

static const short _rust_trans_keys[] = {
	34, 92, 42, 42, 47, 10, 95, 48, 
	57, 43, 45, 95, 48, 57, 95, 48, 
	57, 51, 54, 50, 52, 54, 95, 48, 
	49, 95, 48, 55, 95, 48, 57, 65, 
	70, 97, 102, 9, 32, 34, 92, 10, 
	12, 269, 525, 0, 11, 14, 255, 9, 
	32, 34, 92, 10, 9, 10, 32, 34, 
	92, 9, 10, 12, 32, 42, 269, 525, 
	0, 11, 14, 255, 9, 10, 12, 32, 
	42, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 42, 47, 269, 525, 0, 
	11, 14, 255, 10, 10, 10, 32, 33, 
	34, 47, 48, 91, 95, 97, 98, 99, 
	100, 101, 102, 105, 108, 109, 111, 112, 
	114, 115, 116, 117, 119, 121, 9, 13, 
	37, 38, 40, 46, 49, 57, 58, 64, 
	65, 90, 93, 94, 103, 122, 123, 126, 
	32, 9, 13, 34, 92, 42, 47, 10, 
	92, 12, 13, 92, 269, 525, 0, 12, 
	14, 255, 92, 12, 13, 46, 69, 95, 
	98, 101, 102, 105, 111, 117, 120, 48, 
	57, 69, 95, 101, 102, 48, 57, 95, 
	102, 48, 57, 46, 69, 95, 101, 102, 
	105, 117, 48, 57, 49, 51, 54, 56, 
	95, 105, 117, 48, 49, 95, 105, 117, 
	48, 55, 95, 105, 117, 48, 57, 65, 
	70, 97, 102, 95, 48, 57, 65, 90, 
	97, 122, 95, 108, 115, 48, 57, 65, 
	90, 97, 122, 95, 105, 48, 57, 65, 
	90, 97, 122, 95, 103, 48, 57, 65, 
	90, 97, 122, 95, 110, 48, 57, 65, 
	90, 97, 122, 95, 111, 48, 57, 65, 
	90, 97, 122, 95, 102, 48, 57, 65, 
	90, 97, 122, 95, 101, 114, 48, 57, 
	65, 90, 97, 122, 95, 101, 48, 57, 
	65, 90, 97, 122, 95, 97, 48, 57, 
	65, 90, 98, 122, 95, 107, 48, 57, 
	65, 90, 97, 122, 95, 111, 48, 57, 
	65, 90, 97, 122, 95, 110, 48, 57, 
	65, 90, 97, 122, 95, 115, 116, 48, 
	57, 65, 90, 97, 122, 95, 116, 48, 
	57, 65, 90, 97, 122, 95, 105, 48, 
	57, 65, 90, 97, 122, 95, 110, 48, 
	57, 65, 90, 97, 122, 95, 117, 48, 
	57, 65, 90, 97, 122, 95, 101, 48, 
	57, 65, 90, 97, 122, 95, 111, 48, 
	57, 65, 90, 97, 122, 95, 108, 110, 
	120, 48, 57, 65, 90, 97, 122, 95, 
	115, 48, 57, 65, 90, 97, 122, 95, 
	117, 48, 57, 65, 90, 97, 122, 95, 
	109, 48, 57, 65, 90, 97, 122, 95, 
	116, 48, 57, 65, 90, 97, 122, 95, 
	101, 48, 57, 65, 90, 97, 122, 95, 
	114, 48, 57, 65, 90, 97, 122, 95, 
	110, 48, 57, 65, 90, 97, 122, 95, 
	97, 110, 111, 48, 57, 65, 90, 98, 
	122, 95, 108, 48, 57, 65, 90, 97, 
	122, 95, 114, 48, 57, 65, 90, 97, 
	122, 95, 102, 109, 110, 48, 57, 65, 
	90, 97, 122, 95, 112, 48, 57, 65, 
	90, 97, 122, 95, 108, 48, 57, 65, 
	90, 97, 122, 95, 101, 111, 48, 57, 
	65, 90, 97, 122, 95, 103, 111, 48, 
	57, 65, 90, 97, 122, 95, 112, 48, 
	57, 65, 90, 97, 122, 95, 97, 111, 
	117, 48, 57, 65, 90, 98, 122, 95, 
	116, 48, 57, 65, 90, 97, 122, 95, 
	99, 48, 57, 65, 90, 97, 122, 95, 
	104, 48, 57, 65, 90, 97, 122, 95, 
	100, 48, 57, 65, 90, 97, 122, 95, 
	102, 110, 48, 57, 65, 90, 97, 122, 
	95, 102, 48, 57, 65, 90, 97, 122, 
	95, 115, 48, 57, 65, 90, 97, 122, 
	95, 101, 48, 57, 65, 90, 97, 122, 
	95, 116, 48, 57, 65, 90, 97, 122, 
	95, 99, 48, 57, 65, 90, 97, 122, 
	95, 114, 117, 48, 57, 65, 90, 97, 
	122, 95, 105, 48, 57, 65, 90, 97, 
	122, 95, 118, 48, 57, 65, 90, 97, 
	122, 95, 98, 114, 48, 57, 65, 90, 
	97, 122, 95, 101, 48, 57, 65, 90, 
	97, 122, 95, 102, 116, 48, 57, 65, 
	90, 97, 122, 95, 117, 48, 57, 65, 
	90, 97, 122, 95, 101, 105, 116, 117, 
	48, 57, 65, 90, 97, 122, 95, 108, 
	48, 57, 65, 90, 97, 122, 95, 122, 
	48, 57, 65, 90, 97, 121, 95, 101, 
	48, 57, 65, 90, 97, 122, 95, 97, 
	114, 48, 57, 65, 90, 98, 122, 95, 
	116, 48, 57, 65, 90, 97, 122, 95, 
	105, 48, 57, 65, 90, 97, 122, 95, 
	99, 48, 57, 65, 90, 97, 122, 95, 
	117, 48, 57, 65, 90, 97, 122, 95, 
	99, 48, 57, 65, 90, 97, 122, 95, 
	112, 48, 57, 65, 90, 97, 122, 95, 
	101, 48, 57, 65, 90, 97, 122, 95, 
	114, 121, 48, 57, 65, 90, 97, 122, 
	95, 97, 117, 48, 57, 65, 90, 98, 
	122, 95, 105, 48, 57, 65, 90, 97, 
	122, 95, 112, 48, 57, 65, 90, 97, 
	122, 95, 101, 48, 57, 65, 90, 97, 
	122, 95, 110, 115, 48, 57, 65, 90, 
	97, 122, 95, 115, 48, 57, 65, 90, 
	97, 122, 95, 97, 48, 57, 65, 90, 
	98, 122, 95, 102, 48, 57, 65, 90, 
	97, 122, 95, 104, 48, 57, 65, 90, 
	97, 122, 95, 105, 48, 57, 65, 90, 
	97, 122, 95, 108, 48, 57, 65, 90, 
	97, 122, 95, 105, 48, 57, 65, 90, 
	97, 122, 95, 101, 48, 57, 65, 90, 
	97, 122, 95, 108, 48, 57, 65, 90, 
	97, 122, 9, 10, 12, 32, 34, 47, 
	269, 525, 0, 8, 14, 255, 9, 32, 
	9, 32, 34, 92, 42, 47, 9, 10, 
	32, 92, 12, 13, 9, 10, 12, 32, 
	92, 269, 525, 0, 11, 14, 255, 9, 
	10, 32, 92, 12, 13, 9, 10, 32, 
	92, 12, 13, 10, 0
};

static const char _rust_single_lengths[] = {
	0, 2, 0, 1, 2, 1, 1, 3, 
	1, 2, 1, 1, 1, 1, 1, 1, 
	4, 4, 4, 1, 5, 7, 7, 8, 
	1, 1, 1, 24, 1, 2, 2, 2, 
	3, 1, 10, 4, 2, 7, 4, 3, 
	3, 3, 1, 3, 2, 2, 2, 2, 
	2, 3, 2, 2, 2, 2, 2, 3, 
	2, 2, 2, 2, 2, 2, 4, 2, 
	2, 2, 2, 2, 2, 2, 4, 2, 
	2, 4, 2, 2, 3, 3, 2, 4, 
	2, 2, 2, 2, 3, 2, 2, 2, 
	2, 2, 3, 2, 2, 3, 2, 3, 
	2, 5, 2, 2, 2, 3, 2, 2, 
	2, 2, 2, 2, 2, 3, 3, 2, 
	2, 2, 3, 2, 2, 2, 2, 2, 
	2, 2, 2, 2, 8, 2, 4, 2, 
	4, 7, 4, 4, 1
};

static const char _rust_range_lengths[] = {
	0, 0, 0, 0, 0, 0, 1, 1, 
	1, 0, 0, 0, 0, 1, 1, 3, 
	0, 2, 0, 0, 0, 2, 2, 2, 
	0, 0, 0, 9, 1, 0, 0, 1, 
	2, 1, 1, 1, 1, 1, 0, 1, 
	1, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 2, 0, 0, 0, 
	1, 2, 1, 1, 0
};

static const short _rust_index_offsets[] = {
	0, 0, 3, 4, 6, 9, 11, 14, 
	19, 22, 25, 27, 29, 31, 34, 37, 
	42, 47, 54, 59, 61, 67, 77, 87, 
	98, 100, 102, 104, 138, 141, 144, 147, 
	151, 157, 160, 172, 178, 182, 191, 196, 
	201, 206, 213, 218, 225, 231, 237, 243, 
	249, 255, 262, 268, 274, 280, 286, 292, 
	299, 305, 311, 317, 323, 329, 335, 343, 
	349, 355, 361, 367, 373, 379, 385, 393, 
	399, 405, 413, 419, 425, 432, 439, 445, 
	453, 459, 465, 471, 477, 484, 490, 496, 
	502, 508, 514, 521, 527, 533, 540, 546, 
	553, 559, 568, 574, 580, 586, 593, 599, 
	605, 611, 617, 623, 629, 635, 642, 649, 
	655, 661, 667, 674, 680, 686, 692, 698, 
	704, 710, 716, 722, 728, 739, 742, 747, 
	750, 756, 766, 772, 778
};

static const char _rust_indicies[] = {
	2, 3, 1, 1, 6, 5, 6, 7, 
	5, 9, 8, 11, 11, 10, 12, 12, 
	13, 13, 10, 13, 13, 10, 14, 15, 
	10, 16, 10, 16, 10, 16, 10, 17, 
	17, 10, 18, 18, 10, 19, 19, 19, 
	19, 10, 22, 22, 23, 24, 21, 25, 
	25, 26, 27, 21, 21, 20, 29, 29, 
	30, 31, 28, 25, 20, 29, 32, 29, 
	30, 31, 28, 34, 35, 35, 34, 36, 
	37, 35, 33, 33, 20, 39, 40, 40, 
	39, 41, 42, 40, 38, 38, 20, 34, 
	35, 35, 34, 36, 43, 37, 35, 33, 
	33, 20, 35, 20, 45, 44, 46, 47, 
	49, 50, 51, 52, 53, 50, 55, 56, 
	57, 58, 59, 60, 61, 62, 63, 64, 
	65, 66, 67, 68, 69, 70, 71, 72, 
	49, 50, 50, 54, 50, 55, 50, 55, 
	50, 48, 49, 49, 73, 2, 3, 1, 
	5, 9, 75, 76, 77, 76, 9, 77, 
	78, 79, 9, 9, 76, 77, 76, 9, 
	81, 82, 54, 83, 82, 84, 85, 86, 
	85, 87, 54, 80, 82, 11, 82, 84, 
	11, 80, 13, 84, 13, 80, 81, 82, 
	54, 82, 84, 85, 85, 54, 80, 88, 
	14, 15, 16, 80, 17, 85, 85, 17, 
	80, 18, 85, 85, 18, 80, 19, 85, 
	85, 19, 19, 19, 80, 90, 90, 90, 
	90, 89, 90, 91, 92, 90, 90, 90, 
	89, 90, 93, 90, 90, 90, 89, 90, 
	94, 90, 90, 90, 89, 90, 95, 90, 
	90, 90, 89, 90, 96, 90, 90, 90, 
	89, 90, 92, 90, 90, 90, 89, 90, 
	92, 97, 90, 90, 90, 89, 90, 98, 
	90, 90, 90, 89, 90, 99, 90, 90, 
	90, 89, 90, 92, 90, 90, 90, 89, 
	90, 100, 90, 90, 90, 89, 90, 101, 
	90, 90, 90, 89, 90, 102, 103, 90, 
	90, 90, 89, 90, 92, 90, 90, 90, 
	89, 90, 104, 90, 90, 90, 89, 90, 
	105, 90, 90, 90, 89, 90, 106, 90, 
	90, 90, 89, 90, 92, 90, 90, 90, 
	89, 90, 92, 90, 90, 90, 89, 90, 
	107, 108, 109, 90, 90, 90, 89, 90, 
	106, 90, 90, 90, 89, 90, 110, 90, 
	90, 90, 89, 90, 92, 90, 90, 90, 
	89, 90, 111, 90, 90, 90, 89, 90, 
	112, 90, 90, 90, 89, 90, 113, 90, 
	90, 90, 89, 90, 92, 90, 90, 90, 
	89, 90, 114, 92, 115, 90, 90, 90, 
	89, 90, 107, 90, 90, 90, 89, 90, 
	92, 90, 90, 90, 89, 90, 92, 116, 
	92, 90, 90, 90, 89, 90, 117, 90, 
	90, 90, 89, 90, 92, 90, 90, 90, 
	89, 90, 102, 118, 90, 90, 90, 89, 
	90, 92, 119, 90, 90, 90, 89, 90, 
	92, 90, 90, 90, 89, 90, 120, 121, 
	102, 90, 90, 90, 89, 90, 122, 90, 
	90, 90, 89, 90, 123, 90, 90, 90, 
	89, 90, 92, 90, 90, 90, 89, 90, 
	92, 90, 90, 90, 89, 90, 124, 125, 
	90, 90, 90, 89, 90, 126, 90, 90, 
	90, 89, 90, 127, 90, 90, 90, 89, 
	90, 128, 90, 90, 90, 89, 90, 95, 
	90, 90, 90, 89, 90, 106, 90, 90, 
	90, 89, 90, 129, 130, 90, 90, 90, 
	89, 90, 131, 90, 90, 90, 89, 90, 
	92, 90, 90, 90, 89, 90, 92, 106, 
	90, 90, 90, 89, 90, 132, 90, 90, 
	90, 89, 90, 92, 133, 90, 90, 90, 
	89, 90, 112, 90, 90, 90, 89, 90, 
	134, 135, 136, 137, 90, 90, 90, 89, 
	90, 96, 90, 90, 90, 89, 90, 138, 
	90, 90, 90, 89, 90, 95, 90, 90, 
	90, 89, 90, 139, 140, 90, 90, 90, 
	89, 90, 141, 90, 90, 90, 89, 90, 
	142, 90, 90, 90, 89, 90, 92, 90, 
	90, 90, 89, 90, 143, 90, 90, 90, 
	89, 90, 102, 90, 90, 90, 89, 90, 
	144, 90, 90, 90, 89, 90, 115, 90, 
	90, 90, 89, 90, 145, 146, 90, 90, 
	90, 89, 90, 147, 106, 90, 90, 90, 
	89, 90, 102, 90, 90, 90, 89, 90, 
	148, 90, 90, 90, 89, 90, 95, 90, 
	90, 90, 89, 90, 149, 106, 90, 90, 
	90, 89, 90, 150, 90, 90, 90, 89, 
	90, 151, 90, 90, 90, 89, 90, 106, 
	90, 90, 90, 89, 90, 152, 90, 90, 
	90, 89, 90, 153, 90, 90, 90, 89, 
	90, 106, 90, 90, 90, 89, 90, 154, 
	90, 90, 90, 89, 90, 155, 90, 90, 
	90, 89, 90, 121, 90, 90, 90, 89, 
	157, 46, 46, 157, 158, 159, 160, 161, 
	156, 156, 47, 157, 157, 162, 22, 22, 
	23, 24, 21, 33, 164, 163, 166, 165, 
	166, 167, 165, 164, 166, 45, 45, 166, 
	167, 168, 169, 164, 164, 165, 172, 170, 
	172, 173, 170, 171, 172, 45, 172, 173, 
	170, 171, 46, 174, 0
};

static const char _rust_trans_targs[] = {
	27, 1, 27, 2, 27, 3, 4, 27, 
	27, 31, 27, 35, 8, 36, 10, 11, 
	27, 39, 40, 41, 124, 16, 16, 124, 
	17, 18, 19, 20, 16, 16, 124, 17, 
	18, 21, 21, 22, 23, 24, 21, 21, 
	22, 23, 24, 124, 124, 130, 124, 0, 
	27, 28, 27, 29, 30, 34, 37, 42, 
	43, 49, 53, 61, 62, 70, 73, 76, 
	79, 84, 90, 94, 97, 109, 114, 118, 
	121, 27, 27, 27, 27, 32, 5, 33, 
	27, 6, 7, 13, 9, 38, 14, 15, 
	12, 27, 42, 44, 42, 45, 46, 47, 
	48, 50, 51, 52, 54, 55, 56, 57, 
	58, 59, 60, 63, 64, 66, 65, 67, 
	68, 69, 71, 72, 74, 75, 77, 78, 
	80, 83, 81, 82, 85, 89, 86, 87, 
	88, 91, 93, 92, 95, 96, 98, 99, 
	101, 107, 100, 102, 105, 103, 104, 106, 
	108, 110, 112, 111, 113, 115, 116, 117, 
	119, 120, 122, 123, 124, 125, 126, 127, 
	26, 132, 124, 124, 128, 124, 128, 129, 
	25, 131, 124, 128, 128, 129, 124
};

static const char _rust_trans_actions[] = {
	57, 13, 77, 13, 55, 11, 11, 74, 
	51, 11, 53, 101, 15, 101, 15, 15, 
	80, 15, 15, 15, 37, 1, 0, 25, 
	0, 0, 0, 0, 116, 65, 120, 65, 
	116, 3, 0, 0, 3, 0, 112, 62, 
	62, 112, 62, 23, 35, 0, 68, 0, 
	89, 9, 128, 136, 145, 101, 101, 86, 
	124, 124, 124, 124, 124, 124, 124, 124, 
	124, 124, 124, 124, 124, 124, 124, 124, 
	124, 39, 49, 47, 41, 98, 11, 11, 
	43, 15, 15, 15, 15, 101, 15, 15, 
	15, 45, 17, 83, 83, 83, 83, 83, 
	83, 83, 83, 83, 83, 83, 83, 83, 
	83, 83, 83, 83, 83, 83, 83, 83, 
	83, 83, 83, 83, 83, 83, 83, 83, 
	83, 83, 83, 83, 83, 83, 83, 83, 
	83, 83, 83, 83, 83, 83, 83, 83, 
	83, 83, 83, 83, 83, 83, 83, 83, 
	83, 83, 83, 83, 83, 83, 83, 83, 
	83, 83, 83, 83, 71, 5, 132, 95, 
	7, 7, 27, 33, 3, 29, 0, 92, 
	0, 0, 108, 104, 59, 140, 31
};

static const char _rust_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 19, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 19, 0, 0, 0, 
	0, 0, 0, 0, 0
};

static const char _rust_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 21, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 21, 0, 0, 0, 
	0, 0, 0, 0, 0
};

static const short _rust_eof_trans[] = {
	0, 1, 1, 5, 5, 9, 11, 11, 
	11, 11, 11, 11, 11, 11, 11, 11, 
	21, 21, 21, 21, 21, 21, 21, 21, 
	21, 45, 0, 0, 74, 75, 76, 77, 
	77, 77, 81, 81, 81, 81, 81, 81, 
	81, 81, 90, 90, 90, 90, 90, 90, 
	90, 90, 90, 90, 90, 90, 90, 90, 
	90, 90, 90, 90, 90, 90, 90, 90, 
	90, 90, 90, 90, 90, 90, 90, 90, 
	90, 90, 90, 90, 90, 90, 90, 90, 
	90, 90, 90, 90, 90, 90, 90, 90, 
	90, 90, 90, 90, 90, 90, 90, 90, 
	90, 90, 90, 90, 90, 90, 90, 90, 
	90, 90, 90, 90, 90, 90, 90, 90, 
	90, 90, 90, 90, 90, 90, 90, 90, 
	90, 90, 90, 90, 0, 163, 164, 164, 
	166, 166, 171, 171, 175
};

static const int rust_start = 27;
static const int rust_first_final = 27;
static const int rust_error = 0;

static const int rust_en_rust_line = 124;
static const int rust_en_rust_entity = 27;


#line 140 "rust.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with C/C++ code.
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
void parse_rust(char *buffer, int length, int count,
             void (*callback) (const char *lang, const char *entity, int s,
                               int e, void *udata),
             void *userdata
  ) {
  init

  
#line 547 "rust.h"
	{
	cs = rust_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 163 "rust.rl"
  cs = (count) ? rust_en_rust_line : rust_en_rust_entity;
  
#line 558 "rust.h"
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
	_acts = _rust_actions + _rust_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 18:
#line 1 "NONE"
	{ts = p;}
	break;
#line 580 "rust.h"
		}
	}

	_widec = (*p);
	_klen = _rust_cond_lengths[cs];
	_keys = _rust_cond_keys + (_rust_cond_offsets[cs]*2);
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
				switch ( _rust_cond_spaces[_rust_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _rust_trans_keys + _rust_key_offsets[cs];
	_trans = _rust_index_offsets[cs];

	_klen = _rust_single_lengths[cs];
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

	_klen = _rust_range_lengths[cs];
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
	_trans = _rust_indicies[_trans];
_eof_trans:
	cs = _rust_trans_targs[_trans];

	if ( _rust_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _rust_actions + _rust_trans_actions[_trans];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 )
	{
		switch ( *_acts++ )
		{
	case 0:
#line 53 "common.rl"
	{
  if (!line_contains_code && !line_start) line_start = ts;
  line_contains_code = 1;
}
	break;
	case 1:
#line 58 "common.rl"
	{
  if (!line_contains_code) {
    whole_line_comment = 1;
    if (!line_start) line_start = ts;
  }
}
	break;
	case 2:
#line 34 "rust.rl"
	{
    switch(entity) {
    case RUST_SPACE:
      ls
      break;
    case RUST_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(RUST_LANG)
      break;
    case NEWLINE:
      std_newline(RUST_LANG)
    }
  }
	break;
	case 3:
#line 52 "rust.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 60 "rust.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 70 "rust.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 6:
#line 81 "rust.rl"
	{ entity = RUST_SPACE; }
	break;
	case 7:
#line 84 "rust.rl"
	{ entity = NEWLINE; }
	break;
	case 8:
#line 85 "rust.rl"
	{ entity = RUST_ANY;   }
	break;
	case 9:
#line 131 "rust.rl"
	{ entity = RUST_SPACE;      }
	break;
	case 10:
#line 132 "rust.rl"
	{ entity = RUST_COMMENT;    }
	break;
	case 11:
#line 133 "rust.rl"
	{ entity = RUST_STRING;     }
	break;
	case 12:
#line 134 "rust.rl"
	{ entity = RUST_NUMBER;     }
	break;
	case 13:
#line 135 "rust.rl"
	{ entity = RUST_IDENTIFIER; }
	break;
	case 14:
#line 136 "rust.rl"
	{ entity = RUST_KEYWORD;    }
	break;
	case 15:
#line 137 "rust.rl"
	{ entity = RUST_OPERATOR;   }
	break;
	case 16:
#line 138 "rust.rl"
	{ entity = RUST_ANY;        }
	break;
	case 19:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 20:
#line 82 "rust.rl"
	{te = p+1;}
	break;
	case 21:
#line 83 "rust.rl"
	{te = p+1;}
	break;
	case 22:
#line 34 "rust.rl"
	{te = p+1;{
    switch(entity) {
    case RUST_SPACE:
      ls
      break;
    case RUST_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(RUST_LANG)
      break;
    case NEWLINE:
      std_newline(RUST_LANG)
    }
  }}
	break;
	case 23:
#line 34 "rust.rl"
	{te = p+1;{
    switch(entity) {
    case RUST_SPACE:
      ls
      break;
    case RUST_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(RUST_LANG)
      break;
    case NEWLINE:
      std_newline(RUST_LANG)
    }
  }}
	break;
	case 24:
#line 34 "rust.rl"
	{te = p;p--;{
    switch(entity) {
    case RUST_SPACE:
      ls
      break;
    case RUST_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(RUST_LANG)
      break;
    case NEWLINE:
      std_newline(RUST_LANG)
    }
  }}
	break;
	case 25:
#line 82 "rust.rl"
	{te = p;p--;}
	break;
	case 26:
#line 34 "rust.rl"
	{te = p;p--;{
    switch(entity) {
    case RUST_SPACE:
      ls
      break;
    case RUST_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(RUST_LANG)
      break;
    case NEWLINE:
      std_newline(RUST_LANG)
    }
  }}
	break;
	case 27:
#line 34 "rust.rl"
	{te = p;p--;{
    switch(entity) {
    case RUST_SPACE:
      ls
      break;
    case RUST_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(RUST_LANG)
      break;
    case NEWLINE:
      std_newline(RUST_LANG)
    }
  }}
	break;
	case 28:
#line 82 "rust.rl"
	{{p = ((te))-1;}}
	break;
	case 29:
#line 34 "rust.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case RUST_SPACE:
      ls
      break;
    case RUST_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(RUST_LANG)
      break;
    case NEWLINE:
      std_newline(RUST_LANG)
    }
  }}
	break;
	case 30:
#line 90 "rust.rl"
	{te = p+1;{
    callback(RUST_LANG, rust_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 31:
#line 90 "rust.rl"
	{te = p+1;{
    callback(RUST_LANG, rust_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 32:
#line 90 "rust.rl"
	{te = p+1;{
    callback(RUST_LANG, rust_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 33:
#line 90 "rust.rl"
	{te = p+1;{
    callback(RUST_LANG, rust_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 34:
#line 90 "rust.rl"
	{te = p+1;{
    callback(RUST_LANG, rust_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 35:
#line 90 "rust.rl"
	{te = p;p--;{
    callback(RUST_LANG, rust_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 36:
#line 90 "rust.rl"
	{te = p;p--;{
    callback(RUST_LANG, rust_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 37:
#line 90 "rust.rl"
	{te = p;p--;{
    callback(RUST_LANG, rust_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 38:
#line 90 "rust.rl"
	{te = p;p--;{
    callback(RUST_LANG, rust_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 39:
#line 90 "rust.rl"
	{te = p;p--;{
    callback(RUST_LANG, rust_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 40:
#line 90 "rust.rl"
	{te = p;p--;{
    callback(RUST_LANG, rust_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 41:
#line 90 "rust.rl"
	{{p = ((te))-1;}{
    callback(RUST_LANG, rust_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 42:
#line 90 "rust.rl"
	{{p = ((te))-1;}{
    callback(RUST_LANG, rust_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 43:
#line 90 "rust.rl"
	{{p = ((te))-1;}{
    callback(RUST_LANG, rust_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 44:
#line 90 "rust.rl"
	{{p = ((te))-1;}{
    callback(RUST_LANG, rust_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
#line 985 "rust.h"
		}
	}

_again:
	_acts = _rust_actions + _rust_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 17:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 998 "rust.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _rust_eof_trans[cs] > 0 ) {
		_trans = _rust_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 165 "rust.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(RUST_LANG) }
}

const char *ORIG_RUST_LANG = LANG_RUST;

#endif

/*****************************************************************************/
