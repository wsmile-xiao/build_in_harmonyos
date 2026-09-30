
#line 1 "ruby.rl"
// ruby.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net

/************************* Required for every parser *************************/
#ifndef OHCOUNT_RUBY_PARSER_H
#define OHCOUNT_RUBY_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *RUBY_LANG = LANG_RUBY;

// the languages entities
const char *ruby_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  RUBY_SPACE = 0, RUBY_COMMENT, RUBY_STRING, RUBY_ANY
};

/*****************************************************************************/


#line 28 "ruby.h"
static const char _ruby_actions[] = {
	0, 1, 2, 1, 3, 1, 11, 1, 
	12, 1, 14, 1, 15, 1, 16, 1, 
	17, 1, 23, 1, 24, 1, 25, 1, 
	26, 1, 27, 1, 29, 1, 30, 1, 
	31, 1, 32, 1, 33, 2, 0, 2, 
	2, 0, 3, 2, 1, 19, 2, 2, 
	20, 2, 3, 13, 2, 5, 4, 2, 
	6, 4, 2, 7, 4, 2, 8, 4, 
	2, 9, 4, 2, 10, 4, 2, 12, 
	21, 2, 13, 22, 2, 15, 28, 2, 
	18, 13, 2, 18, 15, 3, 1, 2, 
	20, 3, 5, 4, 3, 3, 6, 4, 
	2, 3, 7, 4, 2, 3, 8, 4, 
	2, 3, 9, 4, 2, 3, 10, 4, 
	2, 4, 18, 0, 2, 13, 5, 6, 
	4, 1, 2, 20, 5, 7, 4, 1, 
	2, 20, 5, 8, 4, 1, 2, 20, 
	5, 9, 4, 1, 2, 20, 5, 10, 
	4, 1, 2, 20
};

static const char _ruby_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 1, 2, 
	3, 4, 5, 6, 6, 6, 7, 8, 
	8, 8, 8, 8, 9, 10, 10, 10, 
	11, 12, 12, 12, 12, 12, 12, 12, 
	12, 12, 13, 14, 15, 16, 17, 17, 
	18, 19, 19, 19, 19, 20, 20, 20, 
	20, 21, 21, 22, 22, 22, 23, 23, 
	23, 24
};

static const char _ruby_cond_lengths[] = {
	0, 0, 0, 0, 0, 1, 1, 1, 
	1, 1, 1, 0, 0, 1, 1, 0, 
	0, 0, 0, 1, 1, 0, 0, 1, 
	1, 0, 0, 0, 0, 0, 0, 0, 
	0, 1, 1, 1, 1, 1, 0, 1, 
	1, 0, 0, 0, 1, 0, 0, 0, 
	1, 0, 1, 0, 0, 1, 0, 0, 
	1, 0
};

static const short _ruby_cond_keys[] = {
	61, 61, 61, 61, 61, 61, 61, 61, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 61, 61, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _ruby_cond_spaces[] = {
	1, 1, 1, 1, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 1, 0, 0, 0, 0, 
	0
};

static const short _ruby_key_offsets[] = {
	0, 0, 1, 2, 3, 4, 10, 17, 
	24, 31, 43, 55, 58, 59, 73, 87, 
	90, 91, 94, 97, 111, 125, 128, 129, 
	141, 153, 156, 157, 162, 165, 166, 167, 
	168, 169, 180, 191, 203, 215, 227, 228, 
	240, 252, 255, 256, 257, 269, 272, 275, 
	276, 293, 295, 307, 310, 318, 330, 335, 
	336, 348
};

static const short _ruby_trans_keys[] = {
	101, 103, 105, 110, 829, 1085, 0, 60, 
	62, 255, 101, 829, 1085, 0, 60, 62, 
	255, 110, 829, 1085, 0, 60, 62, 255, 
	100, 829, 1085, 0, 60, 62, 255, 9, 
	10, 12, 32, 34, 92, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 34, 
	92, 269, 525, 0, 11, 14, 255, 10, 
	12, 13, 10, 9, 10, 12, 32, 41, 
	92, 93, 125, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 41, 92, 93, 
	125, 269, 525, 0, 11, 14, 255, 10, 
	12, 13, 10, 40, 91, 123, 40, 91, 
	123, 9, 10, 12, 32, 41, 92, 93, 
	125, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 41, 92, 93, 125, 269, 
	525, 0, 11, 14, 255, 10, 12, 13, 
	10, 9, 10, 12, 32, 39, 92, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 39, 92, 269, 525, 0, 11, 14, 
	255, 10, 12, 13, 10, 10, 47, 92, 
	12, 13, 10, 12, 13, 101, 103, 105, 
	110, 9, 10, 12, 32, 61, 269, 525, 
	0, 11, 14, 255, 9, 10, 12, 32, 
	61, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 61, 101, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 61, 
	110, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 61, 100, 269, 525, 0, 
	11, 14, 255, 10, 9, 10, 12, 32, 
	92, 96, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 92, 96, 269, 525, 
	0, 11, 14, 255, 10, 12, 13, 10, 
	10, 32, 35, 829, 1085, 0, 8, 9, 
	13, 14, 60, 62, 255, 32, 9, 13, 
	10, 12, 13, 98, 9, 10, 12, 32, 
	34, 35, 37, 39, 47, 61, 96, 269, 
	525, 0, 8, 14, 255, 9, 32, 9, 
	10, 12, 32, 34, 92, 269, 525, 0, 
	11, 14, 255, 10, 12, 13, 40, 81, 
	91, 113, 114, 123, 119, 120, 9, 10, 
	12, 32, 39, 92, 269, 525, 0, 11, 
	14, 255, 10, 47, 92, 12, 13, 98, 
	9, 10, 12, 32, 92, 96, 269, 525, 
	0, 11, 14, 255, 10, 0
};

static const char _ruby_single_lengths[] = {
	0, 1, 1, 1, 1, 2, 3, 3, 
	3, 8, 8, 1, 1, 10, 10, 1, 
	1, 3, 3, 10, 10, 1, 1, 8, 
	8, 1, 1, 3, 1, 1, 1, 1, 
	1, 7, 7, 8, 8, 8, 1, 8, 
	8, 1, 1, 1, 4, 1, 1, 1, 
	13, 2, 8, 1, 6, 8, 3, 1, 
	8, 1
};

static const char _ruby_range_lengths[] = {
	0, 0, 0, 0, 0, 2, 2, 2, 
	2, 2, 2, 1, 0, 2, 2, 1, 
	0, 0, 0, 2, 2, 1, 0, 2, 
	2, 1, 0, 1, 1, 0, 0, 0, 
	0, 2, 2, 2, 2, 2, 0, 2, 
	2, 1, 0, 0, 4, 1, 1, 0, 
	2, 0, 2, 1, 1, 2, 1, 0, 
	2, 0
};

static const short _ruby_index_offsets[] = {
	0, 0, 2, 4, 6, 8, 13, 19, 
	25, 31, 42, 53, 56, 58, 71, 84, 
	87, 89, 93, 97, 110, 123, 126, 128, 
	139, 150, 153, 155, 160, 163, 165, 167, 
	169, 171, 181, 191, 202, 213, 224, 226, 
	237, 248, 251, 253, 255, 264, 267, 270, 
	272, 288, 291, 302, 305, 313, 324, 329, 
	331, 342
};

static const char _ruby_indicies[] = {
	1, 0, 2, 0, 3, 0, 4, 0, 
	4, 5, 4, 4, 0, 6, 4, 5, 
	4, 4, 0, 7, 4, 5, 4, 4, 
	0, 8, 4, 5, 4, 4, 0, 11, 
	12, 12, 11, 13, 14, 15, 12, 10, 
	10, 9, 17, 18, 18, 17, 19, 20, 
	21, 18, 16, 16, 9, 9, 9, 10, 
	12, 9, 23, 24, 24, 23, 13, 25, 
	13, 13, 26, 24, 22, 22, 9, 28, 
	29, 29, 28, 30, 31, 30, 30, 32, 
	29, 27, 27, 9, 9, 9, 22, 24, 
	9, 33, 33, 33, 9, 34, 34, 34, 
	9, 36, 37, 37, 36, 13, 38, 13, 
	13, 39, 37, 35, 35, 9, 41, 42, 
	42, 41, 43, 44, 43, 43, 45, 42, 
	40, 40, 9, 9, 9, 35, 37, 9, 
	47, 48, 48, 47, 13, 49, 50, 48, 
	46, 46, 9, 52, 53, 53, 52, 54, 
	55, 56, 53, 51, 51, 9, 9, 9, 
	46, 48, 9, 9, 58, 59, 9, 57, 
	9, 9, 57, 60, 9, 61, 9, 62, 
	9, 63, 9, 65, 66, 66, 65, 67, 
	68, 66, 64, 64, 9, 70, 71, 71, 
	70, 72, 73, 71, 69, 69, 9, 65, 
	66, 66, 65, 67, 74, 68, 66, 64, 
	64, 9, 65, 66, 66, 65, 67, 75, 
	68, 66, 64, 64, 9, 65, 66, 66, 
	65, 67, 76, 68, 66, 64, 64, 9, 
	66, 9, 78, 79, 79, 78, 80, 13, 
	81, 79, 77, 77, 9, 83, 84, 84, 
	83, 85, 86, 87, 84, 82, 82, 9, 
	9, 9, 77, 79, 9, 88, 89, 91, 
	92, 90, 93, 90, 91, 90, 90, 89, 
	91, 91, 94, 95, 95, 92, 97, 96, 
	99, 88, 88, 99, 100, 101, 102, 103, 
	104, 105, 106, 107, 108, 98, 98, 89, 
	99, 99, 109, 11, 12, 12, 11, 13, 
	14, 15, 12, 10, 10, 110, 111, 111, 
	112, 33, 113, 33, 113, 114, 33, 114, 
	110, 47, 48, 48, 47, 13, 49, 50, 
	48, 46, 46, 110, 110, 58, 59, 110, 
	57, 115, 110, 78, 79, 79, 78, 80, 
	13, 81, 79, 77, 77, 110, 88, 116, 
	0
};

static const char _ruby_trans_targs[] = {
	44, 2, 3, 4, 5, 6, 7, 8, 
	44, 48, 9, 9, 10, 48, 11, 12, 
	9, 9, 10, 48, 11, 12, 13, 13, 
	14, 15, 16, 13, 13, 14, 48, 15, 
	16, 13, 19, 19, 19, 20, 21, 22, 
	19, 19, 20, 48, 21, 22, 23, 23, 
	24, 25, 26, 23, 23, 24, 48, 25, 
	26, 27, 48, 28, 30, 31, 32, 33, 
	33, 33, 34, 35, 38, 33, 33, 34, 
	35, 38, 36, 37, 48, 39, 39, 40, 
	41, 42, 39, 39, 40, 41, 48, 42, 
	48, 0, 44, 45, 46, 47, 44, 44, 
	44, 1, 48, 49, 50, 51, 52, 53, 
	54, 55, 56, 43, 57, 48, 48, 48, 
	51, 17, 18, 29, 48
};

static const char _ruby_trans_actions[] = {
	35, 11, 11, 11, 11, 11, 11, 11, 
	76, 25, 1, 0, 0, 85, 0, 0, 
	97, 58, 58, 124, 58, 58, 1, 0, 
	0, 0, 0, 101, 61, 61, 130, 61, 
	61, 37, 37, 1, 0, 0, 0, 0, 
	109, 67, 67, 142, 67, 67, 1, 0, 
	0, 0, 0, 93, 55, 55, 118, 55, 
	55, 0, 46, 0, 0, 0, 0, 40, 
	3, 0, 0, 3, 0, 89, 52, 52, 
	89, 52, 3, 3, 43, 1, 0, 0, 
	0, 0, 105, 64, 64, 64, 136, 64, 
	70, 0, 27, 9, 11, 82, 29, 31, 
	33, 11, 73, 5, 113, 49, 79, 113, 
	79, 79, 113, 7, 7, 17, 23, 19, 
	0, 0, 0, 0, 21
};

static const char _ruby_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 13, 0, 0, 0, 
	13, 0, 0, 0, 0, 0, 0, 0, 
	0, 0
};

static const char _ruby_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 15, 0, 0, 0, 
	15, 0, 0, 0, 0, 0, 0, 0, 
	0, 0
};

static const short _ruby_eof_trans[] = {
	0, 1, 1, 1, 1, 1, 1, 1, 
	1, 10, 10, 10, 10, 10, 10, 10, 
	10, 10, 10, 10, 10, 10, 10, 10, 
	10, 10, 10, 10, 10, 10, 10, 10, 
	10, 10, 10, 10, 10, 10, 10, 10, 
	10, 10, 10, 0, 0, 95, 96, 97, 
	0, 110, 111, 112, 111, 111, 111, 111, 
	111, 117
};

static const int ruby_start = 44;
static const int ruby_first_final = 44;
static const int ruby_error = 0;

static const int ruby_en_ruby_line = 48;
static const int ruby_en_ruby_entity = 44;


#line 155 "ruby.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Ruby code.
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
void parse_ruby(char *buffer, int length, int count,
                void (*callback) (const char *lang, const char *entity, int s,
                                  int e, void *udata),
                void *userdata
  ) {
  init

  
#line 329 "ruby.h"
	{
	cs = ruby_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 178 "ruby.rl"
  cs = (count) ? ruby_en_ruby_line : ruby_en_ruby_entity;
  
#line 340 "ruby.h"
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
	_acts = _ruby_actions + _ruby_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 17:
#line 1 "NONE"
	{ts = p;}
	break;
#line 362 "ruby.h"
		}
	}

	_widec = (*p);
	_klen = _ruby_cond_lengths[cs];
	_keys = _ruby_cond_keys + (_ruby_cond_offsets[cs]*2);
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
				switch ( _ruby_cond_spaces[_ruby_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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
#line 75 "common.rl"

  p == buffer || *(p-1) == '\r' || *(p-1) == '\n' || *(p-1) == '\f'
 ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _ruby_trans_keys + _ruby_key_offsets[cs];
	_trans = _ruby_index_offsets[cs];

	_klen = _ruby_single_lengths[cs];
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

	_klen = _ruby_range_lengths[cs];
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
	_trans = _ruby_indicies[_trans];
_eof_trans:
	cs = _ruby_trans_targs[_trans];

	if ( _ruby_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _ruby_actions + _ruby_trans_actions[_trans];
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
#line 31 "ruby.rl"
	{
    switch(entity) {
    case RUBY_SPACE:
      ls
      break;
    case RUBY_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(RUBY_LANG)
      break;
    case NEWLINE:
      std_newline(RUBY_LANG)
    }
  }
	break;
	case 5:
#line 52 "ruby.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 6:
#line 62 "ruby.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 72 "ruby.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 8:
#line 91 "ruby.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 9:
#line 101 "ruby.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 10:
#line 114 "ruby.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 11:
#line 131 "ruby.rl"
	{ entity = RUBY_SPACE; }
	break;
	case 12:
#line 134 "ruby.rl"
	{ entity = NEWLINE;    }
	break;
	case 13:
#line 135 "ruby.rl"
	{ entity = RUBY_ANY;   }
	break;
	case 14:
#line 150 "ruby.rl"
	{ entity = RUBY_SPACE;   }
	break;
	case 15:
#line 151 "ruby.rl"
	{ entity = RUBY_COMMENT; }
	break;
	case 18:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 19:
#line 132 "ruby.rl"
	{te = p+1;}
	break;
	case 20:
#line 133 "ruby.rl"
	{te = p+1;}
	break;
	case 21:
#line 31 "ruby.rl"
	{te = p+1;{
    switch(entity) {
    case RUBY_SPACE:
      ls
      break;
    case RUBY_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(RUBY_LANG)
      break;
    case NEWLINE:
      std_newline(RUBY_LANG)
    }
  }}
	break;
	case 22:
#line 31 "ruby.rl"
	{te = p+1;{
    switch(entity) {
    case RUBY_SPACE:
      ls
      break;
    case RUBY_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(RUBY_LANG)
      break;
    case NEWLINE:
      std_newline(RUBY_LANG)
    }
  }}
	break;
	case 23:
#line 31 "ruby.rl"
	{te = p;p--;{
    switch(entity) {
    case RUBY_SPACE:
      ls
      break;
    case RUBY_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(RUBY_LANG)
      break;
    case NEWLINE:
      std_newline(RUBY_LANG)
    }
  }}
	break;
	case 24:
#line 132 "ruby.rl"
	{te = p;p--;}
	break;
	case 25:
#line 31 "ruby.rl"
	{te = p;p--;{
    switch(entity) {
    case RUBY_SPACE:
      ls
      break;
    case RUBY_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(RUBY_LANG)
      break;
    case NEWLINE:
      std_newline(RUBY_LANG)
    }
  }}
	break;
	case 26:
#line 31 "ruby.rl"
	{te = p;p--;{
    switch(entity) {
    case RUBY_SPACE:
      ls
      break;
    case RUBY_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(RUBY_LANG)
      break;
    case NEWLINE:
      std_newline(RUBY_LANG)
    }
  }}
	break;
	case 27:
#line 31 "ruby.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case RUBY_SPACE:
      ls
      break;
    case RUBY_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(RUBY_LANG)
      break;
    case NEWLINE:
      std_newline(RUBY_LANG)
    }
  }}
	break;
	case 28:
#line 140 "ruby.rl"
	{te = p+1;{
    callback(RUBY_LANG, ruby_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 29:
#line 153 "ruby.rl"
	{te = p+1;}
	break;
	case 30:
#line 140 "ruby.rl"
	{te = p;p--;{
    callback(RUBY_LANG, ruby_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 31:
#line 140 "ruby.rl"
	{te = p;p--;{
    callback(RUBY_LANG, ruby_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 32:
#line 153 "ruby.rl"
	{te = p;p--;}
	break;
	case 33:
#line 153 "ruby.rl"
	{{p = ((te))-1;}}
	break;
#line 725 "ruby.h"
		}
	}

_again:
	_acts = _ruby_actions + _ruby_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 16:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 738 "ruby.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _ruby_eof_trans[cs] > 0 ) {
		_trans = _ruby_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 180 "ruby.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(RUBY_LANG) }
}

#endif

/*****************************************************************************/
