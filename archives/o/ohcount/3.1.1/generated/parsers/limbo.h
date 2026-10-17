
#line 1 "limbo.rl"
// limbo.rl
// http://www.vitanuova.com/inferno/papers/limbo.html

/************************* Required for every parser *************************/
#ifndef RAGEL_LIMBO_PARSER
#define RAGEL_LIMBO_PARSER

#include "../parser_macros.h"

// the name of the language
const char *LIMBO_LANG = "limbo";

// the languages entities
const char *limbo_entities[] = {
  "space", "comment", "string", "number",
  "keyword", "identifier", "operator", "any"
};

// constants associated with the entities
enum {
  LIMBO_SPACE = 0, LIMBO_COMMENT, LIMBO_STRING, LIMBO_NUMBER,
  LIMBO_KEYWORD, LIMBO_IDENTIFIER, LIMBO_OPERATOR, LIMBO_ANY
};

/*****************************************************************************/


#line 31 "limbo.h"
static const char _limbo_actions[] = {
	0, 1, 2, 1, 4, 1, 5, 1, 
	7, 1, 8, 1, 9, 1, 10, 1, 
	15, 1, 16, 1, 21, 1, 22, 1, 
	23, 1, 24, 1, 25, 1, 35, 1, 
	36, 1, 37, 1, 38, 1, 39, 1, 
	40, 1, 41, 1, 42, 1, 43, 1, 
	44, 2, 1, 18, 2, 3, 6, 2, 
	5, 19, 2, 6, 20, 2, 8, 14, 
	2, 9, 31, 2, 11, 12, 2, 11, 
	32, 2, 14, 34, 3, 11, 12, 14, 
	3, 11, 13, 14, 3, 13, 33, 14, 
	3, 17, 2, 6, 3, 17, 9, 14, 
	3, 17, 10, 26, 3, 17, 12, 28, 
	4, 17, 0, 2, 6, 4, 17, 10, 
	14, 30, 4, 17, 11, 27, 12, 4, 
	17, 12, 28, 14, 5, 17, 10, 13, 
	29, 14
};

static const char _limbo_cond_offsets[] = {
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
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 1, 1, 
	1, 1, 1
};

static const char _limbo_cond_lengths[] = {
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
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 1, 0, 0, 
	0, 0, 0
};

static const short _limbo_cond_keys[] = {
	13, 13, 0
};

static const char _limbo_cond_spaces[] = {
	0, 0
};

static const short _limbo_key_offsets[] = {
	0, 0, 6, 8, 8, 10, 10, 14, 
	16, 20, 24, 26, 33, 36, 43, 46, 
	47, 93, 97, 99, 105, 108, 110, 113, 
	115, 119, 121, 126, 128, 129, 136, 146, 
	154, 162, 170, 178, 188, 196, 204, 212, 
	220, 228, 236, 247, 255, 263, 271, 279, 
	287, 295, 303, 311, 319, 327, 335, 343, 
	351, 360, 368, 377, 385, 393, 403, 411, 
	420, 428, 436, 444, 452, 460, 470, 478, 
	486, 494, 502, 510, 518, 526, 534, 543, 
	551, 559, 568, 576, 584, 592, 600, 608, 
	616, 624, 632, 640, 648, 658, 666, 674, 
	684, 692, 700, 708, 716, 724, 732, 740, 
	751, 759, 767, 775, 783, 791, 804, 806, 
	813, 816, 823
};

static const short _limbo_trans_keys[] = {
	48, 57, 65, 70, 97, 102, 34, 92, 
	39, 92, 88, 120, 48, 55, 48, 57, 
	69, 101, 48, 57, 43, 45, 48, 57, 
	48, 57, 32, 34, 92, 9, 10, 12, 
	13, 10, 12, 13, 32, 39, 92, 9, 
	10, 12, 13, 10, 12, 13, 10, 0, 
	32, 33, 34, 35, 39, 43, 45, 46, 
	61, 62, 91, 95, 97, 98, 99, 100, 
	101, 102, 104, 105, 108, 109, 110, 111, 
	112, 114, 115, 116, 119, 9, 13, 37, 
	47, 48, 57, 58, 59, 65, 90, 93, 
	94, 103, 122, 123, 126, 88, 120, 48, 
	55, 48, 55, 48, 57, 65, 70, 97, 
	102, 32, 9, 13, 34, 92, 10, 12, 
	13, 39, 92, 0, 46, 48, 57, 48, 
	57, 46, 69, 101, 48, 57, 48, 57, 
	62, 95, 48, 57, 65, 90, 97, 122, 
	95, 100, 108, 114, 48, 57, 65, 90, 
	97, 122, 95, 116, 48, 57, 65, 90, 
	97, 122, 95, 114, 48, 57, 65, 90, 
	97, 122, 95, 97, 48, 57, 65, 90, 
	98, 122, 95, 121, 48, 57, 65, 90, 
	97, 122, 95, 105, 114, 121, 48, 57, 
	65, 90, 97, 122, 95, 103, 48, 57, 
	65, 90, 97, 122, 95, 101, 48, 57, 
	65, 90, 97, 122, 95, 97, 48, 57, 
	65, 90, 98, 122, 95, 107, 48, 57, 
	65, 90, 97, 122, 95, 116, 48, 57, 
	65, 90, 97, 122, 95, 101, 48, 57, 
	65, 90, 97, 122, 95, 97, 104, 111, 
	121, 48, 57, 65, 90, 98, 122, 95, 
	115, 48, 57, 65, 90, 97, 122, 95, 
	97, 48, 57, 65, 90, 98, 122, 95, 
	110, 48, 57, 65, 90, 97, 122, 95, 
	110, 48, 57, 65, 90, 97, 122, 95, 
	116, 48, 57, 65, 90, 97, 122, 95, 
	105, 48, 57, 65, 90, 97, 122, 95, 
	110, 48, 57, 65, 90, 97, 122, 95, 
	117, 48, 57, 65, 90, 97, 122, 95, 
	99, 48, 57, 65, 90, 97, 122, 95, 
	108, 48, 57, 65, 90, 97, 122, 95, 
	105, 48, 57, 65, 90, 97, 122, 95, 
	99, 48, 57, 65, 90, 97, 122, 95, 
	111, 48, 57, 65, 90, 97, 122, 95, 
	108, 120, 48, 57, 65, 90, 97, 122, 
	95, 105, 48, 57, 65, 90, 97, 122, 
	95, 110, 111, 48, 57, 65, 90, 97, 
	122, 95, 114, 48, 57, 65, 90, 97, 
	122, 95, 100, 48, 57, 65, 90, 97, 
	122, 95, 102, 109, 110, 48, 57, 65, 
	90, 97, 122, 95, 112, 48, 57, 65, 
	90, 97, 122, 95, 108, 111, 48, 57, 
	65, 90, 97, 122, 95, 101, 48, 57, 
	65, 90, 97, 122, 95, 109, 48, 57, 
	65, 90, 97, 122, 95, 101, 48, 57, 
	65, 90, 97, 122, 95, 110, 48, 57, 
	65, 90, 97, 122, 95, 114, 48, 57, 
	65, 90, 97, 122, 95, 101, 105, 111, 
	48, 57, 65, 90, 97, 122, 95, 115, 
	48, 57, 65, 90, 97, 122, 95, 97, 
	48, 57, 65, 90, 98, 122, 95, 111, 
	48, 57, 65, 90, 97, 122, 95, 100, 
	48, 57, 65, 90, 97, 122, 95, 117, 
	48, 57, 65, 90, 97, 122, 95, 108, 
	48, 57, 65, 90, 97, 122, 95, 105, 
	48, 57, 65, 90, 97, 122, 95, 108, 
	48, 57, 65, 90, 97, 122, 95, 102, 
	114, 48, 57, 65, 90, 97, 122, 95, 
	105, 48, 57, 65, 90, 97, 122, 95, 
	99, 48, 57, 65, 90, 97, 122, 95, 
	97, 101, 48, 57, 65, 90, 98, 122, 
	95, 105, 48, 57, 65, 90, 97, 122, 
	95, 115, 48, 57, 65, 90, 97, 122, 
	95, 101, 48, 57, 65, 90, 97, 122, 
	95, 115, 48, 57, 65, 90, 97, 122, 
	95, 105, 48, 57, 65, 90, 97, 122, 
	95, 110, 48, 57, 65, 90, 97, 122, 
	95, 99, 48, 57, 65, 90, 97, 122, 
	95, 108, 48, 57, 65, 90, 97, 122, 
	95, 117, 48, 57, 65, 90, 97, 122, 
	95, 100, 48, 57, 65, 90, 97, 122, 
	95, 97, 102, 116, 48, 57, 65, 90, 
	98, 122, 95, 117, 48, 57, 65, 90, 
	97, 122, 95, 114, 48, 57, 65, 90, 
	97, 122, 95, 101, 112, 116, 48, 57, 
	65, 90, 97, 122, 95, 108, 48, 57, 
	65, 90, 97, 122, 95, 102, 48, 57, 
	65, 90, 97, 122, 95, 97, 48, 57, 
	65, 90, 98, 122, 95, 119, 48, 57, 
	65, 90, 97, 122, 95, 114, 48, 57, 
	65, 90, 97, 122, 95, 105, 48, 57, 
	65, 90, 97, 122, 95, 110, 48, 57, 
	65, 90, 97, 122, 95, 97, 108, 111, 
	121, 48, 57, 65, 90, 98, 122, 95, 
	103, 48, 57, 65, 90, 97, 122, 95, 
	111, 48, 57, 65, 90, 97, 122, 95, 
	112, 48, 57, 65, 90, 97, 122, 95, 
	104, 48, 57, 65, 90, 97, 122, 95, 
	105, 48, 57, 65, 90, 97, 122, 9, 
	10, 12, 32, 34, 35, 39, 269, 525, 
	0, 8, 14, 255, 9, 32, 32, 34, 
	92, 9, 10, 12, 13, 10, 12, 13, 
	32, 39, 92, 9, 10, 12, 13, 10, 
	0
};

static const char _limbo_single_lengths[] = {
	0, 0, 2, 0, 2, 0, 2, 0, 
	2, 2, 0, 3, 1, 3, 1, 1, 
	30, 2, 0, 0, 1, 2, 1, 2, 
	2, 0, 3, 0, 1, 1, 4, 2, 
	2, 2, 2, 4, 2, 2, 2, 2, 
	2, 2, 5, 2, 2, 2, 2, 2, 
	2, 2, 2, 2, 2, 2, 2, 2, 
	3, 2, 3, 2, 2, 4, 2, 3, 
	2, 2, 2, 2, 2, 4, 2, 2, 
	2, 2, 2, 2, 2, 2, 3, 2, 
	2, 3, 2, 2, 2, 2, 2, 2, 
	2, 2, 2, 2, 4, 2, 2, 4, 
	2, 2, 2, 2, 2, 2, 2, 5, 
	2, 2, 2, 2, 2, 9, 2, 3, 
	1, 3, 1
};

static const char _limbo_range_lengths[] = {
	0, 3, 0, 0, 0, 0, 1, 1, 
	1, 1, 1, 2, 1, 2, 1, 0, 
	8, 1, 1, 3, 1, 0, 1, 0, 
	1, 1, 1, 1, 0, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 2, 0, 2, 
	1, 2, 0
};

static const short _limbo_index_offsets[] = {
	0, 0, 4, 7, 8, 11, 12, 16, 
	18, 22, 26, 28, 34, 37, 43, 46, 
	48, 87, 91, 93, 97, 100, 103, 106, 
	109, 113, 115, 120, 122, 124, 129, 137, 
	143, 149, 155, 161, 169, 175, 181, 187, 
	193, 199, 205, 214, 220, 226, 232, 238, 
	244, 250, 256, 262, 268, 274, 280, 286, 
	292, 299, 305, 312, 318, 324, 332, 338, 
	345, 351, 357, 363, 369, 375, 383, 389, 
	395, 401, 407, 413, 419, 425, 431, 438, 
	444, 450, 457, 463, 469, 475, 481, 487, 
	493, 499, 505, 511, 517, 525, 531, 537, 
	545, 551, 557, 563, 569, 575, 581, 587, 
	596, 602, 608, 614, 620, 626, 638, 641, 
	647, 650, 656
};

static const char _limbo_indicies[] = {
	1, 1, 1, 0, 4, 5, 3, 3, 
	4, 7, 6, 6, 10, 10, 9, 8, 
	11, 8, 12, 12, 11, 0, 13, 13, 
	14, 0, 14, 0, 15, 17, 18, 15, 
	15, 16, 15, 15, 16, 15, 17, 20, 
	15, 15, 19, 15, 15, 19, 21, 22, 
	23, 25, 26, 27, 28, 29, 30, 30, 
	31, 33, 26, 26, 34, 35, 36, 37, 
	38, 39, 40, 41, 42, 43, 44, 45, 
	46, 47, 48, 49, 50, 51, 25, 26, 
	32, 26, 34, 26, 34, 26, 24, 10, 
	10, 9, 52, 9, 53, 1, 1, 1, 
	53, 25, 25, 54, 4, 5, 3, 55, 
	55, 56, 4, 7, 6, 58, 59, 32, 
	57, 14, 53, 11, 12, 12, 32, 53, 
	11, 57, 60, 57, 61, 61, 61, 61, 
	0, 61, 63, 63, 64, 61, 61, 61, 
	62, 61, 65, 61, 61, 61, 62, 61, 
	66, 61, 61, 61, 62, 61, 67, 61, 
	61, 61, 62, 61, 65, 61, 61, 61, 
	62, 61, 68, 69, 70, 61, 61, 61, 
	62, 61, 65, 61, 61, 61, 62, 61, 
	71, 61, 61, 61, 62, 61, 72, 61, 
	61, 61, 62, 61, 65, 61, 61, 61, 
	62, 61, 73, 61, 61, 61, 62, 61, 
	65, 61, 61, 61, 62, 61, 74, 75, 
	76, 77, 61, 61, 61, 62, 61, 73, 
	61, 61, 61, 62, 61, 78, 61, 61, 
	61, 62, 61, 65, 61, 61, 61, 62, 
	61, 79, 61, 61, 61, 62, 61, 81, 
	61, 61, 61, 80, 61, 82, 61, 61, 
	61, 62, 61, 83, 61, 61, 61, 62, 
	61, 73, 61, 61, 61, 62, 61, 84, 
	61, 61, 61, 62, 61, 85, 61, 61, 
	61, 62, 61, 86, 61, 61, 61, 62, 
	61, 65, 61, 61, 61, 62, 61, 65, 
	61, 61, 61, 62, 61, 74, 87, 61, 
	61, 61, 62, 61, 63, 61, 61, 61, 
	62, 61, 65, 88, 61, 61, 61, 62, 
	61, 65, 61, 61, 61, 62, 61, 65, 
	61, 61, 61, 62, 61, 65, 89, 63, 
	61, 61, 61, 62, 61, 90, 61, 61, 
	61, 62, 61, 91, 92, 61, 61, 61, 
	62, 61, 93, 61, 61, 61, 62, 61, 
	94, 61, 61, 61, 62, 61, 95, 61, 
	61, 61, 62, 61, 63, 61, 61, 61, 
	62, 61, 63, 61, 61, 61, 62, 61, 
	78, 96, 97, 61, 61, 61, 62, 61, 
	63, 61, 61, 61, 62, 61, 98, 61, 
	61, 61, 62, 61, 99, 61, 61, 61, 
	62, 61, 100, 61, 61, 61, 62, 61, 
	101, 61, 61, 61, 62, 61, 73, 61, 
	61, 61, 62, 61, 102, 61, 61, 61, 
	62, 61, 65, 61, 61, 61, 62, 61, 
	65, 65, 61, 61, 61, 62, 61, 103, 
	61, 61, 61, 62, 61, 72, 61, 61, 
	61, 62, 61, 104, 105, 61, 61, 61, 
	62, 61, 106, 61, 61, 61, 62, 61, 
	107, 61, 61, 61, 62, 61, 108, 61, 
	61, 61, 62, 61, 109, 61, 61, 61, 
	80, 61, 110, 61, 61, 61, 62, 61, 
	111, 61, 61, 61, 62, 61, 112, 61, 
	61, 61, 62, 61, 113, 61, 61, 61, 
	62, 61, 114, 61, 61, 61, 62, 61, 
	73, 61, 61, 61, 62, 61, 102, 65, 
	115, 61, 61, 61, 62, 61, 116, 61, 
	61, 61, 62, 61, 78, 61, 61, 61, 
	62, 61, 117, 118, 119, 61, 61, 61, 
	62, 61, 120, 61, 61, 61, 62, 61, 
	65, 61, 61, 61, 62, 61, 121, 61, 
	61, 61, 62, 61, 78, 61, 61, 61, 
	62, 61, 122, 61, 61, 61, 62, 61, 
	123, 61, 61, 61, 62, 61, 68, 61, 
	61, 61, 62, 61, 124, 65, 65, 125, 
	61, 61, 61, 62, 61, 126, 61, 61, 
	61, 62, 61, 120, 61, 61, 61, 62, 
	61, 73, 61, 61, 61, 62, 61, 127, 
	61, 61, 61, 62, 61, 101, 61, 61, 
	61, 62, 129, 21, 21, 129, 130, 131, 
	132, 133, 134, 128, 128, 22, 129, 129, 
	135, 136, 17, 18, 136, 136, 16, 137, 
	137, 138, 136, 17, 20, 136, 136, 19, 
	21, 139, 0
};

static const char _limbo_trans_targs[] = {
	16, 19, 16, 2, 16, 3, 4, 5, 
	16, 18, 1, 8, 9, 10, 25, 109, 
	11, 109, 12, 13, 14, 109, 0, 17, 
	16, 20, 16, 21, 22, 23, 24, 27, 
	26, 28, 29, 30, 35, 42, 55, 56, 
	58, 60, 61, 69, 72, 76, 78, 79, 
	81, 95, 103, 107, 16, 16, 16, 16, 
	22, 16, 6, 7, 16, 29, 16, 31, 
	32, 29, 33, 34, 36, 37, 40, 38, 
	39, 41, 43, 44, 46, 51, 45, 47, 
	16, 48, 49, 50, 52, 53, 54, 57, 
	59, 62, 63, 64, 68, 65, 66, 67, 
	70, 71, 60, 73, 74, 75, 77, 80, 
	82, 92, 83, 84, 85, 86, 87, 88, 
	89, 90, 91, 93, 94, 96, 98, 100, 
	97, 99, 101, 102, 104, 106, 105, 108, 
	109, 110, 111, 112, 113, 15, 114, 109, 
	109, 109, 112, 109
};

static const char _limbo_trans_actions[] = {
	47, 13, 45, 11, 64, 11, 11, 11, 
	43, 13, 13, 13, 13, 13, 13, 27, 
	1, 49, 0, 1, 0, 55, 0, 109, 
	73, 7, 84, 92, 61, 92, 124, 124, 
	96, 80, 119, 76, 76, 76, 76, 76, 
	76, 76, 76, 76, 76, 76, 76, 76, 
	76, 76, 76, 76, 41, 33, 29, 31, 
	9, 39, 13, 13, 70, 100, 37, 67, 
	67, 114, 67, 67, 67, 67, 67, 67, 
	67, 67, 67, 67, 67, 67, 67, 67, 
	35, 67, 67, 67, 67, 67, 67, 67, 
	67, 67, 67, 67, 67, 67, 67, 67, 
	67, 67, 67, 67, 67, 67, 67, 67, 
	67, 67, 67, 67, 67, 67, 67, 67, 
	67, 67, 67, 67, 67, 67, 67, 67, 
	67, 67, 67, 67, 67, 67, 67, 67, 
	58, 3, 104, 52, 88, 5, 5, 19, 
	25, 21, 0, 23
};

static const char _limbo_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	15, 0, 0, 0, 0, 0, 0, 0, 
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
	0, 0, 0, 0, 0, 15, 0, 0, 
	0, 0, 0
};

static const char _limbo_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	17, 0, 0, 0, 0, 0, 0, 0, 
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
	0, 0, 0, 0, 0, 17, 0, 0, 
	0, 0, 0
};

static const short _limbo_eof_trans[] = {
	0, 1, 3, 3, 3, 3, 9, 9, 
	1, 1, 1, 16, 16, 16, 16, 0, 
	0, 53, 54, 54, 55, 53, 56, 53, 
	58, 54, 54, 58, 58, 1, 63, 63, 
	63, 63, 63, 63, 63, 63, 63, 63, 
	63, 63, 63, 63, 63, 63, 63, 81, 
	63, 63, 63, 63, 63, 63, 63, 63, 
	63, 63, 63, 63, 63, 63, 63, 63, 
	63, 63, 63, 63, 63, 63, 63, 63, 
	63, 63, 63, 63, 63, 63, 63, 63, 
	63, 63, 63, 63, 63, 81, 63, 63, 
	63, 63, 63, 63, 63, 63, 63, 63, 
	63, 63, 63, 63, 63, 63, 63, 63, 
	63, 63, 63, 63, 63, 0, 136, 137, 
	138, 137, 140
};

static const int limbo_start = 16;
static const int limbo_first_final = 16;
static const int limbo_error = 0;

static const int limbo_en_limbo_line = 109;
static const int limbo_en_limbo_entity = 16;


#line 114 "limbo.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Limbo code.
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
void parse_limbo(char *buffer, int length, int count,
                 void (*callback) (const char *lang, const char *entity, int s,
                                   int e, void *udata),
                 void *userdata
  ) {
  init

  
#line 489 "limbo.h"
	{
	cs = limbo_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 137 "limbo.rl"
  cs = (count) ? limbo_en_limbo_line : limbo_en_limbo_entity;
  
#line 500 "limbo.h"
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
	_acts = _limbo_actions + _limbo_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 16:
#line 1 "NONE"
	{ts = p;}
	break;
#line 522 "limbo.h"
		}
	}

	_widec = (*p);
	_klen = _limbo_cond_lengths[cs];
	_keys = _limbo_cond_keys + (_limbo_cond_offsets[cs]*2);
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
				switch ( _limbo_cond_spaces[_limbo_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _limbo_trans_keys + _limbo_key_offsets[cs];
	_trans = _limbo_index_offsets[cs];

	_klen = _limbo_single_lengths[cs];
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

	_klen = _limbo_range_lengths[cs];
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
	_trans = _limbo_indicies[_trans];
_eof_trans:
	cs = _limbo_trans_targs[_trans];

	if ( _limbo_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _limbo_actions + _limbo_trans_actions[_trans];
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
#line 67 "limbo.rl"
	{ entity = LIMBO_SPACE; }
	break;
	case 5:
#line 70 "limbo.rl"
	{ entity = NEWLINE;     }
	break;
	case 6:
#line 71 "limbo.rl"
	{ entity = LIMBO_ANY;   }
	break;
	case 7:
#line 105 "limbo.rl"
	{ entity = LIMBO_SPACE;   }
	break;
	case 8:
#line 106 "limbo.rl"
	{ entity = LIMBO_COMMENT; }
	break;
	case 9:
#line 107 "limbo.rl"
	{ entity = LIMBO_STRING;  }
	break;
	case 10:
#line 108 "limbo.rl"
	{ entity = LIMBO_NUMBER;  }
	break;
	case 11:
#line 109 "limbo.rl"
	{ entity = LIMBO_KEYWORD; }
	break;
	case 12:
#line 110 "limbo.rl"
	{ entity = LIMBO_IDENTIFIER; }
	break;
	case 13:
#line 111 "limbo.rl"
	{ entity = LIMBO_OPERATOR; }
	break;
	case 14:
#line 112 "limbo.rl"
	{ entity = C_ANY;         }
	break;
	case 17:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 18:
#line 69 "limbo.rl"
	{te = p+1;}
	break;
	case 19:
#line 34 "limbo.rl"
	{te = p+1;{
    switch(entity) {
    case LIMBO_SPACE:
      ls
      break;
    case LIMBO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LIMBO_LANG)
      break;
    case NEWLINE:
      std_newline(LIMBO_LANG)
    }
  }}
	break;
	case 20:
#line 34 "limbo.rl"
	{te = p+1;{
    switch(entity) {
    case LIMBO_SPACE:
      ls
      break;
    case LIMBO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LIMBO_LANG)
      break;
    case NEWLINE:
      std_newline(LIMBO_LANG)
    }
  }}
	break;
	case 21:
#line 34 "limbo.rl"
	{te = p;p--;{
    switch(entity) {
    case LIMBO_SPACE:
      ls
      break;
    case LIMBO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LIMBO_LANG)
      break;
    case NEWLINE:
      std_newline(LIMBO_LANG)
    }
  }}
	break;
	case 22:
#line 68 "limbo.rl"
	{te = p;p--;}
	break;
	case 23:
#line 34 "limbo.rl"
	{te = p;p--;{
    switch(entity) {
    case LIMBO_SPACE:
      ls
      break;
    case LIMBO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LIMBO_LANG)
      break;
    case NEWLINE:
      std_newline(LIMBO_LANG)
    }
  }}
	break;
	case 24:
#line 34 "limbo.rl"
	{te = p;p--;{
    switch(entity) {
    case LIMBO_SPACE:
      ls
      break;
    case LIMBO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LIMBO_LANG)
      break;
    case NEWLINE:
      std_newline(LIMBO_LANG)
    }
  }}
	break;
	case 25:
#line 34 "limbo.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case LIMBO_SPACE:
      ls
      break;
    case LIMBO_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LIMBO_LANG)
      break;
    case NEWLINE:
      std_newline(LIMBO_LANG)
    }
  }}
	break;
	case 26:
#line 76 "limbo.rl"
	{act = 9;}
	break;
	case 27:
#line 76 "limbo.rl"
	{act = 10;}
	break;
	case 28:
#line 76 "limbo.rl"
	{act = 11;}
	break;
	case 29:
#line 76 "limbo.rl"
	{act = 12;}
	break;
	case 30:
#line 76 "limbo.rl"
	{act = 13;}
	break;
	case 31:
#line 76 "limbo.rl"
	{te = p+1;{
    callback(LIMBO_LANG, limbo_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 32:
#line 76 "limbo.rl"
	{te = p+1;{
    callback(LIMBO_LANG, limbo_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 33:
#line 76 "limbo.rl"
	{te = p+1;{
    callback(LIMBO_LANG, limbo_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 34:
#line 76 "limbo.rl"
	{te = p+1;{
    callback(LIMBO_LANG, limbo_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 35:
#line 76 "limbo.rl"
	{te = p;p--;{
    callback(LIMBO_LANG, limbo_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 36:
#line 76 "limbo.rl"
	{te = p;p--;{
    callback(LIMBO_LANG, limbo_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 37:
#line 76 "limbo.rl"
	{te = p;p--;{
    callback(LIMBO_LANG, limbo_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 38:
#line 76 "limbo.rl"
	{te = p;p--;{
    callback(LIMBO_LANG, limbo_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 39:
#line 76 "limbo.rl"
	{te = p;p--;{
    callback(LIMBO_LANG, limbo_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 40:
#line 76 "limbo.rl"
	{te = p;p--;{
    callback(LIMBO_LANG, limbo_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 41:
#line 76 "limbo.rl"
	{te = p;p--;{
    callback(LIMBO_LANG, limbo_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 42:
#line 76 "limbo.rl"
	{{p = ((te))-1;}{
    callback(LIMBO_LANG, limbo_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 43:
#line 76 "limbo.rl"
	{{p = ((te))-1;}{
    callback(LIMBO_LANG, limbo_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 44:
#line 1 "NONE"
	{	switch( act ) {
	case 9:
	{{p = ((te))-1;}
    callback(LIMBO_LANG, limbo_entities[entity], cint(ts), cint(te), userdata);
  }
	break;
	case 10:
	{{p = ((te))-1;}
    callback(LIMBO_LANG, limbo_entities[entity], cint(ts), cint(te), userdata);
  }
	break;
	case 11:
	{{p = ((te))-1;}
    callback(LIMBO_LANG, limbo_entities[entity], cint(ts), cint(te), userdata);
  }
	break;
	case 12:
	{{p = ((te))-1;}
    callback(LIMBO_LANG, limbo_entities[entity], cint(ts), cint(te), userdata);
  }
	break;
	case 13:
	{{p = ((te))-1;}
    callback(LIMBO_LANG, limbo_entities[entity], cint(ts), cint(te), userdata);
  }
	break;
	}
	}
	break;
#line 953 "limbo.h"
		}
	}

_again:
	_acts = _limbo_actions + _limbo_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 15:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 966 "limbo.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _limbo_eof_trans[cs] > 0 ) {
		_trans = _limbo_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 139 "limbo.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(LIMBO_LANG) }
}

#endif

/*****************************************************************************/
