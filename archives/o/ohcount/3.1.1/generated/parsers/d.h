
#line 1 "d.rl"
// d.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_D_PARSER_H
#define OHCOUNT_D_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *D_LANG = LANG_DMD;

// the languages entities
const char *d_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  D_SPACE = 0, D_COMMENT, D_STRING, D_ANY
};

/*****************************************************************************/


#line 28 "d.h"
static const char _d_actions[] = {
	0, 1, 0, 1, 1, 1, 12, 1, 
	13, 1, 15, 1, 16, 1, 17, 1, 
	18, 1, 20, 1, 21, 1, 24, 1, 
	25, 1, 26, 1, 27, 1, 28, 1, 
	29, 1, 31, 1, 32, 1, 33, 1, 
	34, 1, 35, 1, 36, 2, 1, 20, 
	2, 4, 1, 2, 4, 16, 2, 5, 
	1, 2, 5, 16, 2, 6, 2, 2, 
	7, 2, 2, 8, 2, 2, 9, 2, 
	2, 10, 2, 2, 11, 2, 2, 13, 
	22, 2, 14, 23, 2, 16, 30, 2, 
	19, 1, 2, 19, 16, 3, 6, 2, 
	1, 3, 6, 2, 25, 3, 7, 2, 
	1, 3, 8, 2, 1, 3, 9, 2, 
	0, 3, 9, 2, 21, 3, 10, 2, 
	0, 3, 10, 2, 21, 3, 11, 2, 
	0, 3, 11, 2, 21, 3, 19, 0, 
	14, 3, 19, 3, 14, 3, 19, 3, 
	16, 4, 19, 6, 2, 1
};

static const char _d_cond_offsets[] = {
	0, 0, 0, 0, 1, 2, 3, 5, 
	5, 5, 6, 6, 6, 6, 6, 7, 
	7, 7, 7, 8, 9, 10, 10, 12, 
	14, 16, 16, 18, 21, 21, 21, 22, 
	22, 22, 22, 22, 22, 22, 22, 22, 
	23, 23, 24, 24, 24, 24, 24, 24, 
	25, 25, 25, 25
};

static const char _d_cond_lengths[] = {
	0, 0, 0, 1, 1, 1, 2, 0, 
	0, 1, 0, 0, 0, 0, 1, 0, 
	0, 0, 1, 1, 1, 0, 2, 2, 
	2, 0, 2, 3, 0, 0, 1, 0, 
	0, 0, 0, 0, 0, 0, 0, 1, 
	0, 1, 0, 0, 0, 0, 0, 1, 
	0, 0, 0, 0
};

static const short _d_cond_keys[] = {
	43, 43, 43, 43, 43, 43, 43, 43, 
	47, 47, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 43, 43, 
	13, 13, 43, 43, 13, 13, 43, 43, 
	13, 13, 43, 43, 13, 13, 43, 43, 
	47, 47, 13, 13, 13, 13, 13, 13, 
	13, 13, 0
};

static const char _d_cond_spaces[] = {
	2, 2, 2, 2, 2, 0, 0, 0, 
	0, 0, 0, 1, 0, 1, 0, 1, 
	0, 1, 0, 1, 1, 0, 0, 0, 
	0, 0
};

static const short _d_key_offsets[] = {
	0, 0, 1, 3, 10, 17, 24, 34, 
	35, 39, 47, 51, 52, 57, 61, 69, 
	73, 74, 79, 90, 101, 113, 114, 129, 
	144, 159, 160, 175, 193, 194, 198, 206, 
	210, 211, 216, 217, 221, 224, 227, 231, 
	238, 241, 255, 257, 261, 265, 268, 274, 
	285, 291, 297, 301
};

static const short _d_trans_keys[] = {
	42, 42, 47, 47, 1323, 1579, 0, 42, 
	44, 255, 47, 1323, 1579, 0, 42, 44, 
	255, 47, 1323, 1579, 0, 42, 44, 255, 
	1323, 1327, 1579, 1583, 0, 42, 44, 46, 
	48, 255, 10, 9, 32, 34, 92, 10, 
	12, 269, 525, 0, 11, 14, 255, 9, 
	32, 34, 92, 10, 9, 10, 32, 34, 
	92, 9, 32, 39, 92, 10, 12, 269, 
	525, 0, 11, 14, 255, 9, 32, 39, 
	92, 10, 9, 10, 32, 39, 92, 9, 
	10, 12, 32, 42, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 42, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 42, 47, 269, 525, 0, 11, 14, 
	255, 10, 9, 10, 12, 32, 47, 269, 
	525, 811, 1067, 0, 8, 14, 42, 44, 
	255, 9, 10, 12, 32, 47, 269, 525, 
	811, 1067, 0, 8, 14, 42, 44, 255, 
	9, 10, 12, 32, 47, 269, 525, 811, 
	1067, 0, 8, 14, 42, 44, 255, 10, 
	9, 10, 12, 32, 47, 269, 525, 811, 
	1067, 0, 8, 14, 42, 44, 255, 9, 
	10, 12, 32, 269, 525, 811, 815, 1067, 
	1071, 0, 8, 14, 42, 44, 46, 48, 
	255, 10, 9, 32, 92, 96, 10, 12, 
	269, 525, 0, 11, 14, 255, 9, 32, 
	92, 96, 10, 9, 10, 32, 92, 96, 
	10, 32, 47, 9, 13, 32, 9, 13, 
	42, 43, 47, 10, 92, 12, 13, 92, 
	269, 525, 0, 12, 14, 255, 92, 12, 
	13, 9, 10, 12, 32, 34, 39, 47, 
	96, 269, 525, 0, 8, 14, 255, 9, 
	32, 9, 32, 34, 92, 9, 32, 39, 
	92, 42, 43, 47, 9, 10, 32, 92, 
	12, 13, 9, 10, 12, 32, 92, 269, 
	525, 0, 11, 14, 255, 9, 10, 32, 
	92, 12, 13, 9, 10, 32, 92, 12, 
	13, 9, 32, 92, 96, 10, 0
};

static const char _d_single_lengths[] = {
	0, 1, 2, 3, 3, 3, 4, 1, 
	4, 4, 4, 1, 5, 4, 4, 4, 
	1, 5, 7, 7, 8, 1, 9, 9, 
	9, 1, 9, 10, 1, 4, 4, 4, 
	1, 5, 1, 2, 1, 3, 2, 3, 
	1, 10, 2, 4, 4, 3, 4, 7, 
	4, 4, 4, 1
};

static const char _d_range_lengths[] = {
	0, 0, 0, 2, 2, 2, 3, 0, 
	0, 2, 0, 0, 0, 0, 2, 0, 
	0, 0, 2, 2, 2, 0, 3, 3, 
	3, 0, 3, 4, 0, 0, 2, 0, 
	0, 0, 0, 1, 1, 0, 1, 2, 
	1, 2, 0, 0, 0, 0, 1, 2, 
	1, 1, 0, 0
};

static const short _d_index_offsets[] = {
	0, 0, 2, 5, 11, 17, 23, 31, 
	33, 38, 45, 50, 52, 58, 63, 70, 
	75, 77, 83, 93, 103, 114, 116, 129, 
	142, 155, 157, 170, 185, 187, 192, 199, 
	204, 206, 212, 214, 218, 221, 225, 229, 
	235, 238, 251, 254, 259, 264, 268, 274, 
	284, 290, 296, 301
};

static const char _d_indicies[] = {
	2, 1, 2, 3, 1, 5, 6, 7, 
	4, 4, 0, 5, 8, 9, 4, 4, 
	0, 10, 6, 7, 4, 4, 0, 6, 
	10, 7, 3, 4, 4, 4, 0, 12, 
	11, 15, 15, 16, 17, 14, 18, 18, 
	19, 20, 14, 14, 13, 22, 22, 23, 
	24, 21, 18, 13, 22, 25, 22, 23, 
	24, 21, 27, 27, 16, 28, 26, 29, 
	29, 30, 31, 26, 26, 13, 33, 33, 
	34, 35, 32, 29, 13, 33, 36, 33, 
	34, 35, 32, 38, 39, 39, 38, 40, 
	41, 39, 37, 37, 13, 43, 44, 44, 
	43, 45, 46, 44, 42, 42, 13, 38, 
	39, 39, 38, 40, 47, 41, 39, 37, 
	37, 13, 39, 13, 49, 50, 50, 49, 
	51, 52, 50, 53, 54, 48, 48, 48, 
	13, 56, 57, 57, 56, 58, 59, 57, 
	60, 61, 55, 55, 55, 13, 49, 50, 
	50, 49, 51, 52, 50, 62, 63, 48, 
	48, 48, 13, 50, 13, 49, 50, 50, 
	49, 64, 52, 50, 53, 54, 48, 48, 
	48, 13, 49, 50, 50, 49, 52, 50, 
	53, 64, 54, 65, 48, 48, 48, 48, 
	13, 67, 66, 69, 69, 70, 16, 68, 
	71, 71, 72, 73, 68, 68, 13, 75, 
	75, 76, 77, 74, 71, 13, 75, 78, 
	75, 76, 77, 74, 79, 80, 82, 83, 
	82, 81, 82, 82, 84, 1, 4, 12, 
	85, 86, 87, 86, 12, 87, 88, 89, 
	12, 12, 86, 87, 86, 12, 91, 79, 
	79, 91, 92, 93, 94, 95, 96, 97, 
	90, 90, 80, 91, 91, 98, 15, 15, 
	16, 17, 14, 27, 27, 16, 28, 26, 
	37, 48, 100, 99, 102, 101, 102, 103, 
	101, 100, 102, 67, 67, 102, 103, 104, 
	105, 100, 100, 101, 108, 106, 108, 109, 
	106, 107, 108, 67, 108, 109, 106, 107, 
	69, 69, 70, 16, 68, 79, 110, 0
};

static const char _d_trans_targs[] = {
	35, 1, 2, 35, 3, 4, 5, 6, 
	5, 6, 4, 35, 38, 41, 8, 8, 
	41, 9, 10, 11, 12, 8, 8, 41, 
	9, 10, 13, 13, 14, 15, 16, 17, 
	13, 13, 41, 14, 15, 18, 18, 19, 
	20, 21, 18, 18, 19, 20, 21, 41, 
	22, 22, 23, 24, 25, 26, 27, 22, 
	22, 23, 24, 25, 26, 27, 26, 27, 
	24, 41, 41, 48, 29, 29, 30, 31, 
	32, 33, 29, 29, 30, 41, 31, 41, 
	0, 35, 36, 37, 35, 35, 35, 39, 
	7, 40, 41, 42, 43, 44, 45, 50, 
	34, 51, 41, 41, 46, 41, 46, 47, 
	28, 49, 41, 46, 46, 47, 41
};

static const char _d_trans_actions[] = {
	43, 11, 11, 84, 11, 11, 11, 11, 
	51, 51, 57, 41, 11, 31, 1, 0, 
	19, 0, 0, 0, 0, 117, 72, 121, 
	72, 117, 1, 0, 0, 0, 0, 0, 
	109, 69, 113, 69, 109, 3, 0, 0, 
	3, 0, 101, 63, 63, 101, 63, 17, 
	3, 0, 0, 3, 0, 3, 3, 105, 
	66, 66, 105, 66, 105, 105, 48, 48, 
	54, 45, 29, 0, 1, 0, 0, 0, 
	0, 0, 125, 75, 75, 129, 125, 78, 
	0, 33, 9, 141, 35, 39, 37, 90, 
	11, 11, 81, 5, 133, 133, 137, 133, 
	7, 7, 21, 27, 3, 23, 0, 87, 
	0, 0, 97, 93, 60, 145, 25
};

static const char _d_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 13, 0, 0, 0, 0, 
	0, 13, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0
};

static const char _d_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 15, 0, 0, 0, 0, 
	0, 15, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0
};

static const short _d_eof_trans[] = {
	0, 1, 1, 1, 1, 1, 1, 12, 
	14, 14, 14, 14, 14, 14, 14, 14, 
	14, 14, 14, 14, 14, 14, 14, 14, 
	14, 14, 14, 14, 67, 14, 14, 14, 
	14, 14, 0, 0, 85, 86, 87, 87, 
	87, 0, 99, 100, 100, 100, 102, 102, 
	107, 107, 100, 111
};

static const int d_start = 35;
static const int d_first_final = 35;
static const int d_error = 0;

static const int d_en_d_line = 41;
static const int d_en_d_entity = 35;


#line 145 "d.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with D code.
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
void parse_d(char *buffer, int length, int count,
             void (*callback) (const char *lang, const char *entity, int s,
                               int e, void *udata),
             void *userdata
  ) {
  init

  int nest_count = 0;

  
#line 308 "d.h"
	{
	cs = d_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 170 "d.rl"
  cs = (count) ? d_en_d_line : d_en_d_entity;
  
#line 319 "d.h"
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
	_acts = _d_actions + _d_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 18:
#line 1 "NONE"
	{ts = p;}
	break;
#line 341 "d.h"
		}
	}

	_widec = (*p);
	_klen = _d_cond_lengths[cs];
	_keys = _d_cond_keys + (_d_cond_offsets[cs]*2);
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
				switch ( _d_cond_spaces[_d_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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
#line 78 "d.rl"
 nest_count == 0  ) _widec += 256;
		break;
	}
	case 2: {
		_widec = (short)(1280 + ((*p) - 0));
		if ( 
#line 135 "d.rl"
 nest_count == 0  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _d_trans_keys + _d_key_offsets[cs];
	_trans = _d_index_offsets[cs];

	_klen = _d_single_lengths[cs];
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

	_klen = _d_range_lengths[cs];
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
	_trans = _d_indicies[_trans];
_eof_trans:
	cs = _d_trans_targs[_trans];

	if ( _d_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _d_actions + _d_trans_actions[_trans];
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
#line 31 "d.rl"
	{
    switch(entity) {
    case D_SPACE:
      ls
      break;
    case D_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(D_LANG)
      break;
    case NEWLINE:
      std_newline(D_LANG)
    }
  }
	break;
	case 3:
#line 47 "d.rl"
	{ nest_count = 0; }
	break;
	case 4:
#line 48 "d.rl"
	{ nest_count++; }
	break;
	case 5:
#line 49 "d.rl"
	{ nest_count--; }
	break;
	case 6:
#line 53 "d.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 61 "d.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 8:
#line 69 "d.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 9:
#line 83 "d.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 10:
#line 93 "d.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 11:
#line 103 "d.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 12:
#line 114 "d.rl"
	{ entity = D_SPACE; }
	break;
	case 13:
#line 117 "d.rl"
	{ entity = NEWLINE; }
	break;
	case 14:
#line 118 "d.rl"
	{ entity = D_ANY;   }
	break;
	case 15:
#line 140 "d.rl"
	{ entity = D_SPACE;   }
	break;
	case 16:
#line 141 "d.rl"
	{ entity = D_COMMENT; }
	break;
	case 19:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 20:
#line 115 "d.rl"
	{te = p+1;}
	break;
	case 21:
#line 116 "d.rl"
	{te = p+1;}
	break;
	case 22:
#line 31 "d.rl"
	{te = p+1;{
    switch(entity) {
    case D_SPACE:
      ls
      break;
    case D_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(D_LANG)
      break;
    case NEWLINE:
      std_newline(D_LANG)
    }
  }}
	break;
	case 23:
#line 31 "d.rl"
	{te = p+1;{
    switch(entity) {
    case D_SPACE:
      ls
      break;
    case D_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(D_LANG)
      break;
    case NEWLINE:
      std_newline(D_LANG)
    }
  }}
	break;
	case 24:
#line 31 "d.rl"
	{te = p;p--;{
    switch(entity) {
    case D_SPACE:
      ls
      break;
    case D_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(D_LANG)
      break;
    case NEWLINE:
      std_newline(D_LANG)
    }
  }}
	break;
	case 25:
#line 115 "d.rl"
	{te = p;p--;}
	break;
	case 26:
#line 31 "d.rl"
	{te = p;p--;{
    switch(entity) {
    case D_SPACE:
      ls
      break;
    case D_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(D_LANG)
      break;
    case NEWLINE:
      std_newline(D_LANG)
    }
  }}
	break;
	case 27:
#line 31 "d.rl"
	{te = p;p--;{
    switch(entity) {
    case D_SPACE:
      ls
      break;
    case D_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(D_LANG)
      break;
    case NEWLINE:
      std_newline(D_LANG)
    }
  }}
	break;
	case 28:
#line 115 "d.rl"
	{{p = ((te))-1;}}
	break;
	case 29:
#line 31 "d.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case D_SPACE:
      ls
      break;
    case D_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(D_LANG)
      break;
    case NEWLINE:
      std_newline(D_LANG)
    }
  }}
	break;
	case 30:
#line 123 "d.rl"
	{te = p+1;{
    callback(D_LANG, d_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 31:
#line 143 "d.rl"
	{te = p+1;}
	break;
	case 32:
#line 123 "d.rl"
	{te = p;p--;{
    callback(D_LANG, d_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 33:
#line 123 "d.rl"
	{te = p;p--;{
    callback(D_LANG, d_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 34:
#line 143 "d.rl"
	{te = p;p--;}
	break;
	case 35:
#line 123 "d.rl"
	{{p = ((te))-1;}{
    callback(D_LANG, d_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 36:
#line 143 "d.rl"
	{{p = ((te))-1;}}
	break;
#line 706 "d.h"
		}
	}

_again:
	_acts = _d_actions + _d_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 17:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 719 "d.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _d_eof_trans[cs] > 0 ) {
		_trans = _d_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 172 "d.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(D_LANG) }
}

#endif

/*****************************************************************************/
