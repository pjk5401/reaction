import os

class Config:
    MYSQL_HOST = 'localhost'
    MYSQL_USER = os.getenv('DB_USER', 'root')
    MYSQL_PASSWORD = os.getenv('DB_PASSWORD', '1234')
    MYSQL_DB = os.getenv('DB_NAME', 'reaction_test')
