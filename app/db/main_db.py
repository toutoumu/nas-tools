import os
import threading
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import log
from app.db.models import Base
from config import Config
from app.utils.commons import singleton
from app.utils import PathUtils

lock = threading.Lock()


@singleton
class MainDb:
    __connection = None
    __engine = None
    __session = None

    def __init__(self):
        self.init_config()
        self.__init_tables()
        self.__cleardata()
        self.__initdata()

    def init_config(self):
        config = Config()
        if not config.get_config_path():
            log.console("【Config】NASTOOL_CONFIG 环境变量未设置，程序无法工作，正在退出...")
            quit()
        self.__engine = create_engine(f"sqlite:///{os.path.join(config.get_config_path(), 'user.db')}",
                                      echo=True,
                                      pool_recycle=60 * 30
                                      )
        self.__session = sessionmaker(bind=self.__engine)()

    def __init_tables(self):
        Base.metadata.create_all(self.__engine)

    def __cleardata(self):
        self.__excute(
            """DELETE FROM SITE_USER_INFO_STATS 
                WHERE EXISTS (SELECT 1 
                    FROM SITE_USER_INFO_STATS p2 
                    WHERE SITE_USER_INFO_STATS.URL = p2.URL 
                    AND SITE_USER_INFO_STATS.rowid < p2.rowid);""")
        self.__excute(
            """DELETE FROM SITE_STATISTICS_HISTORY 
                WHERE EXISTS (SELECT 1 
                    FROM SITE_STATISTICS_HISTORY p2 
                    WHERE SITE_STATISTICS_HISTORY.URL = p2.URL 
                    AND SITE_STATISTICS_HISTORY.DATE = p2.DATE 
                    AND SITE_STATISTICS_HISTORY.rowid < p2.rowid);""")

    def __initdata(self):
        config = Config().get_config()
        init_files = Config().get_config("app").get("init_files") or []
        config_dir = os.path.join(Config().get_root_path(), "config")
        sql_files = PathUtils.get_dir_level1_files(in_path=config_dir, exts=".sql")
        config_flag = False
        for sql_file in sql_files:
            if os.path.basename(sql_file) not in init_files:
                config_flag = True
                with open(sql_file, "r", encoding="utf-8") as f:
                    sql_list = f.read().split(';\n')
                    for sql in sql_list:
                        self.__excute(sql)
                init_files.append(os.path.basename(sql_file))
        if config_flag:
            config['app']['init_files'] = init_files
            Config().save_config(config)

    def __excute(self, sql, data=None):
        if not sql:
            return False
        with lock:
            with self.__engine.connect() as conn:
                try:
                    if data:
                        conn.execute(sql, data)
                    else:
                        conn.execute(sql)
                    conn.commit()
                except Exception as e:
                    log.debug(f"【Db】执行SQL出错：sql:{sql}; parameters:{data}; {e}")
                    return False
                return True

    def __excute_many(self, sql, data_list):
        if not sql or not data_list:
            return False
        with lock:
            with self.__engine.connect() as conn:
                try:
                    if data_list:
                        conn.execute(sql, data_list)
                    else:
                        conn.execute(sql)
                    conn.commit()
                except Exception as e:
                    log.debug(f"【Db】执行SQL出错：sql:{sql}; parameters:{data_list}; {e}")
                    return False
                return True

    def __select(self, sql, data):
        if not sql:
            return False
        with lock:
            with self.__engine.connect() as conn:
                try:
                    if data:
                        return conn.execute(sql, data)
                    else:
                        return conn.execute(sql)
                except Exception as e:
                    log.debug(f"【Db】执行SQL出错：sql:{sql}; parameters:{data}; {e}")
                    return []

    def select_by_sql(self, sql, data=None):
        """
        执行查询
        :param sql: 查询的SQL语句
        :param data: 数据，需为列表或者元祖
        :return: 查询结果的二级列表
        """
        return self.__select(sql, data)

    def update_by_sql(self, sql, data=None):
        """
        执行更新或删除
        :param sql: SQL语句
        :param data: 数据，需为列表或者元祖
        :return: 执行状态
        """
        return self.__excute(sql, data)

    def update_by_sql_batch(self, sql, data_list):
        """
        执行更新或删除
        :param sql: 批量更新SQL语句
        :param data_list: 数据列表
        :return: 执行状态
        """
        return self.__excute_many(sql, data_list)
