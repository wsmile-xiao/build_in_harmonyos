
#line 1 "vim.rl"
// vim.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_VIM_PARSER_H
#define OHCOUNT_VIM_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *VIM_LANG = LANG_VIM;

// the languages entities
const char *vim_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  VIM_SPACE = 0, VIM_COMMENT, VIM_STRING, VIM_ANY
};

/*****************************************************************************/


#line 28 "vim.h"
static const char _vim_actions[] = {
	0, 1, 0, 1, 1, 1, 2, 1, 
	3, 1, 5, 1, 6, 1, 8, 1, 
	11, 1, 12, 1, 13, 1, 14, 1, 
	15, 2, 3, 9, 2, 4, 10, 3, 
	7, 0, 4
};

static const char _vim_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 2, 2, 2, 
	2
};

static const char _vim_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 2, 0, 0, 0, 
	0
};

static const short _vim_cond_keys[] = {
	13, 13, 34, 34, 0
};

static const char _vim_cond_spaces[] = {
	0, 1, 0
};

static const char _vim_key_offsets[] = {
	0, 0, 1, 2, 3, 4, 5, 10, 
	10, 15, 15, 16, 16, 31, 33, 38, 
	41
};

static const short _vim_trans_keys[] = {
	84, 79, 68, 79, 58, 10, 39, 92, 
	12, 13, 10, 34, 92, 12, 13, 10, 
	9, 10, 12, 32, 39, 290, 546, 781, 
	1037, 0, 8, 14, 33, 35, 255, 9, 
	32, 10, 39, 92, 12, 13, 10, 12, 
	13, 10, 0
};

static const char _vim_single_lengths[] = {
	0, 1, 1, 1, 1, 1, 3, 0, 
	3, 0, 1, 0, 9, 2, 3, 1, 
	1
};

static const char _vim_range_lengths[] = {
	0, 0, 0, 0, 0, 0, 1, 0, 
	1, 0, 0, 0, 3, 0, 1, 1, 
	0
};

static const char _vim_index_offsets[] = {
	0, 0, 2, 4, 6, 8, 10, 15, 
	16, 21, 22, 24, 25, 38, 41, 46, 
	49
};

static const char _vim_indicies[] = {
	0, 1, 2, 1, 3, 1, 4, 1, 
	5, 1, 6, 8, 9, 6, 7, 7, 
	1, 8, 11, 1, 10, 10, 12, 1, 
	1, 14, 12, 12, 14, 15, 16, 17, 
	18, 19, 13, 13, 13, 1, 14, 14, 
	20, 21, 8, 9, 21, 7, 22, 22, 
	23, 12, 24, 0
};

static const char _vim_trans_targs[] = {
	2, 0, 3, 4, 5, 11, 12, 6, 
	12, 7, 8, 9, 12, 12, 13, 14, 
	8, 15, 10, 16, 12, 12, 12, 15, 
	12
};

static const char _vim_trans_actions[] = {
	0, 0, 0, 0, 0, 0, 23, 0, 
	13, 0, 0, 0, 25, 28, 5, 31, 
	1, 3, 7, 7, 15, 21, 17, 0, 
	19
};

static const char _vim_to_state_actions[] = {
	0, 9, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 9, 0, 0, 0, 
	0
};

static const char _vim_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 11, 0, 0, 0, 
	0
};

static const char _vim_eof_trans[] = {
	0, 0, 0, 0, 0, 0, 7, 7, 
	0, 0, 0, 0, 0, 21, 22, 23, 
	25
};

static const int vim_start = 1;
static const int vim_first_final = 11;
static const int vim_error = 0;

static const int vim_en_vim_line = 12;
static const int vim_en_vim_entity = 1;


#line 70 "vim.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Vim code.
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
void parse_vim(char *buffer, int length, int count,
               void (*callback) (const char *lang, const char *entity, int s,
                                 int e, void *udata),
               void *userdata
  ) {
  init

  
#line 164 "vim.h"
	{
	cs = vim_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 93 "vim.rl"
  cs = (count) ? vim_en_vim_line : vim_en_vim_entity;
  
#line 175 "vim.h"
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
	_acts = _vim_actions + _vim_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 6:
#line 1 "NONE"
	{ts = p;}
	break;
#line 197 "vim.h"
		}
	}

	_widec = (*p);
	_klen = _vim_cond_lengths[cs];
	_keys = _vim_cond_keys + (_vim_cond_offsets[cs]*2);
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
				switch ( _vim_cond_spaces[_vim_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
	case 0: {
		_widec = (short)(768 + ((*p) - 0));
		if ( 
#line 9 "common.rl"
 p+1 < pe && *(p+1) != '\n'  ) _widec += 256;
		break;
	}
	case 1: {
		_widec = (short)(256 + ((*p) - 0));
		if ( 
#line 71 "common.rl"
 !line_contains_code  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _vim_trans_keys + _vim_key_offsets[cs];
	_trans = _vim_index_offsets[cs];

	_klen = _vim_single_lengths[cs];
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

	_klen = _vim_range_lengths[cs];
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
	_trans = _vim_indicies[_trans];
_eof_trans:
	cs = _vim_trans_targs[_trans];

	if ( _vim_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _vim_actions + _vim_trans_actions[_trans];
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
#line 54 "vim.rl"
	{ entity = VIM_SPACE; }
	break;
	case 3:
#line 57 "vim.rl"
	{ entity = NEWLINE;   }
	break;
	case 4:
#line 59 "vim.rl"
	{ entity = VIM_ANY;   }
	break;
	case 7:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 8:
#line 56 "vim.rl"
	{te = p+1;}
	break;
	case 9:
#line 31 "vim.rl"
	{te = p+1;{
    switch(entity) {
    case VIM_SPACE:
      ls
      break;
    case VIM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(VIM_LANG)
      break;
    case NEWLINE:
      std_newline(VIM_LANG)
    }
  }}
	break;
	case 10:
#line 31 "vim.rl"
	{te = p+1;{
    switch(entity) {
    case VIM_SPACE:
      ls
      break;
    case VIM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(VIM_LANG)
      break;
    case NEWLINE:
      std_newline(VIM_LANG)
    }
  }}
	break;
	case 11:
#line 31 "vim.rl"
	{te = p;p--;{
    switch(entity) {
    case VIM_SPACE:
      ls
      break;
    case VIM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(VIM_LANG)
      break;
    case NEWLINE:
      std_newline(VIM_LANG)
    }
  }}
	break;
	case 12:
#line 55 "vim.rl"
	{te = p;p--;}
	break;
	case 13:
#line 31 "vim.rl"
	{te = p;p--;{
    switch(entity) {
    case VIM_SPACE:
      ls
      break;
    case VIM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(VIM_LANG)
      break;
    case NEWLINE:
      std_newline(VIM_LANG)
    }
  }}
	break;
	case 14:
#line 31 "vim.rl"
	{te = p;p--;{
    switch(entity) {
    case VIM_SPACE:
      ls
      break;
    case VIM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(VIM_LANG)
      break;
    case NEWLINE:
      std_newline(VIM_LANG)
    }
  }}
	break;
	case 15:
#line 31 "vim.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case VIM_SPACE:
      ls
      break;
    case VIM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(VIM_LANG)
      break;
    case NEWLINE:
      std_newline(VIM_LANG)
    }
  }}
	break;
#line 449 "vim.h"
		}
	}

_again:
	_acts = _vim_actions + _vim_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 5:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 462 "vim.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _vim_eof_trans[cs] > 0 ) {
		_trans = _vim_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 95 "vim.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(VIM_LANG) }
}

#endif

/*****************************************************************************/
