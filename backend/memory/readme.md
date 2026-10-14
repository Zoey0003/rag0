# 需要修改数据库中某类字段或者增加数据库数据类型的时候  
1：修改model类
2：迁移环境初始化：
cd D:\1pyproject\rag0\backend
python -m alembic revision --autogenerate -m "add session history summary"

backend\migrations\versions下会多一个迁移后修改字段的的文件记录
3：执行迁移
python -m alembic upgrade head
