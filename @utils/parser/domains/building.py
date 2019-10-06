#!/usr/bin/env python
# -*- coding: utf-8 -*-

from parsing import BlockToken
from .common import Collection


class Upgrades(object):
    __instance = None

    def __new__(class_name):
        if class_name.__instance is None:
            class_name.__instance = super(Upgrades, class_name).__new__(class_name)
            class_name.__instance.__upgrades_from = dict()
            class_name.__instance.__upgrades_into = dict()

        return class_name.__instance

    def set(self, building: str, upgrades: list):
        for upgrade in upgrades:
            self.add(building, upgrade)

    def add(self, building: str, upgrade: str):
        if building not in self.__upgrades_into:
            self.__upgrades_into[building] = set()
        if upgrade not in self.__upgrades_from:
            self.__upgrades_from[upgrade] = set()

        self.__upgrades_from[upgrade].add(building)
        self.__upgrades_into[building].add(upgrade)

    def path(self, building: str) -> list:
        if building not in self.__upgrades_from:
            return list()

        upgrades = list()
        for upgrade in self.__upgrades_from.get(building):
            upgrades_path = self.path(upgrade)
            if len(upgrades_path) > 0:
                for upgrade_path in upgrades_path:
                    upgrades.append((upgrade, *(upgrade_path)))
            else:
                upgrades.append((upgrade,))

        upgrades.sort(key=lambda upgrades: len(upgrades), reverse=True)

        return upgrades


class Building(object):
    def __init__(self, name: str):
        self.__name = name
        self.__category = None
        self.__upgrades = Upgrades()

    @property
    def name(self) -> str:
        return self.__name

    @property
    def category(self) -> str:
        return self.__category

    @category.setter
    def category(self, category: str):
        self.__category = category

    @property
    def upgrade(self) -> list:
        return self.__upgrades.path(self.__name)

    @upgrade.setter
    def upgrade(self, upgrade: str):
        self.__upgrades.add(self.__name, upgrade)

    @staticmethod
    def from_token(token: BlockToken):
        building = Building(token.name)
        building.category = token.properties.get('category')
        if 'upgrades' in token.properties:
            for upgrade in token.properties.get('upgrades'):
                building.upgrade = upgrade

        return building


class Buildings(Collection):
    def __contains__(self, building: Building):
        if not isinstance(building, Building):
            raise ValueError('Unexpected argument')

        if building in self._items:
            return True

        for item in self._items:  # type: Building
            if item.name == building.name and item.category == building.category:
                return True

        return False

    def add(self, building: Building):
        if not isinstance(building, Building):
            raise ValueError('Unexpected argument')

        self._items.add(building)

    def categories(self) -> list:
        categories = set()
        for building in self._items:
            if building.category is not None:
                categories.add(building.category)

        return categories
