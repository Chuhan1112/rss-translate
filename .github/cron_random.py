import random

# coding:utf-8 

# 生成一个在早上的小时数、中午的小时数、晚上的小时数和凌晨的小时数
h_morning = random.randint(7, 11)
h_afternoon = random.randint(12, 16)
h_evening = random.randint(17, 20)
h_midnight = random.randint(0, 6)

# 分钟数可以固定，也可以随机
min_morning = random.randint(0, 59)
min_afternoon = random.randint(0, 59)
min_evening = random.randint(0, 59)
min_midnight = random.randint(0, 59)

YML = ".github/workflows/circle_translate.yml"

f = open(YML, "r+", encoding="UTF-8")
list1 = f.readlines()
# 设置四个时间段的时间点
list1[15] = "   - cron: '%d %d * * *'\n" % (min_morning, h_morning)
list1[16] = "   - cron: '%d %d * * *'\n" % (min_afternoon, h_afternoon)
list1[17] = "   - cron: '%d %d * * *'\n" % (min_evening, h_evening)
list1[18] = "   - cron: '%d %d * * *'\n" % (min_midnight, h_midnight)

f = open(YML, "w+", encoding="UTF-8")
f.writelines(list1)
f.close()
