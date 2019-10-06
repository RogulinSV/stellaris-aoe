#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import atexit
from json import JSONDecodeError


class Cache(object):
    def __init__(self, cache_path: str):
        self.__cache_path = cache_path
        self.__cache_data = None
        self.__cache_changed = False
        atexit.register(lambda cache: cache.flush(), self)

    def __initialize(self) -> dict:
        if self.__cache_data is None:
            if os.path.exists(self.__cache_path):
                with open(self.__cache_path, 'rt') as handler:
                    self.__cache_data = json.load(handler)
            else:
                self.__cache_data = dict()

        return self.__cache_data

    def get(self, *args):
        cache_data = self.__initialize()
        for i, cache_key in enumerate(args):
            if not isinstance(cache_data, dict):
                raise ValueError('Key %s not exists in cache' % args[:i + 1])
            if cache_key in cache_data:
                cache_data = cache_data.get(cache_key)
            else:
                return None

        return cache_data

    def has(self, *args) -> bool:
        return self.get(*args) is not None

    def set(self, value, key: str, *args):
        cache_data = self.__initialize()
        for i, cache_key in enumerate(args):
            if not isinstance(cache_data, dict):
                raise ValueError('Key %s not exists in cache' % args[:i + 1])
            if cache_key not in cache_data:
                cache_data[cache_key] = dict()
            cache_data = cache_data.get(cache_key)

        if not isinstance(cache_data, dict):
            raise ValueError('Key %s in cache is not a dictionary' % args)

        if key not in cache_data or cache_data.get(key) != value:
            self.__cache_changed = True
        cache_data[key] = value

    def flush(self):
        if self.__cache_changed:
            with open(self.__cache_path, 'wt') as handler:
                json.dump(self.__initialize(), handler)
            self.__cache_changed = False

    def locate(self) -> str:
        return self.__cache_path
