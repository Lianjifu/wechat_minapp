#!/usr/bin/python
#encoding=utf-8
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import re
import time
import pprint
import MySQLdb
import tornado
import json
import logging

# 初始化 response
def f_rsp(res='Server Error', msg='50000', **kwargs):
    rsp = {'result': res, 'msg': msg}
    for k in kwargs:
        rsp[k] = kwargs[k]
    return rsp

# 记录 handler 开始时间
def api_log_start(handler_name):
    logging.info("### START " + handler_name + " ###")
    return None

# 记录 handler 结束时间及打印结果
def api_log_end(log, handler_name, dsplyRs=True):
    logging.info("### RESPONSE ###")
    if dsplyRs:
        pprint.pprint(log)
    logging.info("### END " + handler_name + " ###")
    return None

import os
# 最终结果的长度为 digits 的两倍
def random_string(digits=8):
    return ''.join(map(lambda xx:(hex(ord(xx))[2:]),os.urandom(digits)))

import hashlib
# 生成 AccessToken
def make_access_token():
    return str(hashlib.md5(random_string()).hexdigest().upper())

# 合并 SELECT 各个字段结果(元组 - ({'id_a':1,'id_b':2},{'id_a':6,'id_b':11},{..},{..}) )
# 返回以各字段为 key 的字典
def unify_db_select_cols(rsSel):
    udsc = {}
    if rsSel:
        for rs in rsSel:
            for key in rs:
                if udsc.has_key(key):
                    udsc[key].append(str(rs[key]))
                else:
                    udsc[key] = [str(rs[key])]
    return udsc


# json 封装 response 字典 并兼容中文（类似 \x70s）
def json_dumps_ensure_chinese(DictInfo):
    return json.dumps(DictInfo, ensure_ascii=False)

######################
# 数据处理及校验
######################

# 仅对 request arguments 的数据进行验证与转义
def EscapeArguments(obj):
    # RqstDt = {k: obj.get_argument(k) for k in obj.request.arguments}
    RqstDt = {}
    print "       ~~~~~ REAUEST ARGUMENTS ~~~~~: \n"
    pprint.pprint(obj.request.arguments)
    for k in obj.request.arguments:
        if k == 'email':
            temp = MySQLdb.escape_string(obj.get_argument(k))
            email_pattern = '(^[A-Z0-9a-z][\w\.-]*\w+@(?:[\w-]+\.)+[A-Za-z]{2,}$)|(^[0-9]+$)'
            p = re.compile(email_pattern)
            re_result = p.match(temp)
            if re_result:
                RqstDt[k] = temp
            else:
                RqstDt[k] = 'illegal'
                return False
        else:
            temp = MySQLdb.escape_string(obj.get_argument(k))
            RqstDt[k] = temp
    return RqstDt

# 对 request body 数据处理, ExpectParams 必要参数名单并且非空
# ExpectParamsOpt 可选参数名单(输入参数除了必要参数名单外的参数需在 ExpectParamsOpt 参数名单之内)并且非空
# OptionalParams 可为空值
def verify_request_body(obj, ExpectParams, ExpectParamsOpt=[], OptionalParams=[]):
    def verify_rules(RqstBody, VerifyKey):
        # 除了 OptionalParams，其它参数不能为空
        if (RqstBody.get(VerifyKey) == "") and (VerifyKey not in OptionalParams):
            return False
        # 邮箱格式验证
        if VerifyKey == 'email':
            temp = MySQLdb.escape_string(RqstBody.get(VerifyKey))
            email_pattern = '(^[A-Z0-9a-z][\w\.-]*\w+@(?:[\w-]+\.)+[A-Za-z]{2,}$)'
            p = re.compile(email_pattern)
            re_result = p.match(temp)
            if re_result:
                return temp
            else:
                return False
        else:
            print "abcdef:::",RqstBody.get(VerifyKey)
            if not isinstance(RqstBody.get(VerifyKey), str):
                if isinstance(RqstBody.get(VerifyKey), unicode):
                    return MySQLdb.escape_string(str(RqstBody.get(VerifyKey)))
                return RqstBody.get(VerifyKey)
            else:
                return MySQLdb.escape_string(RqstBody.get(VerifyKey))

    RqstDt = {}
    # print "input data body", pprint.pprint(tornado.escape.json_decode(obj.request.body))
    RqstBody = tornado.escape.json_decode(obj.request.body)
    if RqstBody:
        for ep in ExpectParams:
            if RqstBody.has_key(ep):
                RqstDt[ep] = verify_rules(RqstBody, ep)
                if not RqstDt[ep]:
                    return False
                    break
            else:
                return False
                break

    # 到了这一步, 证明 self.request.body 通过了必要参数 ExpectParams;
    # 并且 RqstDt 必有值;
    # 然后再判断是否有可选参数 ExpectParamsOpt 要检验
    if ExpectParamsOpt:
        for rbk in RqstBody.keys():
            if rbk in ExpectParamsOpt: # 在可选参数中但不在必要参数中
                RqstDt[rbk] = verify_rules(RqstBody, rbk)
                if not RqstDt[rbk]:
                    return False
                    break

    if OptionalParams:
        for rbk in RqstBody.keys():
            if rbk in OptionalParams: # 在可选参数中但不在必要参数中
                RqstDt[rbk] = verify_rules(RqstBody, rbk)

    return RqstDt

# 对 request arguments 的数据进行验证与转义，ExpectParams 待校验参数列表
def InputVerified(obj, ExpectParams):
    # RqstDt = {k: obj.get_argument(k) for k in obj.request.arguments}
    RqstDt = {}
    msg = {}
    logging.info("### REQUEST ###")
    pprint.pprint(obj.request.arguments)
    p_flag = True
    if ExpectParams and isinstance(ExpectParams, list):
        # 传入参数
        r_params = obj.request.arguments
        for p_value in ExpectParams:
            if r_params.has_key(p_value):
                if obj.get_argument(p_value) == "" and p_value != "device_token":
                    p_flag=False
                    break
                # 邮箱格式验证
                if p_value == 'email':
                    temp = MySQLdb.escape_string(obj.get_argument(p_value))
                    email_pattern = '(^[A-Z0-9a-z][\w\.-]*\w+@(?:[\w-]+\.)+[A-Za-z]{2,}$)'
                    p = re.compile(email_pattern)
                    re_result = p.match(temp)
                    if re_result:
                        RqstDt[p_value] = temp
                    else:
                        p_flag = False
                        break
                # 参数格式校验
                elif False:
                    pass
                else:
                    RqstDt[p_value] = MySQLdb.escape_string(obj.get_argument(p_value))
            else:
                p_flag = False
                break
    else:
        p_flag = False
    if not p_flag:
        RqstDt = {}
    return RqstDt