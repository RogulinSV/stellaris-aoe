#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import logging
import urllib.request
from urllib.error import URLError

from caching import Cache
from domains import Technologies, Buildings, Ships, Categories as TraditionCategories


def fetch_url(url: str) -> bytes:
    with urllib.request.urlopen(url) as response:
        return response.read()


def detect_module(module_id: int, module_url: str, cache: Cache = None) -> str:
    module_id = str(module_id)
    if cache is not None and cache.has('modules', module_id):
        return cache.get('modules', module_id)

    page_content = None
    logging.debug('-> fetching module (%s) name from %s...' % (module_id, module_url))
    try:
        page_content = fetch_url(module_url).decode('UTF-8')
    except URLError as err:
        logging.error('Error occurred while fetching url %s: %s' % (module_url, err))
    except OSError as err:
        logging.error('Error occurred while fetching module data: %s' % err)

    module_name = None
    if page_content is not None:
        module_name = re.search(r'<title>([^>]+)</title>', page_content).group(1)

        if module_name is not None:
            module_name = module_name.replace('Steam Workshop ::', '')
            module_name = module_name.strip()
            logging.debug('-> fetched module (%s) name as "%s"' % (module_id, module_name))

            if cache is not None:
                cache.set(module_name, module_id, 'modules')

    return module_name


class Module(object):
    def __init__(self, id):
        self.__id = id
        self.__name = str(id)
        self.__technologies = None
        self.__buildings = None
        self.__ships = None
        self.__traditions = None

    def __str__(self):
        return '(%s) %s' % (str(self.__id), str(self.__name))

    @property
    def id(self):
        return self.__id

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, value: str):
        self.__name = value

    @property
    def technologies(self) -> Technologies:
        return self.__technologies

    @technologies.setter
    def technologies(self, value: Technologies):
        self.__technologies = value

    @property
    def buildings(self) -> Buildings:
        return self.__buildings

    @buildings.setter
    def buildings(self, value: Buildings):
        self.__buildings = value

    @property
    def ships(self) -> Ships:
        return self.__ships

    @ships.setter
    def ships(self, value: Ships):
        self.__ships = value

    @property
    def traditions(self) -> TraditionCategories:
        return self.__traditions

    @traditions.setter
    def traditions(self, value: TraditionCategories):
        self.__traditions = value

    @staticmethod
    def url(module_id: int) -> str:
        return 'https://steamcommunity.com/sharedfiles/filedetails/?id=' + str(module_id)


class Settings(object):
    def __init__(self):
        self.__settings = dict()
        self.__modules = dict()

    def __contains__(self, item):
        return item in self.__settings

    def get(self, key: str):
        return self.__settings.get(key)

    def set(self, key: str, item):
        self.__settings[key] = item
