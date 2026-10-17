
#line 1 "scilab.rl"
// scilab.rl written by Sylvestre Ledru based on matlab Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef RAGEL_SCILAB_PARSER
#define RAGEL_SCILAB_PARSER

#include "../parser_macros.h"

// the name of the language
const char *SCILAB_LANG = "scilab";

// the languages entities
const char *scilab_entities[] = {
  "space", "comment", "string", "any",
};

// constants associated with the entities
enum {
  SCILAB_SPACE = 0, SCILAB_COMMENT, SCILAB_STRING, SCILAB_ANY
};

/*****************************************************************************/


#line 28 "scilab.h"
static const char _scilab_actions[] = {
	0, 1, 1, 1, 2, 1, 3, 1, 
	4, 1, 5, 1, 6, 1, 7, 1, 
	8, 1, 10, 1, 13, 1, 14, 1, 
	15, 1, 16, 1, 17, 1, 18, 1, 
	19, 1, 20, 1, 21, 2, 1, 6, 
	2, 3, 11, 2, 4, 12, 3, 9, 
	0, 4
};

static const char _scilab_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 1, 1, 1, 1, 1, 
	1
};

static const char _scilab_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 1, 0, 0, 0, 0, 0, 
	0
};

static const short _scilab_cond_keys[] = {
	13, 13, 0
};

static const char _scilab_cond_spaces[] = {
	0, 0
};

static const char _scilab_key_offsets[] = {
	0, 0, 5, 8, 13, 16, 17, 21, 
	24, 25, 28, 41, 43, 48, 53, 54, 
	57
};

static const short _scilab_trans_keys[] = {
	10, 34, 92, 12, 13, 10, 12, 13, 
	10, 39, 92, 12, 13, 10, 12, 13, 
	10, 32, 47, 9, 13, 32, 9, 13, 
	47, 10, 12, 13, 9, 10, 12, 32, 
	34, 39, 47, 269, 525, 0, 8, 14, 
	255, 9, 32, 10, 34, 92, 12, 13, 
	10, 39, 92, 12, 13, 47, 10, 12, 
	13, 10, 0
};

static const char _scilab_single_lengths[] = {
	0, 3, 1, 3, 1, 1, 2, 1, 
	1, 1, 9, 2, 3, 3, 1, 1, 
	1
};

static const char _scilab_range_lengths[] = {
	0, 1, 1, 1, 1, 0, 1, 1, 
	0, 1, 2, 0, 1, 1, 0, 1, 
	0
};

static const char _scilab_index_offsets[] = {
	0, 0, 5, 8, 13, 16, 18, 22, 
	25, 27, 30, 42, 45, 50, 55, 57, 
	60
};

static const char _scilab_indicies[] = {
	0, 2, 3, 0, 1, 0, 0, 1, 
	0, 2, 5, 0, 4, 0, 0, 4, 
	6, 7, 9, 10, 9, 8, 9, 9, 
	11, 13, 12, 14, 14, 15, 17, 6, 
	6, 17, 18, 19, 20, 21, 22, 16, 
	16, 7, 17, 17, 23, 24, 2, 3, 
	24, 1, 24, 2, 5, 24, 4, 25, 
	24, 26, 26, 27, 6, 28, 0
};

static const char _scilab_trans_targs[] = {
	10, 1, 10, 2, 3, 4, 10, 0, 
	6, 7, 8, 6, 6, 9, 6, 9, 
	10, 11, 12, 13, 14, 5, 16, 10, 
	10, 15, 10, 15, 10
};

static const char _scilab_trans_actions[] = {
	27, 0, 17, 0, 0, 0, 40, 0, 
	29, 9, 11, 31, 35, 37, 33, 11, 
	43, 3, 46, 46, 7, 5, 5, 19, 
	25, 1, 21, 0, 23
};

static const char _scilab_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 13, 0, 
	0, 0, 13, 0, 0, 0, 0, 0, 
	0
};

static const char _scilab_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 15, 0, 
	0, 0, 15, 0, 0, 0, 0, 0, 
	0
};

static const char _scilab_eof_trans[] = {
	0, 1, 1, 1, 1, 0, 0, 12, 
	13, 15, 0, 24, 25, 25, 25, 27, 
	29
};

static const int scilab_start = 6;
static const int scilab_first_final = 6;
static const int scilab_error = 0;

static const int scilab_en_scilab_line = 10;
static const int scilab_en_scilab_entity = 6;


#line 78 "scilab.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with SCILAB code.
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
void parse_scilab(char *buffer, int length, int count,
                  void (*callback) (const char *lang, const char *entity, int s,
                                    int e, void *udata),
                  void *userdata
  ) {
  init

  
#line 169 "scilab.h"
	{
	cs = scilab_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 101 "scilab.rl"
  cs = (count) ? scilab_en_scilab_line : scilab_en_scilab_entity;
  
#line 180 "scilab.h"
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
	_acts = _scilab_actions + _scilab_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 8:
#line 1 "NONE"
	{ts = p;}
	break;
#line 202 "scilab.h"
		}
	}

	_widec = (*p);
	_klen = _scilab_cond_lengths[cs];
	_keys = _scilab_cond_keys + (_scilab_cond_offsets[cs]*2);
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
				switch ( _scilab_cond_spaces[_scilab_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _scilab_trans_keys + _scilab_key_offsets[cs];
	_trans = _scilab_index_offsets[cs];

	_klen = _scilab_single_lengths[cs];
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

	_klen = _scilab_range_lengths[cs];
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
	_trans = _scilab_indicies[_trans];
_eof_trans:
	cs = _scilab_trans_targs[_trans];

	if ( _scilab_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _scilab_actions + _scilab_trans_actions[_trans];
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
#line 56 "scilab.rl"
	{ entity = SCILAB_SPACE; }
	break;
	case 3:
#line 59 "scilab.rl"
	{ entity = NEWLINE;      }
	break;
	case 4:
#line 60 "scilab.rl"
	{ entity = SCILAB_ANY;   }
	break;
	case 5:
#line 73 "scilab.rl"
	{ entity = SCILAB_SPACE;   }
	break;
	case 6:
#line 74 "scilab.rl"
	{ entity = SCILAB_COMMENT; }
	break;
	case 9:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 10:
#line 58 "scilab.rl"
	{te = p+1;}
	break;
	case 11:
#line 31 "scilab.rl"
	{te = p+1;{
    switch(entity) {
    case SCILAB_SPACE:
      ls
      break;
    case SCILAB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SCILAB_LANG)
      break;
    case NEWLINE:
      std_newline(SCILAB_LANG)
    }
  }}
	break;
	case 12:
#line 31 "scilab.rl"
	{te = p+1;{
    switch(entity) {
    case SCILAB_SPACE:
      ls
      break;
    case SCILAB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SCILAB_LANG)
      break;
    case NEWLINE:
      std_newline(SCILAB_LANG)
    }
  }}
	break;
	case 13:
#line 31 "scilab.rl"
	{te = p;p--;{
    switch(entity) {
    case SCILAB_SPACE:
      ls
      break;
    case SCILAB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SCILAB_LANG)
      break;
    case NEWLINE:
      std_newline(SCILAB_LANG)
    }
  }}
	break;
	case 14:
#line 57 "scilab.rl"
	{te = p;p--;}
	break;
	case 15:
#line 31 "scilab.rl"
	{te = p;p--;{
    switch(entity) {
    case SCILAB_SPACE:
      ls
      break;
    case SCILAB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SCILAB_LANG)
      break;
    case NEWLINE:
      std_newline(SCILAB_LANG)
    }
  }}
	break;
	case 16:
#line 31 "scilab.rl"
	{te = p;p--;{
    switch(entity) {
    case SCILAB_SPACE:
      ls
      break;
    case SCILAB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SCILAB_LANG)
      break;
    case NEWLINE:
      std_newline(SCILAB_LANG)
    }
  }}
	break;
	case 17:
#line 31 "scilab.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case SCILAB_SPACE:
      ls
      break;
    case SCILAB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SCILAB_LANG)
      break;
    case NEWLINE:
      std_newline(SCILAB_LANG)
    }
  }}
	break;
	case 18:
#line 76 "scilab.rl"
	{te = p+1;}
	break;
	case 19:
#line 65 "scilab.rl"
	{te = p;p--;{
    callback(SCILAB_LANG, scilab_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 20:
#line 65 "scilab.rl"
	{te = p;p--;{
    callback(SCILAB_LANG, scilab_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 21:
#line 76 "scilab.rl"
	{te = p;p--;}
	break;
#line 477 "scilab.h"
		}
	}

_again:
	_acts = _scilab_actions + _scilab_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 7:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 490 "scilab.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _scilab_eof_trans[cs] > 0 ) {
		_trans = _scilab_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 103 "scilab.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(SCILAB_LANG) }
}

#endif

/*****************************************************************************/
