from database import store as db_store


class MultiDB:
    def __init__(self):
        self.db_map = {}

    def insert_into_db(self, db_name, table, item:dict):
        if db_name not in self.db_map:
            self.db_map[db_name] = self.create_db(db_name)

        self.db_map[db_name].store_insert(table, item)

    def create_db(self, db_name):
        return db_store.Store(db_name)
