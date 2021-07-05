#!/usr/bin/env python
#-*- coding:utf8 -*-

from database.dispatch import MultiDB

class Dash(object):
    def __init__(self):
        self.multidb = MultiDB()
    
    def query_database(self,db,sql):
        return self.multidb.query_db(db,sql)