"""Tiferet Ly Production Service"""

# *** imports

# ** core
from abc import abstractmethod

# ** app
from tiferet.interfaces import Service
from tiferet_ly.mappers.production import ProductionRuleAggregate

# *** interfaces

# ** interface: production_service
class ProductionService(Service):
    '''
    The configuration contract for declared production rules stored as ordered alternatives.

    A repeated name and grammar is a legal alternative, not a duplicate. Pair
    lookup returns the first stored alternative. Saving and removing one
    alternative uses the specification so its siblings stay in place.
    '''

    # * method: exists
    @abstractmethod
    def exists(self, name: str, grammar_id: str) -> bool:
        '''
        Report whether any stored production has the exact name and grammar pair.

        :param name: The declared production name.
        :type name: str
        :param grammar_id: The grammar that owns the production.
        :type grammar_id: str
        :return: True when a stored production has that pair, otherwise False.
        :rtype: bool
        '''

        # Pair lookup has no specification parameter.
        raise NotImplementedError()

    # * method: get
    @abstractmethod
    def get(self, name: str, grammar_id: str) -> ProductionRuleAggregate | None:
        '''
        Return the first stored production with the exact name and grammar pair.

        :param name: The declared production name.
        :type name: str
        :param grammar_id: The grammar that owns the production.
        :type grammar_id: str
        :return: The first matching production aggregate, or None.
        :rtype: ProductionRuleAggregate | None
        '''

        # Pair lookup has no specification parameter.
        raise NotImplementedError()

    # * method: list
    @abstractmethod
    def list(self) -> list[ProductionRuleAggregate]:
        '''
        Return every stored production, unfiltered, in declared order.

        :return: The stored production aggregates.
        :rtype: list[ProductionRuleAggregate]
        '''

        # Listing does not collapse alternatives.
        raise NotImplementedError()

    # * method: save
    @abstractmethod
    def save(self, production: ProductionRuleAggregate) -> None:
        '''
        Replace the row with the same name, grammar, and spec, or append.

        A different specification is a different stored alternative. This
        operation does not replace the first pair.

        :param production: The production aggregate to persist.
        :type production: ProductionRuleAggregate
        :return: None
        :rtype: None
        '''

        # Triple identity keeps sibling alternatives.
        raise NotImplementedError()

    # * method: delete
    @abstractmethod
    def delete(self, name: str, grammar_id: str) -> None:
        '''
        Remove the first matching pair. Absence does not raise.

        :param name: The declared production name.
        :type name: str
        :param grammar_id: The grammar that owns the production.
        :type grammar_id: str
        :return: None
        :rtype: None
        '''

        # Pair deletion has no specification parameter.
        raise NotImplementedError()

    # * method: replace
    @abstractmethod
    def replace(
            self,
            old_name: str,
            old_grammar_id: str,
            old_spec: str,
            production: ProductionRuleAggregate,
        ) -> None:
        '''
        Replace the old triple in its original index. An absent triple does not append.

        :param old_name: The stored production name to replace.
        :type old_name: str
        :param old_grammar_id: The stored grammar id to replace.
        :type old_grammar_id: str
        :param old_spec: The stored specification to replace.
        :type old_spec: str
        :param production: The production aggregate to write at that index.
        :type production: ProductionRuleAggregate
        :return: None
        :rtype: None
        '''

        # An absent old triple is not an append.
        raise NotImplementedError()

    # * method: delete_alternative
    @abstractmethod
    def delete_alternative(
            self,
            name: str,
            grammar_id: str,
            spec: str,
        ) -> None:
        '''
        Remove only the matching triple. Absence does not raise.

        :param name: The declared production name.
        :type name: str
        :param grammar_id: The grammar that owns the production.
        :type grammar_id: str
        :param spec: The specification of the alternative to remove.
        :type spec: str
        :return: None
        :rtype: None
        '''

        # A different specification that shares the pair stays stored.
        raise NotImplementedError()
