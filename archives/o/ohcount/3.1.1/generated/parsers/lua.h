
#line 1 "lua.rl"
// lua.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_LUA_PARSER_H
#define OHCOUNT_LUA_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *LUA_LANG = LANG_LUA;

// the languages entities
const char *lua_entities[] = {
  "space", "comment", "string", "number", "keyword",
  "identifier", "operator", "any"
};

// constants associated with the entities
enum {
  LUA_SPACE = 0, LUA_COMMENT, LUA_STRING, LUA_NUMBER, LUA_KEYWORD,
  LUA_IDENTIFIER, LUA_OPERATOR, LUA_ANY
};

/*****************************************************************************/


#line 30 "lua.h"
static const char _lua_actions[] = {
	0, 1, 1, 1, 2, 1, 3, 1, 
	5, 1, 6, 1, 12, 1, 13, 1, 
	14, 1, 15, 1, 16, 1, 17, 1, 
	18, 1, 19, 1, 23, 1, 24, 1, 
	25, 1, 27, 1, 30, 1, 31, 1, 
	32, 1, 33, 1, 34, 1, 35, 1, 
	43, 1, 44, 1, 45, 1, 46, 1, 
	47, 1, 48, 1, 49, 1, 50, 1, 
	51, 1, 52, 2, 0, 2, 2, 1, 
	26, 2, 1, 27, 2, 2, 7, 2, 
	3, 7, 2, 6, 16, 2, 7, 16, 
	2, 8, 4, 2, 9, 4, 2, 10, 
	4, 2, 11, 4, 2, 13, 28, 2, 
	14, 29, 2, 16, 39, 2, 17, 40, 
	2, 19, 20, 2, 19, 22, 2, 21, 
	22, 2, 21, 41, 2, 22, 42, 2, 
	25, 3, 2, 25, 16, 3, 8, 4, 
	3, 3, 9, 4, 2, 3, 10, 4, 
	2, 3, 10, 4, 27, 3, 11, 4, 
	2, 3, 11, 4, 27, 3, 19, 20, 
	22, 3, 21, 41, 22, 3, 25, 0, 
	3, 3, 25, 2, 14, 3, 25, 3, 
	7, 3, 25, 5, 14, 3, 25, 7, 
	16, 3, 25, 17, 22, 3, 25, 18, 
	36, 4, 25, 18, 22, 38, 4, 25, 
	18, 36, 22, 5, 25, 18, 21, 37, 
	22, 7, 25, 5, 16, 18, 21, 37, 
	22
};

static const char _lua_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 1, 2, 
	3, 3, 3, 4, 5, 5, 5, 6, 
	7, 9, 9, 9, 10, 11, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 14, 14, 
	14, 14, 14, 14, 14, 14, 14, 14, 
	14, 14, 14, 14, 14, 14, 14, 14, 
	14, 14, 14, 14, 14, 14, 14, 14, 
	14, 14, 14, 14, 14, 14, 14, 14, 
	14, 14, 14, 14, 14, 14, 14, 14, 
	14, 14, 14, 14, 14, 14, 14, 14, 
	15, 15, 16, 17, 17, 17, 17, 17, 
	18, 20, 20
};

static const char _lua_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 1, 1, 1, 
	0, 0, 1, 1, 0, 0, 1, 1, 
	2, 0, 0, 1, 1, 2, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 1, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 1, 
	0, 1, 1, 0, 0, 0, 0, 1, 
	2, 0, 0
};

static const short _lua_cond_keys[] = {
	93, 93, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	93, 93, 13, 13, 13, 13, 13, 13, 
	93, 93, 93, 93, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 93, 93, 
	0
};

static const char _lua_cond_spaces[] = {
	3, 0, 0, 0, 0, 0, 0, 0, 
	1, 0, 0, 0, 2, 3, 0, 0, 
	0, 0, 0, 1, 0
};

static const short _lua_key_offsets[] = {
	0, 0, 6, 8, 8, 10, 10, 12, 
	16, 20, 22, 27, 29, 30, 37, 49, 
	61, 64, 65, 77, 89, 92, 93, 104, 
	115, 130, 131, 133, 144, 155, 170, 171, 
	172, 213, 215, 221, 224, 226, 228, 231, 
	233, 238, 242, 245, 250, 254, 266, 271, 
	273, 279, 286, 293, 300, 307, 314, 321, 
	328, 336, 343, 350, 357, 364, 373, 380, 
	387, 394, 401, 408, 415, 422, 429, 436, 
	443, 451, 458, 465, 472, 479, 487, 494, 
	501, 509, 516, 523, 530, 537, 545, 552, 
	559, 566, 573, 580, 587, 594, 601, 602, 
	616, 618, 630, 642, 643, 647, 650, 655, 
	666, 681, 683
};

static const short _lua_trans_keys[] = {
	48, 57, 65, 70, 97, 102, 34, 92, 
	39, 92, 48, 57, 69, 101, 48, 57, 
	43, 45, 48, 57, 48, 57, 46, 69, 
	101, 48, 57, 88, 120, 93, 61, 1885, 
	2141, 0, 92, 94, 255, 9, 10, 12, 
	32, 34, 92, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 34, 92, 269, 
	525, 0, 11, 14, 255, 10, 12, 13, 
	10, 9, 10, 12, 32, 39, 92, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 39, 92, 269, 525, 0, 11, 14, 
	255, 10, 12, 13, 10, 9, 10, 12, 
	32, 93, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 93, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 61, 
	269, 525, 861, 1117, 0, 11, 14, 92, 
	94, 255, 10, 61, 91, 9, 10, 12, 
	32, 93, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 93, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 61, 
	269, 525, 1373, 1629, 0, 11, 14, 92, 
	94, 255, 10, 10, 0, 32, 34, 35, 
	37, 39, 43, 45, 46, 91, 95, 97, 
	98, 100, 101, 102, 105, 108, 110, 111, 
	114, 116, 117, 119, 123, 125, 126, 9, 
	13, 40, 47, 48, 57, 58, 62, 65, 
	90, 93, 94, 99, 122, 88, 120, 48, 
	57, 65, 70, 97, 102, 32, 9, 13, 
	34, 92, 39, 92, 46, 48, 57, 48, 
	57, 0, 45, 46, 48, 57, 10, 91, 
	12, 13, 10, 12, 13, 10, 61, 91, 
	12, 13, 10, 93, 12, 13, 10, 61, 
	1885, 2141, 0, 11, 12, 13, 14, 92, 
	94, 255, 46, 69, 101, 48, 57, 48, 
	57, 48, 57, 65, 90, 97, 122, 110, 
	48, 57, 65, 90, 97, 122, 100, 48, 
	57, 65, 90, 97, 122, 114, 48, 57, 
	65, 90, 97, 122, 101, 48, 57, 65, 
	90, 97, 122, 97, 48, 57, 65, 90, 
	98, 122, 107, 48, 57, 65, 90, 97, 
	122, 111, 48, 57, 65, 90, 97, 122, 
	108, 110, 48, 57, 65, 90, 97, 122, 
	115, 48, 57, 65, 90, 97, 122, 101, 
	48, 57, 65, 90, 97, 122, 105, 48, 
	57, 65, 90, 97, 122, 102, 48, 57, 
	65, 90, 97, 122, 97, 111, 117, 48, 
	57, 65, 90, 98, 122, 108, 48, 57, 
	65, 90, 97, 122, 115, 48, 57, 65, 
	90, 97, 122, 101, 48, 57, 65, 90, 
	97, 122, 114, 48, 57, 65, 90, 97, 
	122, 110, 48, 57, 65, 90, 97, 122, 
	99, 48, 57, 65, 90, 97, 122, 116, 
	48, 57, 65, 90, 97, 122, 105, 48, 
	57, 65, 90, 97, 122, 111, 48, 57, 
	65, 90, 97, 122, 110, 48, 57, 65, 
	90, 97, 122, 102, 110, 48, 57, 65, 
	90, 97, 122, 111, 48, 57, 65, 90, 
	97, 122, 99, 48, 57, 65, 90, 97, 
	122, 97, 48, 57, 65, 90, 98, 122, 
	108, 48, 57, 65, 90, 97, 122, 105, 
	111, 48, 57, 65, 90, 97, 122, 116, 
	48, 57, 65, 90, 97, 122, 101, 48, 
	57, 65, 90, 97, 122, 112, 116, 48, 
	57, 65, 90, 97, 122, 101, 48, 57, 
	65, 90, 97, 122, 97, 48, 57, 65, 
	90, 98, 122, 117, 48, 57, 65, 90, 
	97, 122, 114, 48, 57, 65, 90, 97, 
	122, 104, 114, 48, 57, 65, 90, 97, 
	122, 101, 48, 57, 65, 90, 97, 122, 
	117, 48, 57, 65, 90, 97, 122, 110, 
	48, 57, 65, 90, 97, 122, 116, 48, 
	57, 65, 90, 97, 122, 105, 48, 57, 
	65, 90, 97, 122, 104, 48, 57, 65, 
	90, 97, 122, 105, 48, 57, 65, 90, 
	97, 122, 108, 48, 57, 65, 90, 97, 
	122, 61, 9, 10, 12, 32, 34, 39, 
	45, 91, 269, 525, 0, 8, 14, 255, 
	9, 32, 9, 10, 12, 32, 34, 92, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 39, 92, 269, 525, 0, 11, 
	14, 255, 45, 10, 91, 12, 13, 10, 
	12, 13, 10, 61, 91, 12, 13, 9, 
	10, 12, 32, 93, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 61, 269, 
	525, 861, 1117, 0, 11, 14, 92, 94, 
	255, 61, 91, 10, 0
};

static const char _lua_single_lengths[] = {
	0, 0, 2, 0, 2, 0, 0, 2, 
	2, 0, 3, 2, 1, 3, 8, 8, 
	1, 1, 8, 8, 1, 1, 7, 7, 
	9, 1, 2, 7, 7, 9, 1, 1, 
	27, 2, 0, 1, 2, 2, 1, 0, 
	3, 2, 1, 3, 2, 4, 3, 0, 
	0, 1, 1, 1, 1, 1, 1, 1, 
	2, 1, 1, 1, 1, 3, 1, 1, 
	1, 1, 1, 1, 1, 1, 1, 1, 
	2, 1, 1, 1, 1, 2, 1, 1, 
	2, 1, 1, 1, 1, 2, 1, 1, 
	1, 1, 1, 1, 1, 1, 1, 10, 
	2, 8, 8, 1, 2, 1, 3, 7, 
	9, 2, 1
};

static const char _lua_range_lengths[] = {
	0, 3, 0, 0, 0, 0, 1, 1, 
	1, 1, 1, 0, 0, 2, 2, 2, 
	1, 0, 2, 2, 1, 0, 2, 2, 
	3, 0, 0, 2, 2, 3, 0, 0, 
	7, 0, 3, 1, 0, 0, 1, 1, 
	1, 1, 1, 1, 1, 4, 1, 1, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 0, 2, 
	0, 2, 2, 0, 1, 1, 1, 2, 
	3, 0, 0
};

static const short _lua_index_offsets[] = {
	0, 0, 4, 7, 8, 11, 12, 14, 
	18, 22, 24, 29, 32, 34, 40, 51, 
	62, 65, 67, 78, 89, 92, 94, 104, 
	114, 127, 129, 132, 142, 152, 165, 167, 
	169, 204, 207, 211, 214, 217, 220, 223, 
	225, 230, 234, 237, 242, 246, 255, 260, 
	262, 266, 271, 276, 281, 286, 291, 296, 
	301, 307, 312, 317, 322, 327, 334, 339, 
	344, 349, 354, 359, 364, 369, 374, 379, 
	384, 390, 395, 400, 405, 410, 416, 421, 
	426, 432, 437, 442, 447, 452, 458, 463, 
	468, 473, 478, 483, 488, 493, 498, 500, 
	513, 516, 527, 538, 540, 544, 547, 552, 
	562, 575, 578
};

static const char _lua_indicies[] = {
	1, 1, 1, 0, 4, 5, 3, 3, 
	4, 7, 6, 6, 9, 8, 10, 10, 
	9, 0, 11, 11, 12, 0, 12, 0, 
	9, 10, 10, 13, 8, 14, 14, 8, 
	17, 16, 18, 17, 19, 16, 16, 15, 
	22, 23, 23, 22, 24, 25, 26, 23, 
	21, 21, 20, 28, 29, 29, 28, 30, 
	31, 32, 29, 27, 27, 20, 20, 20, 
	21, 23, 20, 34, 35, 35, 34, 24, 
	36, 37, 35, 33, 33, 20, 39, 40, 
	40, 39, 41, 42, 43, 40, 38, 38, 
	20, 20, 20, 33, 35, 20, 46, 47, 
	47, 46, 48, 49, 47, 45, 45, 44, 
	51, 52, 52, 51, 53, 54, 52, 50, 
	50, 44, 51, 52, 52, 51, 55, 54, 
	52, 53, 56, 50, 50, 50, 44, 52, 
	44, 57, 58, 20, 60, 61, 61, 60, 
	62, 63, 61, 59, 59, 20, 65, 66, 
	66, 65, 67, 68, 66, 64, 64, 20, 
	60, 61, 61, 60, 69, 63, 61, 62, 
	70, 59, 59, 59, 20, 61, 20, 71, 
	72, 73, 75, 76, 77, 77, 78, 79, 
	80, 81, 77, 83, 84, 85, 86, 87, 
	88, 89, 90, 91, 92, 93, 94, 95, 
	96, 77, 77, 97, 75, 77, 82, 77, 
	83, 77, 83, 74, 14, 14, 98, 1, 
	1, 1, 99, 75, 75, 100, 4, 5, 
	3, 4, 7, 6, 102, 13, 101, 12, 
	99, 103, 104, 102, 105, 101, 106, 108, 
	106, 107, 106, 106, 107, 106, 109, 110, 
	106, 107, 16, 111, 16, 110, 16, 112, 
	111, 107, 110, 16, 110, 110, 106, 9, 
	10, 10, 105, 99, 9, 101, 114, 114, 
	114, 113, 115, 114, 114, 114, 113, 116, 
	114, 114, 114, 113, 117, 114, 114, 114, 
	113, 118, 114, 114, 114, 113, 119, 114, 
	114, 114, 113, 116, 114, 114, 114, 113, 
	116, 114, 114, 114, 113, 120, 115, 114, 
	114, 114, 113, 121, 114, 114, 114, 113, 
	122, 114, 114, 114, 113, 123, 114, 114, 
	114, 113, 116, 114, 114, 114, 113, 124, 
	125, 126, 114, 114, 114, 113, 127, 114, 
	114, 114, 113, 128, 114, 114, 114, 113, 
	116, 114, 114, 114, 113, 116, 114, 114, 
	114, 113, 129, 114, 114, 114, 113, 130, 
	114, 114, 114, 113, 131, 114, 114, 114, 
	113, 132, 114, 114, 114, 113, 133, 114, 
	114, 114, 113, 116, 114, 114, 114, 113, 
	116, 116, 114, 114, 114, 113, 134, 114, 
	114, 114, 113, 135, 114, 114, 114, 113, 
	136, 114, 114, 114, 113, 116, 114, 114, 
	114, 113, 136, 137, 114, 114, 114, 113, 
	116, 114, 114, 114, 113, 138, 114, 114, 
	114, 113, 139, 140, 114, 114, 114, 113, 
	141, 114, 114, 114, 113, 137, 114, 114, 
	114, 113, 142, 114, 114, 114, 113, 133, 
	114, 114, 114, 113, 143, 144, 114, 114, 
	114, 113, 133, 114, 114, 114, 113, 128, 
	114, 114, 114, 113, 145, 114, 114, 114, 
	113, 146, 114, 114, 114, 113, 136, 114, 
	114, 114, 113, 147, 114, 114, 114, 113, 
	148, 114, 114, 114, 113, 128, 114, 114, 
	114, 113, 149, 98, 151, 71, 71, 151, 
	152, 153, 154, 155, 156, 157, 150, 150, 
	72, 151, 151, 158, 22, 23, 23, 22, 
	24, 25, 26, 23, 21, 21, 159, 34, 
	35, 35, 34, 24, 36, 37, 35, 33, 
	33, 159, 160, 159, 161, 163, 161, 162, 
	161, 161, 162, 161, 164, 165, 161, 162, 
	167, 52, 52, 167, 168, 54, 52, 166, 
	166, 161, 167, 52, 52, 167, 169, 54, 
	52, 168, 170, 166, 166, 166, 161, 57, 
	58, 159, 71, 171, 0
};

static const char _lua_trans_targs[] = {
	32, 34, 32, 2, 32, 3, 4, 5, 
	32, 7, 8, 9, 39, 10, 1, 32, 
	12, 13, 13, 32, 95, 14, 14, 15, 
	95, 16, 17, 14, 14, 15, 95, 16, 
	17, 18, 18, 19, 20, 21, 18, 18, 
	19, 95, 20, 21, 95, 23, 23, 22, 
	24, 25, 23, 23, 22, 24, 25, 24, 
	95, 26, 27, 27, 27, 28, 29, 30, 
	27, 27, 28, 29, 30, 29, 95, 95, 
	0, 33, 32, 35, 36, 32, 37, 38, 
	40, 47, 46, 48, 49, 51, 55, 56, 
	61, 72, 73, 77, 65, 79, 85, 88, 
	91, 94, 32, 32, 32, 32, 6, 11, 
	41, 46, 32, 42, 43, 43, 44, 45, 
	45, 32, 48, 50, 48, 52, 53, 54, 
	57, 58, 59, 60, 62, 65, 66, 63, 
	64, 67, 68, 69, 70, 71, 74, 75, 
	76, 78, 80, 81, 83, 82, 84, 86, 
	87, 89, 90, 92, 93, 32, 95, 96, 
	97, 98, 99, 105, 31, 106, 95, 95, 
	100, 95, 101, 102, 102, 103, 103, 103, 
	104, 104, 101, 95
};

static const char _lua_trans_actions[] = {
	65, 23, 63, 21, 109, 21, 21, 21, 
	61, 23, 23, 23, 23, 23, 23, 59, 
	19, 19, 85, 106, 45, 3, 0, 0, 
	33, 0, 0, 149, 97, 97, 153, 97, 
	97, 3, 0, 0, 0, 0, 141, 94, 
	94, 145, 94, 94, 43, 133, 88, 88, 
	133, 88, 5, 0, 0, 5, 0, 79, 
	70, 9, 67, 3, 0, 0, 3, 0, 
	137, 91, 91, 137, 91, 76, 73, 100, 
	0, 193, 124, 17, 185, 161, 185, 203, 
	209, 203, 198, 115, 157, 157, 157, 157, 
	157, 157, 157, 157, 157, 157, 157, 157, 
	157, 118, 57, 51, 47, 55, 23, 23, 
	19, 189, 49, 19, 19, 82, 130, 130, 
	181, 53, 25, 112, 112, 112, 112, 112, 
	112, 112, 112, 112, 112, 112, 112, 112, 
	112, 112, 112, 112, 112, 112, 112, 112, 
	112, 112, 112, 112, 112, 112, 112, 112, 
	112, 112, 112, 112, 112, 121, 103, 11, 
	169, 169, 15, 177, 13, 13, 35, 41, 
	5, 37, 0, 7, 9, 165, 127, 31, 
	127, 173, 1, 39
};

static const char _lua_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	27, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 27, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0
};

static const char _lua_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	29, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 29, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0
};

static const short _lua_eof_trans[] = {
	0, 1, 3, 3, 3, 3, 9, 1, 
	1, 1, 9, 9, 16, 16, 21, 21, 
	21, 21, 21, 21, 21, 21, 45, 45, 
	45, 45, 21, 21, 21, 21, 21, 0, 
	0, 99, 100, 101, 99, 99, 102, 100, 
	102, 107, 107, 107, 107, 107, 100, 102, 
	114, 114, 114, 114, 114, 114, 114, 114, 
	114, 114, 114, 114, 114, 114, 114, 114, 
	114, 114, 114, 114, 114, 114, 114, 114, 
	114, 114, 114, 114, 114, 114, 114, 114, 
	114, 114, 114, 114, 114, 114, 114, 114, 
	114, 114, 114, 114, 114, 114, 99, 0, 
	159, 160, 160, 160, 162, 162, 162, 162, 
	162, 160, 172
};

static const int lua_start = 32;
static const int lua_first_final = 32;
static const int lua_error = 0;

static const int lua_en_lua_line = 95;
static const int lua_en_lua_entity = 32;


#line 138 "lua.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Lua code.
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
void parse_lua(char *buffer, int length, int count,
               void (*callback) (const char *lang, const char *entity, int s,
                                 int e, void *udata),
               void *userdata
  ) {
  init

  int equal_count = 0;

  
#line 479 "lua.h"
	{
	cs = lua_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 163 "lua.rl"
  cs = (count) ? lua_en_lua_line : lua_en_lua_entity;
  
#line 490 "lua.h"
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
	_acts = _lua_actions + _lua_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 24:
#line 1 "NONE"
	{ts = p;}
	break;
#line 512 "lua.h"
		}
	}

	_widec = (*p);
	_klen = _lua_cond_lengths[cs];
	_keys = _lua_cond_keys + (_lua_cond_offsets[cs]*2);
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
				switch ( _lua_cond_spaces[_lua_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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
#line 60 "lua.rl"
 equal_count == 0  ) _widec += 256;
		break;
	}
	case 2: {
		_widec = (short)(1280 + ((*p) - 0));
		if ( 
#line 71 "lua.rl"
 equal_count == 0  ) _widec += 256;
		break;
	}
	case 3: {
		_widec = (short)(1792 + ((*p) - 0));
		if ( 
#line 110 "lua.rl"
 equal_count == 0  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _lua_trans_keys + _lua_key_offsets[cs];
	_trans = _lua_index_offsets[cs];

	_klen = _lua_single_lengths[cs];
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

	_klen = _lua_range_lengths[cs];
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
	_trans = _lua_indicies[_trans];
_eof_trans:
	cs = _lua_trans_targs[_trans];

	if ( _lua_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _lua_actions + _lua_trans_actions[_trans];
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
#line 33 "lua.rl"
	{
    switch(entity) {
    case LUA_SPACE:
      ls
      break;
    case LUA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LUA_LANG)
      break;
    case NEWLINE:
      std_newline(LUA_LANG)
    }
  }
	break;
	case 5:
#line 49 "lua.rl"
	{ equal_count = 0; }
	break;
	case 6:
#line 50 "lua.rl"
	{ equal_count++; }
	break;
	case 7:
#line 51 "lua.rl"
	{ equal_count--; }
	break;
	case 8:
#line 55 "lua.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 9:
#line 66 "lua.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 10:
#line 74 "lua.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 11:
#line 84 "lua.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 12:
#line 95 "lua.rl"
	{ entity = LUA_SPACE; }
	break;
	case 13:
#line 98 "lua.rl"
	{ entity = NEWLINE;   }
	break;
	case 14:
#line 99 "lua.rl"
	{ entity = LUA_ANY;   }
	break;
	case 15:
#line 129 "lua.rl"
	{ entity = LUA_SPACE;      }
	break;
	case 16:
#line 130 "lua.rl"
	{ entity = LUA_COMMENT;    }
	break;
	case 17:
#line 131 "lua.rl"
	{ entity = LUA_STRING;     }
	break;
	case 18:
#line 132 "lua.rl"
	{ entity = LUA_NUMBER;     }
	break;
	case 19:
#line 133 "lua.rl"
	{ entity = LUA_IDENTIFIER; }
	break;
	case 20:
#line 134 "lua.rl"
	{ entity = LUA_KEYWORD;    }
	break;
	case 21:
#line 135 "lua.rl"
	{ entity = LUA_OPERATOR;   }
	break;
	case 22:
#line 136 "lua.rl"
	{ entity = LUA_ANY;        }
	break;
	case 25:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 26:
#line 96 "lua.rl"
	{te = p+1;}
	break;
	case 27:
#line 97 "lua.rl"
	{te = p+1;}
	break;
	case 28:
#line 33 "lua.rl"
	{te = p+1;{
    switch(entity) {
    case LUA_SPACE:
      ls
      break;
    case LUA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LUA_LANG)
      break;
    case NEWLINE:
      std_newline(LUA_LANG)
    }
  }}
	break;
	case 29:
#line 33 "lua.rl"
	{te = p+1;{
    switch(entity) {
    case LUA_SPACE:
      ls
      break;
    case LUA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LUA_LANG)
      break;
    case NEWLINE:
      std_newline(LUA_LANG)
    }
  }}
	break;
	case 30:
#line 33 "lua.rl"
	{te = p;p--;{
    switch(entity) {
    case LUA_SPACE:
      ls
      break;
    case LUA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LUA_LANG)
      break;
    case NEWLINE:
      std_newline(LUA_LANG)
    }
  }}
	break;
	case 31:
#line 96 "lua.rl"
	{te = p;p--;}
	break;
	case 32:
#line 33 "lua.rl"
	{te = p;p--;{
    switch(entity) {
    case LUA_SPACE:
      ls
      break;
    case LUA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LUA_LANG)
      break;
    case NEWLINE:
      std_newline(LUA_LANG)
    }
  }}
	break;
	case 33:
#line 33 "lua.rl"
	{te = p;p--;{
    switch(entity) {
    case LUA_SPACE:
      ls
      break;
    case LUA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LUA_LANG)
      break;
    case NEWLINE:
      std_newline(LUA_LANG)
    }
  }}
	break;
	case 34:
#line 96 "lua.rl"
	{{p = ((te))-1;}}
	break;
	case 35:
#line 33 "lua.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case LUA_SPACE:
      ls
      break;
    case LUA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LUA_LANG)
      break;
    case NEWLINE:
      std_newline(LUA_LANG)
    }
  }}
	break;
	case 36:
#line 104 "lua.rl"
	{act = 9;}
	break;
	case 37:
#line 104 "lua.rl"
	{act = 12;}
	break;
	case 38:
#line 104 "lua.rl"
	{act = 13;}
	break;
	case 39:
#line 104 "lua.rl"
	{te = p+1;{
    callback(LUA_LANG, lua_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 40:
#line 104 "lua.rl"
	{te = p+1;{
    callback(LUA_LANG, lua_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 41:
#line 104 "lua.rl"
	{te = p+1;{
    callback(LUA_LANG, lua_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 42:
#line 104 "lua.rl"
	{te = p+1;{
    callback(LUA_LANG, lua_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 43:
#line 104 "lua.rl"
	{te = p;p--;{
    callback(LUA_LANG, lua_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 44:
#line 104 "lua.rl"
	{te = p;p--;{
    callback(LUA_LANG, lua_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 45:
#line 104 "lua.rl"
	{te = p;p--;{
    callback(LUA_LANG, lua_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 46:
#line 104 "lua.rl"
	{te = p;p--;{
    callback(LUA_LANG, lua_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 47:
#line 104 "lua.rl"
	{te = p;p--;{
    callback(LUA_LANG, lua_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 48:
#line 104 "lua.rl"
	{te = p;p--;{
    callback(LUA_LANG, lua_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 49:
#line 104 "lua.rl"
	{{p = ((te))-1;}{
    callback(LUA_LANG, lua_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 50:
#line 104 "lua.rl"
	{{p = ((te))-1;}{
    callback(LUA_LANG, lua_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 51:
#line 104 "lua.rl"
	{{p = ((te))-1;}{
    callback(LUA_LANG, lua_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 52:
#line 1 "NONE"
	{	switch( act ) {
	case 9:
	{{p = ((te))-1;}
    callback(LUA_LANG, lua_entities[entity], cint(ts), cint(te), userdata);
  }
	break;
	case 12:
	{{p = ((te))-1;}
    callback(LUA_LANG, lua_entities[entity], cint(ts), cint(te), userdata);
  }
	break;
	case 13:
	{{p = ((te))-1;}
    callback(LUA_LANG, lua_entities[entity], cint(ts), cint(te), userdata);
  }
	break;
	}
	}
	break;
#line 1000 "lua.h"
		}
	}

_again:
	_acts = _lua_actions + _lua_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 23:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 1013 "lua.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _lua_eof_trans[cs] > 0 ) {
		_trans = _lua_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 165 "lua.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(LUA_LANG) }
}

#endif

/*****************************************************************************/
