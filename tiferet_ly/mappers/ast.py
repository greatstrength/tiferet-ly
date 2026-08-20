"""Tiferet-Ly AST Mappers"""

# *** imports

# ** core
from typing import Any, List, Optional

# ** app
from tiferet import Aggregate
from ..domain.ast import AstNode

# *** constants

# ** constant: default_format_indent
DEFAULT_FORMAT_INDENT = ''

# ** constant: default_format_indent_step
DEFAULT_FORMAT_INDENT_STEP = '  '

# *** mappers

# ** mapper: ast_node_aggregate
class AstNodeAggregate(AstNode, Aggregate):
    '''
    Mutable factory for the optional generic tree node. Declared actions
    construct this type (or a rebound subclass) rather than a bare AstNode.
    '''

    # * method: new (classmethod)
    @classmethod
    def new(cls,
            kind: str,
            children: Optional[List[AstNode]] = None,
            value: Any = None,
            lineno: Optional[int] = None,
            lexpos: Optional[int] = None) -> 'AstNodeAggregate':
        '''
        Construct a generic tree node.

        :param kind: A language-chosen node kind.
        :type kind: str
        :param children: Child nodes; defaults to an empty list.
        :type children: Optional[List[AstNode]]
        :param value: Optional leaf payload.
        :type value: Any
        :param lineno: Source line of the first meaningful symbol.
        :type lineno: Optional[int]
        :param lexpos: Source position of the first meaningful symbol.
        :type lexpos: Optional[int]
        :return: The constructed node.
        :rtype: AstNodeAggregate
        '''

        # Construct through the aggregate so callers never bind a bare domain object.
        return cls(
            kind=kind,
            children=children if children is not None else [],
            value=value,
            lineno=lineno,
            lexpos=lexpos,
        )

    # * method: leaf (classmethod)
    @classmethod
    def leaf(cls,
             kind: str,
             value: Any,
             lineno: Optional[int] = None,
             lexpos: Optional[int] = None) -> 'AstNodeAggregate':
        '''
        Construct a leaf node with no children.

        :param kind: A language-chosen node kind.
        :type kind: str
        :param value: The leaf payload.
        :type value: Any
        :param lineno: Source line of the first meaningful symbol.
        :type lineno: Optional[int]
        :param lexpos: Source position of the first meaningful symbol.
        :type lexpos: Optional[int]
        :return: The constructed leaf node.
        :rtype: AstNodeAggregate
        '''

        # Delegate to new with an empty child list.
        return cls.new(
            kind,
            children=[],
            value=value,
            lineno=lineno,
            lexpos=lexpos,
        )

    # * method: add_child
    def add_child(self, node: AstNode) -> None:
        '''
        Append a child node.

        :param node: The child to append.
        :type node: AstNode
        :return: None
        :rtype: None
        '''

        # Reassign so validate_assignment re-validates the child list.
        self.children = list(self.children) + [node]

    # * method: set_value
    def set_value(self, value: Any) -> None:
        '''
        Set the node payload.

        :param value: The new payload.
        :type value: Any
        :return: None
        :rtype: None
        '''

        # Update the payload; validate_assignment=True handles re-validation.
        self.value = value

    # * method: format
    def format(
            self,
            indent: str = DEFAULT_FORMAT_INDENT,
            indent_step: str = DEFAULT_FORMAT_INDENT_STEP) -> str:
        '''
        Render this node as indented text, omitting source span.

        :param indent: Leading whitespace for this node.
        :type indent: str
        :param indent_step: Extra indent applied to each child.
        :type indent_step: str
        :return: The deterministic indented rendering.
        :rtype: str
        '''

        # A leaf is one line: kind, plus the value when it is set.
        if not self.children and self.value is not None:
            line = f'{indent}{self.kind} {self.value}'
        else:
            line = f'{indent}{self.kind}'

        # An internal node is its kind, then each child one indent deeper.
        if not self.children:
            return line

        # Recurse through child aggregates so the tree formats itself.
        child_text = [
            child.format(
                indent=indent + indent_step,
                indent_step=indent_step,
            )
            for child in self.children
        ]

        # Join this line with the formatted children.
        return '\n'.join([line] + child_text)
