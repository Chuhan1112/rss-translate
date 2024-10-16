import random

YML = ".github/workflows/circle_translate.yml"

# 生成白天的小时数列表（8点到20点）
day_hours = list(range(8, 21))

# 生成晚上的小时数列表（0点到7点）
night_hours = list(range(0, 8))

# 随机选择晚上的两个小时数
random_night_hours = random.sample(night_hours, 2)

# 分钟数可以固定，也可以随机
minute = random.randint(0, 59)

with open(YML, "r+", encoding="UTF-8") as f:
    list1 = f.readlines()

# 设置白天每小时的时间点
for i, hour in enumerate(day_hours):
    list1[15 + i] = "   - cron: '%d %d * * *'\n" % (minute, hour)

# 设置晚上的两个随机时间点
list1[15 + len(day_hours)] = "   - cron: '%d %d * * *'\n" % (minute, random_night_hours[0])
list1[16 + len(day_hours)] = "   - cron: '%d %d * * *'\n" % (minute, random_night_hours[1])

with open(YML, "w+", encoding="UTF-8") as f:
    f.writelines(list1)