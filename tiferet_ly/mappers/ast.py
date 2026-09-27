"""Tiferet Ly AST Mappers"""

# *** imports

# ** core
from typing import Any

# ** app
from tiferet import Aggregate
from tiferet_ly.domain.ast import AstNode

# *** constants

# ** constant: default_format_indent
DEFAULT_FORMAT_INDENT = ''

# ** constant: default_format_indent_step
DEFAULT_FORMAT_INDENT_STEP = '  '

# *** mappers

# ** mapper: ast_node_aggregate
class AstNodeAggregate(AstNode, Aggregate):
    '''
    The mutable node a compiled action uses to build an optional tree.

    ``new`` and ``leaf`` construct that node. They do not format it and
    they do not call PLY.
    '''

    # * method: new
    @classmethod
    def new(
            cls,
            kind: str,
            children: list | None = None,
            value: Any | None = None,
            lineno: int | None = None,
            lexpos: int | None = None,
        ) -> 'AstNodeAggregate':
        '''
        Build an aggregate for a parent or a leaf.

        :param kind: The kind of generic node.
        :type kind: str
        :param children: The child nodes, or None for an empty list.
        :type children: list | None
        :param value: The optional value carried by this node.
        :type value: Any | None
        :param lineno: The optional source line of this node.
        :type lineno: int | None
        :param lexpos: The optional source character offset of this node.
        :type lexpos: int | None
        :return: The node aggregate.
        :rtype: AstNodeAggregate
        '''

        # Copy children so each node owns its list.
        owned = [] if children is None else list(children)

        # Build from the receiving class so a subclass factory stays a subclass.
        return cls(
            kind=kind,
            children=owned,
            value=value,
            lineno=lineno,
            lexpos=lexpos,
        )

    # * method: leaf
    @classmethod
    def leaf(
            cls,
            kind: str,
            value: Any,
            lineno: int | None = None,
            lexpos: int | None = None,
        ) -> 'AstNodeAggregate':
        '''
        Build a node with empty children and the given value.

        :param kind: The kind of generic node.
        :type kind: str
        :param value: The value carried by this leaf.
        :type value: Any
        :param lineno: The optional source line of this node.
        :type lineno: int | None
        :param lexpos: The optional source character offset of this node.
        :type lexpos: int | None
        :return: The leaf aggregate.
        :rtype: AstNodeAggregate
        '''

        # A leaf carries a value and no children.
        return cls.new(
            kind,
            children=[],
            value=value,
            lineno=lineno,
            lexpos=lexpos,
        )

    # * method: add_child
    def add_child(self, child: Any) -> None:
        '''
        Append a child node.

        :param child: The child to append.
        :type child: Any
        :return: None
        :rtype: None
        '''

        # Append without replacing the child list.
        self.children.append(child)

    # * method: set_value
    def set_value(self, value: Any) -> None:
        '''
        Assign the node value.

        :param value: The value to store.
        :type value: Any
        :return: None
        :rtype: None
        '''

        # Assign the value without formatting the node.
        self.value = value

    # * method: format
    def format(
            self,
            indent: str = DEFAULT_FORMAT_INDENT,
            step: str = DEFAULT_FORMAT_INDENT_STEP,
        ) -> str:
        '''
        Render this node as one deterministic tree string.

        The kind is always rendered. The value is a following line only
        when it is not None. Each child is rendered, in order, on the
        following indented lines. Line and character offsets are omitted.

        :param indent: The prefix for this node's own lines.
        :type indent: str
        :param step: The extra indent added for each child level.
        :type step: str
        :return: The rendered tree.
        :rtype: str
        '''

        # Render the kind. Source span is not part of the string.
        lines = [f'{indent}{self.kind}']

        # Include the value line only when a value is present.
        if self.value is not None:
            lines.append(f'{indent}{self.value}')

        # Render each child beneath this node, in stored order.
        child_indent = f'{indent}{step}'
        for child in self.children:
            lines.append(child.format(
                indent=child_indent,
                step=step,
            ))

        # Join the lines into one string.
        return '\n'.join(lines)
