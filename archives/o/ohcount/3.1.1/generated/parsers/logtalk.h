
#line 1 "logtalk.rl"
// logtalk.rl written by Paulo Moura. pmoura<att>logtalk<dott>org.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_LOGTALK_PARSER_H
#define OHCOUNT_LOGTALK_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *LOGTALK_LANG = LANG_LOGTALK;

// the languages entities
const char *logtalk_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  LOGTALK_SPACE = 0, LOGTALK_COMMENT, LOGTALK_STRING, LOGTALK_ANY
};

/*****************************************************************************/


#line 28 "logtalk.h"
static const char _logtalk_actions[] = {
	0, 1, 1, 1, 4, 1, 5, 1, 
	7, 1, 8, 1, 9, 1, 10, 1, 
	12, 1, 13, 1, 16, 1, 17, 1, 
	18, 1, 19, 1, 20, 1, 22, 1, 
	23, 1, 24, 1, 25, 1, 26, 2, 
	1, 6, 2, 3, 2, 2, 5, 14, 
	2, 6, 15, 2, 8, 21, 2, 11, 
	6, 2, 11, 8, 3, 3, 2, 1, 
	3, 11, 0, 6
};

static const char _logtalk_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 2, 3, 3, 3, 3, 3, 3, 
	3, 4, 4, 4, 4, 4, 4
};

static const char _logtalk_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 1, 
	1, 1, 0, 0, 0, 0, 0, 0, 
	1, 0, 0, 0, 0, 0, 0
};

static const short _logtalk_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _logtalk_cond_spaces[] = {
	0, 0, 0, 0, 0
};

static const char _logtalk_key_offsets[] = {
	0, 0, 1, 3, 8, 11, 16, 19, 
	30, 41, 53, 54, 55, 60, 63, 66, 
	67, 81, 83, 88, 91, 96, 97
};

static const short _logtalk_trans_keys[] = {
	42, 42, 47, 10, 34, 92, 12, 13, 
	10, 12, 13, 10, 39, 92, 12, 13, 
	10, 12, 13, 9, 10, 12, 32, 42, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 42, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 42, 47, 269, 
	525, 0, 11, 14, 255, 10, 10, 32, 
	37, 47, 9, 13, 32, 9, 13, 10, 
	12, 13, 42, 9, 10, 12, 32, 34, 
	37, 39, 47, 269, 525, 0, 8, 14, 
	255, 9, 32, 10, 34, 92, 12, 13, 
	10, 12, 13, 10, 39, 92, 12, 13, 
	42, 10, 0
};

static const char _logtalk_single_lengths[] = {
	0, 1, 2, 3, 1, 3, 1, 7, 
	7, 8, 1, 1, 3, 1, 1, 1, 
	10, 2, 3, 1, 3, 1, 1
};

static const char _logtalk_range_lengths[] = {
	0, 0, 0, 1, 1, 1, 1, 2, 
	2, 2, 0, 0, 1, 1, 1, 0, 
	2, 0, 1, 1, 1, 0, 0
};

static const char _logtalk_index_offsets[] = {
	0, 0, 2, 5, 10, 13, 18, 21, 
	31, 41, 52, 54, 56, 61, 64, 67, 
	69, 82, 85, 90, 93, 98, 100
};

static const char _logtalk_indicies[] = {
	2, 1, 2, 3, 1, 4, 6, 7, 
	4, 5, 4, 4, 5, 4, 6, 9, 
	4, 8, 4, 4, 8, 11, 12, 12, 
	11, 13, 14, 12, 10, 10, 4, 16, 
	17, 17, 16, 18, 19, 17, 15, 15, 
	4, 11, 12, 12, 11, 13, 20, 14, 
	12, 10, 10, 4, 12, 4, 21, 22, 
	24, 25, 26, 24, 23, 24, 24, 27, 
	28, 28, 25, 1, 29, 31, 21, 21, 
	31, 32, 33, 34, 35, 36, 37, 30, 
	30, 22, 31, 31, 38, 39, 6, 7, 
	39, 5, 40, 40, 41, 39, 6, 9, 
	39, 8, 10, 39, 21, 42, 0
};

static const char _logtalk_trans_targs[] = {
	12, 1, 2, 12, 16, 3, 16, 4, 
	5, 6, 7, 7, 8, 9, 10, 7, 
	7, 8, 9, 10, 16, 16, 0, 12, 
	13, 14, 15, 12, 12, 12, 16, 17, 
	18, 19, 20, 21, 11, 22, 16, 16, 
	16, 19, 16
};

static const char _logtalk_trans_actions[] = {
	37, 9, 9, 51, 27, 0, 17, 0, 
	0, 0, 1, 0, 0, 1, 0, 60, 
	42, 42, 60, 42, 15, 45, 0, 29, 
	7, 9, 57, 31, 33, 35, 48, 3, 
	64, 39, 64, 54, 5, 5, 19, 25, 
	21, 0, 23
};

static const char _logtalk_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 11, 0, 0, 0, 
	11, 0, 0, 0, 0, 0, 0
};

static const char _logtalk_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 13, 0, 0, 0, 
	13, 0, 0, 0, 0, 0, 0
};

static const char _logtalk_eof_trans[] = {
	0, 1, 1, 5, 5, 5, 5, 5, 
	5, 5, 5, 0, 0, 28, 29, 30, 
	0, 39, 40, 41, 40, 40, 43
};

static const int logtalk_start = 12;
static const int logtalk_first_final = 12;
static const int logtalk_error = 0;

static const int logtalk_en_logtalk_line = 16;
static const int logtalk_en_logtalk_entity = 12;


#line 87 "logtalk.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Logtalk code.
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
void parse_logtalk(char *buffer, int length, int count,
                  void (*callback) (const char *lang, const char *entity, int s,
                                    int e, void *udata),
                  void *userdata
  ) {
  init

  
#line 186 "logtalk.h"
	{
	cs = logtalk_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 110 "logtalk.rl"
  cs = (count) ? logtalk_en_logtalk_line : logtalk_en_logtalk_entity;
  
#line 197 "logtalk.h"
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
	_acts = _logtalk_actions + _logtalk_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 10:
#line 1 "NONE"
	{ts = p;}
	break;
#line 219 "logtalk.h"
		}
	}

	_widec = (*p);
	_klen = _logtalk_cond_lengths[cs];
	_keys = _logtalk_cond_keys + (_logtalk_cond_offsets[cs]*2);
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
				switch ( _logtalk_cond_spaces[_logtalk_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _logtalk_trans_keys + _logtalk_key_offsets[cs];
	_trans = _logtalk_index_offsets[cs];

	_klen = _logtalk_single_lengths[cs];
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

	_klen = _logtalk_range_lengths[cs];
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
	_trans = _logtalk_indicies[_trans];
_eof_trans:
	cs = _logtalk_trans_targs[_trans];

	if ( _logtalk_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _logtalk_actions + _logtalk_trans_actions[_trans];
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
#line 31 "logtalk.rl"
	{
    switch(entity) {
    case LOGTALK_SPACE:
      ls
      break;
    case LOGTALK_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LOGTALK_LANG)
      break;
    case NEWLINE:
      std_newline(LOGTALK_LANG)
    }
  }
	break;
	case 3:
#line 50 "logtalk.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 63 "logtalk.rl"
	{ entity = LOGTALK_SPACE; }
	break;
	case 5:
#line 66 "logtalk.rl"
	{ entity = NEWLINE;   }
	break;
	case 6:
#line 67 "logtalk.rl"
	{ entity = LOGTALK_ANY;   }
	break;
	case 7:
#line 82 "logtalk.rl"
	{ entity = LOGTALK_SPACE;   }
	break;
	case 8:
#line 83 "logtalk.rl"
	{ entity = LOGTALK_COMMENT; }
	break;
	case 11:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 12:
#line 64 "logtalk.rl"
	{te = p+1;}
	break;
	case 13:
#line 65 "logtalk.rl"
	{te = p+1;}
	break;
	case 14:
#line 31 "logtalk.rl"
	{te = p+1;{
    switch(entity) {
    case LOGTALK_SPACE:
      ls
      break;
    case LOGTALK_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LOGTALK_LANG)
      break;
    case NEWLINE:
      std_newline(LOGTALK_LANG)
    }
  }}
	break;
	case 15:
#line 31 "logtalk.rl"
	{te = p+1;{
    switch(entity) {
    case LOGTALK_SPACE:
      ls
      break;
    case LOGTALK_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LOGTALK_LANG)
      break;
    case NEWLINE:
      std_newline(LOGTALK_LANG)
    }
  }}
	break;
	case 16:
#line 31 "logtalk.rl"
	{te = p;p--;{
    switch(entity) {
    case LOGTALK_SPACE:
      ls
      break;
    case LOGTALK_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LOGTALK_LANG)
      break;
    case NEWLINE:
      std_newline(LOGTALK_LANG)
    }
  }}
	break;
	case 17:
#line 64 "logtalk.rl"
	{te = p;p--;}
	break;
	case 18:
#line 31 "logtalk.rl"
	{te = p;p--;{
    switch(entity) {
    case LOGTALK_SPACE:
      ls
      break;
    case LOGTALK_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LOGTALK_LANG)
      break;
    case NEWLINE:
      std_newline(LOGTALK_LANG)
    }
  }}
	break;
	case 19:
#line 31 "logtalk.rl"
	{te = p;p--;{
    switch(entity) {
    case LOGTALK_SPACE:
      ls
      break;
    case LOGTALK_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LOGTALK_LANG)
      break;
    case NEWLINE:
      std_newline(LOGTALK_LANG)
    }
  }}
	break;
	case 20:
#line 31 "logtalk.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case LOGTALK_SPACE:
      ls
      break;
    case LOGTALK_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(LOGTALK_LANG)
      break;
    case NEWLINE:
      std_newline(LOGTALK_LANG)
    }
  }}
	break;
	case 21:
#line 72 "logtalk.rl"
	{te = p+1;{
    callback(LOGTALK_LANG, logtalk_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 22:
#line 85 "logtalk.rl"
	{te = p+1;}
	break;
	case 23:
#line 72 "logtalk.rl"
	{te = p;p--;{
    callback(LOGTALK_LANG, logtalk_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 24:
#line 72 "logtalk.rl"
	{te = p;p--;{
    callback(LOGTALK_LANG, logtalk_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 25:
#line 85 "logtalk.rl"
	{te = p;p--;}
	break;
	case 26:
#line 85 "logtalk.rl"
	{{p = ((te))-1;}}
	break;
#line 531 "logtalk.h"
		}
	}

_again:
	_acts = _logtalk_actions + _logtalk_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 9:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 544 "logtalk.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _logtalk_eof_trans[cs] > 0 ) {
		_trans = _logtalk_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 112 "logtalk.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(LOGTALK_LANG) }
}

#endif

/*****************************************************************************/
