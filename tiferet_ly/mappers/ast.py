"""Tiferet Ly AST Mappers"""

# *** imports

# ** core
from typing import Any

# ** app
from tiferet import Aggregate
from tiferet_ly.domain.ast import AstNode

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
