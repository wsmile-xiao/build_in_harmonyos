
#line 1 "mxml.rl.tmp"
// mxml.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_MXML_PARSER_H
#define OHCOUNT_MXML_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *MXML_LANG = LANG_MXML;

// the languages entities
const char *mxml_entities[] = {
  "space", "comment", "doctype",
  "tag", "entity", "any"
};

// constants associated with the entities
enum {
  MXML_SPACE = 0, MXML_COMMENT, MXML_DOCTYPE,
  MXML_TAG, MXML_ENTITY, MXML_ANY
};

/*****************************************************************************/

#include "css.h"
#include "actionscript.h"


#line 33 "mxml.h"
static const char _mxml_actions[] = {
	0, 1, 0, 1, 1, 1, 7, 1, 
	8, 1, 10, 1, 11, 1, 15, 1, 
	16, 1, 18, 1, 19, 1, 25, 1, 
	26, 1, 29, 1, 30, 1, 36, 1, 
	37, 1, 40, 1, 41, 1, 43, 1, 
	44, 1, 45, 1, 46, 1, 47, 1, 
	48, 1, 49, 1, 50, 1, 51, 1, 
	54, 1, 55, 1, 56, 1, 57, 1, 
	59, 1, 60, 1, 61, 1, 62, 1, 
	63, 1, 64, 1, 67, 1, 68, 1, 
	69, 1, 70, 1, 71, 1, 73, 1, 
	74, 1, 75, 1, 76, 1, 77, 1, 
	79, 1, 80, 1, 83, 1, 84, 1, 
	85, 1, 86, 1, 88, 1, 89, 1, 
	92, 1, 93, 1, 94, 1, 95, 1, 
	96, 1, 99, 1, 100, 1, 103, 1, 
	104, 1, 105, 1, 106, 1, 109, 1, 
	110, 1, 111, 1, 112, 1, 115, 1, 
	116, 1, 117, 1, 118, 1, 119, 1, 
	120, 1, 121, 1, 123, 1, 124, 1, 
	125, 1, 126, 2, 4, 3, 2, 5, 
	3, 2, 6, 3, 2, 8, 52, 2, 
	9, 53, 2, 11, 58, 2, 13, 12, 
	2, 14, 12, 2, 16, 65, 2, 17, 
	66, 2, 19, 72, 2, 21, 20, 2, 
	22, 20, 2, 23, 20, 2, 26, 81, 
	2, 27, 82, 2, 30, 90, 2, 31, 
	91, 2, 37, 101, 2, 38, 102, 2, 
	39, 107, 2, 41, 108, 2, 42, 113, 
	2, 44, 114, 2, 46, 122, 2, 49, 
	9, 2, 49, 11, 2, 49, 17, 2, 
	49, 19, 2, 49, 27, 2, 49, 31, 
	2, 49, 38, 2, 49, 41, 2, 49, 
	44, 2, 49, 46, 3, 4, 3, 1, 
	3, 5, 3, 0, 3, 5, 3, 51, 
	3, 5, 3, 80, 3, 6, 3, 0, 
	3, 6, 3, 51, 3, 6, 3, 80, 
	3, 13, 12, 1, 3, 14, 12, 0, 
	3, 21, 20, 1, 3, 22, 20, 0, 
	3, 22, 20, 100, 3, 23, 20, 0, 
	3, 23, 20, 100, 3, 49, 0, 9, 
	3, 49, 0, 17, 3, 49, 0, 27, 
	3, 49, 0, 31, 3, 49, 0, 38, 
	4, 2, 0, 24, 78, 4, 2, 0, 
	28, 87, 5, 0, 32, 20, 33, 97, 
	5, 0, 34, 20, 35, 98
};

static const char _mxml_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 1, 2, 2, 2, 
	3, 4, 4, 4, 5, 6, 7, 7, 
	7, 7, 7, 7, 7, 7, 7, 8, 
	9, 10, 10, 10, 10, 10, 10, 10, 
	10, 10, 11, 12, 13, 14, 14, 14, 
	14, 14, 15, 16, 16, 16, 17, 18, 
	18, 18, 19, 20, 21, 21, 21, 21, 
	21, 21, 21, 21, 21, 21, 21, 21, 
	21, 21, 21, 21, 22, 23, 24, 24, 
	24, 24, 24, 24, 24, 24, 24, 25, 
	26, 27, 28, 28, 28, 28, 28, 28, 
	28, 28, 28, 28, 28, 28, 28, 29, 
	30, 30, 30, 31, 32, 32, 32, 32, 
	32, 33, 34, 35, 36, 36, 36, 36, 
	36, 36, 36, 36, 36, 36, 36, 36, 
	36, 36, 36, 36, 36, 36, 36, 36, 
	36, 36, 36, 36, 36, 36, 36, 36, 
	36, 36, 36, 36, 36, 36, 36, 36, 
	36, 36, 36, 36, 36, 36, 37, 37, 
	38, 39, 39, 39, 39, 39, 39, 40, 
	40, 40, 40, 40, 40, 40, 40, 40, 
	40, 40, 40, 41, 41, 42, 43, 43, 
	43, 43, 44, 44, 44, 44, 44, 44, 
	44, 44, 45, 45, 46, 47, 47, 47, 
	47, 47, 47, 47, 47, 47, 47, 47
};

static const char _mxml_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 1, 1, 0, 0, 1, 
	1, 0, 0, 1, 1, 1, 0, 0, 
	0, 0, 0, 0, 0, 0, 1, 1, 
	1, 0, 0, 0, 0, 0, 0, 0, 
	0, 1, 1, 1, 1, 0, 0, 0, 
	0, 1, 1, 0, 0, 1, 1, 0, 
	0, 1, 1, 1, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 1, 1, 1, 0, 0, 
	0, 0, 0, 0, 0, 0, 1, 1, 
	1, 1, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 1, 1, 
	0, 0, 1, 1, 0, 0, 0, 0, 
	1, 1, 1, 1, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 1, 0, 1, 
	1, 0, 0, 0, 0, 0, 1, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 1, 0, 1, 1, 0, 0, 
	0, 1, 0, 0, 0, 0, 0, 0, 
	0, 1, 0, 1, 1, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0
};

static const short _mxml_cond_keys[] = {
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
	13, 13, 13, 13, 13, 13, 0
};

static const char _mxml_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0
};

static const short _mxml_key_offsets[] = {
	0, 0, 1, 2, 3, 4, 6, 7, 
	8, 9, 11, 12, 13, 14, 15, 16, 
	17, 18, 19, 20, 32, 44, 47, 48, 
	60, 72, 75, 76, 87, 98, 110, 111, 
	112, 113, 115, 120, 123, 128, 131, 142, 
	153, 165, 166, 167, 168, 169, 170, 171, 
	172, 173, 184, 195, 206, 218, 219, 220, 
	221, 223, 235, 247, 250, 251, 263, 275, 
	278, 279, 290, 301, 313, 314, 315, 316, 
	317, 318, 319, 320, 321, 322, 323, 324, 
	329, 332, 337, 340, 351, 362, 374, 375, 
	376, 377, 378, 379, 380, 381, 382, 393, 
	404, 415, 427, 428, 429, 430, 431, 432, 
	433, 434, 435, 436, 437, 438, 439, 451, 
	463, 466, 467, 479, 491, 494, 495, 496, 
	497, 508, 519, 530, 542, 543, 544, 545, 
	546, 548, 549, 550, 551, 552, 553, 554, 
	555, 556, 557, 558, 559, 561, 562, 563, 
	564, 565, 566, 567, 568, 569, 570, 571, 
	573, 574, 575, 576, 577, 578, 579, 580, 
	581, 582, 583, 587, 590, 592, 605, 607, 
	619, 631, 632, 633, 637, 640, 641, 655, 
	657, 662, 667, 669, 672, 673, 674, 678, 
	681, 683, 686, 700, 702, 714, 726, 727, 
	728, 729, 743, 745, 750, 755, 757, 760, 
	762, 763, 776, 778, 790, 802, 804, 805, 
	810, 813, 814, 815, 820, 823, 825, 828
};

static const short _mxml_trans_keys[] = {
	45, 45, 45, 45, 45, 62, 120, 58, 
	83, 99, 116, 114, 105, 112, 116, 62, 
	121, 108, 101, 62, 9, 10, 12, 32, 
	34, 92, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 34, 92, 269, 525, 
	0, 11, 14, 255, 10, 12, 13, 10, 
	9, 10, 12, 32, 39, 92, 269, 525, 
	0, 11, 14, 255, 9, 10, 12, 32, 
	39, 92, 269, 525, 0, 11, 14, 255, 
	10, 12, 13, 10, 9, 10, 12, 32, 
	42, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 42, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 42, 47, 
	269, 525, 0, 11, 14, 255, 10, 10, 
	42, 42, 47, 10, 34, 92, 12, 13, 
	10, 12, 13, 10, 39, 92, 12, 13, 
	10, 12, 13, 9, 10, 12, 32, 42, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 42, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 42, 47, 269, 
	525, 0, 11, 14, 255, 10, 91, 67, 
	68, 65, 84, 65, 91, 9, 10, 12, 
	32, 93, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 93, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 93, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 62, 93, 269, 525, 0, 11, 
	14, 255, 10, 10, 42, 42, 47, 9, 
	10, 12, 32, 34, 92, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 34, 
	92, 269, 525, 0, 11, 14, 255, 10, 
	12, 13, 10, 9, 10, 12, 32, 39, 
	92, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 39, 92, 269, 525, 0, 
	11, 14, 255, 10, 12, 13, 10, 9, 
	10, 12, 32, 42, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 42, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 42, 47, 269, 525, 0, 11, 14, 
	255, 10, 109, 120, 58, 83, 116, 121, 
	108, 101, 62, 10, 10, 34, 92, 12, 
	13, 10, 12, 13, 10, 39, 92, 12, 
	13, 10, 12, 13, 9, 10, 12, 32, 
	42, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 42, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 42, 47, 
	269, 525, 0, 11, 14, 255, 10, 91, 
	67, 68, 65, 84, 65, 91, 9, 10, 
	12, 32, 93, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 93, 269, 525, 
	0, 11, 14, 255, 9, 10, 12, 32, 
	93, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 62, 93, 269, 525, 0, 
	11, 14, 255, 10, 109, 120, 58, 83, 
	99, 114, 105, 112, 116, 62, 10, 9, 
	10, 12, 32, 34, 92, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 34, 
	92, 269, 525, 0, 11, 14, 255, 10, 
	12, 13, 10, 9, 10, 12, 32, 39, 
	92, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 39, 92, 269, 525, 0, 
	11, 14, 255, 10, 12, 13, 10, 45, 
	45, 9, 10, 12, 32, 45, 269, 525, 
	0, 11, 14, 255, 9, 10, 12, 32, 
	45, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 45, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 45, 62, 
	269, 525, 0, 11, 14, 255, 10, 120, 
	58, 83, 99, 116, 114, 105, 112, 116, 
	62, 121, 108, 101, 62, 10, 42, 42, 
	47, 109, 120, 58, 83, 116, 121, 108, 
	101, 62, 42, 42, 47, 109, 120, 58, 
	83, 99, 114, 105, 112, 116, 62, 32, 
	60, 9, 13, 32, 9, 13, 33, 109, 
	9, 10, 12, 32, 34, 39, 47, 269, 
	525, 0, 8, 14, 255, 9, 32, 9, 
	10, 12, 32, 34, 92, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 39, 
	92, 269, 525, 0, 11, 14, 255, 42, 
	10, 32, 47, 9, 13, 32, 9, 13, 
	42, 9, 10, 12, 32, 34, 39, 47, 
	60, 269, 525, 0, 8, 14, 255, 9, 
	32, 10, 34, 92, 12, 13, 10, 39, 
	92, 12, 13, 42, 47, 10, 12, 13, 
	33, 10, 32, 47, 9, 13, 32, 9, 
	13, 42, 47, 10, 12, 13, 9, 10, 
	12, 32, 34, 39, 47, 60, 269, 525, 
	0, 8, 14, 255, 9, 32, 9, 10, 
	12, 32, 34, 92, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 39, 92, 
	269, 525, 0, 11, 14, 255, 42, 47, 
	10, 9, 10, 12, 32, 34, 39, 47, 
	60, 269, 525, 0, 8, 14, 255, 9, 
	32, 10, 34, 92, 12, 13, 10, 39, 
	92, 12, 13, 42, 47, 10, 12, 13, 
	33, 47, 10, 9, 10, 12, 32, 34, 
	39, 60, 269, 525, 0, 8, 14, 255, 
	9, 32, 9, 10, 12, 32, 34, 92, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 39, 92, 269, 525, 0, 11, 
	14, 255, 33, 109, 10, 32, 47, 60, 
	9, 13, 32, 9, 13, 42, 47, 32, 
	47, 60, 9, 13, 32, 9, 13, 42, 
	47, 10, 12, 13, 47, 0
};

static const char _mxml_single_lengths[] = {
	0, 1, 1, 1, 1, 2, 1, 1, 
	1, 2, 1, 1, 1, 1, 1, 1, 
	1, 1, 1, 8, 8, 1, 1, 8, 
	8, 1, 1, 7, 7, 8, 1, 1, 
	1, 2, 3, 1, 3, 1, 7, 7, 
	8, 1, 1, 1, 1, 1, 1, 1, 
	1, 7, 7, 7, 8, 1, 1, 1, 
	2, 8, 8, 1, 1, 8, 8, 1, 
	1, 7, 7, 8, 1, 1, 1, 1, 
	1, 1, 1, 1, 1, 1, 1, 3, 
	1, 3, 1, 7, 7, 8, 1, 1, 
	1, 1, 1, 1, 1, 1, 7, 7, 
	7, 8, 1, 1, 1, 1, 1, 1, 
	1, 1, 1, 1, 1, 1, 8, 8, 
	1, 1, 8, 8, 1, 1, 1, 1, 
	7, 7, 7, 8, 1, 1, 1, 1, 
	2, 1, 1, 1, 1, 1, 1, 1, 
	1, 1, 1, 1, 2, 1, 1, 1, 
	1, 1, 1, 1, 1, 1, 1, 2, 
	1, 1, 1, 1, 1, 1, 1, 1, 
	1, 1, 2, 1, 2, 9, 2, 8, 
	8, 1, 1, 2, 1, 1, 10, 2, 
	3, 3, 2, 1, 1, 1, 2, 1, 
	2, 1, 10, 2, 8, 8, 1, 1, 
	1, 10, 2, 3, 3, 2, 1, 2, 
	1, 9, 2, 8, 8, 2, 1, 3, 
	1, 1, 1, 3, 1, 2, 1, 1
};

static const char _mxml_range_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 2, 2, 1, 0, 2, 
	2, 1, 0, 2, 2, 2, 0, 0, 
	0, 0, 1, 1, 1, 1, 2, 2, 
	2, 0, 0, 0, 0, 0, 0, 0, 
	0, 2, 2, 2, 2, 0, 0, 0, 
	0, 2, 2, 1, 0, 2, 2, 1, 
	0, 2, 2, 2, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 1, 
	1, 1, 1, 2, 2, 2, 0, 0, 
	0, 0, 0, 0, 0, 0, 2, 2, 
	2, 2, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 2, 2, 
	1, 0, 2, 2, 1, 0, 0, 0, 
	2, 2, 2, 2, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 1, 1, 0, 2, 0, 2, 
	2, 0, 0, 1, 1, 0, 2, 0, 
	1, 1, 0, 1, 0, 0, 1, 1, 
	0, 1, 2, 0, 2, 2, 0, 0, 
	0, 2, 0, 1, 1, 0, 1, 0, 
	0, 2, 0, 2, 2, 0, 0, 1, 
	1, 0, 0, 1, 1, 0, 1, 0
};

static const short _mxml_index_offsets[] = {
	0, 0, 2, 4, 6, 8, 11, 13, 
	15, 17, 20, 22, 24, 26, 28, 30, 
	32, 34, 36, 38, 49, 60, 63, 65, 
	76, 87, 90, 92, 102, 112, 123, 125, 
	127, 129, 132, 137, 140, 145, 148, 158, 
	168, 179, 181, 183, 185, 187, 189, 191, 
	193, 195, 205, 215, 225, 236, 238, 240, 
	242, 245, 256, 267, 270, 272, 283, 294, 
	297, 299, 309, 319, 330, 332, 334, 336, 
	338, 340, 342, 344, 346, 348, 350, 352, 
	357, 360, 365, 368, 378, 388, 399, 401, 
	403, 405, 407, 409, 411, 413, 415, 425, 
	435, 445, 456, 458, 460, 462, 464, 466, 
	468, 470, 472, 474, 476, 478, 480, 491, 
	502, 505, 507, 518, 529, 532, 534, 536, 
	538, 548, 558, 568, 579, 581, 583, 585, 
	587, 590, 592, 594, 596, 598, 600, 602, 
	604, 606, 608, 610, 612, 615, 617, 619, 
	621, 623, 625, 627, 629, 631, 633, 635, 
	638, 640, 642, 644, 646, 648, 650, 652, 
	654, 656, 658, 662, 665, 668, 680, 683, 
	694, 705, 707, 709, 713, 716, 718, 731, 
	734, 739, 744, 747, 750, 752, 754, 758, 
	761, 764, 767, 780, 783, 794, 805, 807, 
	809, 811, 824, 827, 832, 837, 840, 843, 
	846, 848, 860, 863, 874, 885, 888, 890, 
	895, 898, 900, 902, 907, 910, 913, 916
};

static const char _mxml_trans_targs[] = {
	2, 162, 3, 162, 4, 3, 5, 3, 
	5, 162, 3, 7, 162, 8, 162, 9, 
	162, 10, 15, 162, 11, 162, 12, 162, 
	13, 162, 14, 162, 162, 162, 16, 162, 
	17, 162, 18, 162, 162, 162, 19, 20, 
	20, 19, 165, 21, 22, 20, 19, 19, 
	165, 19, 20, 20, 19, 165, 21, 22, 
	20, 19, 19, 165, 165, 165, 19, 20, 
	165, 23, 24, 24, 23, 165, 25, 26, 
	24, 23, 23, 165, 23, 24, 24, 23, 
	165, 25, 26, 24, 23, 23, 165, 165, 
	165, 23, 24, 165, 27, 28, 28, 27, 
	29, 30, 28, 27, 27, 165, 27, 28, 
	28, 27, 29, 30, 28, 27, 27, 165, 
	27, 28, 28, 27, 29, 165, 30, 28, 
	27, 27, 165, 28, 165, 165, 0, 33, 
	32, 33, 171, 32, 174, 174, 35, 174, 
	34, 174, 174, 34, 174, 174, 37, 174, 
	36, 174, 174, 36, 38, 39, 39, 38, 
	40, 41, 39, 38, 38, 174, 38, 39, 
	39, 38, 40, 41, 39, 38, 38, 174, 
	38, 39, 39, 38, 40, 174, 41, 39, 
	38, 38, 174, 39, 174, 43, 174, 44, 
	174, 45, 174, 46, 174, 47, 174, 48, 
	174, 49, 174, 49, 50, 50, 49, 51, 
	53, 50, 49, 49, 174, 49, 50, 50, 
	49, 51, 53, 50, 49, 49, 174, 49, 
	50, 50, 49, 52, 53, 50, 49, 49, 
	174, 49, 50, 50, 49, 174, 52, 53, 
	50, 49, 49, 174, 50, 174, 174, 0, 
	56, 55, 56, 182, 55, 57, 58, 58, 
	57, 186, 59, 60, 58, 57, 57, 186, 
	57, 58, 58, 57, 186, 59, 60, 58, 
	57, 57, 186, 186, 186, 57, 58, 186, 
	61, 62, 62, 61, 186, 63, 64, 62, 
	61, 61, 186, 61, 62, 62, 61, 186, 
	63, 64, 62, 61, 61, 186, 186, 186, 
	61, 62, 186, 65, 66, 66, 65, 67, 
	68, 66, 65, 65, 186, 65, 66, 66, 
	65, 67, 68, 66, 65, 65, 186, 65, 
	66, 66, 65, 67, 186, 68, 66, 65, 
	65, 186, 66, 186, 70, 186, 71, 186, 
	72, 186, 73, 186, 74, 186, 75, 186, 
	76, 186, 77, 186, 186, 186, 186, 0, 
	193, 193, 80, 193, 79, 193, 193, 79, 
	193, 193, 82, 193, 81, 193, 193, 81, 
	83, 84, 84, 83, 85, 86, 84, 83, 
	83, 193, 83, 84, 84, 83, 85, 86, 
	84, 83, 83, 193, 83, 84, 84, 83, 
	85, 193, 86, 84, 83, 83, 193, 84, 
	193, 88, 193, 89, 193, 90, 193, 91, 
	193, 92, 193, 93, 193, 94, 193, 94, 
	95, 95, 94, 96, 98, 95, 94, 94, 
	193, 94, 95, 95, 94, 96, 98, 95, 
	94, 94, 193, 94, 95, 95, 94, 97, 
	98, 95, 94, 94, 193, 94, 95, 95, 
	94, 193, 97, 98, 95, 94, 94, 193, 
	95, 193, 100, 193, 101, 193, 102, 193, 
	103, 193, 104, 193, 105, 193, 106, 193, 
	107, 193, 108, 193, 193, 193, 193, 0, 
	110, 111, 111, 110, 201, 112, 113, 111, 
	110, 110, 201, 110, 111, 111, 110, 201, 
	112, 113, 111, 110, 110, 201, 201, 201, 
	110, 111, 201, 114, 115, 115, 114, 201, 
	116, 117, 115, 114, 114, 201, 114, 115, 
	115, 114, 201, 116, 117, 115, 114, 114, 
	201, 201, 201, 114, 115, 201, 119, 201, 
	120, 201, 120, 121, 121, 120, 122, 124, 
	121, 120, 120, 201, 120, 121, 121, 120, 
	122, 124, 121, 120, 120, 201, 120, 121, 
	121, 120, 123, 124, 121, 120, 120, 201, 
	120, 121, 121, 120, 123, 201, 124, 121, 
	120, 120, 201, 121, 201, 126, 201, 127, 
	201, 128, 201, 129, 134, 201, 130, 201, 
	131, 201, 132, 201, 133, 201, 201, 201, 
	135, 201, 136, 201, 137, 201, 201, 201, 
	201, 0, 140, 139, 140, 207, 139, 142, 
	207, 143, 207, 144, 207, 145, 207, 146, 
	207, 147, 207, 148, 207, 149, 207, 207, 
	207, 151, 150, 151, 211, 150, 153, 211, 
	154, 211, 155, 211, 156, 211, 157, 211, 
	158, 211, 159, 211, 160, 211, 161, 211, 
	211, 211, 163, 164, 163, 162, 163, 163, 
	162, 1, 6, 162, 166, 165, 165, 166, 
	167, 168, 169, 31, 170, 165, 165, 0, 
	166, 166, 165, 19, 20, 20, 19, 165, 
	21, 22, 20, 19, 19, 165, 23, 24, 
	24, 23, 165, 25, 26, 24, 23, 23, 
	165, 27, 165, 165, 165, 172, 173, 172, 
	171, 172, 172, 171, 32, 171, 175, 174, 
	174, 175, 176, 177, 178, 180, 54, 181, 
	174, 174, 0, 175, 175, 174, 174, 174, 
	35, 174, 34, 174, 174, 37, 174, 36, 
	38, 179, 174, 174, 174, 179, 42, 174, 
	174, 174, 183, 184, 183, 182, 183, 183, 
	182, 55, 185, 182, 182, 182, 185, 187, 
	186, 186, 187, 188, 189, 190, 191, 78, 
	192, 186, 186, 0, 187, 187, 186, 57, 
	58, 58, 57, 186, 59, 60, 58, 57, 
	57, 186, 61, 62, 62, 61, 186, 63, 
	64, 62, 61, 61, 186, 65, 186, 69, 
	186, 186, 186, 194, 193, 193, 194, 195, 
	196, 197, 199, 109, 200, 193, 193, 0, 
	194, 194, 193, 193, 193, 80, 193, 79, 
	193, 193, 82, 193, 81, 83, 198, 193, 
	193, 193, 198, 87, 99, 193, 193, 193, 
	202, 201, 201, 202, 203, 204, 205, 138, 
	206, 201, 201, 0, 202, 202, 201, 110, 
	111, 111, 110, 201, 112, 113, 111, 110, 
	110, 201, 114, 115, 115, 114, 201, 116, 
	117, 115, 114, 114, 201, 118, 125, 201, 
	201, 201, 208, 209, 210, 208, 207, 208, 
	208, 207, 139, 207, 141, 207, 212, 213, 
	215, 212, 211, 212, 212, 211, 150, 214, 
	211, 211, 211, 214, 152, 211, 162, 162, 
	162, 162, 162, 162, 162, 162, 162, 162, 
	162, 162, 162, 162, 162, 162, 162, 162, 
	165, 165, 165, 165, 165, 165, 165, 165, 
	165, 165, 165, 165, 171, 171, 174, 174, 
	174, 174, 174, 174, 174, 174, 174, 174, 
	174, 174, 174, 174, 174, 174, 174, 174, 
	174, 174, 182, 182, 186, 186, 186, 186, 
	186, 186, 186, 186, 186, 186, 186, 186, 
	186, 186, 186, 186, 186, 186, 186, 186, 
	186, 193, 193, 193, 193, 193, 193, 193, 
	193, 193, 193, 193, 193, 193, 193, 193, 
	193, 193, 193, 193, 193, 193, 193, 193, 
	193, 193, 193, 193, 193, 193, 193, 201, 
	201, 201, 201, 201, 201, 201, 201, 201, 
	201, 201, 201, 201, 201, 201, 201, 201, 
	201, 201, 201, 201, 201, 201, 201, 201, 
	201, 201, 201, 207, 207, 207, 207, 207, 
	207, 207, 207, 207, 207, 207, 211, 211, 
	211, 211, 211, 211, 211, 211, 211, 211, 
	211, 211, 162, 162, 165, 165, 165, 165, 
	165, 171, 171, 174, 174, 174, 174, 174, 
	174, 174, 182, 182, 182, 186, 186, 186, 
	186, 186, 186, 193, 193, 193, 193, 193, 
	193, 193, 201, 201, 201, 201, 201, 207, 
	207, 207, 211, 211, 211, 211, 0
};

static const short _mxml_trans_actions[] = {
	43, 161, 43, 161, 43, 43, 43, 43, 
	43, 235, 43, 0, 161, 0, 161, 0, 
	161, 0, 0, 161, 0, 161, 0, 161, 
	0, 161, 0, 161, 153, 161, 0, 161, 
	0, 161, 0, 161, 151, 161, 0, 0, 
	0, 0, 53, 0, 0, 0, 1, 1, 
	61, 169, 169, 169, 169, 288, 169, 169, 
	169, 284, 284, 61, 61, 61, 1, 0, 
	61, 0, 0, 0, 0, 53, 0, 0, 
	0, 1, 1, 61, 166, 166, 166, 166, 
	276, 166, 166, 166, 272, 272, 61, 61, 
	61, 1, 0, 61, 0, 0, 0, 0, 
	3, 0, 0, 3, 3, 61, 163, 163, 
	163, 163, 268, 163, 163, 268, 268, 61, 
	0, 0, 0, 0, 3, 51, 0, 0, 
	3, 3, 61, 0, 61, 172, 0, 11, 
	11, 11, 178, 11, 83, 73, 0, 83, 
	0, 83, 83, 0, 83, 73, 0, 83, 
	0, 83, 83, 0, 0, 0, 0, 0, 
	3, 0, 0, 3, 3, 83, 181, 181, 
	181, 181, 296, 181, 181, 296, 296, 83, 
	0, 0, 0, 0, 3, 71, 0, 0, 
	3, 3, 83, 0, 83, 0, 83, 0, 
	83, 0, 83, 0, 83, 0, 83, 0, 
	83, 1, 83, 0, 0, 0, 0, 1, 
	0, 0, 1, 1, 83, 184, 184, 184, 
	184, 300, 184, 184, 300, 300, 83, 0, 
	0, 0, 0, 1, 0, 0, 1, 1, 
	83, 0, 0, 0, 0, 73, 1, 0, 
	0, 1, 1, 83, 0, 83, 187, 0, 
	19, 19, 19, 193, 19, 0, 0, 0, 
	0, 97, 0, 0, 0, 1, 1, 105, 
	169, 169, 169, 169, 292, 169, 169, 169, 
	284, 284, 105, 105, 105, 1, 0, 105, 
	0, 0, 0, 0, 97, 0, 0, 0, 
	1, 1, 105, 166, 166, 166, 166, 280, 
	166, 166, 166, 272, 272, 105, 105, 105, 
	1, 0, 105, 0, 0, 0, 0, 3, 
	0, 0, 3, 3, 105, 163, 163, 163, 
	163, 268, 163, 163, 268, 268, 105, 0, 
	0, 0, 0, 3, 95, 0, 0, 3, 
	3, 105, 0, 105, 0, 105, 0, 105, 
	0, 105, 0, 105, 0, 105, 0, 105, 
	0, 105, 0, 105, 344, 105, 205, 0, 
	119, 109, 0, 119, 0, 119, 119, 0, 
	119, 109, 0, 119, 0, 119, 119, 0, 
	0, 0, 0, 0, 3, 0, 0, 3, 
	3, 119, 181, 181, 181, 181, 296, 181, 
	181, 296, 296, 119, 0, 0, 0, 0, 
	3, 107, 0, 0, 3, 3, 119, 0, 
	119, 0, 119, 0, 119, 0, 119, 0, 
	119, 0, 119, 0, 119, 1, 119, 0, 
	0, 0, 0, 1, 0, 0, 1, 1, 
	119, 184, 184, 184, 184, 300, 184, 184, 
	300, 300, 119, 0, 0, 0, 0, 1, 
	0, 0, 1, 1, 119, 0, 0, 0, 
	0, 109, 1, 0, 0, 1, 1, 119, 
	0, 119, 0, 119, 0, 119, 0, 119, 
	0, 119, 0, 119, 0, 119, 0, 119, 
	0, 119, 0, 119, 349, 119, 211, 0, 
	0, 0, 0, 0, 123, 0, 0, 0, 
	1, 1, 131, 202, 202, 202, 202, 320, 
	202, 202, 202, 316, 316, 131, 131, 131, 
	1, 0, 131, 0, 0, 0, 0, 123, 
	0, 0, 0, 1, 1, 131, 199, 199, 
	199, 199, 312, 199, 199, 199, 308, 308, 
	131, 131, 131, 1, 0, 131, 0, 131, 
	3, 131, 0, 0, 0, 0, 3, 0, 
	0, 3, 3, 131, 196, 196, 196, 196, 
	304, 196, 196, 304, 304, 131, 0, 0, 
	0, 0, 3, 0, 0, 3, 3, 131, 
	0, 0, 0, 0, 3, 121, 0, 0, 
	3, 3, 131, 0, 131, 0, 131, 0, 
	131, 0, 131, 0, 0, 131, 0, 131, 
	0, 131, 0, 131, 0, 131, 360, 131, 
	0, 131, 0, 131, 0, 131, 354, 131, 
	217, 0, 35, 35, 35, 226, 35, 0, 
	139, 0, 139, 0, 139, 0, 139, 0, 
	139, 0, 139, 0, 139, 0, 139, 223, 
	139, 39, 39, 39, 232, 39, 0, 149, 
	0, 149, 0, 149, 0, 149, 0, 149, 
	0, 149, 0, 149, 0, 149, 0, 149, 
	229, 149, 41, 265, 41, 155, 41, 41, 
	157, 43, 0, 159, 5, 172, 172, 5, 
	324, 324, 238, 7, 7, 175, 175, 0, 
	5, 5, 55, 0, 0, 0, 0, 53, 
	0, 0, 0, 1, 1, 59, 0, 0, 
	0, 0, 53, 0, 0, 0, 1, 1, 
	59, 3, 59, 172, 57, 9, 241, 9, 
	63, 9, 9, 65, 11, 67, 13, 187, 
	187, 13, 328, 328, 244, 244, 15, 15, 
	190, 190, 0, 13, 13, 75, 81, 73, 
	0, 81, 0, 81, 73, 0, 81, 0, 
	3, 3, 81, 77, 77, 0, 0, 81, 
	187, 79, 17, 247, 17, 85, 17, 17, 
	87, 19, 19, 91, 89, 89, 19, 21, 
	205, 205, 21, 332, 332, 250, 250, 23, 
	23, 208, 208, 0, 21, 21, 99, 0, 
	0, 0, 0, 97, 0, 0, 0, 1, 
	1, 103, 0, 0, 0, 0, 97, 0, 
	0, 0, 1, 1, 103, 3, 103, 0, 
	103, 205, 101, 25, 211, 211, 25, 336, 
	336, 253, 253, 27, 27, 214, 214, 0, 
	25, 25, 111, 117, 109, 0, 117, 0, 
	117, 109, 0, 117, 0, 3, 3, 117, 
	113, 113, 0, 0, 0, 117, 211, 115, 
	29, 217, 217, 29, 340, 340, 256, 31, 
	31, 220, 220, 0, 29, 29, 125, 0, 
	0, 0, 0, 123, 0, 0, 0, 1, 
	1, 129, 0, 0, 0, 0, 123, 0, 
	0, 0, 1, 1, 129, 0, 0, 129, 
	217, 127, 33, 259, 49, 33, 133, 33, 
	33, 135, 35, 137, 0, 137, 37, 262, 
	49, 37, 141, 37, 37, 143, 39, 39, 
	147, 145, 145, 39, 0, 147, 161, 161, 
	161, 161, 161, 161, 161, 161, 161, 161, 
	161, 161, 161, 161, 161, 161, 161, 161, 
	61, 61, 61, 61, 61, 61, 61, 61, 
	61, 61, 61, 61, 69, 69, 83, 83, 
	83, 83, 83, 83, 83, 83, 83, 83, 
	83, 83, 83, 83, 83, 83, 83, 83, 
	83, 83, 93, 93, 105, 105, 105, 105, 
	105, 105, 105, 105, 105, 105, 105, 105, 
	105, 105, 105, 105, 105, 105, 105, 105, 
	105, 119, 119, 119, 119, 119, 119, 119, 
	119, 119, 119, 119, 119, 119, 119, 119, 
	119, 119, 119, 119, 119, 119, 119, 119, 
	119, 119, 119, 119, 119, 119, 119, 131, 
	131, 131, 131, 131, 131, 131, 131, 131, 
	131, 131, 131, 131, 131, 131, 131, 131, 
	131, 131, 131, 131, 131, 131, 131, 131, 
	131, 131, 131, 139, 139, 139, 139, 139, 
	139, 139, 139, 139, 139, 139, 149, 149, 
	149, 149, 149, 149, 149, 149, 149, 149, 
	149, 149, 157, 159, 55, 59, 59, 59, 
	57, 65, 67, 75, 81, 81, 81, 77, 
	81, 79, 87, 91, 89, 99, 103, 103, 
	103, 103, 101, 111, 117, 117, 117, 113, 
	117, 115, 125, 129, 129, 129, 127, 135, 
	137, 137, 143, 147, 145, 147, 0
};

static const short _mxml_to_state_actions[] = {
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
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 45, 0, 0, 45, 0, 0, 
	0, 0, 0, 45, 0, 0, 45, 0, 
	0, 0, 0, 0, 0, 0, 45, 0, 
	0, 0, 45, 0, 0, 0, 0, 0, 
	0, 45, 0, 0, 0, 0, 0, 0, 
	0, 45, 0, 0, 0, 0, 0, 45, 
	0, 0, 0, 45, 0, 0, 0, 0
};

static const short _mxml_from_state_actions[] = {
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
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 47, 0, 0, 47, 0, 0, 
	0, 0, 0, 47, 0, 0, 47, 0, 
	0, 0, 0, 0, 0, 0, 47, 0, 
	0, 0, 47, 0, 0, 0, 0, 0, 
	0, 47, 0, 0, 0, 0, 0, 0, 
	0, 47, 0, 0, 0, 0, 0, 47, 
	0, 0, 0, 47, 0, 0, 0, 0
};

static const short _mxml_eof_trans[] = {
	0, 936, 936, 936, 936, 936, 936, 936, 
	936, 936, 936, 936, 936, 936, 936, 936, 
	936, 936, 936, 948, 948, 948, 948, 948, 
	948, 948, 948, 948, 948, 948, 948, 0, 
	950, 950, 970, 970, 970, 970, 970, 970, 
	970, 970, 970, 970, 970, 970, 970, 970, 
	970, 970, 970, 970, 970, 970, 0, 972, 
	972, 993, 993, 993, 993, 993, 993, 993, 
	993, 993, 993, 993, 993, 993, 993, 993, 
	993, 993, 993, 993, 993, 993, 0, 1023, 
	1023, 1023, 1023, 1023, 1023, 1023, 1023, 1023, 
	1023, 1023, 1023, 1023, 1023, 1023, 1023, 1023, 
	1023, 1023, 1023, 1023, 1023, 1023, 1023, 1023, 
	1023, 1023, 1023, 1023, 1023, 0, 1051, 1051, 
	1051, 1051, 1051, 1051, 1051, 1051, 1051, 1051, 
	1051, 1051, 1051, 1051, 1051, 1051, 1051, 1051, 
	1051, 1051, 1051, 1051, 1051, 1051, 1051, 1051, 
	1051, 1051, 0, 1062, 1062, 1062, 1062, 1062, 
	1062, 1062, 1062, 1062, 1062, 1062, 1074, 1074, 
	1074, 1074, 1074, 1074, 1074, 1074, 1074, 1074, 
	1074, 1074, 0, 1075, 1076, 0, 1077, 1080, 
	1080, 1080, 1081, 0, 1082, 1083, 0, 1084, 
	1089, 1089, 1089, 1088, 1089, 1090, 0, 1091, 
	1092, 1093, 0, 1094, 1098, 1098, 1098, 1098, 
	1099, 0, 1100, 1105, 1105, 1105, 1104, 1105, 
	1106, 0, 1107, 1110, 1110, 1110, 1111, 0, 
	1112, 1114, 1114, 0, 1115, 1118, 1117, 1118
};

static const int mxml_start = 162;
static const int mxml_first_final = 162;
static const int mxml_error = 0;

static const int mxml_en_css_line = 165;
static const int mxml_en_css_entity = 171;
static const int mxml_en_as_line = 174;
static const int mxml_en_as_entity = 182;
static const int mxml_en_mxml_css_line = 186;
static const int mxml_en_mxml_as_line = 193;
static const int mxml_en_mxml_line = 201;
static const int mxml_en_mxml_css_entity = 207;
static const int mxml_en_mxml_as_entity = 211;
static const int mxml_en_mxml_entity = 162;


#line 34 "mxml.rl.tmp"


#line 112 "mxml.rl.tmp"


#line 316 "mxml.rl.tmp"


/************************* Required for every parser *************************/

/* Parses a string buffer with MXML markup.
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
void parse_mxml(char *buffer, int length, int count,
                void (*callback) (const char *lang, const char *entity, int s,
                                  int e, void *udata),
                void *userdata
  ) {
  init

  
#line 816 "mxml.h"
	{
	cs = mxml_start;
	top = 0;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 339 "mxml.rl.tmp"
  cs = (count) ? mxml_en_mxml_line : mxml_en_mxml_entity;
  
#line 828 "mxml.h"
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
	_acts = _mxml_actions + _mxml_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 48:
#line 1 "NONE"
	{ts = p;}
	break;
#line 850 "mxml.h"
		}
	}

	_widec = (*p);
	_klen = _mxml_cond_lengths[cs];
	_keys = _mxml_cond_keys + (_mxml_cond_offsets[cs]*2);
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
				switch ( _mxml_cond_spaces[_mxml_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _mxml_trans_keys + _mxml_key_offsets[cs];
	_trans = _mxml_index_offsets[cs];

	_klen = _mxml_single_lengths[cs];
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

	_klen = _mxml_range_lengths[cs];
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
	cs = _mxml_trans_targs[_trans];

	if ( _mxml_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _mxml_actions + _mxml_trans_actions[_trans];
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
#line 65 "common.rl"
	{
  if (!line_contains_code && !whole_line_comment) seen = 0;
}
	break;
	case 3:
#line 43 "mxml.rl.tmp"
	{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }
	break;
	case 4:
#line 61 "mxml.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 70 "mxml.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 6:
#line 80 "mxml.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 91 "mxml.rl.tmp"
	{ entity = CSS_SPACE; }
	break;
	case 8:
#line 94 "mxml.rl.tmp"
	{ entity = NEWLINE;   }
	break;
	case 9:
#line 95 "mxml.rl.tmp"
	{ entity = CSS_ANY;   }
	break;
	case 10:
#line 107 "mxml.rl.tmp"
	{ entity = CSS_SPACE;   }
	break;
	case 11:
#line 108 "mxml.rl.tmp"
	{ entity = CSS_COMMENT; }
	break;
	case 12:
#line 121 "mxml.rl.tmp"
	{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }
	break;
	case 13:
#line 140 "mxml.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 14:
#line 151 "mxml.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 15:
#line 160 "mxml.rl.tmp"
	{ entity = AS_SPACE; }
	break;
	case 16:
#line 163 "mxml.rl.tmp"
	{ entity = NEWLINE;  }
	break;
	case 17:
#line 164 "mxml.rl.tmp"
	{ entity = AS_ANY;   }
	break;
	case 18:
#line 178 "mxml.rl.tmp"
	{ entity = AS_SPACE;   }
	break;
	case 19:
#line 179 "mxml.rl.tmp"
	{ entity = AS_COMMENT; }
	break;
	case 20:
#line 187 "mxml.rl.tmp"
	{
    switch(entity) {
    case MXML_SPACE:
      ls
      break;
    case MXML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MXML_LANG)
      break;
    case NEWLINE:
      std_newline(MXML_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(MXML_LANG)
    }
  }
	break;
	case 21:
#line 208 "mxml.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 22:
#line 217 "mxml.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 23:
#line 227 "mxml.rl.tmp"
	{ entity = INTERNAL_NL; }
	break;
	case 24:
#line 242 "mxml.rl.tmp"
	{ p = ts; {cs = stack[--top]; goto _again;} }
	break;
	case 25:
#line 244 "mxml.rl.tmp"
	{ entity = CSS_SPACE; }
	break;
	case 26:
#line 247 "mxml.rl.tmp"
	{ entity = NEWLINE;   }
	break;
	case 27:
#line 248 "mxml.rl.tmp"
	{ entity = CSS_ANY;   }
	break;
	case 28:
#line 254 "mxml.rl.tmp"
	{ p = ts; {cs = stack[--top]; goto _again;} }
	break;
	case 29:
#line 256 "mxml.rl.tmp"
	{ entity = AS_SPACE; }
	break;
	case 30:
#line 259 "mxml.rl.tmp"
	{ entity = NEWLINE;  }
	break;
	case 31:
#line 260 "mxml.rl.tmp"
	{ entity = AS_ANY;   }
	break;
	case 32:
#line 264 "mxml.rl.tmp"
	{ entity = CHECK_BLANK_ENTRY; }
	break;
	case 33:
#line 265 "mxml.rl.tmp"
	{ saw(CSS_LANG); }
	break;
	case 34:
#line 266 "mxml.rl.tmp"
	{ entity = CHECK_BLANK_ENTRY; }
	break;
	case 35:
#line 267 "mxml.rl.tmp"
	{ saw(AS_LANG); }
	break;
	case 36:
#line 269 "mxml.rl.tmp"
	{ entity = MXML_SPACE; }
	break;
	case 37:
#line 272 "mxml.rl.tmp"
	{ entity = NEWLINE;    }
	break;
	case 38:
#line 273 "mxml.rl.tmp"
	{ entity = MXML_ANY;   }
	break;
	case 39:
#line 285 "mxml.rl.tmp"
	{ {cs = stack[--top]; goto _again;} }
	break;
	case 40:
#line 287 "mxml.rl.tmp"
	{ entity = CSS_SPACE;   }
	break;
	case 41:
#line 288 "mxml.rl.tmp"
	{ entity = CSS_COMMENT; }
	break;
	case 42:
#line 296 "mxml.rl.tmp"
	{ {cs = stack[--top]; goto _again;} }
	break;
	case 43:
#line 298 "mxml.rl.tmp"
	{ entity = AS_SPACE;   }
	break;
	case 44:
#line 299 "mxml.rl.tmp"
	{ entity = AS_COMMENT; }
	break;
	case 45:
#line 311 "mxml.rl.tmp"
	{ entity = MXML_SPACE;   }
	break;
	case 46:
#line 312 "mxml.rl.tmp"
	{ entity = MXML_COMMENT; }
	break;
	case 49:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 50:
#line 92 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 51:
#line 93 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 52:
#line 43 "mxml.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }}
	break;
	case 53:
#line 43 "mxml.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }}
	break;
	case 54:
#line 43 "mxml.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }}
	break;
	case 55:
#line 43 "mxml.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }}
	break;
	case 56:
#line 43 "mxml.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }}
	break;
	case 57:
#line 43 "mxml.rl.tmp"
	{{p = ((te))-1;}{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }}
	break;
	case 58:
#line 100 "mxml.rl.tmp"
	{te = p+1;{
    callback(CSS_LANG, css_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 59:
#line 110 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 60:
#line 100 "mxml.rl.tmp"
	{te = p;p--;{
    callback(CSS_LANG, css_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 61:
#line 110 "mxml.rl.tmp"
	{te = p;p--;}
	break;
	case 62:
#line 110 "mxml.rl.tmp"
	{{p = ((te))-1;}}
	break;
	case 63:
#line 161 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 64:
#line 162 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 65:
#line 121 "mxml.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }}
	break;
	case 66:
#line 121 "mxml.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }}
	break;
	case 67:
#line 121 "mxml.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }}
	break;
	case 68:
#line 161 "mxml.rl.tmp"
	{te = p;p--;}
	break;
	case 69:
#line 121 "mxml.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }}
	break;
	case 70:
#line 121 "mxml.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }}
	break;
	case 71:
#line 121 "mxml.rl.tmp"
	{{p = ((te))-1;}{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }}
	break;
	case 72:
#line 169 "mxml.rl.tmp"
	{te = p+1;{
    callback(AS_LANG, as_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 73:
#line 181 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 74:
#line 169 "mxml.rl.tmp"
	{te = p;p--;{
    callback(AS_LANG, as_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 75:
#line 169 "mxml.rl.tmp"
	{te = p;p--;{
    callback(AS_LANG, as_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 76:
#line 181 "mxml.rl.tmp"
	{te = p;p--;}
	break;
	case 77:
#line 181 "mxml.rl.tmp"
	{{p = ((te))-1;}}
	break;
	case 78:
#line 242 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 79:
#line 245 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 80:
#line 246 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 81:
#line 43 "mxml.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }}
	break;
	case 82:
#line 43 "mxml.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }}
	break;
	case 83:
#line 43 "mxml.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }}
	break;
	case 84:
#line 43 "mxml.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }}
	break;
	case 85:
#line 43 "mxml.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }}
	break;
	case 86:
#line 43 "mxml.rl.tmp"
	{{p = ((te))-1;}{
    switch(entity) {
    case CSS_SPACE:
      ls
      break;
    case CSS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CSS_LANG)
      break;
    case NEWLINE:
      std_newline(CSS_LANG)
    }
  }}
	break;
	case 87:
#line 254 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 88:
#line 257 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 89:
#line 258 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 90:
#line 121 "mxml.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }}
	break;
	case 91:
#line 121 "mxml.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }}
	break;
	case 92:
#line 121 "mxml.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }}
	break;
	case 93:
#line 257 "mxml.rl.tmp"
	{te = p;p--;}
	break;
	case 94:
#line 121 "mxml.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }}
	break;
	case 95:
#line 121 "mxml.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }}
	break;
	case 96:
#line 121 "mxml.rl.tmp"
	{{p = ((te))-1;}{
    switch(entity) {
    case AS_SPACE:
      ls
      break;
    case AS_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(AS_LANG)
      break;
    case NEWLINE:
      std_newline(AS_LANG)
    }
  }}
	break;
	case 97:
#line 265 "mxml.rl.tmp"
	{te = p+1;{ {stack[top++] = cs; cs = 186;goto _again;} }}
	break;
	case 98:
#line 267 "mxml.rl.tmp"
	{te = p+1;{ {stack[top++] = cs; cs = 193;goto _again;} }}
	break;
	case 99:
#line 270 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 100:
#line 271 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 101:
#line 187 "mxml.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case MXML_SPACE:
      ls
      break;
    case MXML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MXML_LANG)
      break;
    case NEWLINE:
      std_newline(MXML_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(MXML_LANG)
    }
  }}
	break;
	case 102:
#line 187 "mxml.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case MXML_SPACE:
      ls
      break;
    case MXML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MXML_LANG)
      break;
    case NEWLINE:
      std_newline(MXML_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(MXML_LANG)
    }
  }}
	break;
	case 103:
#line 187 "mxml.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case MXML_SPACE:
      ls
      break;
    case MXML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MXML_LANG)
      break;
    case NEWLINE:
      std_newline(MXML_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(MXML_LANG)
    }
  }}
	break;
	case 104:
#line 187 "mxml.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case MXML_SPACE:
      ls
      break;
    case MXML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MXML_LANG)
      break;
    case NEWLINE:
      std_newline(MXML_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(MXML_LANG)
    }
  }}
	break;
	case 105:
#line 187 "mxml.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case MXML_SPACE:
      ls
      break;
    case MXML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MXML_LANG)
      break;
    case NEWLINE:
      std_newline(MXML_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(MXML_LANG)
    }
  }}
	break;
	case 106:
#line 187 "mxml.rl.tmp"
	{{p = ((te))-1;}{
    switch(entity) {
    case MXML_SPACE:
      ls
      break;
    case MXML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MXML_LANG)
      break;
    case NEWLINE:
      std_newline(MXML_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(MXML_LANG)
    }
  }}
	break;
	case 107:
#line 285 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 108:
#line 100 "mxml.rl.tmp"
	{te = p+1;{
    callback(CSS_LANG, css_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 109:
#line 290 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 110:
#line 100 "mxml.rl.tmp"
	{te = p;p--;{
    callback(CSS_LANG, css_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 111:
#line 290 "mxml.rl.tmp"
	{te = p;p--;}
	break;
	case 112:
#line 290 "mxml.rl.tmp"
	{{p = ((te))-1;}}
	break;
	case 113:
#line 296 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 114:
#line 169 "mxml.rl.tmp"
	{te = p+1;{
    callback(AS_LANG, as_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 115:
#line 301 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 116:
#line 169 "mxml.rl.tmp"
	{te = p;p--;{
    callback(AS_LANG, as_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 117:
#line 169 "mxml.rl.tmp"
	{te = p;p--;{
    callback(AS_LANG, as_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 118:
#line 301 "mxml.rl.tmp"
	{te = p;p--;}
	break;
	case 119:
#line 301 "mxml.rl.tmp"
	{{p = ((te))-1;}}
	break;
	case 120:
#line 308 "mxml.rl.tmp"
	{te = p+1;{ {stack[top++] = cs; cs = 207;goto _again;} }}
	break;
	case 121:
#line 309 "mxml.rl.tmp"
	{te = p+1;{ {stack[top++] = cs; cs = 211;goto _again;}  }}
	break;
	case 122:
#line 278 "mxml.rl.tmp"
	{te = p+1;{
    callback(MXML_LANG, mxml_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 123:
#line 314 "mxml.rl.tmp"
	{te = p+1;}
	break;
	case 124:
#line 278 "mxml.rl.tmp"
	{te = p;p--;{
    callback(MXML_LANG, mxml_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 125:
#line 314 "mxml.rl.tmp"
	{te = p;p--;}
	break;
	case 126:
#line 314 "mxml.rl.tmp"
	{{p = ((te))-1;}}
	break;
#line 1963 "mxml.h"
		}
	}

_again:
	_acts = _mxml_actions + _mxml_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 47:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 1976 "mxml.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _mxml_eof_trans[cs] > 0 ) {
		_trans = _mxml_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 341 "mxml.rl.tmp"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(MXML_LANG) }
}

#endif

/*****************************************************************************/
