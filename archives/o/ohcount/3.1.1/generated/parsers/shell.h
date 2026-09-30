
#line 1 "shell.rl"
// shell.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net

/************************* Required for every parser *************************/
#ifndef OHCOUNT_SHELL_PARSER_H
#define OHCOUNT_SHELL_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *SHELL_LANG = LANG_SHELL;

// the languages entities
const char *shell_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  SHELL_SPACE = 0, SHELL_COMMENT, SHELL_STRING, SHELL_ANY
};

/*****************************************************************************/


#line 28 "shell.h"
static const char _shell_actions[] = {
	0, 1, 2, 1, 9, 1, 10, 1, 
	12, 1, 13, 1, 14, 1, 15, 1, 
	20, 1, 21, 1, 22, 1, 23, 1, 
	24, 1, 25, 1, 26, 1, 27, 2, 
	1, 17, 2, 3, 11, 2, 5, 4, 
	2, 6, 4, 2, 7, 4, 2, 8, 
	4, 2, 10, 18, 2, 11, 19, 3, 
	5, 4, 2, 3, 5, 4, 6, 3, 
	6, 4, 2, 3, 7, 4, 2, 3, 
	7, 4, 8, 3, 8, 4, 2, 4, 
	5, 4, 1, 17, 4, 5, 4, 6, 
	2, 4, 6, 4, 1, 17, 4, 7, 
	4, 1, 17, 4, 7, 4, 8, 2, 
	4, 8, 4, 1, 17, 4, 16, 0, 
	2, 11, 5, 5, 4, 6, 1, 17, 
	5, 7, 4, 8, 1, 17
};

static const char _shell_cond_offsets[] = {
	0, 0, 1, 2, 3, 4, 4, 4, 
	5, 6, 7, 8, 9, 10, 10, 10, 
	11, 12, 12, 12, 12, 12, 13, 13, 
	14, 14, 15
};

static const char _shell_cond_lengths[] = {
	0, 1, 1, 1, 1, 0, 0, 1, 
	1, 1, 1, 1, 1, 0, 0, 1, 
	1, 0, 0, 0, 0, 1, 0, 1, 
	0, 1, 0
};

static const short _shell_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 0
};

static const char _shell_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0
};

static const char _shell_key_offsets[] = {
	0, 0, 12, 24, 32, 44, 45, 46, 
	58, 70, 82, 94, 102, 114, 115, 116, 
	128, 140, 141, 145, 148, 151, 164, 166, 
	178, 181, 193
};

static const short _shell_trans_keys[] = {
	9, 10, 12, 32, 34, 92, 269, 525, 
	0, 11, 14, 255, 9, 10, 12, 32, 
	34, 92, 269, 525, 0, 11, 14, 255, 
	10, 12, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 34, 92, 269, 525, 
	0, 11, 14, 255, 10, 10, 9, 10, 
	12, 32, 34, 92, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 34, 92, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 39, 92, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 39, 92, 
	269, 525, 0, 11, 14, 255, 10, 12, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 39, 92, 269, 525, 0, 11, 
	14, 255, 10, 10, 9, 10, 12, 32, 
	39, 92, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 39, 92, 269, 525, 
	0, 11, 14, 255, 10, 32, 35, 9, 
	13, 32, 9, 13, 10, 12, 13, 9, 
	10, 12, 32, 34, 35, 39, 269, 525, 
	0, 8, 14, 255, 9, 32, 9, 10, 
	12, 32, 34, 92, 269, 525, 0, 11, 
	14, 255, 10, 12, 13, 9, 10, 12, 
	32, 39, 92, 269, 525, 0, 11, 14, 
	255, 10, 0
};

static const char _shell_single_lengths[] = {
	0, 8, 8, 4, 8, 1, 1, 8, 
	8, 8, 8, 4, 8, 1, 1, 8, 
	8, 1, 2, 1, 1, 9, 2, 8, 
	1, 8, 1
};

static const char _shell_range_lengths[] = {
	0, 2, 2, 2, 2, 0, 0, 2, 
	2, 2, 2, 2, 2, 0, 0, 2, 
	2, 0, 1, 1, 1, 2, 0, 2, 
	1, 2, 0
};

static const char _shell_index_offsets[] = {
	0, 0, 11, 22, 29, 40, 42, 44, 
	55, 66, 77, 88, 95, 106, 108, 110, 
	121, 132, 134, 138, 141, 144, 156, 159, 
	170, 173, 184
};

static const char _shell_indicies[] = {
	2, 3, 3, 2, 4, 5, 6, 3, 
	1, 1, 0, 8, 9, 9, 8, 10, 
	11, 12, 9, 7, 7, 0, 13, 13, 
	14, 15, 1, 1, 0, 17, 18, 18, 
	17, 19, 20, 21, 18, 16, 16, 0, 
	3, 0, 13, 0, 17, 22, 18, 17, 
	19, 20, 21, 18, 16, 16, 0, 24, 
	25, 25, 24, 26, 27, 28, 25, 23, 
	23, 0, 30, 31, 31, 30, 4, 32, 
	33, 31, 29, 29, 0, 35, 36, 36, 
	35, 37, 38, 39, 36, 34, 34, 0, 
	40, 40, 41, 42, 29, 29, 0, 44, 
	45, 45, 44, 46, 47, 48, 45, 43, 
	43, 0, 31, 0, 40, 0, 44, 49, 
	45, 44, 46, 47, 48, 45, 43, 43, 
	0, 51, 52, 52, 51, 53, 54, 55, 
	52, 50, 50, 0, 56, 57, 59, 60, 
	59, 58, 59, 59, 61, 62, 62, 60, 
	64, 56, 56, 64, 65, 66, 67, 68, 
	69, 63, 63, 57, 64, 64, 70, 2, 
	3, 3, 2, 4, 5, 6, 3, 1, 
	1, 71, 72, 72, 73, 30, 31, 31, 
	30, 4, 32, 33, 31, 29, 29, 71, 
	56, 74, 0
};

static const char _shell_trans_targs[] = {
	21, 1, 1, 2, 21, 3, 5, 1, 
	1, 2, 21, 3, 5, 4, 6, 7, 
	1, 1, 2, 21, 3, 5, 8, 1, 
	1, 2, 21, 3, 5, 9, 9, 10, 
	11, 13, 9, 9, 10, 21, 11, 13, 
	12, 14, 15, 9, 9, 10, 21, 11, 
	13, 16, 9, 9, 10, 21, 11, 13, 
	21, 0, 18, 19, 20, 18, 18, 21, 
	22, 23, 24, 25, 17, 26, 21, 21, 
	21, 24, 21
};

static const char _shell_trans_actions[] = {
	23, 1, 0, 0, 31, 0, 0, 67, 
	43, 43, 94, 43, 43, 0, 0, 0, 
	75, 46, 46, 104, 46, 46, 46, 99, 
	71, 71, 120, 71, 71, 1, 0, 0, 
	0, 0, 55, 37, 37, 79, 37, 37, 
	0, 0, 0, 63, 40, 40, 89, 40, 
	40, 40, 84, 59, 59, 114, 59, 59, 
	49, 0, 25, 7, 9, 27, 29, 52, 
	3, 109, 34, 109, 5, 5, 15, 21, 
	17, 0, 19
};

static const char _shell_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 11, 0, 0, 11, 0, 0, 
	0, 0, 0
};

static const char _shell_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 13, 0, 0, 13, 0, 0, 
	0, 0, 0
};

static const char _shell_eof_trans[] = {
	0, 1, 1, 1, 1, 1, 1, 1, 
	1, 1, 1, 1, 1, 1, 1, 1, 
	1, 0, 0, 62, 63, 0, 71, 72, 
	73, 72, 75
};

static const int shell_start = 18;
static const int shell_first_final = 18;
static const int shell_error = 0;

static const int shell_en_shell_line = 21;
static const int shell_en_shell_entity = 18;


#line 98 "shell.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Shell code.
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
void parse_shell(char *buffer, int length, int count,
                 void (*callback) (const char *lang, const char *entity, int s,
                                   int e, void *udata),
                 void *userdata
  ) {
  init

  
#line 236 "shell.h"
	{
	cs = shell_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 121 "shell.rl"
  cs = (count) ? shell_en_shell_line : shell_en_shell_entity;
  
#line 247 "shell.h"
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
	_acts = _shell_actions + _shell_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 15:
#line 1 "NONE"
	{ts = p;}
	break;
#line 269 "shell.h"
		}
	}

	_widec = (*p);
	_klen = _shell_cond_lengths[cs];
	_keys = _shell_cond_keys + (_shell_cond_offsets[cs]*2);
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
				switch ( _shell_cond_spaces[_shell_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _shell_trans_keys + _shell_key_offsets[cs];
	_trans = _shell_index_offsets[cs];

	_klen = _shell_single_lengths[cs];
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

	_klen = _shell_range_lengths[cs];
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
	_trans = _shell_indicies[_trans];
_eof_trans:
	cs = _shell_trans_targs[_trans];

	if ( _shell_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _shell_actions + _shell_trans_actions[_trans];
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
#line 31 "shell.rl"
	{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }
	break;
	case 5:
#line 51 "shell.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 6:
#line 53 "shell.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 63 "shell.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 8:
#line 65 "shell.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 9:
#line 77 "shell.rl"
	{ entity = SHELL_SPACE; }
	break;
	case 10:
#line 80 "shell.rl"
	{ entity = NEWLINE;     }
	break;
	case 11:
#line 81 "shell.rl"
	{ entity = SHELL_ANY;   }
	break;
	case 12:
#line 93 "shell.rl"
	{ entity = SHELL_SPACE;   }
	break;
	case 13:
#line 94 "shell.rl"
	{ entity = SHELL_COMMENT; }
	break;
	case 16:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 17:
#line 79 "shell.rl"
	{te = p+1;}
	break;
	case 18:
#line 31 "shell.rl"
	{te = p+1;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 19:
#line 31 "shell.rl"
	{te = p+1;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 20:
#line 31 "shell.rl"
	{te = p;p--;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 21:
#line 78 "shell.rl"
	{te = p;p--;}
	break;
	case 22:
#line 31 "shell.rl"
	{te = p;p--;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 23:
#line 31 "shell.rl"
	{te = p;p--;{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 24:
#line 31 "shell.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case SHELL_SPACE:
      ls
      break;
    case SHELL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SHELL_LANG)
      break;
    case NEWLINE:
      std_newline(SHELL_LANG)
    }
  }}
	break;
	case 25:
#line 96 "shell.rl"
	{te = p+1;}
	break;
	case 26:
#line 86 "shell.rl"
	{te = p;p--;{
    callback(SHELL_LANG, shell_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 27:
#line 86 "shell.rl"
	{te = p;p--;{
    callback(SHELL_LANG, shell_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
#line 597 "shell.h"
		}
	}

_again:
	_acts = _shell_actions + _shell_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 14:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 610 "shell.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _shell_eof_trans[cs] > 0 ) {
		_trans = _shell_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 123 "shell.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(SHELL_LANG) }
}

#endif

/*****************************************************************************/
