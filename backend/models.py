from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text,Boolean
from sqlalchemy.orm import relationship
from .database import Base
import datetime
import pytz


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    refresh_token = Column(String, nullable=True) # 新增字段，用于存储刷新令牌
    invitation_code = Column(String, unique=True, index=True, nullable=True) # 邀请码字段
    score = Column(Integer, default=0, nullable=False) # 用户得分字段

    partner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    partner = relationship("User", remote_side=[id], uselist=False)
    bind_date = Column(DateTime, nullable=True)  # 伴侣绑定时间
    
    created_tasks = relationship("Task", back_populates="creator")
    check_ins = relationship("CheckIn", back_populates="user")
    comments = relationship("Comment", back_populates="user")
    likes = relationship("Like", back_populates="user")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    is_active = Column(Boolean, default=True)

    creator_id = Column(Integer, ForeignKey("users.id"))
    creator = relationship("User", back_populates="created_tasks")

    check_ins = relationship("CheckIn", back_populates="task")


class CheckIn(Base):
    __tablename__ = "check_ins"
    id = Column(Integer, primary_key=True, index=True) # 主键，自增，带索引（查询打卡记录常用）
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False) # 对应的任务
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # 打卡人
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(pytz.timezone('Asia/Shanghai')), nullable=False) # 打卡时间
    text = Column(Text, nullable=True) # 打卡信息
    image_url = Column(String, nullable=True) # 打卡图片

    task = relationship("Task", back_populates="check_ins")
    user = relationship("User", back_populates="check_ins")
    comments = relationship("Comment", back_populates="check_in")
    likes = relationship("Like", back_populates="check_in")


class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    check_in_id = Column(Integer, ForeignKey("check_ins.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(pytz.timezone('Asia/Shanghai')), nullable=False)
    
    check_in = relationship("CheckIn", back_populates="comments")
    user = relationship("User", back_populates="comments")


class Like(Base):
    __tablename__ = "likes"
    
    id = Column(Integer, primary_key=True, index=True)
    check_in_id = Column(Integer, ForeignKey("check_ins.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(pytz.timezone('Asia/Shanghai')), nullable=False)
    
    check_in = relationship("CheckIn", back_populates="likes")
    user = relationship("User", back_populates="likes")


class ScoreRequest(Base):
    __tablename__ = "score_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 申请人
    target_id = Column(Integer, ForeignKey("users.id"), nullable=False)     # 被申请人（伴侣）
    points = Column(Integer, nullable=False)                                # 申请的分数
    reason = Column(Text, nullable=False)                                   # 申请理由
    status = Column(String, default="pending", nullable=False)              # 状态：pending, approved, rejected
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(pytz.timezone('Asia/Shanghai')), nullable=False)
    
    requester = relationship("User", foreign_keys=[requester_id])
    target = relationship("User", foreign_keys=[target_id])