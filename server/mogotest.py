from pymongo import MongoClient

# MongoDB setup
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['migration_db']
credentials_collection = db['credentials']

# Fetch and print data
for credential in credentials_collection.find():
    print(credential)