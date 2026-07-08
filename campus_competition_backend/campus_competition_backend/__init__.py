import pymysql

# 核心修复：手动指定伪装的版本号，骗过 Django 的版本检查
pymysql.version_info = (1, 4, 6, 'final', 0)  # 伪装成 mysqlclient 1.4.6
pymysql.install_as_MySQLdb()