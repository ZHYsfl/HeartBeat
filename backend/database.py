from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 使用SQLite数据库，数据库文件名为 a_love_story.db
SQLALCHEMY_DATABASE_URL = "sqlite:///./a_love_story.db"


# SQLite 默认限制同一连接仅能被创建它的线程使用，这里关闭检查是为了让同一个连接可以被不同线程复用，便于在 Web 场景下运行。
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 创建每次请求使用的数据库会话工厂。autocommit=False 意味着你需要显式 db.commit()；autoflush=False 可以避免在访问属性时自动发出 flush，通常搭配手动控制提交更直观。
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# SQLAlchemy ORM 的基类，所有模型类都要继承它，才能参与建表与映射。
Base = declarative_base()

# Dependency to get DB session
# 这是一个 FastAPI 的依赖函数，使用生成器 yield 出一个新的会话对象 db，并在请求结束后 finally: db.close() 确保资源释放。
# 在路由中通过 Depends(get_db) 注入会话，这样每次请求得到隔离的会话，线程安全且生命周期明确。
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()