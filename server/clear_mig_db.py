from pymongo import MongoClient

# Configuración de MongoDB
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['migration_db']
migration_collection = db['migration_history']

def drop_all_migrations():
    try:
        result = migration_collection.delete_many({})
        print(f"Deleted {result.deleted_count} documents from 'migration_collection'.")
    except Exception as e:
        print(f"Error deleting documents from 'migration_collection': {e}")

if __name__ == '__main__':
    drop_all_migrations()