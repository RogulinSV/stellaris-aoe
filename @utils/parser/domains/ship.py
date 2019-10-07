#!/usr/bin/env python
# -*- coding: utf-8 -*-

from parsing import BlockToken
from .common import Collection


class Ship(object):
    def __init__(self, name: str):
        self.__name = name
        self.__size = None
        self.__class_name = None

    def __str__(self):
        return self.__name

    @property
    def name(self) -> str:
        return self.__name

    @property
    def size(self) -> int:
        return self.__size

    @size.setter
    def size(self, value: int) -> int:
        self.__size = value

    @property
    def class_name(self) -> str:
        return self.__class_name

    @class_name.setter
    def class_name(self, value: int) -> int:
        self.__class_name = value

    @staticmethod
    def from_token(token: BlockToken):
        ship = Ship(token.name)
        ship.size = token.properties.get('size_multiplier')
        ship.class_name = token.properties.get('class')

        return ship


class Ships(Collection):
    def __contains__(self, ship: Ship):
        if not isinstance(ship, Ship):
            raise ValueError('Unexpected argument')

        if ship in self._items:
            return True

        for item in self._items:  # type: Ship
            if item.name == ship.name and ship.class_name == ship.class_name:
                return True

        return False

    def add(self, ship: Ship):
        if not isinstance(ship, Ship):
            raise ValueError('Unexpected argument')

        self._items.add(ship)
