#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
# @Time : 2019/5/23 10:33 
# @File : demo
# @Author : Wangji 
# @Software: PyCharm


from flask import Flask
from flask_look_mysql import FlaskLookMysql

app = Flask(__name__)
app.config["URL_LIST"] = ["mysql://root:cmic@123@10.30.0.171:3306/backendadmin"]
FlaskLookMysql(app)

if __name__ == '__main__':
    app.run()