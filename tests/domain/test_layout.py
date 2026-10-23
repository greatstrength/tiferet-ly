"""Tiferet Ly Layout Profile Domain Tests"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError
from tiferet import use_tester
from tiferet.domain.core import DomainObject

# ** app
from tiferet_ly.domain.layout import LayoutProfile

# *** testers

# ** tester: test_layout_profile
@use_tester(
    type='domain',
    target_cls=LayoutProfile,
    sample_data={
        'indent_token': 'INDENT',
        'dedent_token': 'DEDENT',
    },
    equality_fields=['indent_token', 'dedent_token'],
)
class TestLayoutProfile:
    '''
    Tests for the declared layout profile.
    '''

    # * test: new
    def test_new(self, test_ctx, session):
        '''
        Declare the eight layout fields, with only the two synthetic names required.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Assert the model is a domain object with exactly these fields, in order.
        assert issubclass(LayoutProfile, DomainObject)
        assert list(LayoutProfile.model_fields) == [
            'block_tokens',
            'open_delimiters',
            'close_delimiters',
            'newline_token',
            'suppress_newline_in_delimiters',
            'indent_token',
            'dedent_token',
            'tab_size',
        ]

        # Assert only the indent and dedent names are required.
        fields = LayoutProfile.model_fields
        assert fields['indent_token'].is_required() is True
        assert fields['dedent_token'].is_required() is True
        for name in (
            'block_tokens',
            'open_delimiters',
            'close_delimiters',
            'newline_token',
            'suppress_newline_in_delimiters',
            'tab_size',
        ):
            assert fields[name].is_required() is False

        # Assert the declared defaults.
        assert fields['block_tokens'].default_factory is list
        assert fields['open_delimiters'].default_factory is list
        assert fields['close_delimiters'].default_factory is list
        assert fields['newline_token'].default is None
        assert fields['suppress_newline_in_delimiters'].default is True
        assert fields['tab_size'].default == 4

        # Assert construction from the two-name sample.
        test_ctx.assert_new()

    # * test: indent_token_required
    def test_indent_token_required(self, test_ctx, session):
        '''
        Reject a profile without an indent token name.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A missing indent name is invalid.
        with pytest.raises(ValidationError):
            LayoutProfile(dedent_token='DEDENT')

    # * test: dedent_token_required
    def test_dedent_token_required(self, test_ctx, session):
        '''
        Reject a profile without a dedent token name.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A missing dedent name is invalid.
        with pytest.raises(ValidationError):
            LayoutProfile(indent_token='INDENT')

    # * test: defaults
    def test_defaults(self, test_ctx, session):
        '''
        Fill every other field from its default, with fresh lists per instance.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Construct the minimal profile a grammar layout uses.
        first = LayoutProfile(indent_token='INDENT', dedent_token='DEDENT')

        # Assert the two names and every default.
        assert first.indent_token == 'INDENT'
        assert first.dedent_token == 'DEDENT'
        assert first.block_tokens == []
        assert first.open_delimiters == []
        assert first.close_delimiters == []
        assert first.newline_token is None
        assert first.suppress_newline_in_delimiters is True
        assert first.tab_size == 4

        # Assert each instance gets its own lists.
        second = LayoutProfile(indent_token='INDENT', dedent_token='DEDENT')
        assert first.block_tokens is not second.block_tokens
        assert first.open_delimiters is not second.open_delimiters
        assert first.close_delimiters is not second.close_delimiters

    # * test: construct_full
    def test_construct_full(self, test_ctx, session):
        '''
        Store every declared value from a full keyword construction.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Construct a profile with every field declared.
        profile = LayoutProfile(
            block_tokens=['IF', 'FOR', 'DEF'],
            open_delimiters=['LPAREN'],
            close_delimiters=['RPAREN'],
            newline_token='NEWLINE',
            suppress_newline_in_delimiters=True,
            indent_token='INDENT',
            dedent_token='DEDENT',
            tab_size=4,
        )

        # Assert each attribute stores its declared value.
        assert profile.block_tokens == ['IF', 'FOR', 'DEF']
        assert profile.open_delimiters == ['LPAREN']
        assert profile.close_delimiters == ['RPAREN']
        assert profile.newline_token == 'NEWLINE'
        assert profile.suppress_newline_in_delimiters is True
        assert profile.indent_token == 'INDENT'
        assert profile.dedent_token == 'DEDENT'
        assert profile.tab_size == 4

    # * test: forbids_extra_fields
    def test_forbids_extra_fields(self, test_ctx, session):
        '''
        Reject an undeclared field.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # An unknown field is not part of the profile.
        with pytest.raises(ValidationError):
            LayoutProfile(
                indent_token='INDENT',
                dedent_token='DEDENT',
                unknown='value',
            )
