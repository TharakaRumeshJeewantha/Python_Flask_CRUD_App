#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
# @Time : 2019/5/23 10:36 
# @File : __init__.py
# @Author : Wangji 
# @Software: PyCharm


import logging
import os
from collections import OrderedDict

import pymysql
from flask import render_template, Blueprint


class FlaskMysqlHTML(object):
    def __init__(self, app, blueprint_api="db", url_prefix="/db", index="db"):
        self.__app = app
        self.__path = os.path.dirname(__file__)
        self.__temp_path = os.path.join(self.__path, "templates")
        self.__db_api = Blueprint(blueprint_api, __name__, url_prefix=url_prefix, template_folder=self.__temp_path)
        self.__db_api.add_url_rule('/<string:name>', index, self.v2_listModel)
        self.__app.register_blueprint(self.__db_api)
        self.db_api = self.__db_api
        self._url_dict = {}
        self.get_url_mysql()

    def get_url_mysql(self):
        if "URL_LIST" not in self.__app.config.keys():
            logging.warning("URL_LIST is None")
            return
        self._urls_list = self.__app.config.get("URL_LIST", [])

        for _url in self._urls_list:
            try:
                url_list = _url.rsplit("@", 1)
                _user_pwd = url_list[0][8:].split(":", 1)
                _user = _user_pwd[0]
                _pwd = _user_pwd[-1]
                _host = url_list[-1].split("/")[0].split(":")[0]
                _port = int(url_list[-1].split("/")[0].split(":")[-1])
                _dbname = url_list[-1].split("/")[-1]
                _url_dict = {
                    'host': _host,
                    'port': _port,
                    'user': _user,
                    'password': _pwd,
                    'db': _dbname,
                    'charset': 'utf8',
                    # 'cursorclass': pymysql.cursors.DictCursor,
                }
                self._url_dict[_dbname] = _url_dict
            except:
                logging.warning("mysql连接有问题！{}".format(_url))

    def conenct_mysql(self, dbname):
        for _db, _url in self._url_dict.items():
            if _db == dbname:
                self._db = pymysql.connect(**_url)
                break
        self._db_cur = self._db.cursor()
        return self._db_cur

    def v2_listModel(self, name):
        if name not in self._url_dict.keys():
            return "hello,world!"
        self.__db = self.conenct_mysql(dbname=name)
        dbName = name
        all_tableStr = """select table_name,table_comment,TABLE_TYPE from information_schema.tables where TABLE_TYPE in ('BASE TABLE','VIEW') and  table_schema='{}'""".format(
            dbName)
        allresultList = self.executeSql(all_tableStr)
        tableresultList = []
        viewresultList = []
        if allresultList:
            for result in allresultList:
                if result[2] == "BASE TABLE":
                    tableresultList.append([result[0], result[1]])
                else:
                    viewresultList.append([result[0], result[1]])
        _infoList = []
        if tableresultList:
            rowTable = self.v2_listModels(tableresultList, dbName)
        else:
            rowTable = {}
        if viewresultList:
            rowView = self.v2_listModels(viewresultList, dbName)
        else:
            rowView = {}
        self._db.close()
        return render_template("demos.html", rows=rowTable, dbName=dbName, rowView=rowView)

    def executeSql(self, sqlStr):
        try:
            self.__db.execute(sqlStr)
            queryList = self.__db.fetchall()
            return queryList
        except Exception as  e:
            print(e)
            return {}

    def v2_listModels(self, tableresultList, dbName):
        resultList = []
        table_name_dict = OrderedDict()
        resultConmentDict = OrderedDict()
        for table in tableresultList:
            resultConmentDict[str(table[0])] = table[1]
            resultList.append(str(table[0]))
            table_name_dict[str(table[0])] = []
        if len(resultList) == 1:
            resultList = str(tuple(resultList)).replace(",", "")
        elif len(resultList) > 1:
            resultList = tuple(resultList)
        else:
            return
        filedStr = """select ORDINAL_POSITION,column_name,COLUMN_COMMENT,DATA_TYPE,CHARACTER_MAXIMUM_LENGTH,numeric_precision,numeric_scale,COLUMN_KEY,COLUMN_DEFAULT,IS_NULLABLE,table_name from information_schema.columns where  table_schema='{}' and table_name in {} """.format(
            dbName, resultList)
        filedList = self.executeSql(filedStr)
        _infoList = []
        k = []
        if filedList:
            for index, field in enumerate(filedList):
                tableName = field[10]
                if field[3] == "datetime":
                    k.append(tableName)
                if field[5]:
                    CHARACTER_MAXIMUM_LENGTH = field[5]
                elif field[4]:
                    CHARACTER_MAXIMUM_LENGTH = field[4]
                else:
                    CHARACTER_MAXIMUM_LENGTH = 0
                if field[9] == "YES":
                    IS_NULLABLE = "Y"
                else:
                    IS_NULLABLE = "N"
                _infoDict = {
                    "ORDINAL_POSITION": field[0],
                    "column_name": field[1],
                    "COLUMN_COMMENT": field[2],
                    "DATA_TYPE": field[3],
                    "CHARACTER_MAXIMUM_LENGTH": CHARACTER_MAXIMUM_LENGTH,
                    "numeric_scale": field[6] if field[6] else 0,
                    "COLUMN_KEY": "Y" if field[7] else "",
                    "COLUMN_DEFAULT": field[8] if field[8] else "",
                    "IS_NULLABLE": IS_NULLABLE,
                }
                table_name_dict[tableName].append(_infoDict)
            for key, value in table_name_dict.items():
                infoDict = {
                    "index": len(_infoList) + 1,
                    "tableName": key,
                    "table_comment": resultConmentDict[key],
                    "fields": value
                }
                _infoList.append(infoDict)
        return _infoList
