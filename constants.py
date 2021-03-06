# coding:utf-8

PIC_CODE_EXPIRES_SECONDS = 180 # 图片验证码的有效期，单位秒
SMS_CODE_EXPIRES_SECONDS = 300 # 短信验证码的有效期，单位秒

SESSION_EXPIRES_SECONDS = 86400 # session数据有效期， 单位秒

REDIS_HOME_INFO_EXPIRES_SECONDES = 86400 # redis缓存主页信息的有效期


HOME_PAGE_MAX_HOUSES = 5 # 主页展示最大数量
HOME_PAGE_DATA_REDIS_EXPIRE_SECOND = 7200 # 主页缓存数据过期时间 秒

HOUSE_LIST_PAGE_CAPACITY = 3 # 列表页每页显示数目
HOUSE_LIST_PAGE_CACHE_NUM = 2 # 列表页每次缓存页面书

REDIS_HOUSE_LIST_EXPIRES_SECONDS = 7200 # 列表页数据缓存时间 秒


