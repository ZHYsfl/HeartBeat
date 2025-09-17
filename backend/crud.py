# CRUD 是 C reate（增）, R ead（查）, U pdate（改）, D elete（删）这四个单词的首字母缩写。
# 它的核心思想是： 将业务逻辑（API 路由）与数据持久化逻辑（数据库操作）分离开 。
# main.py (业务逻辑层) : 负责处理 HTTP 请求、解析请求体、验证路径参数、调用认证依赖、返回 HTTP 响应。它关心的是“程序的入口和出口”。
# crud.py (数据逻辑层) : 负责所有直接与数据库交互的操作。它接收来自业务逻辑层的数据，然后执行具体的数据库查询、插入、更新或删除，并返回结果。它关心的是“如何与数据表打交道”。
# 这种分离带来了巨大的好处：
# - 代码清晰 : main.py 不会充斥着大量的数据库查询语句，变得非常整洁。
# - 可维护性 : 如果底层数据库换了（比如从 SQLite 换成 PostgreSQL），或者查询方式需要优化，我们很可能只需要修改 crud.py 里的函数，而 main.py 的代码可以保持不变。
# - 可测试性 : 我们可以独立地测试 crud.py 中的数据库函数，确保它们工作正常。

# 数据库操作：
# - db.commit() : 将你做的所有更改“写入”数据库 。
# - db.refresh() : 用数据库里的最新状态“刷新”你的 Python 对象 。
# - db.add() : 将新创建的对象添加到数据库会话中。
# - db.delete() : 将对象从数据库会话中删除。

from sqlalchemy.orm import Session, joinedload
from . import models, schemas, auth
from datetime import date, datetime, time
import secrets
import string


def get_user(db: Session, user_id: int): 
    '''通过用户 ID 查询数据库，返回对应的用户模型实例。如果用户不存在，返回 None。'''
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str): # 通过用户名获取用户。
    '''通过用户名查询数据库，返回对应的用户模型实例。如果用户不存在，返回 None。'''
    return db.query(models.User).options(joinedload(models.User.partner)).filter(models.User.username == username).first()


def generate_invitation_code(db: Session) -> str:
    '''生成唯一的邀请码'''
    while True:
        # 生成8位随机字符串，包含大小写字母和数字
        code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        # 检查是否已存在
        existing_user = db.query(models.User).filter(models.User.invitation_code == code).first()
        if not existing_user:
            return code


def get_user_by_invitation_code(db: Session, invitation_code: str):
    '''通过邀请码查询用户'''
    return db.query(models.User).filter(models.User.invitation_code == invitation_code).first()


def create_user(db: Session, user: schemas.UserCreate): # 创建用户。
    '''创建一个新用户，将用户名和密码哈希后存储到数据库中。'''
    hashed_password = auth.get_password_hash(user.password)
    invitation_code = generate_invitation_code(db)
    db_user = models.User(
        username=user.username, 
        hashed_password=hashed_password,
        invitation_code=invitation_code
    )
    db.add(db_user)
    db.commit() # 提交事务，将新用户添加到数据库中。
    db.refresh(db_user) # 刷新实例，确保返回的实例包含数据库生成的 ID 等信息。
    return db_user


def update_user_refresh_token(db: Session, user: models.User, refresh_token: str): # 更新用户的 Refresh Token。
    '''更新用户的 Refresh Token。这通常在用户登录后调用，用于存储长效 Refresh Token。'''
    user.refresh_token = refresh_token
    db.commit()
    db.refresh(user)
    return user


# 新增：成对绑定伴侣，保证双方互为伴侣
# 业务约束：
# - 不允许与自己绑定
# - 双方都必须尚未绑定（partner_id 为空）
# - 操作应为原子：要么两侧都更新成功，要么都不生效

def bind_partners(db: Session, user_a: models.User, user_b: models.User): # 绑定伴侣。
    '''绑定两个用户为一对伴侣。这是一个原子操作，要么都成功，要么都失败。'''
    if user_a.id == user_b.id:
        raise ValueError("Cannot bind to self")
    if user_a.partner_id is not None or user_b.partner_id is not None:
        raise ValueError("One of the users already has a partner")

    try:
        # 设置绑定时间
        bind_time = datetime.now()
        
        user_a.partner_id = user_b.id
        user_a.bind_date = bind_time
        user_b.partner_id = user_a.id
        user_b.bind_date = bind_time
        db.add(user_a)
        db.add(user_b)
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)
        return user_a, user_b
    except Exception:
        db.rollback()
        raise


# ==================================================
# 任务 (Task) 相关的 CRUD 函数
# ==================================================

def get_task(db: Session, task_id: int): # 根据任务的唯一 ID 从数据库中精确查找并返回一个任务。
    """通过 ID 获取单个任务""" 
    return db.query(models.Task).filter(models.Task.id == task_id).first()


def get_tasks(db: Session, skip: int = 0, limit: int = 100): # 获取数据库中所有的任务列表，支持分页查询，这在未来任务数量增多时能有效提升性能。
    """获取所有任务（支持分页）"""
    return db.query(models.Task).offset(skip).limit(limit).all()


def create_task(db: Session, task: schemas.TaskCreate, creator_id: int):
    """创建一个新任务"""
    db_task = models.Task(**task.model_dump(), creator_id=creator_id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def update_task(db: Session, task_id: int, task_update: schemas.TaskUpdate):
    """更新任务，包括禁用/激活"""
    db_task = get_task(db, task_id)
    if not db_task:
        return None
    update_data = task_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_checkins_by_task(db: Session, task_id: int):
    """获取某个特定任务的所有打卡记录"""
    return db.query(models.CheckIn).filter(models.CheckIn.task_id == task_id).order_by(models.CheckIn.timestamp.desc()).all()


# ==================================================
# 打卡 (Check-in) 相关的 CRUD 函数
# ==================================================

def create_check_in(db: Session, user_id: int, task_id: int, text_content: str | None, image_url: str | None):# 这是功能的核心之一。它为指定的用户和任务创建一个新的打卡记录，同时可以附带一条文字消息和一张图片的 URL。
    """为指定用户和任务创建一个新的打卡记录"""
    db_check_in = models.CheckIn(
        user_id=user_id,
        task_id=task_id,
        text=text_content,
        image_url=image_url
    )
    db.add(db_check_in)
    db.commit()
    db.refresh(db_check_in)
    return db_check_in


def get_check_ins_for_user_on_date(db: Session, user_id: int, target_date: date):
    """获取某个用户在特定一天的所有打卡记录"""
    start_of_day = datetime.combine(target_date, time.min)
    end_of_day = datetime.combine(target_date, time.max)
    
    return db.query(models.CheckIn).filter(
        models.CheckIn.user_id == user_id,
        models.CheckIn.timestamp >= start_of_day,
        models.CheckIn.timestamp <= end_of_day
    ).all()
# 这是为"每日仪表盘"量身打造的函数。它能高效地查询出某个用户在 特定某一天 的所有打卡记录。为了实现这一点，它会根据传入的 target_date （日期），自动计算出那一天的开始时间（00:00:00）和结束时间（23:59:59），然后查询这个时间范围内的所有打卡数据。


# ==================================================
# 评论 (Comment) 相关的 CRUD 函数
# ==================================================

def create_comment(db: Session, user_id: int, check_in_id: int, content: str):
    """为指定的打卡记录创建评论"""
    db_comment = models.Comment(
        user_id=user_id,
        check_in_id=check_in_id,
        content=content
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


def get_comments_by_check_in(db: Session, check_in_id: int):
    """获取某个打卡记录的所有评论"""
    return db.query(models.Comment).filter(
        models.Comment.check_in_id == check_in_id
    ).order_by(models.Comment.timestamp.asc()).all()


def delete_comment(db: Session, comment_id: int, user_id: int):
    """删除评论（只能删除自己的评论）"""
    comment = db.query(models.Comment).filter(
        models.Comment.id == comment_id,
        models.Comment.user_id == user_id
    ).first()
    if comment:
        db.delete(comment)
        db.commit()
        return True
    return False


# ==================================================
# 点赞 (Like) 相关的 CRUD 函数
# ==================================================

def create_like(db: Session, user_id: int, check_in_id: int):
    """为指定的打卡记录点赞"""
    # 检查是否已经点过赞
    existing_like = db.query(models.Like).filter(
        models.Like.user_id == user_id,
        models.Like.check_in_id == check_in_id
    ).first()
    
    if existing_like:
        return None  # 已经点过赞了
    
    db_like = models.Like(
        user_id=user_id,
        check_in_id=check_in_id
    )
    db.add(db_like)
    db.commit()
    db.refresh(db_like)
    return db_like


def delete_like(db: Session, user_id: int, check_in_id: int):
    """取消点赞"""
    like = db.query(models.Like).filter(
        models.Like.user_id == user_id,
        models.Like.check_in_id == check_in_id
    ).first()
    
    if like:
        db.delete(like)
        db.commit()
        return True
    return False


def get_likes_by_check_in(db: Session, check_in_id: int):
    """获取某个打卡记录的所有点赞"""
    return db.query(models.Like).filter(
        models.Like.check_in_id == check_in_id
    ).order_by(models.Like.timestamp.desc()).all()


def get_like_count_by_check_in(db: Session, check_in_id: int):
    """获取某个打卡记录的点赞数量"""
    return db.query(models.Like).filter(
        models.Like.check_in_id == check_in_id
    ).count()
