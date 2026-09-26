
#line 1 "kotlin.rl"
// kotlin.rl written by Tuomas Tynkkynen <tuomas.tynkkynen@iki.fi>
// Inspired by rust.rl, python.rl and haskell.rl

/************************* Required for every parser *************************/
#ifndef OHCOUNT_KOTLIN_PARSER_H
#define OHCOUNT_KOTLIN_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *KOTLIN_LANG = LANG_KOTLIN;

// the languages entities
const char *kotlin_entities[] = {
  "space", "comment", "string", "number",
  "keyword", "identifier", "operator", "any"
};

// constants associated with the entities
enum {
  KOTLIN_SPACE = 0, KOTLIN_COMMENT, KOTLIN_STRING, KOTLIN_NUMBER,
  KOTLIN_KEYWORD, KOTLIN_IDENTIFIER, KOTLIN_OPERATOR, KOTLIN_ANY
};

/*****************************************************************************/


#line 31 "kotlin.h"
static const char _kotlin_actions[] = {
	0, 1, 0, 1, 1, 1, 8, 1, 
	10, 1, 11, 1, 13, 1, 14, 1, 
	15, 1, 16, 1, 17, 1, 21, 1, 
	22, 1, 27, 1, 30, 1, 31, 1, 
	32, 1, 33, 1, 34, 1, 35, 1, 
	36, 1, 43, 1, 44, 1, 45, 1, 
	46, 1, 47, 1, 48, 1, 49, 1, 
	50, 1, 51, 1, 52, 1, 53, 2, 
	1, 26, 2, 4, 1, 2, 5, 1, 
	2, 6, 2, 2, 7, 8, 2, 9, 
	2, 2, 11, 28, 2, 12, 29, 2, 
	14, 37, 2, 15, 38, 2, 16, 39, 
	2, 17, 18, 2, 17, 20, 2, 17, 
	40, 2, 20, 42, 2, 23, 15, 2, 
	23, 16, 3, 6, 2, 1, 3, 9, 
	2, 0, 3, 17, 18, 20, 3, 19, 
	41, 20, 3, 23, 0, 24, 3, 23, 
	3, 12, 3, 23, 15, 20, 3, 23, 
	17, 20, 4, 23, 0, 12, 25, 4, 
	23, 14, 19, 20
};

static const char _kotlin_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 1, 2, 3, 4, 6, 8, 
	10, 10, 12, 15, 15, 15, 15, 15, 
	15, 15, 15, 15, 15, 15, 15, 15, 
	15, 15, 15, 15, 15, 15, 15, 15, 
	15, 15, 15, 15, 15, 15, 15, 15, 
	15, 15, 15, 15, 15, 15, 15, 15, 
	15, 15, 15, 15, 15, 15, 15, 15, 
	15, 15, 15, 15, 15, 15, 15, 15, 
	15, 15, 15, 15, 15, 15, 15, 15, 
	15, 15, 15, 15, 15, 15, 15, 15, 
	15, 15, 15, 15, 16, 16, 16, 17, 
	17, 17
};

static const char _kotlin_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 1, 1, 1, 1, 2, 2, 2, 
	0, 2, 3, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 1, 0, 0, 1, 0, 
	0, 0
};

static const short _kotlin_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 42, 42, 13, 13, 42, 42, 
	13, 13, 42, 42, 13, 13, 42, 42, 
	13, 13, 42, 42, 47, 47, 13, 13, 
	13, 13, 0
};

static const char _kotlin_cond_spaces[] = {
	0, 0, 0, 0, 0, 1, 0, 1, 
	0, 1, 0, 1, 0, 1, 1, 0, 
	0, 0
};

static const short _kotlin_key_offsets[] = {
	0, 0, 2, 2, 3, 4, 5, 6, 
	8, 10, 14, 16, 18, 24, 31, 36, 
	39, 40, 51, 62, 73, 84, 99, 114, 
	129, 130, 145, 163, 164, 205, 208, 210, 
	211, 212, 214, 217, 227, 233, 237, 245, 
	248, 256, 262, 269, 277, 285, 293, 298, 
	306, 314, 322, 330, 339, 347, 355, 363, 
	371, 379, 387, 395, 403, 411, 419, 427, 
	437, 445, 453, 463, 471, 479, 487, 495, 
	503, 511, 519, 527, 535, 543, 551, 559, 
	567, 575, 583, 591, 599, 607, 615, 623, 
	633, 642, 650, 658, 668, 676, 684, 692, 
	701, 709, 718, 726, 738, 740, 741, 752, 
	754, 757
};

static const short _kotlin_trans_keys[] = {
	34, 92, 34, 34, 34, 42, 42, 47, 
	48, 57, 43, 45, 48, 57, 48, 57, 
	48, 49, 48, 57, 65, 70, 97, 102, 
	96, 48, 57, 65, 90, 95, 122, 10, 
	34, 92, 12, 13, 10, 12, 13, 34, 
	9, 10, 12, 32, 34, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 34, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 34, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 34, 269, 525, 
	0, 11, 14, 255, 9, 10, 12, 32, 
	47, 269, 525, 810, 1066, 0, 11, 14, 
	41, 43, 255, 9, 10, 12, 32, 47, 
	269, 525, 810, 1066, 0, 11, 14, 41, 
	43, 255, 9, 10, 12, 32, 47, 269, 
	525, 810, 1066, 0, 11, 14, 41, 43, 
	255, 10, 9, 10, 12, 32, 47, 269, 
	525, 810, 1066, 0, 11, 14, 41, 43, 
	255, 9, 10, 12, 32, 269, 525, 810, 
	815, 1066, 1071, 0, 11, 14, 41, 43, 
	46, 48, 255, 10, 32, 33, 34, 47, 
	48, 84, 91, 96, 97, 98, 99, 100, 
	101, 102, 105, 110, 111, 112, 114, 115, 
	116, 118, 119, 9, 13, 37, 38, 40, 
	46, 49, 57, 58, 63, 65, 90, 93, 
	94, 95, 122, 123, 126, 32, 9, 13, 
	34, 92, 34, 34, 42, 47, 10, 12, 
	13, 46, 69, 70, 76, 98, 101, 102, 
	120, 48, 57, 69, 70, 101, 102, 48, 
	57, 70, 102, 48, 57, 46, 69, 70, 
	76, 101, 102, 48, 57, 76, 48, 49, 
	46, 76, 48, 57, 65, 70, 97, 102, 
	48, 57, 65, 70, 97, 102, 95, 48, 
	57, 65, 90, 97, 122, 95, 104, 48, 
	57, 65, 90, 97, 122, 95, 105, 48, 
	57, 65, 90, 97, 122, 95, 115, 48, 
	57, 65, 90, 97, 122, 95, 65, 90, 
	97, 122, 95, 114, 48, 57, 65, 90, 
	97, 122, 95, 101, 48, 57, 65, 90, 
	97, 122, 95, 97, 48, 57, 65, 90, 
	98, 122, 95, 107, 48, 57, 65, 90, 
	97, 122, 95, 108, 111, 48, 57, 65, 
	90, 97, 122, 95, 97, 48, 57, 65, 
	90, 98, 122, 95, 115, 48, 57, 65, 
	90, 97, 122, 95, 110, 48, 57, 65, 
	90, 97, 122, 95, 116, 48, 57, 65, 
	90, 97, 122, 95, 105, 48, 57, 65, 
	90, 97, 122, 95, 110, 48, 57, 65, 
	90, 97, 122, 95, 117, 48, 57, 65, 
	90, 97, 122, 95, 101, 48, 57, 65, 
	90, 97, 122, 95, 111, 48, 57, 65, 
	90, 97, 122, 95, 108, 48, 57, 65, 
	90, 97, 122, 95, 115, 48, 57, 65, 
	90, 97, 122, 95, 97, 111, 117, 48, 
	57, 65, 90, 98, 122, 95, 114, 48, 
	57, 65, 90, 97, 122, 95, 110, 48, 
	57, 65, 90, 97, 122, 95, 102, 110, 
	115, 48, 57, 65, 90, 97, 122, 95, 
	117, 48, 57, 65, 90, 97, 122, 95, 
	108, 48, 57, 65, 90, 97, 122, 95, 
	108, 48, 57, 65, 90, 97, 122, 95, 
	98, 48, 57, 65, 90, 97, 122, 95, 
	106, 48, 57, 65, 90, 97, 122, 95, 
	101, 48, 57, 65, 90, 97, 122, 95, 
	99, 48, 57, 65, 90, 97, 122, 95, 
	116, 48, 57, 65, 90, 97, 122, 95, 
	97, 48, 57, 65, 90, 98, 122, 95, 
	99, 48, 57, 65, 90, 97, 122, 95, 
	107, 48, 57, 65, 90, 97, 122, 95, 
	97, 48, 57, 65, 90, 98, 122, 95, 
	103, 48, 57, 65, 90, 97, 122, 95, 
	101, 48, 57, 65, 90, 97, 122, 95, 
	116, 48, 57, 65, 90, 97, 122, 95, 
	117, 48, 57, 65, 90, 97, 122, 95, 
	114, 48, 57, 65, 90, 97, 122, 95, 
	117, 48, 57, 65, 90, 97, 122, 95, 
	112, 48, 57, 65, 90, 97, 122, 95, 
	101, 48, 57, 65, 90, 97, 122, 95, 
	104, 114, 121, 48, 57, 65, 90, 97, 
	122, 95, 105, 114, 48, 57, 65, 90, 
	97, 122, 95, 111, 48, 57, 65, 90, 
	97, 122, 95, 119, 48, 57, 65, 90, 
	97, 122, 95, 97, 117, 121, 48, 57, 
	65, 90, 98, 122, 95, 105, 48, 57, 
	65, 90, 97, 122, 95, 112, 48, 57, 
	65, 90, 97, 122, 95, 97, 48, 57, 
	65, 90, 98, 122, 95, 108, 114, 48, 
	57, 65, 90, 97, 122, 95, 104, 48, 
	57, 65, 90, 97, 122, 95, 101, 105, 
	48, 57, 65, 90, 97, 122, 95, 108, 
	48, 57, 65, 90, 97, 122, 9, 10, 
	12, 32, 34, 47, 269, 525, 0, 8, 
	14, 255, 9, 32, 34, 9, 10, 12, 
	32, 34, 269, 525, 0, 11, 14, 255, 
	42, 47, 10, 12, 13, 10, 0
};

static const char _kotlin_single_lengths[] = {
	0, 2, 0, 1, 1, 1, 1, 2, 
	0, 2, 0, 0, 0, 1, 3, 1, 
	1, 7, 7, 7, 7, 9, 9, 9, 
	1, 9, 10, 1, 23, 1, 2, 1, 
	1, 2, 1, 8, 4, 2, 6, 1, 
	2, 0, 1, 2, 2, 2, 1, 2, 
	2, 2, 2, 3, 2, 2, 2, 2, 
	2, 2, 2, 2, 2, 2, 2, 4, 
	2, 2, 4, 2, 2, 2, 2, 2, 
	2, 2, 2, 2, 2, 2, 2, 2, 
	2, 2, 2, 2, 2, 2, 2, 4, 
	3, 2, 2, 4, 2, 2, 2, 3, 
	2, 3, 2, 8, 2, 1, 7, 2, 
	1, 1
};

static const char _kotlin_range_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 1, 1, 1, 3, 3, 1, 1, 
	0, 2, 2, 2, 2, 3, 3, 3, 
	0, 3, 4, 0, 9, 1, 0, 0, 
	0, 0, 1, 1, 1, 1, 1, 1, 
	3, 3, 3, 3, 3, 3, 2, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 2, 0, 0, 2, 0, 
	1, 0
};

static const short _kotlin_index_offsets[] = {
	0, 0, 3, 4, 6, 8, 10, 12, 
	15, 17, 21, 23, 25, 29, 34, 39, 
	42, 44, 54, 64, 74, 84, 97, 110, 
	123, 125, 138, 153, 155, 188, 191, 194, 
	196, 198, 201, 204, 214, 220, 224, 232, 
	235, 241, 245, 250, 256, 262, 268, 272, 
	278, 284, 290, 296, 303, 309, 315, 321, 
	327, 333, 339, 345, 351, 357, 363, 369, 
	377, 383, 389, 397, 403, 409, 415, 421, 
	427, 433, 439, 445, 451, 457, 463, 469, 
	475, 481, 487, 493, 499, 505, 511, 517, 
	525, 532, 538, 544, 552, 558, 564, 570, 
	577, 583, 590, 596, 607, 610, 612, 622, 
	625, 628
};

static const char _kotlin_indicies[] = {
	2, 3, 1, 1, 6, 5, 7, 5, 
	8, 5, 11, 10, 11, 12, 10, 14, 
	13, 15, 15, 16, 13, 16, 13, 17, 
	13, 18, 18, 18, 13, 20, 19, 19, 
	19, 0, 21, 23, 24, 21, 22, 21, 
	21, 22, 26, 25, 28, 29, 29, 28, 
	30, 26, 29, 26, 26, 27, 32, 33, 
	33, 32, 34, 31, 33, 31, 31, 27, 
	28, 29, 29, 28, 35, 26, 29, 26, 
	26, 27, 28, 29, 29, 28, 36, 26, 
	29, 26, 26, 27, 38, 39, 39, 38, 
	40, 41, 39, 42, 43, 37, 37, 37, 
	21, 45, 46, 46, 45, 47, 48, 46, 
	49, 50, 44, 44, 44, 21, 38, 39, 
	39, 38, 40, 41, 39, 51, 52, 37, 
	37, 37, 21, 39, 21, 38, 39, 39, 
	38, 53, 41, 39, 42, 43, 37, 37, 
	37, 21, 38, 39, 39, 38, 41, 39, 
	42, 53, 43, 54, 37, 37, 37, 37, 
	21, 55, 56, 58, 59, 60, 61, 62, 
	65, 59, 66, 67, 68, 69, 70, 71, 
	72, 73, 74, 75, 76, 77, 78, 79, 
	80, 81, 58, 59, 59, 63, 59, 64, 
	59, 64, 59, 57, 58, 58, 82, 84, 
	3, 1, 5, 85, 2, 85, 10, 87, 
	86, 88, 88, 87, 90, 91, 92, 92, 
	93, 91, 92, 94, 63, 89, 91, 92, 
	91, 92, 14, 89, 92, 92, 16, 89, 
	90, 91, 92, 92, 91, 92, 63, 89, 
	92, 17, 89, 95, 92, 18, 18, 18, 
	89, 95, 95, 95, 89, 97, 97, 97, 
	97, 96, 97, 98, 97, 97, 97, 96, 
	97, 99, 97, 97, 97, 96, 97, 100, 
	97, 97, 97, 96, 19, 19, 19, 83, 
	97, 101, 97, 97, 97, 96, 97, 102, 
	97, 97, 97, 96, 97, 103, 97, 97, 
	97, 96, 97, 100, 97, 97, 97, 96, 
	97, 104, 105, 97, 97, 97, 96, 97, 
	106, 97, 97, 97, 96, 97, 99, 97, 
	97, 97, 96, 97, 107, 97, 97, 97, 
	96, 97, 108, 97, 97, 97, 96, 97, 
	109, 97, 97, 97, 96, 97, 110, 97, 
	97, 97, 96, 97, 111, 97, 97, 97, 
	96, 97, 100, 97, 97, 97, 96, 97, 
	100, 97, 97, 97, 96, 97, 112, 97, 
	97, 97, 96, 97, 111, 97, 97, 97, 
	96, 97, 113, 114, 115, 97, 97, 97, 
	96, 97, 100, 97, 97, 97, 96, 97, 
	100, 97, 97, 97, 96, 97, 100, 100, 
	100, 97, 97, 97, 96, 97, 116, 97, 
	97, 97, 96, 97, 117, 97, 97, 97, 
	96, 97, 100, 97, 97, 97, 96, 97, 
	118, 97, 97, 97, 96, 97, 119, 97, 
	97, 97, 96, 97, 120, 97, 97, 97, 
	96, 97, 121, 97, 97, 97, 96, 97, 
	100, 97, 97, 97, 96, 97, 122, 97, 
	97, 97, 96, 97, 123, 97, 97, 97, 
	96, 97, 124, 97, 97, 97, 96, 97, 
	125, 97, 97, 97, 96, 97, 111, 97, 
	97, 97, 96, 97, 126, 97, 97, 97, 
	96, 97, 127, 97, 97, 97, 96, 97, 
	128, 97, 97, 97, 96, 97, 115, 97, 
	97, 97, 96, 97, 129, 97, 97, 97, 
	96, 97, 130, 97, 97, 97, 96, 97, 
	114, 97, 97, 97, 96, 97, 131, 132, 
	133, 97, 97, 97, 96, 97, 99, 134, 
	97, 97, 97, 96, 97, 135, 97, 97, 
	97, 96, 97, 100, 97, 97, 97, 96, 
	97, 136, 111, 100, 97, 97, 97, 96, 
	97, 121, 97, 97, 97, 96, 97, 111, 
	97, 97, 97, 96, 97, 137, 97, 97, 
	97, 96, 97, 100, 100, 97, 97, 97, 
	96, 97, 138, 97, 97, 97, 96, 97, 
	115, 139, 97, 97, 97, 96, 97, 111, 
	97, 97, 97, 96, 141, 55, 55, 141, 
	142, 143, 144, 145, 140, 140, 56, 141, 
	141, 146, 149, 148, 28, 29, 29, 28, 
	36, 26, 29, 26, 26, 150, 37, 151, 
	147, 152, 152, 153, 55, 154, 0
};

static const char _kotlin_trans_targs[] = {
	28, 1, 28, 2, 28, 3, 4, 5, 
	32, 28, 6, 7, 28, 28, 36, 10, 
	37, 39, 40, 13, 28, 99, 14, 99, 
	15, 14, 17, 99, 17, 18, 19, 17, 
	17, 18, 19, 20, 102, 21, 21, 22, 
	23, 24, 25, 26, 21, 21, 22, 23, 
	24, 25, 26, 25, 26, 23, 99, 99, 
	0, 28, 29, 28, 30, 33, 35, 38, 
	42, 43, 46, 45, 47, 51, 60, 61, 
	63, 66, 67, 70, 75, 80, 84, 87, 
	94, 96, 28, 28, 31, 28, 28, 34, 
	28, 28, 8, 9, 28, 11, 12, 41, 
	28, 42, 44, 45, 42, 48, 49, 50, 
	52, 54, 53, 55, 56, 57, 58, 59, 
	62, 61, 64, 65, 68, 69, 71, 72, 
	73, 74, 76, 77, 78, 79, 81, 82, 
	83, 85, 86, 88, 91, 93, 89, 90, 
	92, 95, 97, 98, 99, 100, 101, 103, 
	27, 105, 99, 99, 14, 16, 99, 104, 
	99, 104, 99
};

static const char _kotlin_trans_actions[] = {
	61, 15, 90, 15, 55, 15, 15, 15, 
	15, 59, 13, 13, 87, 57, 111, 17, 
	17, 17, 17, 19, 102, 37, 0, 25, 
	0, 75, 1, 39, 0, 1, 1, 118, 
	78, 118, 118, 1, 130, 3, 0, 0, 
	3, 0, 3, 3, 114, 72, 72, 114, 
	72, 114, 114, 66, 66, 69, 63, 81, 
	0, 105, 11, 126, 138, 151, 111, 111, 
	99, 122, 142, 122, 122, 122, 122, 122, 
	122, 122, 122, 122, 122, 122, 122, 122, 
	122, 122, 41, 53, 108, 45, 51, 13, 
	43, 47, 17, 17, 93, 17, 17, 17, 
	49, 19, 96, 96, 96, 96, 96, 96, 
	96, 96, 96, 96, 96, 96, 96, 96, 
	96, 96, 96, 96, 96, 96, 96, 96, 
	96, 96, 96, 96, 96, 96, 96, 96, 
	96, 96, 96, 96, 96, 96, 96, 96, 
	96, 96, 96, 96, 84, 7, 146, 134, 
	9, 9, 27, 35, 5, 0, 31, 3, 
	29, 0, 33
};

static const char _kotlin_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 21, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 21, 0, 0, 0, 0, 
	0, 0
};

static const char _kotlin_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 23, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 23, 0, 0, 0, 0, 
	0, 0
};

static const short _kotlin_eof_trans[] = {
	0, 1, 1, 5, 5, 5, 10, 10, 
	14, 14, 14, 14, 14, 1, 22, 22, 
	22, 28, 28, 28, 28, 22, 22, 22, 
	22, 22, 22, 0, 0, 83, 84, 86, 
	86, 87, 89, 90, 90, 90, 90, 90, 
	90, 90, 97, 97, 97, 97, 84, 97, 
	97, 97, 97, 97, 97, 97, 97, 97, 
	97, 97, 97, 97, 97, 97, 97, 97, 
	97, 97, 97, 97, 97, 97, 97, 97, 
	97, 97, 97, 97, 97, 97, 97, 97, 
	97, 97, 97, 97, 97, 97, 97, 97, 
	97, 97, 97, 97, 97, 97, 97, 97, 
	97, 97, 97, 0, 147, 148, 151, 148, 
	153, 155
};

static const int kotlin_start = 28;
static const int kotlin_first_final = 28;
static const int kotlin_error = 0;

static const int kotlin_en_kotlin_line = 99;
static const int kotlin_en_kotlin_entity = 28;


#line 141 "kotlin.rl"


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
void parse_kotlin(char *buffer, int length, int count,
             void (*callback) (const char *lang, const char *entity, int s,
                               int e, void *udata),
             void *userdata
  ) {
  init

  int kotlin_comment_nest_count = 0;

  
#line 482 "kotlin.h"
	{
	cs = kotlin_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 166 "kotlin.rl"
  cs = (count) ? kotlin_en_kotlin_line : kotlin_en_kotlin_entity;
  
#line 493 "kotlin.h"
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
	_acts = _kotlin_actions + _kotlin_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 22:
#line 1 "NONE"
	{ts = p;}
	break;
#line 515 "kotlin.h"
		}
	}

	_widec = (*p);
	_klen = _kotlin_cond_lengths[cs];
	_keys = _kotlin_cond_keys + (_kotlin_cond_offsets[cs]*2);
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
				switch ( _kotlin_cond_spaces[_kotlin_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
	case 0: {
		_widec = (short)(256 + ((*p) - 0));
		if ( 
#line 9 "common.rl"
 p+1 < pe && *(p+1) != '\n'  ) _widec += 256;
		break;
	}
	case 1: {
		_widec = (short)(768 + ((*p) - 0));
		if ( 
#line 66 "kotlin.rl"
 kotlin_comment_nest_count == 0  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _kotlin_trans_keys + _kotlin_key_offsets[cs];
	_trans = _kotlin_index_offsets[cs];

	_klen = _kotlin_single_lengths[cs];
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

	_klen = _kotlin_range_lengths[cs];
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
	_trans = _kotlin_indicies[_trans];
_eof_trans:
	cs = _kotlin_trans_targs[_trans];

	if ( _kotlin_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _kotlin_actions + _kotlin_trans_actions[_trans];
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
#line 34 "kotlin.rl"
	{
    switch(entity) {
    case KOTLIN_SPACE:
      ls
      break;
    case KOTLIN_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(KOTLIN_LANG)
      break;
    case NEWLINE:
      std_newline(KOTLIN_LANG)
    }
  }
	break;
	case 3:
#line 50 "kotlin.rl"
	{ kotlin_comment_nest_count = 0; }
	break;
	case 4:
#line 51 "kotlin.rl"
	{ kotlin_comment_nest_count++; }
	break;
	case 5:
#line 52 "kotlin.rl"
	{ kotlin_comment_nest_count--; }
	break;
	case 6:
#line 57 "kotlin.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 70 "kotlin.rl"
	{ p--; }
	break;
	case 8:
#line 70 "kotlin.rl"
	{ p--; }
	break;
	case 9:
#line 74 "kotlin.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 10:
#line 83 "kotlin.rl"
	{ entity = KOTLIN_SPACE; }
	break;
	case 11:
#line 86 "kotlin.rl"
	{ entity = NEWLINE;      }
	break;
	case 12:
#line 87 "kotlin.rl"
	{ entity = KOTLIN_ANY;   }
	break;
	case 13:
#line 132 "kotlin.rl"
	{ entity = KOTLIN_SPACE;      }
	break;
	case 14:
#line 133 "kotlin.rl"
	{ entity = KOTLIN_COMMENT;    }
	break;
	case 15:
#line 134 "kotlin.rl"
	{ entity = KOTLIN_STRING;     }
	break;
	case 16:
#line 135 "kotlin.rl"
	{ entity = KOTLIN_NUMBER;     }
	break;
	case 17:
#line 136 "kotlin.rl"
	{ entity = KOTLIN_IDENTIFIER; }
	break;
	case 18:
#line 137 "kotlin.rl"
	{ entity = KOTLIN_KEYWORD;    }
	break;
	case 19:
#line 138 "kotlin.rl"
	{ entity = KOTLIN_OPERATOR;   }
	break;
	case 20:
#line 139 "kotlin.rl"
	{ entity = KOTLIN_ANY;        }
	break;
	case 23:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 24:
#line 85 "kotlin.rl"
	{act = 3;}
	break;
	case 25:
#line 34 "kotlin.rl"
	{act = 5;}
	break;
	case 26:
#line 84 "kotlin.rl"
	{te = p+1;}
	break;
	case 27:
#line 85 "kotlin.rl"
	{te = p+1;}
	break;
	case 28:
#line 34 "kotlin.rl"
	{te = p+1;{
    switch(entity) {
    case KOTLIN_SPACE:
      ls
      break;
    case KOTLIN_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(KOTLIN_LANG)
      break;
    case NEWLINE:
      std_newline(KOTLIN_LANG)
    }
  }}
	break;
	case 29:
#line 34 "kotlin.rl"
	{te = p+1;{
    switch(entity) {
    case KOTLIN_SPACE:
      ls
      break;
    case KOTLIN_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(KOTLIN_LANG)
      break;
    case NEWLINE:
      std_newline(KOTLIN_LANG)
    }
  }}
	break;
	case 30:
#line 34 "kotlin.rl"
	{te = p;p--;{
    switch(entity) {
    case KOTLIN_SPACE:
      ls
      break;
    case KOTLIN_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(KOTLIN_LANG)
      break;
    case NEWLINE:
      std_newline(KOTLIN_LANG)
    }
  }}
	break;
	case 31:
#line 84 "kotlin.rl"
	{te = p;p--;}
	break;
	case 32:
#line 85 "kotlin.rl"
	{te = p;p--;}
	break;
	case 33:
#line 34 "kotlin.rl"
	{te = p;p--;{
    switch(entity) {
    case KOTLIN_SPACE:
      ls
      break;
    case KOTLIN_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(KOTLIN_LANG)
      break;
    case NEWLINE:
      std_newline(KOTLIN_LANG)
    }
  }}
	break;
	case 34:
#line 34 "kotlin.rl"
	{te = p;p--;{
    switch(entity) {
    case KOTLIN_SPACE:
      ls
      break;
    case KOTLIN_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(KOTLIN_LANG)
      break;
    case NEWLINE:
      std_newline(KOTLIN_LANG)
    }
  }}
	break;
	case 35:
#line 34 "kotlin.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case KOTLIN_SPACE:
      ls
      break;
    case KOTLIN_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(KOTLIN_LANG)
      break;
    case NEWLINE:
      std_newline(KOTLIN_LANG)
    }
  }}
	break;
	case 36:
#line 1 "NONE"
	{	switch( act ) {
	case 5:
	{{p = ((te))-1;}
    switch(entity) {
    case KOTLIN_SPACE:
      ls
      break;
    case KOTLIN_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(KOTLIN_LANG)
      break;
    case NEWLINE:
      std_newline(KOTLIN_LANG)
    }
  }
	break;
	default:
	{{p = ((te))-1;}}
	break;
	}
	}
	break;
	case 37:
#line 92 "kotlin.rl"
	{te = p+1;{
    callback(KOTLIN_LANG, kotlin_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 38:
#line 92 "kotlin.rl"
	{te = p+1;{
    callback(KOTLIN_LANG, kotlin_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 39:
#line 92 "kotlin.rl"
	{te = p+1;{
    callback(KOTLIN_LANG, kotlin_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 40:
#line 92 "kotlin.rl"
	{te = p+1;{
    callback(KOTLIN_LANG, kotlin_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 41:
#line 92 "kotlin.rl"
	{te = p+1;{
    callback(KOTLIN_LANG, kotlin_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 42:
#line 92 "kotlin.rl"
	{te = p+1;{
    callback(KOTLIN_LANG, kotlin_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 43:
#line 92 "kotlin.rl"
	{te = p;p--;{
    callback(KOTLIN_LANG, kotlin_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 44:
#line 92 "kotlin.rl"
	{te = p;p--;{
    callback(KOTLIN_LANG, kotlin_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 45:
#line 92 "kotlin.rl"
	{te = p;p--;{
    callback(KOTLIN_LANG, kotlin_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 46:
#line 92 "kotlin.rl"
	{te = p;p--;{
    callback(KOTLIN_LANG, kotlin_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 47:
#line 92 "kotlin.rl"
	{te = p;p--;{
    callback(KOTLIN_LANG, kotlin_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 48:
#line 92 "kotlin.rl"
	{te = p;p--;{
    callback(KOTLIN_LANG, kotlin_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 49:
#line 92 "kotlin.rl"
	{te = p;p--;{
    callback(KOTLIN_LANG, kotlin_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 50:
#line 92 "kotlin.rl"
	{{p = ((te))-1;}{
    callback(KOTLIN_LANG, kotlin_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 51:
#line 92 "kotlin.rl"
	{{p = ((te))-1;}{
    callback(KOTLIN_LANG, kotlin_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 52:
#line 92 "kotlin.rl"
	{{p = ((te))-1;}{
    callback(KOTLIN_LANG, kotlin_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 53:
#line 92 "kotlin.rl"
	{{p = ((te))-1;}{
    callback(KOTLIN_LANG, kotlin_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
#line 989 "kotlin.h"
		}
	}

_again:
	_acts = _kotlin_actions + _kotlin_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 21:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 1002 "kotlin.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _kotlin_eof_trans[cs] > 0 ) {
		_trans = _kotlin_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 168 "kotlin.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(KOTLIN_LANG) }
}

const char *ORIG_KOTLIN_LANG = LANG_KOTLIN;

#endif

/*****************************************************************************/
