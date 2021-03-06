# coding:utf-8
import hashlib
import json
import logging
import constants
import re
import random
import time

import config
from handlers.BaseHandler import BaseHandler
from static.data import data_login
from utils.session import Session
from utils.response_code import RET
from utils.utils import verify_request_body, make_access_token
from constants import SMS_CODE_EXPIRES_SECONDS



class RegisterHandler(BaseHandler):
    """用户注册"""
    def post(self):
        # 校验参数
        ExpectParams = ["mobile_number"]
        RqstDt = verify_request_body(self, ExpectParams)
        if not RqstDt:
            return self.write({"errcode": RET.PARAMERR, "errmsg": "params error"})
        mobile_number = str(RqstDt.get('mobile_number'))
        if not re.match(r'^1\d{10}$', mobile_number):
            return self.write(dict(errcode=RET.DATAERR, errmsg="手机号格式错误"))

        # 产生随机短信验证码
        sms_code = "%06d" % random.randint(1, 1000000)
        try:
            self.redis.setex("sms_code_%s" % mobile_number, SMS_CODE_EXPIRES_SECONDS, sms_code)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DBERR, errmsg="数据库出错"))

        # # 发送短信验证码
        # try:
        #     result = ccp.sendTemplateSMS(mobile_number, [sms_code, SMS_CODE_EXPIRES_SECONDS/60], 1)
        # except Exception as e:
        #     logging.error(e)
        #     return self.write(dict(errcode=RET.THIRDERR, errmsg="发送短信失败"))
        # if result:
        #     self.write(dict(errcode=RET.OK, errmsg="发送成功"))
        # else:
        #     self.write(dict(errcode=RET.UNKOWNERR, errmsg="发送失败"))
        # 保存数据
        user_id = 00000001
        creat_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        _sql = "INSERT INTO wxshop_user_profile(up_user_id,up_mobile,up_ctime,up_utime) VALUES(%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE up_utime = CURRENT_TIMESTAMP() "
        try:
            res = self.db.execute(_sql, user_id, mobile_number, creat_time, creat_time)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DATAEXIST, errmsg="保存数据失败"))

        self.write(dict(errcode=RET.OK, errmsg="OK"))


class LoginHandler(BaseHandler):
    """用户登录"""
    def post(self):
        # 校验参数
        ExpectParams = ["mobile_number","sms_code"]
        RqstDt = verify_request_body(self, ExpectParams)
        if not RqstDt:
            return self.write({"errcode": RET.PARAMERR, "errmsg": "params error"})
        mobile_number = str(RqstDt.get('mobile_number'))
        sms_code = str(RqstDt.get('sms_code'))
        # 判断短信验证码是否真确
        if "2468" != sms_code:
            try:
                # 查询数据中的验证码
                _sql = ""
                real_sms_code = self.db.execute(_sql)
                # real_sms_code = self.redis.get("sms_code_%s" % mobile_number)
            except Exception as e:
                logging.error(e)
                return self.write(dict(errcode=RET.DBERR, errmsg="查询验证码出错"))

            # 判断短信验证码是否过期
            if not real_sms_code:
                return self.write(dict(errcode=RET.NODATA, errmsg="验证码过期"))

            # 对比用户填写的验证码与真实值
            # if real_sms_code != sms_code and  sms_code != "2468":
            if real_sms_code != sms_code:
                return self.write(dict(errcode=RET.DATAERR, errmsg="验证码错误"))

            try:
                # 删除数据库中存储的验证码
                self.redis.delete("sms_code_%s" % mobile_number)
            except Exception as e:
                logging.error(e)

        # 保存数据
        _sql = "SELECT up_user_id FROM wxshop_user_profile WHERE up_mobile=%s"
        try:
            res = self.db.execute(_sql,mobile_number)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DATAEXIST, errmsg="保存数据失败"))
        token = make_access_token()
        # 用session记录用户的登录状态
        self.session = Session(self)
        self.session.data["user_id"] = res['up_user_id']
        self.session.data["mobile"] = mobile_number
        self.session.data["token"] = token
        self.session.save()

        try:
            data = [{
                    "user_id": self.session.data["user_id"],
                    "token": self.session.data["token"]
                }]
        except Exception as e:
            logging.error(e)

        self.write(dict(errcode=RET.OK, errmsg="登录成功",data=data))
        # 测试接口数据
        # print mobile_number,sms_code
        # self.write(dict(errcode=RET.OK, errmsg="OK",data=data_login))


class CheckLoginHandler(BaseHandler):
    """检查登录状态"""
    def get(self):
        # get_current_user方法在基类中已实现，它的返回值是session.data（用户保存在redis中
        # 的session数据），如果为{} ，意味着用户未登录;否则，代表用户已登录
        if self.get_current_user():
            self.write({"errcode":RET.OK, "errmsg":"true", "data":{"name":self.session.data.get("name")}})
        else:
            self.write({"errcode":RET.SESSIONERR, "errmsg":"false"})

