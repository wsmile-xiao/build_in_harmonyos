
#line 1 "coq.rl"
/************************* Required for every parser *************************/
#ifndef OHCOUNT_COQ_PARSER_H
#define OHCOUNT_COQ_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *COQ_LANG = LANG_COQ;

// the languages entities
const char *coq_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  COQ_SPACE = 0, COQ_COMMENT, COQ_STRING, COQ_ANY
};

/*****************************************************************************/


#line 26 "coq.h"
static const char _coq_actions[] = {
	0, 1, 0, 1, 1, 1, 8, 1, 
	9, 1, 11, 1, 12, 1, 13, 1, 
	14, 1, 17, 1, 20, 1, 21, 1, 
	22, 1, 23, 1, 25, 1, 26, 1, 
	27, 1, 28, 2, 1, 16, 2, 4, 
	1, 2, 4, 12, 2, 5, 1, 2, 
	5, 12, 2, 6, 2, 2, 9, 18, 
	2, 10, 19, 2, 12, 24, 3, 6, 
	2, 1, 3, 7, 2, 0, 3, 7, 
	2, 17, 3, 15, 0, 10, 3, 15, 
	3, 10, 3, 15, 3, 12
};

static const char _coq_cond_offsets[] = {
	0, 0, 1, 2, 3, 5, 6, 7, 
	9, 11, 13, 13, 15, 18, 18, 18, 
	18, 18, 19, 19, 20, 20
};

static const char _coq_cond_lengths[] = {
	0, 1, 1, 1, 2, 1, 1, 2, 
	2, 2, 0, 2, 3, 0, 0, 0, 
	0, 1, 0, 1, 0, 0
};

static const short _coq_cond_keys[] = {
	42, 42, 42, 42, 42, 42, 41, 41, 
	42, 42, 13, 13, 13, 13, 13, 13, 
	42, 42, 13, 13, 42, 42, 13, 13, 
	42, 42, 13, 13, 42, 42, 13, 13, 
	41, 41, 42, 42, 13, 13, 13, 13, 
	0
};

static const char _coq_cond_spaces[] = {
	2, 2, 2, 2, 2, 0, 0, 0, 
	1, 0, 1, 0, 1, 0, 1, 0, 
	1, 1, 0, 0, 0
};

static const char _coq_key_offsets[] = {
	0, 0, 7, 14, 22, 31, 40, 49, 
	64, 79, 94, 95, 111, 128, 129, 133, 
	136, 137, 149, 151, 160, 161
};

static const short _coq_trans_keys[] = {
	40, 1322, 1578, 0, 41, 43, 255, 40, 
	1322, 1578, 0, 41, 43, 255, 40, 41, 
	1322, 1578, 0, 39, 43, 255, 40, 1321, 
	1322, 1577, 1578, 0, 39, 43, 255, 10, 
	12, 34, 269, 525, 0, 11, 14, 255, 
	10, 12, 34, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 40, 269, 525, 
	810, 1066, 0, 11, 14, 41, 43, 255, 
	9, 10, 12, 32, 40, 269, 525, 810, 
	1066, 0, 11, 14, 41, 43, 255, 9, 
	10, 12, 32, 40, 269, 525, 810, 1066, 
	0, 11, 14, 41, 43, 255, 10, 9, 
	10, 12, 32, 40, 41, 269, 525, 810, 
	1066, 0, 11, 14, 39, 43, 255, 9, 
	10, 12, 32, 40, 269, 525, 809, 810, 
	1065, 1066, 0, 11, 14, 39, 43, 255, 
	10, 32, 40, 9, 13, 32, 9, 13, 
	42, 9, 10, 12, 32, 34, 40, 269, 
	525, 0, 8, 14, 255, 9, 32, 10, 
	12, 34, 269, 525, 0, 11, 14, 255, 
	42, 10, 0
};

static const char _coq_single_lengths[] = {
	0, 3, 3, 4, 5, 5, 5, 9, 
	9, 9, 1, 10, 11, 1, 2, 1, 
	1, 8, 2, 5, 1, 1
};

static const char _coq_range_lengths[] = {
	0, 2, 2, 2, 2, 2, 2, 3, 
	3, 3, 0, 3, 3, 0, 1, 1, 
	0, 2, 0, 2, 0, 0
};

static const char _coq_index_offsets[] = {
	0, 0, 6, 12, 19, 27, 35, 43, 
	56, 69, 82, 84, 98, 113, 115, 119, 
	122, 124, 135, 138, 146, 148
};

static const char _coq_indicies[] = {
	2, 3, 4, 1, 1, 0, 2, 5, 
	6, 1, 1, 0, 2, 7, 3, 4, 
	1, 1, 0, 2, 7, 3, 8, 4, 
	1, 1, 0, 11, 11, 12, 10, 11, 
	10, 10, 9, 14, 14, 15, 13, 14, 
	13, 13, 9, 17, 18, 18, 17, 19, 
	20, 18, 21, 22, 16, 16, 16, 9, 
	24, 25, 25, 24, 26, 27, 25, 28, 
	29, 23, 23, 23, 9, 17, 18, 18, 
	17, 19, 20, 18, 30, 31, 16, 16, 
	16, 9, 18, 9, 17, 18, 18, 17, 
	19, 32, 20, 18, 21, 22, 16, 16, 
	16, 9, 17, 18, 18, 17, 19, 20, 
	18, 32, 21, 33, 22, 16, 16, 16, 
	9, 34, 35, 37, 38, 37, 36, 37, 
	37, 39, 1, 40, 42, 34, 34, 42, 
	43, 44, 45, 46, 41, 41, 35, 42, 
	42, 47, 11, 11, 12, 10, 11, 10, 
	10, 48, 16, 48, 34, 49, 0
};

static const char _coq_trans_targs[] = {
	14, 1, 2, 3, 4, 3, 4, 1, 
	14, 17, 5, 6, 17, 5, 6, 17, 
	7, 7, 8, 9, 10, 11, 12, 7, 
	7, 8, 9, 10, 11, 12, 11, 12, 
	7, 17, 17, 0, 14, 15, 16, 14, 
	14, 17, 18, 19, 20, 13, 21, 17, 
	17, 17
};

static const char _coq_trans_actions[] = {
	33, 11, 11, 11, 11, 41, 41, 47, 
	59, 25, 1, 1, 17, 66, 66, 70, 
	3, 0, 0, 3, 0, 3, 3, 62, 
	50, 50, 62, 50, 62, 62, 38, 38, 
	44, 35, 53, 0, 27, 9, 82, 29, 
	31, 56, 5, 74, 78, 7, 7, 19, 
	23, 21
};

static const char _coq_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 13, 0, 
	0, 13, 0, 0, 0, 0
};

static const char _coq_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 15, 0, 
	0, 15, 0, 0, 0, 0
};

static const char _coq_eof_trans[] = {
	0, 1, 1, 1, 1, 10, 10, 10, 
	10, 10, 10, 10, 10, 0, 0, 40, 
	41, 0, 48, 49, 49, 50
};

static const int coq_start = 14;
static const int coq_first_final = 14;
static const int coq_error = 0;

static const int coq_en_coq_line = 17;
static const int coq_en_coq_entity = 14;


#line 101 "coq.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Coq code.
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
void parse_coq(char *buffer, int length, int count,
               void (*callback) (const char *lang, const char *entity, int s,
                                 int e, void *udata),
               void *userdata
  ) {
  init

  int nest_count = 0;

  
#line 210 "coq.h"
	{
	cs = coq_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 126 "coq.rl"
  cs = (count) ? coq_en_coq_line : coq_en_coq_entity;
  
#line 221 "coq.h"
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
	_acts = _coq_actions + _coq_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 14:
#line 1 "NONE"
	{ts = p;}
	break;
#line 243 "coq.h"
		}
	}

	_widec = (*p);
	_klen = _coq_cond_lengths[cs];
	_keys = _coq_cond_keys + (_coq_cond_offsets[cs]*2);
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
				switch ( _coq_cond_spaces[_coq_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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
#line 60 "coq.rl"
 nest_count == 0  ) _widec += 256;
		break;
	}
	case 2: {
		_widec = (short)(1280 + ((*p) - 0));
		if ( 
#line 93 "coq.rl"
 nest_count == 0  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _coq_trans_keys + _coq_key_offsets[cs];
	_trans = _coq_index_offsets[cs];

	_klen = _coq_single_lengths[cs];
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

	_klen = _coq_range_lengths[cs];
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
	_trans = _coq_indicies[_trans];
_eof_trans:
	cs = _coq_trans_targs[_trans];

	if ( _coq_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _coq_actions + _coq_trans_actions[_trans];
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
#line 29 "coq.rl"
	{
    switch(entity) {
    case COQ_SPACE:
      ls
      break;
    case COQ_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(COQ_LANG)
      break;
    case NEWLINE:
      std_newline(COQ_LANG)
    }
  }
	break;
	case 3:
#line 45 "coq.rl"
	{ nest_count = 0; }
	break;
	case 4:
#line 46 "coq.rl"
	{ nest_count++; }
	break;
	case 5:
#line 47 "coq.rl"
	{ nest_count--; }
	break;
	case 6:
#line 51 "coq.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 66 "coq.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 8:
#line 74 "coq.rl"
	{ entity = COQ_SPACE; }
	break;
	case 9:
#line 77 "coq.rl"
	{ entity = NEWLINE;   }
	break;
	case 10:
#line 78 "coq.rl"
	{ entity = COQ_ANY;   }
	break;
	case 11:
#line 96 "coq.rl"
	{ entity = COQ_SPACE;   }
	break;
	case 12:
#line 97 "coq.rl"
	{ entity = COQ_COMMENT; }
	break;
	case 15:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 16:
#line 75 "coq.rl"
	{te = p+1;}
	break;
	case 17:
#line 76 "coq.rl"
	{te = p+1;}
	break;
	case 18:
#line 29 "coq.rl"
	{te = p+1;{
    switch(entity) {
    case COQ_SPACE:
      ls
      break;
    case COQ_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(COQ_LANG)
      break;
    case NEWLINE:
      std_newline(COQ_LANG)
    }
  }}
	break;
	case 19:
#line 29 "coq.rl"
	{te = p+1;{
    switch(entity) {
    case COQ_SPACE:
      ls
      break;
    case COQ_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(COQ_LANG)
      break;
    case NEWLINE:
      std_newline(COQ_LANG)
    }
  }}
	break;
	case 20:
#line 29 "coq.rl"
	{te = p;p--;{
    switch(entity) {
    case COQ_SPACE:
      ls
      break;
    case COQ_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(COQ_LANG)
      break;
    case NEWLINE:
      std_newline(COQ_LANG)
    }
  }}
	break;
	case 21:
#line 29 "coq.rl"
	{te = p;p--;{
    switch(entity) {
    case COQ_SPACE:
      ls
      break;
    case COQ_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(COQ_LANG)
      break;
    case NEWLINE:
      std_newline(COQ_LANG)
    }
  }}
	break;
	case 22:
#line 29 "coq.rl"
	{te = p;p--;{
    switch(entity) {
    case COQ_SPACE:
      ls
      break;
    case COQ_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(COQ_LANG)
      break;
    case NEWLINE:
      std_newline(COQ_LANG)
    }
  }}
	break;
	case 23:
#line 29 "coq.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case COQ_SPACE:
      ls
      break;
    case COQ_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(COQ_LANG)
      break;
    case NEWLINE:
      std_newline(COQ_LANG)
    }
  }}
	break;
	case 24:
#line 83 "coq.rl"
	{te = p+1;{
    callback(COQ_LANG, coq_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 25:
#line 99 "coq.rl"
	{te = p+1;}
	break;
	case 26:
#line 83 "coq.rl"
	{te = p;p--;{
    callback(COQ_LANG, coq_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 27:
#line 99 "coq.rl"
	{te = p;p--;}
	break;
	case 28:
#line 99 "coq.rl"
	{{p = ((te))-1;}}
	break;
#line 572 "coq.h"
		}
	}

_again:
	_acts = _coq_actions + _coq_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 13:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 585 "coq.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _coq_eof_trans[cs] > 0 ) {
		_trans = _coq_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 128 "coq.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(COQ_LANG) }
}

#endif

/*****************************************************************************/
