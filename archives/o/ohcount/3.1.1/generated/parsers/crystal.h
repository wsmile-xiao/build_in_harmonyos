
#line 1 "crystal.rl"
// renamed copy of ruby.rl(without *_sq_str).

/************************* Required for every parser *************************/
#ifndef OHCOUNT_CRYSTAL_PARSER_H
#define OHCOUNT_CRYSTAL_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *CRYSTAL_LANG = LANG_CRYSTAL;

// the languages entities
const char *crystal_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  CRYSTAL_SPACE = 0, CRYSTAL_COMMENT, CRYSTAL_STRING, CRYSTAL_ANY
};

/*****************************************************************************/


#line 28 "crystal.h"
static const char _crystal_actions[] = {
	0, 1, 2, 1, 3, 1, 10, 1, 
	11, 1, 13, 1, 14, 1, 15, 1, 
	16, 1, 22, 1, 23, 1, 24, 1, 
	25, 1, 26, 1, 28, 1, 29, 1, 
	30, 1, 31, 1, 32, 2, 0, 2, 
	2, 0, 3, 2, 1, 18, 2, 2, 
	19, 2, 3, 12, 2, 5, 4, 2, 
	6, 4, 2, 7, 4, 2, 8, 4, 
	2, 9, 4, 2, 11, 20, 2, 12, 
	21, 2, 14, 27, 2, 17, 12, 2, 
	17, 14, 3, 1, 2, 19, 3, 5, 
	4, 3, 3, 6, 4, 2, 3, 7, 
	4, 2, 3, 8, 4, 2, 3, 9, 
	4, 2, 4, 17, 0, 2, 12, 5, 
	6, 4, 1, 2, 19, 5, 7, 4, 
	1, 2, 19, 5, 8, 4, 1, 2, 
	19, 5, 9, 4, 1, 2, 19
};

static const char _crystal_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 1, 2, 
	3, 4, 5, 6, 6, 6, 7, 8, 
	8, 8, 8, 8, 9, 10, 10, 10, 
	10, 10, 10, 10, 10, 10, 11, 12, 
	13, 14, 15, 15, 16, 17, 17, 17, 
	17, 18, 18, 18, 18, 19, 19, 20, 
	20, 20, 20, 20, 21
};

static const char _crystal_cond_lengths[] = {
	0, 0, 0, 0, 0, 1, 1, 1, 
	1, 1, 1, 0, 0, 1, 1, 0, 
	0, 0, 0, 1, 1, 0, 0, 0, 
	0, 0, 0, 0, 0, 1, 1, 1, 
	1, 1, 0, 1, 1, 0, 0, 0, 
	1, 0, 0, 0, 1, 0, 1, 0, 
	0, 0, 0, 1, 0
};

static const short _crystal_cond_keys[] = {
	61, 61, 61, 61, 61, 61, 61, 61, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 61, 61, 13, 13, 13, 13, 
	13, 13, 0
};

static const char _crystal_cond_spaces[] = {
	1, 1, 1, 1, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 1, 0, 0, 0, 0
};

static const short _crystal_key_offsets[] = {
	0, 0, 1, 2, 3, 4, 10, 17, 
	24, 31, 43, 55, 58, 59, 73, 87, 
	90, 91, 94, 97, 111, 125, 128, 129, 
	134, 137, 138, 139, 140, 141, 152, 163, 
	175, 187, 199, 200, 212, 224, 227, 228, 
	229, 241, 244, 247, 248, 264, 266, 278, 
	281, 289, 294, 295, 307
};

static const short _crystal_trans_keys[] = {
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
	10, 10, 47, 92, 12, 13, 10, 12, 
	13, 101, 103, 105, 110, 9, 10, 12, 
	32, 61, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 61, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 61, 
	101, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 61, 110, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 61, 
	100, 269, 525, 0, 11, 14, 255, 10, 
	9, 10, 12, 32, 92, 96, 269, 525, 
	0, 11, 14, 255, 9, 10, 12, 32, 
	92, 96, 269, 525, 0, 11, 14, 255, 
	10, 12, 13, 10, 10, 32, 35, 829, 
	1085, 0, 8, 9, 13, 14, 60, 62, 
	255, 32, 9, 13, 10, 12, 13, 98, 
	9, 10, 12, 32, 34, 35, 37, 47, 
	61, 96, 269, 525, 0, 8, 14, 255, 
	9, 32, 9, 10, 12, 32, 34, 92, 
	269, 525, 0, 11, 14, 255, 10, 12, 
	13, 40, 81, 91, 113, 114, 123, 119, 
	120, 10, 47, 92, 12, 13, 98, 9, 
	10, 12, 32, 92, 96, 269, 525, 0, 
	11, 14, 255, 10, 0
};

static const char _crystal_single_lengths[] = {
	0, 1, 1, 1, 1, 2, 3, 3, 
	3, 8, 8, 1, 1, 10, 10, 1, 
	1, 3, 3, 10, 10, 1, 1, 3, 
	1, 1, 1, 1, 1, 7, 7, 8, 
	8, 8, 1, 8, 8, 1, 1, 1, 
	4, 1, 1, 1, 12, 2, 8, 1, 
	6, 3, 1, 8, 1
};

static const char _crystal_range_lengths[] = {
	0, 0, 0, 0, 0, 2, 2, 2, 
	2, 2, 2, 1, 0, 2, 2, 1, 
	0, 0, 0, 2, 2, 1, 0, 1, 
	1, 0, 0, 0, 0, 2, 2, 2, 
	2, 2, 0, 2, 2, 1, 0, 0, 
	4, 1, 1, 0, 2, 0, 2, 1, 
	1, 1, 0, 2, 0
};

static const short _crystal_index_offsets[] = {
	0, 0, 2, 4, 6, 8, 13, 19, 
	25, 31, 42, 53, 56, 58, 71, 84, 
	87, 89, 93, 97, 110, 123, 126, 128, 
	133, 136, 138, 140, 142, 144, 154, 164, 
	175, 186, 197, 199, 210, 221, 224, 226, 
	228, 237, 240, 243, 245, 260, 263, 274, 
	277, 285, 290, 292, 303
};

static const char _crystal_indicies[] = {
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
	9, 47, 48, 9, 46, 9, 9, 46, 
	49, 9, 50, 9, 51, 9, 52, 9, 
	54, 55, 55, 54, 56, 57, 55, 53, 
	53, 9, 59, 60, 60, 59, 61, 62, 
	60, 58, 58, 9, 54, 55, 55, 54, 
	56, 63, 57, 55, 53, 53, 9, 54, 
	55, 55, 54, 56, 64, 57, 55, 53, 
	53, 9, 54, 55, 55, 54, 56, 65, 
	57, 55, 53, 53, 9, 55, 9, 67, 
	68, 68, 67, 69, 13, 70, 68, 66, 
	66, 9, 72, 73, 73, 72, 74, 75, 
	76, 73, 71, 71, 9, 9, 9, 66, 
	68, 9, 77, 78, 80, 81, 79, 82, 
	79, 80, 79, 79, 78, 80, 80, 83, 
	84, 84, 81, 86, 85, 88, 77, 77, 
	88, 89, 90, 91, 92, 93, 94, 95, 
	96, 87, 87, 78, 88, 88, 97, 11, 
	12, 12, 11, 13, 14, 15, 12, 10, 
	10, 98, 99, 99, 100, 33, 101, 33, 
	101, 102, 33, 102, 98, 98, 47, 48, 
	98, 46, 103, 98, 67, 68, 68, 67, 
	69, 13, 70, 68, 66, 66, 98, 77, 
	104, 0
};

static const char _crystal_trans_targs[] = {
	40, 2, 3, 4, 5, 6, 7, 8, 
	40, 44, 9, 9, 10, 44, 11, 12, 
	9, 9, 10, 44, 11, 12, 13, 13, 
	14, 15, 16, 13, 13, 14, 44, 15, 
	16, 13, 19, 19, 19, 20, 21, 22, 
	19, 19, 20, 44, 21, 22, 23, 44, 
	24, 26, 27, 28, 29, 29, 29, 30, 
	31, 34, 29, 29, 30, 31, 34, 32, 
	33, 44, 35, 35, 36, 37, 38, 35, 
	35, 36, 37, 44, 38, 44, 0, 40, 
	41, 42, 43, 40, 40, 40, 1, 44, 
	45, 46, 47, 48, 49, 50, 51, 39, 
	52, 44, 44, 44, 47, 17, 18, 25, 
	44
};

static const char _crystal_trans_actions[] = {
	35, 11, 11, 11, 11, 11, 11, 11, 
	73, 25, 1, 0, 0, 82, 0, 0, 
	90, 55, 55, 111, 55, 55, 1, 0, 
	0, 0, 0, 94, 58, 58, 117, 58, 
	58, 37, 37, 1, 0, 0, 0, 0, 
	102, 64, 64, 129, 64, 64, 0, 46, 
	0, 0, 0, 0, 40, 3, 0, 0, 
	3, 0, 86, 52, 52, 86, 52, 3, 
	3, 43, 1, 0, 0, 0, 0, 98, 
	61, 61, 61, 123, 61, 67, 0, 27, 
	9, 11, 79, 29, 31, 33, 11, 70, 
	5, 106, 49, 76, 76, 76, 106, 7, 
	7, 17, 23, 19, 0, 0, 0, 0, 
	21
};

static const char _crystal_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	13, 0, 0, 0, 13, 0, 0, 0, 
	0, 0, 0, 0, 0
};

static const char _crystal_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	15, 0, 0, 0, 15, 0, 0, 0, 
	0, 0, 0, 0, 0
};

static const short _crystal_eof_trans[] = {
	0, 1, 1, 1, 1, 1, 1, 1, 
	1, 10, 10, 10, 10, 10, 10, 10, 
	10, 10, 10, 10, 10, 10, 10, 10, 
	10, 10, 10, 10, 10, 10, 10, 10, 
	10, 10, 10, 10, 10, 10, 10, 0, 
	0, 84, 85, 86, 0, 98, 99, 100, 
	99, 99, 99, 99, 105
};

static const int crystal_start = 40;
static const int crystal_first_final = 40;
static const int crystal_error = 0;

static const int crystal_en_crystal_line = 44;
static const int crystal_en_crystal_entity = 40;


#line 145 "crystal.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with crystal code.
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
void parse_crystal(char *buffer, int length, int count,
                void (*callback) (const char *lang, const char *entity, int s,
                                  int e, void *udata),
                void *userdata
  ) {
  init

  
#line 304 "crystal.h"
	{
	cs = crystal_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 168 "crystal.rl"
  cs = (count) ? crystal_en_crystal_line : crystal_en_crystal_entity;
  
#line 315 "crystal.h"
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
	_acts = _crystal_actions + _crystal_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 16:
#line 1 "NONE"
	{ts = p;}
	break;
#line 337 "crystal.h"
		}
	}

	_widec = (*p);
	_klen = _crystal_cond_lengths[cs];
	_keys = _crystal_cond_keys + (_crystal_cond_offsets[cs]*2);
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
				switch ( _crystal_cond_spaces[_crystal_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _crystal_trans_keys + _crystal_key_offsets[cs];
	_trans = _crystal_index_offsets[cs];

	_klen = _crystal_single_lengths[cs];
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

	_klen = _crystal_range_lengths[cs];
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
	_trans = _crystal_indicies[_trans];
_eof_trans:
	cs = _crystal_trans_targs[_trans];

	if ( _crystal_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _crystal_actions + _crystal_trans_actions[_trans];
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
#line 31 "crystal.rl"
	{
    switch(entity) {
    case CRYSTAL_SPACE:
      ls
      break;
    case CRYSTAL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CRYSTAL_LANG)
      break;
    case NEWLINE:
      std_newline(CRYSTAL_LANG)
    }
  }
	break;
	case 5:
#line 52 "crystal.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 6:
#line 62 "crystal.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 81 "crystal.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 8:
#line 91 "crystal.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 9:
#line 104 "crystal.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 10:
#line 121 "crystal.rl"
	{ entity = CRYSTAL_SPACE; }
	break;
	case 11:
#line 124 "crystal.rl"
	{ entity = NEWLINE;    }
	break;
	case 12:
#line 125 "crystal.rl"
	{ entity = CRYSTAL_ANY;   }
	break;
	case 13:
#line 140 "crystal.rl"
	{ entity = CRYSTAL_SPACE;   }
	break;
	case 14:
#line 141 "crystal.rl"
	{ entity = CRYSTAL_COMMENT; }
	break;
	case 17:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 18:
#line 122 "crystal.rl"
	{te = p+1;}
	break;
	case 19:
#line 123 "crystal.rl"
	{te = p+1;}
	break;
	case 20:
#line 31 "crystal.rl"
	{te = p+1;{
    switch(entity) {
    case CRYSTAL_SPACE:
      ls
      break;
    case CRYSTAL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CRYSTAL_LANG)
      break;
    case NEWLINE:
      std_newline(CRYSTAL_LANG)
    }
  }}
	break;
	case 21:
#line 31 "crystal.rl"
	{te = p+1;{
    switch(entity) {
    case CRYSTAL_SPACE:
      ls
      break;
    case CRYSTAL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CRYSTAL_LANG)
      break;
    case NEWLINE:
      std_newline(CRYSTAL_LANG)
    }
  }}
	break;
	case 22:
#line 31 "crystal.rl"
	{te = p;p--;{
    switch(entity) {
    case CRYSTAL_SPACE:
      ls
      break;
    case CRYSTAL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CRYSTAL_LANG)
      break;
    case NEWLINE:
      std_newline(CRYSTAL_LANG)
    }
  }}
	break;
	case 23:
#line 122 "crystal.rl"
	{te = p;p--;}
	break;
	case 24:
#line 31 "crystal.rl"
	{te = p;p--;{
    switch(entity) {
    case CRYSTAL_SPACE:
      ls
      break;
    case CRYSTAL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CRYSTAL_LANG)
      break;
    case NEWLINE:
      std_newline(CRYSTAL_LANG)
    }
  }}
	break;
	case 25:
#line 31 "crystal.rl"
	{te = p;p--;{
    switch(entity) {
    case CRYSTAL_SPACE:
      ls
      break;
    case CRYSTAL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CRYSTAL_LANG)
      break;
    case NEWLINE:
      std_newline(CRYSTAL_LANG)
    }
  }}
	break;
	case 26:
#line 31 "crystal.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case CRYSTAL_SPACE:
      ls
      break;
    case CRYSTAL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CRYSTAL_LANG)
      break;
    case NEWLINE:
      std_newline(CRYSTAL_LANG)
    }
  }}
	break;
	case 27:
#line 130 "crystal.rl"
	{te = p+1;{
    callback(CRYSTAL_LANG, crystal_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 28:
#line 143 "crystal.rl"
	{te = p+1;}
	break;
	case 29:
#line 130 "crystal.rl"
	{te = p;p--;{
    callback(CRYSTAL_LANG, crystal_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 30:
#line 130 "crystal.rl"
	{te = p;p--;{
    callback(CRYSTAL_LANG, crystal_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 31:
#line 143 "crystal.rl"
	{te = p;p--;}
	break;
	case 32:
#line 143 "crystal.rl"
	{{p = ((te))-1;}}
	break;
#line 696 "crystal.h"
		}
	}

_again:
	_acts = _crystal_actions + _crystal_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 15:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 709 "crystal.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _crystal_eof_trans[cs] > 0 ) {
		_trans = _crystal_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 170 "crystal.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(CRYSTAL_LANG) }
}

#endif

/*****************************************************************************/
