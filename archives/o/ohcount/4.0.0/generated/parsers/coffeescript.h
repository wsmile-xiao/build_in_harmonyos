
#line 1 "coffeescript.rl.tmp"
/************************* Required for every parser *************************/
#ifndef OHCOUNT_COFFEESCRIPT_PARSER_H
#define OHCOUNT_COFFEESCRIPT_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *COFFEESCRIPT_LANG = LANG_COFFEESCRIPT;

// the languages entities
const char *coffeescript_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  COFFEESCRIPT_SPACE = 0, COFFEESCRIPT_COMMENT, COFFEESCRIPT_STRING, COFFEESCRIPT_ANY
};

/*****************************************************************************/

#include "javascript.h"


#line 28 "coffeescript.h"
static const char _coffeescript_actions[] = {
	0, 1, 2, 1, 3, 1, 9, 1, 
	10, 1, 12, 1, 13, 1, 21, 1, 
	22, 1, 25, 1, 26, 1, 28, 1, 
	29, 1, 30, 1, 31, 1, 32, 1, 
	33, 1, 34, 1, 37, 1, 38, 1, 
	39, 1, 40, 1, 41, 1, 43, 1, 
	44, 1, 45, 1, 46, 1, 47, 1, 
	49, 1, 50, 1, 53, 1, 54, 1, 
	55, 1, 56, 1, 57, 1, 59, 1, 
	63, 1, 64, 1, 65, 1, 66, 1, 
	67, 1, 68, 1, 69, 1, 70, 1, 
	72, 1, 73, 1, 74, 1, 75, 2, 
	2, 34, 2, 2, 50, 2, 2, 60, 
	2, 3, 27, 2, 6, 5, 2, 7, 
	5, 2, 8, 5, 2, 10, 35, 2, 
	11, 36, 2, 13, 42, 2, 15, 14, 
	2, 16, 14, 2, 17, 14, 2, 18, 
	14, 2, 19, 14, 2, 22, 51, 2, 
	23, 52, 2, 26, 61, 2, 27, 62, 
	2, 29, 71, 2, 32, 3, 2, 32, 
	11, 2, 32, 13, 2, 32, 23, 2, 
	32, 29, 3, 1, 2, 60, 3, 6, 
	5, 3, 3, 7, 5, 2, 3, 7, 
	5, 34, 3, 7, 5, 50, 3, 8, 
	5, 2, 3, 8, 5, 34, 3, 8, 
	5, 50, 3, 15, 14, 3, 3, 16, 
	14, 2, 3, 17, 14, 2, 3, 18, 
	14, 2, 3, 19, 14, 2, 3, 32, 
	1, 2, 3, 32, 2, 11, 3, 32, 
	2, 23, 4, 32, 0, 2, 27, 5, 
	2, 14, 24, 58, 27, 5, 4, 2, 
	20, 48, 23, 5, 16, 14, 1, 2, 
	60, 5, 17, 14, 1, 2, 60
};

static const char _coffeescript_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 1, 1, 
	1, 1, 1, 2, 2, 2, 2, 2, 
	2, 3, 4, 5, 5, 5, 5, 5, 
	5, 6, 6, 6, 6, 6, 7, 7, 
	7, 7, 7, 7, 8, 9, 10, 10, 
	10, 11, 12, 12, 12, 13, 14, 15, 
	16, 16, 17, 18, 19, 20, 20, 21, 
	22, 22, 22, 23, 24, 25, 26, 26, 
	26, 26, 26, 26, 26, 26, 26, 26, 
	26, 26, 27, 27, 27, 27, 27, 27, 
	27, 27, 27, 27, 27, 28, 28, 28, 
	28, 28, 28, 28, 29, 29, 30, 30, 
	30, 30, 30, 30, 31, 32, 33, 34, 
	34, 34
};

static const char _coffeescript_cond_lengths[] = {
	0, 0, 0, 0, 0, 1, 0, 0, 
	0, 0, 1, 0, 0, 0, 0, 0, 
	1, 1, 1, 0, 0, 0, 0, 0, 
	1, 0, 0, 0, 0, 1, 0, 0, 
	0, 0, 0, 1, 1, 1, 0, 0, 
	1, 1, 0, 0, 1, 1, 1, 1, 
	0, 1, 1, 1, 1, 0, 1, 1, 
	0, 0, 1, 1, 1, 1, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 1, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 1, 0, 0, 0, 
	0, 0, 0, 1, 0, 1, 0, 0, 
	0, 0, 0, 1, 1, 1, 1, 0, 
	0, 0
};

static const short _coffeescript_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 0
};

static const char _coffeescript_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0
};

static const short _coffeescript_key_offsets[] = {
	0, 0, 1, 2, 3, 7, 15, 19, 
	20, 25, 29, 37, 41, 42, 47, 52, 
	55, 66, 77, 89, 90, 91, 92, 94, 
	98, 106, 110, 111, 116, 120, 128, 132, 
	133, 138, 143, 146, 157, 168, 180, 181, 
	182, 194, 206, 209, 210, 221, 232, 243, 
	254, 255, 266, 277, 288, 299, 300, 312, 
	324, 327, 328, 339, 350, 361, 372, 373, 
	374, 378, 381, 385, 388, 392, 396, 397, 
	401, 405, 418, 420, 424, 428, 430, 433, 
	434, 438, 441, 443, 446, 460, 462, 466, 
	470, 472, 475, 476, 490, 492, 504, 505, 
	506, 510, 513, 517, 528, 539, 550, 562, 
	563, 564
};

static const short _coffeescript_trans_keys[] = {
	35, 35, 35, 9, 32, 34, 92, 10, 
	12, 269, 525, 0, 11, 14, 255, 9, 
	32, 34, 92, 10, 9, 10, 32, 34, 
	92, 9, 32, 39, 92, 10, 12, 269, 
	525, 0, 11, 14, 255, 9, 32, 39, 
	92, 10, 9, 10, 32, 39, 92, 10, 
	47, 92, 12, 13, 10, 12, 13, 9, 
	10, 12, 32, 42, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 42, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 42, 47, 269, 525, 0, 11, 14, 
	255, 10, 10, 42, 42, 47, 9, 32, 
	34, 92, 10, 12, 269, 525, 0, 11, 
	14, 255, 9, 32, 34, 92, 10, 9, 
	10, 32, 34, 92, 9, 32, 39, 92, 
	10, 12, 269, 525, 0, 11, 14, 255, 
	9, 32, 39, 92, 10, 9, 10, 32, 
	39, 92, 10, 47, 92, 12, 13, 10, 
	12, 13, 9, 10, 12, 32, 42, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 42, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 42, 47, 269, 525, 
	0, 11, 14, 255, 10, 10, 9, 10, 
	12, 32, 34, 92, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 34, 92, 
	269, 525, 0, 11, 14, 255, 10, 12, 
	13, 10, 9, 10, 12, 32, 34, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 34, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 34, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 34, 
	269, 525, 0, 11, 14, 255, 10, 9, 
	10, 12, 32, 35, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 35, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 35, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 35, 269, 525, 0, 
	11, 14, 255, 10, 9, 10, 12, 32, 
	39, 92, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 39, 92, 269, 525, 
	0, 11, 14, 255, 10, 12, 13, 10, 
	9, 10, 12, 32, 39, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 39, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 39, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 39, 269, 525, 
	0, 11, 14, 255, 10, 10, 32, 35, 
	9, 13, 32, 9, 13, 10, 35, 12, 
	13, 10, 12, 13, 10, 35, 12, 13, 
	10, 35, 12, 13, 35, 10, 35, 12, 
	13, 10, 35, 12, 13, 9, 10, 12, 
	32, 34, 39, 47, 269, 525, 0, 8, 
	14, 255, 9, 32, 9, 32, 34, 92, 
	9, 32, 39, 92, 42, 47, 10, 12, 
	13, 10, 32, 47, 9, 13, 32, 9, 
	13, 42, 47, 10, 12, 13, 9, 10, 
	12, 32, 34, 39, 47, 96, 269, 525, 
	0, 8, 14, 255, 9, 32, 9, 32, 
	34, 92, 9, 32, 39, 92, 42, 47, 
	10, 12, 13, 10, 9, 10, 12, 32, 
	34, 35, 39, 96, 269, 525, 0, 8, 
	14, 255, 9, 32, 9, 10, 12, 32, 
	34, 92, 269, 525, 0, 11, 14, 255, 
	34, 34, 10, 35, 12, 13, 10, 12, 
	13, 10, 35, 12, 13, 9, 10, 12, 
	32, 35, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 35, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 35, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 39, 92, 269, 525, 0, 11, 
	14, 255, 39, 39, 10, 0
};

static const char _coffeescript_single_lengths[] = {
	0, 1, 1, 1, 4, 4, 4, 1, 
	5, 4, 4, 4, 1, 5, 3, 1, 
	7, 7, 8, 1, 1, 1, 2, 4, 
	4, 4, 1, 5, 4, 4, 4, 1, 
	5, 3, 1, 7, 7, 8, 1, 1, 
	8, 8, 1, 1, 7, 7, 7, 7, 
	1, 7, 7, 7, 7, 1, 8, 8, 
	1, 1, 7, 7, 7, 7, 1, 1, 
	2, 1, 2, 1, 2, 2, 1, 2, 
	2, 9, 2, 4, 4, 2, 1, 1, 
	2, 1, 2, 1, 10, 2, 4, 4, 
	2, 1, 1, 10, 2, 8, 1, 1, 
	2, 1, 2, 7, 7, 7, 8, 1, 
	1, 1
};

static const char _coffeescript_range_lengths[] = {
	0, 0, 0, 0, 0, 2, 0, 0, 
	0, 0, 2, 0, 0, 0, 1, 1, 
	2, 2, 2, 0, 0, 0, 0, 0, 
	2, 0, 0, 0, 0, 2, 0, 0, 
	0, 1, 1, 2, 2, 2, 0, 0, 
	2, 2, 1, 0, 2, 2, 2, 2, 
	0, 2, 2, 2, 2, 0, 2, 2, 
	1, 0, 2, 2, 2, 2, 0, 0, 
	1, 1, 1, 1, 1, 1, 0, 1, 
	1, 2, 0, 0, 0, 0, 1, 0, 
	1, 1, 0, 1, 2, 0, 0, 0, 
	0, 1, 0, 2, 0, 2, 0, 0, 
	1, 1, 1, 2, 2, 2, 2, 0, 
	0, 0
};

static const short _coffeescript_index_offsets[] = {
	0, 0, 2, 4, 6, 11, 18, 23, 
	25, 31, 36, 43, 48, 50, 56, 61, 
	64, 74, 84, 95, 97, 99, 101, 104, 
	109, 116, 121, 123, 129, 134, 141, 146, 
	148, 154, 159, 162, 172, 182, 193, 195, 
	197, 208, 219, 222, 224, 234, 244, 254, 
	264, 266, 276, 286, 296, 306, 308, 319, 
	330, 333, 335, 345, 355, 365, 375, 377, 
	379, 383, 386, 390, 393, 397, 401, 403, 
	407, 411, 423, 426, 431, 436, 439, 442, 
	444, 448, 451, 454, 457, 470, 473, 478, 
	483, 486, 489, 491, 504, 507, 518, 520, 
	522, 526, 529, 533, 543, 553, 563, 574, 
	576, 578
};

static const char _coffeescript_indicies[] = {
	2, 1, 3, 1, 4, 1, 7, 7, 
	8, 9, 6, 10, 10, 11, 12, 6, 
	6, 5, 14, 14, 15, 16, 13, 10, 
	5, 14, 17, 14, 15, 16, 13, 19, 
	19, 8, 20, 18, 21, 21, 22, 23, 
	18, 18, 5, 25, 25, 26, 27, 24, 
	21, 5, 25, 28, 25, 26, 27, 24, 
	5, 30, 31, 5, 29, 5, 5, 29, 
	33, 34, 34, 33, 35, 36, 34, 32, 
	32, 5, 38, 39, 39, 38, 40, 41, 
	39, 37, 37, 5, 33, 34, 34, 33, 
	35, 42, 36, 34, 32, 32, 5, 34, 
	5, 43, 44, 47, 46, 47, 48, 46, 
	51, 51, 52, 53, 50, 54, 54, 55, 
	56, 50, 50, 49, 58, 58, 59, 60, 
	57, 54, 49, 58, 61, 58, 59, 60, 
	57, 63, 63, 52, 64, 62, 65, 65, 
	66, 67, 62, 62, 49, 69, 69, 70, 
	71, 68, 65, 49, 69, 72, 69, 70, 
	71, 68, 49, 74, 75, 49, 73, 49, 
	49, 73, 77, 78, 78, 77, 79, 80, 
	78, 76, 76, 49, 82, 83, 83, 82, 
	84, 85, 83, 81, 81, 49, 77, 78, 
	78, 77, 79, 86, 80, 78, 76, 76, 
	49, 78, 49, 87, 44, 90, 91, 91, 
	90, 92, 93, 94, 91, 89, 89, 88, 
	96, 97, 97, 96, 98, 99, 100, 97, 
	95, 95, 88, 88, 88, 89, 91, 88, 
	103, 104, 104, 103, 105, 106, 104, 102, 
	102, 101, 108, 109, 109, 108, 110, 111, 
	109, 107, 107, 101, 103, 104, 104, 103, 
	112, 106, 104, 102, 102, 101, 103, 104, 
	104, 103, 113, 106, 104, 102, 102, 101, 
	104, 101, 116, 117, 117, 116, 118, 119, 
	117, 115, 115, 114, 121, 122, 122, 121, 
	123, 124, 122, 120, 120, 114, 121, 122, 
	122, 121, 125, 124, 122, 120, 120, 114, 
	121, 122, 122, 121, 126, 124, 122, 120, 
	120, 114, 122, 114, 128, 129, 129, 128, 
	92, 130, 131, 129, 127, 127, 88, 133, 
	134, 134, 133, 135, 136, 137, 134, 132, 
	132, 88, 88, 88, 127, 129, 88, 139, 
	140, 140, 139, 141, 142, 140, 138, 138, 
	101, 144, 145, 145, 144, 146, 147, 145, 
	143, 143, 101, 139, 140, 140, 139, 148, 
	142, 140, 138, 138, 101, 139, 140, 140, 
	139, 149, 142, 140, 138, 138, 101, 140, 
	101, 150, 44, 152, 153, 152, 151, 152, 
	152, 154, 155, 157, 155, 156, 155, 155, 
	156, 155, 158, 155, 156, 1, 159, 1, 
	158, 160, 155, 1, 161, 1, 158, 1, 
	156, 1, 158, 163, 43, 43, 163, 164, 
	165, 166, 167, 168, 162, 162, 44, 163, 
	163, 169, 7, 7, 8, 9, 6, 19, 
	19, 8, 20, 18, 32, 171, 29, 172, 
	172, 173, 43, 174, 176, 177, 176, 175, 
	176, 176, 178, 46, 180, 179, 181, 181, 
	180, 183, 87, 87, 183, 184, 185, 186, 
	187, 188, 189, 182, 182, 44, 183, 183, 
	190, 51, 51, 52, 53, 50, 63, 63, 
	52, 64, 62, 76, 192, 73, 193, 193, 
	194, 87, 195, 197, 150, 150, 197, 198, 
	199, 200, 201, 202, 203, 196, 196, 44, 
	197, 197, 204, 90, 91, 91, 90, 206, 
	93, 94, 91, 89, 89, 205, 102, 207, 
	208, 207, 209, 211, 209, 210, 209, 209, 
	210, 209, 212, 209, 210, 213, 122, 122, 
	213, 214, 124, 122, 212, 212, 209, 213, 
	122, 122, 213, 215, 124, 122, 212, 212, 
	209, 213, 122, 122, 213, 210, 124, 122, 
	212, 212, 209, 128, 129, 129, 128, 216, 
	130, 131, 129, 127, 127, 205, 138, 207, 
	208, 207, 150, 217, 0
};

static const char _coffeescript_trans_targs[] = {
	64, 1, 2, 3, 70, 73, 4, 4, 
	73, 5, 6, 7, 8, 4, 4, 73, 
	5, 6, 9, 9, 10, 11, 12, 13, 
	9, 9, 73, 10, 11, 14, 73, 15, 
	16, 16, 17, 18, 19, 16, 16, 17, 
	18, 19, 73, 73, 0, 80, 21, 22, 
	80, 84, 23, 23, 84, 24, 25, 26, 
	27, 23, 23, 84, 24, 25, 28, 28, 
	29, 30, 31, 32, 28, 28, 84, 29, 
	30, 33, 84, 34, 35, 35, 36, 37, 
	38, 35, 35, 36, 37, 38, 84, 84, 
	91, 40, 40, 41, 91, 42, 43, 40, 
	40, 41, 91, 42, 43, 91, 44, 44, 
	45, 46, 48, 44, 44, 45, 46, 48, 
	47, 95, 91, 50, 50, 49, 51, 53, 
	50, 50, 49, 51, 53, 52, 91, 54, 
	54, 55, 56, 57, 54, 54, 55, 91, 
	56, 57, 58, 58, 59, 60, 62, 58, 
	58, 59, 60, 62, 61, 104, 91, 64, 
	65, 66, 64, 64, 67, 68, 69, 71, 
	64, 72, 73, 74, 75, 76, 77, 20, 
	79, 73, 73, 78, 73, 78, 73, 80, 
	81, 82, 80, 80, 83, 80, 84, 85, 
	86, 87, 88, 84, 39, 90, 84, 84, 
	89, 84, 89, 84, 91, 92, 93, 96, 
	102, 91, 63, 105, 91, 91, 94, 91, 
	91, 91, 97, 98, 99, 99, 100, 101, 
	103, 91
};

static const short _coffeescript_trans_actions[] = {
	93, 23, 23, 23, 23, 43, 1, 0, 
	33, 0, 0, 0, 0, 190, 113, 194, 
	113, 190, 1, 0, 0, 0, 0, 0, 
	178, 110, 182, 110, 178, 0, 95, 0, 
	3, 0, 0, 3, 0, 174, 107, 107, 
	174, 107, 31, 116, 0, 53, 11, 11, 
	122, 67, 1, 0, 57, 0, 0, 0, 
	0, 190, 113, 198, 113, 190, 1, 0, 
	0, 0, 0, 0, 178, 110, 186, 110, 
	178, 0, 98, 0, 3, 0, 0, 3, 
	0, 174, 107, 107, 174, 107, 55, 140, 
	85, 1, 0, 0, 170, 0, 0, 210, 
	131, 131, 257, 131, 131, 83, 1, 0, 
	0, 1, 0, 218, 137, 137, 218, 137, 
	1, 1, 81, 202, 125, 125, 202, 125, 
	3, 0, 0, 3, 0, 3, 69, 1, 
	0, 0, 0, 0, 206, 128, 128, 251, 
	128, 128, 1, 0, 0, 1, 0, 214, 
	134, 134, 214, 134, 1, 1, 146, 87, 
	21, 23, 89, 91, 23, 23, 167, 167, 
	152, 167, 119, 5, 226, 226, 158, 7, 
	7, 35, 41, 3, 37, 0, 39, 45, 
	9, 161, 47, 51, 11, 49, 143, 13, 
	230, 230, 164, 245, 15, 15, 59, 65, 
	3, 61, 0, 63, 149, 17, 234, 104, 
	234, 239, 19, 19, 71, 79, 222, 75, 
	101, 73, 0, 0, 155, 29, 155, 155, 
	222, 77
};

static const short _coffeescript_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	25, 0, 0, 0, 0, 0, 0, 0, 
	0, 25, 0, 0, 0, 0, 0, 0, 
	25, 0, 0, 0, 25, 0, 0, 0, 
	0, 0, 0, 25, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0
};

static const short _coffeescript_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	27, 0, 0, 0, 0, 0, 0, 0, 
	0, 27, 0, 0, 0, 0, 0, 0, 
	27, 0, 0, 0, 27, 0, 0, 0, 
	0, 0, 0, 27, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0
};

static const short _coffeescript_eof_trans[] = {
	0, 1, 1, 1, 6, 6, 6, 6, 
	6, 6, 6, 6, 6, 6, 6, 6, 
	6, 6, 6, 6, 0, 46, 46, 50, 
	50, 50, 50, 50, 50, 50, 50, 50, 
	50, 50, 50, 50, 50, 50, 50, 0, 
	89, 89, 89, 89, 102, 102, 102, 102, 
	102, 115, 115, 115, 115, 115, 89, 89, 
	89, 89, 102, 102, 102, 102, 102, 0, 
	0, 155, 156, 156, 156, 156, 156, 156, 
	156, 0, 170, 171, 171, 171, 173, 175, 
	0, 179, 180, 182, 0, 191, 192, 192, 
	192, 194, 196, 0, 205, 206, 208, 208, 
	210, 210, 210, 210, 210, 210, 206, 208, 
	208, 218
};

static const int coffeescript_start = 64;
static const int coffeescript_first_final = 64;
static const int coffeescript_error = 0;

static const int coffeescript_en_js_line = 73;
static const int coffeescript_en_js_entity = 80;
static const int coffeescript_en_coffeescript_js_line = 84;
static const int coffeescript_en_coffeescript_line = 91;
static const int coffeescript_en_coffeescript_entity = 64;


#line 29 "coffeescript.rl.tmp"


#line 224 "coffeescript.rl.tmp"


/************************* Required for every parser *************************/

/* Parses a string buffer with CoffeeScript code.
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
void parse_coffeescript(char *buffer, int length, int count,
                  void (*callback) (const char *lang, const char *entity, int s,
                                    int e, void *udata),
                  void *userdata
  ) {
  init

  
#line 488 "coffeescript.h"
	{
	cs = coffeescript_start;
	top = 0;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 247 "coffeescript.rl.tmp"
  cs = (count) ? coffeescript_en_coffeescript_line : coffeescript_en_coffeescript_entity;
  
#line 500 "coffeescript.h"
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
	_acts = _coffeescript_actions + _coffeescript_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 31:
#line 1 "NONE"
	{ts = p;}
	break;
#line 522 "coffeescript.h"
		}
	}

	_widec = (*p);
	_klen = _coffeescript_cond_lengths[cs];
	_keys = _coffeescript_cond_keys + (_coffeescript_cond_offsets[cs]*2);
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
				switch ( _coffeescript_cond_spaces[_coffeescript_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _coffeescript_trans_keys + _coffeescript_key_offsets[cs];
	_trans = _coffeescript_index_offsets[cs];

	_klen = _coffeescript_single_lengths[cs];
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

	_klen = _coffeescript_range_lengths[cs];
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
	_trans = _coffeescript_indicies[_trans];
_eof_trans:
	cs = _coffeescript_trans_targs[_trans];

	if ( _coffeescript_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _coffeescript_actions + _coffeescript_trans_actions[_trans];
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
#line 38 "coffeescript.rl.tmp"
	{
    switch(entity) {
    case JS_SPACE:
      ls
      break;
    case JS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JS_LANG)
      break;
    case NEWLINE:
      std_newline(JS_LANG)
    }
  }
	break;
	case 6:
#line 57 "coffeescript.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 69 "coffeescript.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 8:
#line 79 "coffeescript.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 9:
#line 91 "coffeescript.rl.tmp"
	{ entity = JS_SPACE; }
	break;
	case 10:
#line 94 "coffeescript.rl.tmp"
	{ entity = NEWLINE;  }
	break;
	case 11:
#line 95 "coffeescript.rl.tmp"
	{ entity = JS_ANY;   }
	break;
	case 12:
#line 109 "coffeescript.rl.tmp"
	{ entity = JS_SPACE;   }
	break;
	case 13:
#line 110 "coffeescript.rl.tmp"
	{ entity = JS_COMMENT; }
	break;
	case 14:
#line 118 "coffeescript.rl.tmp"
	{
    switch(entity) {
    case COFFEESCRIPT_SPACE:
      ls
      break;
    case COFFEESCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(COFFEESCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(COFFEESCRIPT_LANG)
    }
  }
	break;
	case 15:
#line 137 "coffeescript.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 16:
#line 147 "coffeescript.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 17:
#line 157 "coffeescript.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 18:
#line 167 "coffeescript.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 19:
#line 175 "coffeescript.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 20:
#line 187 "coffeescript.rl.tmp"
	{ p = ts; {cs = stack[--top]; goto _again;} }
	break;
	case 21:
#line 189 "coffeescript.rl.tmp"
	{ entity = JS_SPACE; }
	break;
	case 22:
#line 192 "coffeescript.rl.tmp"
	{ entity = NEWLINE;    }
	break;
	case 23:
#line 193 "coffeescript.rl.tmp"
	{ entity = JS_ANY;   }
	break;
	case 24:
#line 198 "coffeescript.rl.tmp"
	{ saw(JS_LANG); }
	break;
	case 25:
#line 199 "coffeescript.rl.tmp"
	{ entity = COFFEESCRIPT_SPACE; }
	break;
	case 26:
#line 202 "coffeescript.rl.tmp"
	{ entity = NEWLINE;      }
	break;
	case 27:
#line 203 "coffeescript.rl.tmp"
	{ entity = COFFEESCRIPT_ANY;   }
	break;
	case 28:
#line 219 "coffeescript.rl.tmp"
	{ entity = COFFEESCRIPT_SPACE;   }
	break;
	case 29:
#line 220 "coffeescript.rl.tmp"
	{ entity = COFFEESCRIPT_COMMENT; }
	break;
	case 32:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 33:
#line 92 "coffeescript.rl.tmp"
	{te = p+1;}
	break;
	case 34:
#line 93 "coffeescript.rl.tmp"
	{te = p+1;}
	break;
	case 35:
#line 38 "coffeescript.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case JS_SPACE:
      ls
      break;
    case JS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JS_LANG)
      break;
    case NEWLINE:
      std_newline(JS_LANG)
    }
  }}
	break;
	case 36:
#line 38 "coffeescript.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case JS_SPACE:
      ls
      break;
    case JS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JS_LANG)
      break;
    case NEWLINE:
      std_newline(JS_LANG)
    }
  }}
	break;
	case 37:
#line 38 "coffeescript.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case JS_SPACE:
      ls
      break;
    case JS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JS_LANG)
      break;
    case NEWLINE:
      std_newline(JS_LANG)
    }
  }}
	break;
	case 38:
#line 92 "coffeescript.rl.tmp"
	{te = p;p--;}
	break;
	case 39:
#line 38 "coffeescript.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case JS_SPACE:
      ls
      break;
    case JS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JS_LANG)
      break;
    case NEWLINE:
      std_newline(JS_LANG)
    }
  }}
	break;
	case 40:
#line 38 "coffeescript.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case JS_SPACE:
      ls
      break;
    case JS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JS_LANG)
      break;
    case NEWLINE:
      std_newline(JS_LANG)
    }
  }}
	break;
	case 41:
#line 38 "coffeescript.rl.tmp"
	{{p = ((te))-1;}{
    switch(entity) {
    case JS_SPACE:
      ls
      break;
    case JS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JS_LANG)
      break;
    case NEWLINE:
      std_newline(JS_LANG)
    }
  }}
	break;
	case 42:
#line 100 "coffeescript.rl.tmp"
	{te = p+1;{
    callback(JS_LANG, js_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 43:
#line 112 "coffeescript.rl.tmp"
	{te = p+1;}
	break;
	case 44:
#line 100 "coffeescript.rl.tmp"
	{te = p;p--;{
    callback(JS_LANG, js_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 45:
#line 100 "coffeescript.rl.tmp"
	{te = p;p--;{
    callback(JS_LANG, js_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 46:
#line 112 "coffeescript.rl.tmp"
	{te = p;p--;}
	break;
	case 47:
#line 112 "coffeescript.rl.tmp"
	{{p = ((te))-1;}}
	break;
	case 48:
#line 187 "coffeescript.rl.tmp"
	{te = p+1;}
	break;
	case 49:
#line 190 "coffeescript.rl.tmp"
	{te = p+1;}
	break;
	case 50:
#line 191 "coffeescript.rl.tmp"
	{te = p+1;}
	break;
	case 51:
#line 38 "coffeescript.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case JS_SPACE:
      ls
      break;
    case JS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JS_LANG)
      break;
    case NEWLINE:
      std_newline(JS_LANG)
    }
  }}
	break;
	case 52:
#line 38 "coffeescript.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case JS_SPACE:
      ls
      break;
    case JS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JS_LANG)
      break;
    case NEWLINE:
      std_newline(JS_LANG)
    }
  }}
	break;
	case 53:
#line 38 "coffeescript.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case JS_SPACE:
      ls
      break;
    case JS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JS_LANG)
      break;
    case NEWLINE:
      std_newline(JS_LANG)
    }
  }}
	break;
	case 54:
#line 190 "coffeescript.rl.tmp"
	{te = p;p--;}
	break;
	case 55:
#line 38 "coffeescript.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case JS_SPACE:
      ls
      break;
    case JS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JS_LANG)
      break;
    case NEWLINE:
      std_newline(JS_LANG)
    }
  }}
	break;
	case 56:
#line 38 "coffeescript.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case JS_SPACE:
      ls
      break;
    case JS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JS_LANG)
      break;
    case NEWLINE:
      std_newline(JS_LANG)
    }
  }}
	break;
	case 57:
#line 38 "coffeescript.rl.tmp"
	{{p = ((te))-1;}{
    switch(entity) {
    case JS_SPACE:
      ls
      break;
    case JS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(JS_LANG)
      break;
    case NEWLINE:
      std_newline(JS_LANG)
    }
  }}
	break;
	case 58:
#line 198 "coffeescript.rl.tmp"
	{te = p+1;{ {stack[top++] = cs; cs = 84;goto _again;} }}
	break;
	case 59:
#line 200 "coffeescript.rl.tmp"
	{te = p+1;}
	break;
	case 60:
#line 201 "coffeescript.rl.tmp"
	{te = p+1;}
	break;
	case 61:
#line 118 "coffeescript.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case COFFEESCRIPT_SPACE:
      ls
      break;
    case COFFEESCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(COFFEESCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(COFFEESCRIPT_LANG)
    }
  }}
	break;
	case 62:
#line 118 "coffeescript.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case COFFEESCRIPT_SPACE:
      ls
      break;
    case COFFEESCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(COFFEESCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(COFFEESCRIPT_LANG)
    }
  }}
	break;
	case 63:
#line 118 "coffeescript.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case COFFEESCRIPT_SPACE:
      ls
      break;
    case COFFEESCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(COFFEESCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(COFFEESCRIPT_LANG)
    }
  }}
	break;
	case 64:
#line 200 "coffeescript.rl.tmp"
	{te = p;p--;}
	break;
	case 65:
#line 201 "coffeescript.rl.tmp"
	{te = p;p--;}
	break;
	case 66:
#line 118 "coffeescript.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case COFFEESCRIPT_SPACE:
      ls
      break;
    case COFFEESCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(COFFEESCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(COFFEESCRIPT_LANG)
    }
  }}
	break;
	case 67:
#line 118 "coffeescript.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case COFFEESCRIPT_SPACE:
      ls
      break;
    case COFFEESCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(COFFEESCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(COFFEESCRIPT_LANG)
    }
  }}
	break;
	case 68:
#line 200 "coffeescript.rl.tmp"
	{{p = ((te))-1;}}
	break;
	case 69:
#line 201 "coffeescript.rl.tmp"
	{{p = ((te))-1;}}
	break;
	case 70:
#line 118 "coffeescript.rl.tmp"
	{{p = ((te))-1;}{
    switch(entity) {
    case COFFEESCRIPT_SPACE:
      ls
      break;
    case COFFEESCRIPT_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(COFFEESCRIPT_LANG)
      break;
    case NEWLINE:
      std_newline(COFFEESCRIPT_LANG)
    }
  }}
	break;
	case 71:
#line 208 "coffeescript.rl.tmp"
	{te = p+1;{
    callback(COFFEESCRIPT_LANG, coffeescript_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 72:
#line 222 "coffeescript.rl.tmp"
	{te = p+1;}
	break;
	case 73:
#line 208 "coffeescript.rl.tmp"
	{te = p;p--;{
    callback(COFFEESCRIPT_LANG, coffeescript_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 74:
#line 208 "coffeescript.rl.tmp"
	{te = p;p--;{
    callback(COFFEESCRIPT_LANG, coffeescript_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 75:
#line 208 "coffeescript.rl.tmp"
	{{p = ((te))-1;}{
    callback(COFFEESCRIPT_LANG, coffeescript_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
#line 1240 "coffeescript.h"
		}
	}

_again:
	_acts = _coffeescript_actions + _coffeescript_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 30:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 1253 "coffeescript.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _coffeescript_eof_trans[cs] > 0 ) {
		_trans = _coffeescript_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 249 "coffeescript.rl.tmp"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(COFFEESCRIPT_LANG) }
}

#endif

/*****************************************************************************/
