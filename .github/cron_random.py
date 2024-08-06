# coding:utf-8 
import random

# 生成一个在上午的小时数和一个在下午的小时数
h_morning = random.randint(7, 11)
h_afternoon = random.randint(12, 23)

# 分钟数可以固定，也可以随机
min_morning = random.randint(0, 59)
min_afternoon = random.randint(0, 59)

YML = ".github/workflows/circle_translate.yml"

f = open(YML, "r+", encoding="UTF-8")
list1 = f.readlines()
# 设置一个在上午，一个在下午的时间点
list1[7] = "   - cron: '%d %d * * *'\n" % (min_morning, h_morning)
list1[8] = "   - cron: '%d %d * * *'\n" % (min_afternoon, h_afternoon)

f = open(YML, "w+", encoding="UTF-8")
f.writelines(list1)
f.close()
