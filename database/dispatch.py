from database import store as db_store


class MultiDB:
    def __init__(self):
        self.db_map = {}

    def insert_into_db(self, db_name, table, item:dict):
        if db_name not in self.db_map:
            self.db_map[db_name] = self.create_db(db_name)
        self.db_map[db_name].store_insert(table, item)
    
    def insert_ingore_into_db(self,db_name,table,item:dict):
        if db_name not in self.db_map:
            self.db_map[db_name] = self.create_db(db_name)
        self.db_map[db_name].store_ignore_insert(table, item)

    def insert_update_into_db(self,db_name,table,item:dict,update_item:list):
        if db_name not in self.db_map:
            self.db_map[db_name] = self.create_db(db_name)
        self.db_map[db_name].store_insert_update(table,item,update_item)

    def create_db(self, db_name):
        return db_store.Store(db_name)
    

    # for dash query_core use:

    def query_db(self,db_name,sql):
        if db_name not in self.db_map:
            self.db_map[db_name] = self.create_db(db_name)

        return self.db_map[db_name].query(sql)
