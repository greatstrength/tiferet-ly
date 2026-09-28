"""Tiferet Ly Test Assets"""

# *** constants

# ** constant: feature_data
FEATURE_DATA = {
    'features': {
        'lex': {
            'default': {
                'name': 'Lex Text',
                'description': 'Collect declared catalogues, then read text as lexemes.',
                'steps': [
                    {
                        'name': 'List tokens',
                        'service_id': 'list_tokens_event',
                        'data_key': 'tokens',
                    },
                    {
                        'name': 'List productions',
                        'service_id': 'list_productions_event',
                        'data_key': 'productions',
                    },
                    {
                        'name': 'List grammars',
                        'service_id': 'list_grammars_event',
                        'data_key': 'grammars',
                    },
                    {
                        'name': 'Lex text',
                        'service_id': 'lex_text_event',
                        'params': {
                            'grammar_id': '$r.grammar_id',
                            'text': '$r.text',
                            'tokens': '$r.tokens',
                            'productions': '$r.productions',
                            'grammars': '$r.grammars',
                        },
                    },
                ],
            },
        },
        'parse': {
            'default': {
                'name': 'Parse Text',
                'description': 'Collect declared catalogues, then read text into a parse result.',
                'params_schema': {
                    'render_result': {
                        'type': 'bool',
                        'required': False,
                        'default': False,
                    },
                },
                'steps': [
                    {
                        'name': 'List tokens',
                        'service_id': 'list_tokens_event',
                        'data_key': 'tokens',
                    },
                    {
                        'name': 'List productions',
                        'service_id': 'list_productions_event',
                        'data_key': 'productions',
                    },
                    {
                        'name': 'List grammars',
                        'service_id': 'list_grammars_event',
                        'data_key': 'grammars',
                    },
                    {
                        'name': 'Parse text',
                        'service_id': 'parse_text_event',
                        'data_key': 'result',
                        'params': {
                            'grammar_id': '$r.grammar_id',
                            'text': '$r.text',
                            'tokens': '$r.tokens',
                            'productions': '$r.productions',
                            'grammars': '$r.grammars',
                        },
                    },
                    {
                        'name': 'Render result',
                        'service_id': 'render_result_event',
                        'params': {
                            'result': '$r.result',
                            'render_result': '$r.render_result',
                        },
                    },
                ],
            },
        },
    },
}

# ** constant: di_data
DI_DATA = {
    'services': {
        'lexer_service': {
            'name': 'Lexer Service',
            'module_path': 'tiferet_ly.utils.lex',
            'class_name': 'PlyLexer',
        },
        'parser_service': {
            'name': 'Parser Service',
            'module_path': 'tiferet_ly.utils.parse',
            'class_name': 'PlyParser',
        },
        'list_tokens_event': {
            'name': 'List Tokens',
            'module_path': 'tiferet_ly.events.token',
            'class_name': 'ListTokens',
        },
        'list_productions_event': {
            'name': 'List Productions',
            'module_path': 'tiferet_ly.events.production',
            'class_name': 'ListProductions',
        },
        'list_grammars_event': {
            'name': 'List Grammars',
            'module_path': 'tiferet_ly.events.grammar',
            'class_name': 'ListGrammars',
        },
        'lex_text_event': {
            'name': 'Lex Text',
            'module_path': 'tiferet_ly.events.reader',
            'class_name': 'LexText',
        },
        'parse_text_event': {
            'name': 'Parse Text',
            'module_path': 'tiferet_ly.events.reader',
            'class_name': 'ParseText',
        },
        'render_result_event': {
            'name': 'Render Result',
            'module_path': 'tiferet_ly.events.render',
            'class_name': 'RenderResult',
        },
    },
}

# ** constant: cli_data
CLI_DATA = {
    'cli': {
        'cmds': {
            'parse': {
                'default': {
                    'group_key': 'parse',
                    'key': 'default',
                    'name': 'Parse Text',
                    'description': 'Read text into a parse result.',
                    'args': [
                        {
                            'name_or_flags': ['--render-result'],
                            'type': 'bool',
                            'description': 'Render the parse result as a string.',
                        },
                    ],
                },
            },
        },
    },
}
