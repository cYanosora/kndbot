from typing import Optional

# 回复消息名称
NICKNAME: str = "小奏"

# bot一号机
MAIN_BOT: int = 2953928559
# bot二号机
SUB_BOT: int = 2488024911

# 数据库（必要）
# 如果填写了bind就不需要再填写后面的字段了#）
# 示例："bind": "postgresql://user:password@127.0.0.1:5432/database"
bind: str = "postgresql://kanade:kawaii@127.0.0.1:5432/botdb"  # 数据库连接链接
sql_name: str = "postgresql"
user: str = "kanade"  # 数据用户名
password: str = "kawaii"  # 数据库密码
address: str = "127.0.0.1"  # 数据库地址
port: str = "5432"  # 数据库端口
database: str = "botdb"  # 数据库名称

# 代理，例如 "http://127.0.0.1:7890"
SYSTEM_PROXY: Optional[str] = None  # 全局代理


