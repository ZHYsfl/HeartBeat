# 这个文件定义了项目的 数据校验模型 (Data Validation Models) ，它利用了 pydantic 库。
# 它的核心作用是： 定义 API 的“输入”和“输出”应该长什么样。
# 输入校验 ：当客户端（比如前端页面）发送数据给我们的 API 时，FastAPI 会用 schemas.py 里定义的模型来检查数据格式是否正确。
# 比如， UserCreate 模型要求客户端必须提供 username 和 password 两个字符串字段，如果缺了或者类型不对，FastAPI 会自动返回一个清晰的 422 Unprocessable Entity 错误，根本不会进入我们的业务逻辑。
# 输出过滤 ：当我们的 API 要返回数据给客户端时，我们可以指定一个 response_model 。FastAPI 会用这个模型来“过滤”和格式化我们返回的数据。
# 最典型的例子就是 UserOut ，它只包含 id , username , partner_id ，而 不会 包含 hashed_password 。这保证了我们永远不会意外地把用户的密码哈希泄露给客户端。
from pydantic import BaseModel
from typing import Optional
import datetime
from datetime import date

# 简化的伴侣信息模型，避免循环引用
class PartnerInfo(BaseModel):
    '''简化的伴侣信息模型，只包含基本字段，避免循环引用'''
    id: int
    username: str
    score: int = 0
    bind_date: Optional[datetime.datetime] = None  # 伴侣绑定时间
    
    model_config = {"from_attributes": True}

class UserCreate(BaseModel):
    '''
    - 用途 : 用户注册 ( /users/ ) 接口的 输入模型 。
    - 字段 : username: str , password: str 。
    - 作用 : 强制注册请求必须包含用户名和密码。
    '''
    username: str
    password: str

# 想象一下，我们现在有两种“用户”对象：
# 1. 1.
#    数据库用户对象 ( models.User ) :
#    - 这是 SQLAlchemy 的 ORM 模型实例。
#    - 我们从数据库里查出来的用户都是这种类型，比如 db_user = crud.get_user(...) 。
#    - 你可以通过 属性 来访问它的数据，比如 db_user.id , db_user.username , db_user.hashed_password 。
# 2. 2.
#    API 输出用户对象 ( schemas.UserOut ) :
#    - 这是 Pydantic 的数据模型实例。
#    - 这是我们希望返回给前端的、经过“清洗”的数据结构。
#    - 它只定义了 id , username , partner_id 这几个字段。
# 问题来了 ：在 API 路由的最后，我们从数据库拿到了一个 models.User 对象，但 FastAPI 需要返回一个 schemas.UserOut 对象。怎么把前者转换成后者？
# 它告诉 Pydantic：“除了可以从字典创建我，你现在也可以直接从一个 对象 来创建我。我会尝试读取这个对象的 同名属性 来填充我自己的字段。”
# 当 FastAPI 看到你的路由函数（比如 read_users_me ）返回了一个 models.User 对象，并且这个路由的 response_model 被设置为了 schemas.UserOut ，它会：
# 1. 1.
#    检查 schemas.UserOut 的配置。
# 2. 2.
#    发现 from_attributes 是 True 。
# 3. 3.
#    于是 FastAPI 就明白了：“哦，我不需要开发者手动转成字典了！我可以自动把 models.User 对象的 id , username , partner_id 属性 ，直接映射到 schemas.UserOut 模型的 id , username , partner_id 字段 上。”

class UserOut(BaseModel):
    '''
    - 用途 : 大部分返回用户信息的接口的 输出模型。
    - 字段 : id: int , username: str , partner_id: Optional[int] = None, invitation_code: Optional[str] = None, partner: Optional[PartnerInfo] = None。
    - 作用 : 定义了哪些用户字段可以安全地暴露给外界。
    - class Config: from_attributes = True : 这是一个关键配置。它告诉 Pydantic 模型可以直接从 ORM 对象（比如我们从 crud.py 获取的 models.User 对象）的属性来创建实例，实现了 ORM 模型和 Pydantic 模型之间的无缝转换。
    '''
    id: int
    username: str
    partner_id: Optional[int] = None
    invitation_code: Optional[str] = None
    score: int = 0  # 用户得分
    partner: Optional[PartnerInfo] = None  # 伴侣简化信息，避免循环引用

    model_config = {"from_attributes": True}


class Token(BaseModel):
    '''
    - 用途 : 登录 ( /auth/token ) 接口的 输出模型 。
    - 字段 : access_token , refresh_token , token_type 。
    - 作用 : 规范了登录成功后返回的令牌格式。
    '''
    access_token: str
    refresh_token: str
    token_type: str


# 新增：绑定伴侣的请求体
class PartnerBindRequest(BaseModel):
    '''
    - 用途 : 绑定伴侣 ( /users/partner ) 接口的 输入模型 。
    - 字段 : invitation_code: str 。
    - 作用 : 强制绑定请求必须包含伴侣的邀请码。
    '''
    invitation_code: str


# 新增：绑定结果（返回双方的精简信息）
class RefreshTokenRequest(BaseModel):
    refresh_token: str


class BindResult(BaseModel):
    '''
    - 用途 : 绑定伴侣 ( /users/partner ) 接口的 输出模型 。
    - 字段 : user: UserOut , partner: UserOut 。
    - 作用 : 定义了绑定成功后返回的用户和伴侣的精简信息。
    '''
    user: UserOut
    partner: UserOut


# ==================================================
# 任务 (Task) 相关的模型
# ==================================================

class TaskBase(BaseModel):
    # 定义了“任务”最基础的数据字段： title (标题) 和 description (描述)
    title: str
    description: Optional[str] = None


class TaskCreate(TaskBase):
    # 用于 创建任务 的输入模型，它直接继承自 TaskBase ，意味着创建一个任务只需要提供标题和描述。
    pass


class Task(TaskBase):
    # 用于 读取或返回任务信息 的输出模型。它在 TaskBase 的基础上增加了 id 字段，并且配置了 from_attributes = True ，这样就能直接从数据库的 Task 对象转换而来。
    id: int
    is_active: bool # 新增：任务是否激活
    creator_id: int
    creator: UserOut  # 包含创建者的完整信息

    model_config = {"from_attributes": True}


class TaskUpdate(BaseModel):
    """用于更新任务的模型"""
    title: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

# ==================================================
# 打卡 (Check-in) 相关的模型
# ==================================================

class CheckInBase(BaseModel):
    # 定义了"打卡"的基础字段，这里只有一个可选的 text (留言)。
    text: Optional[str] = None


class CheckInCreate(CheckInBase):
    # 用于 创建打卡记录 的输入模型。它要求客户端在提供可选的留言之外，必须提供 task_id ，以明确这次打卡是针对哪个任务的。
    task_id: int


class CheckIn(CheckInBase):
    # 用于 返回打卡信息 的输出模型。它包含了打卡的所有详细信息，如 id , task_id , user_id , timestamp (时间戳) 和 image_url (图片链接)，同样配置了 from_attributes = True 。
    id: int
    task_id: int
    user_id: int
    user: UserOut  # 包含打卡用户的完整信息
    timestamp: datetime.datetime
    image_url: Optional[str] = None

    model_config = {"from_attributes": True}


# ==================================================
# 评论 (Comment) 相关的模型
# ==================================================

class CommentBase(BaseModel):
    content: str


class CommentCreate(CommentBase):
    pass


class Comment(CommentBase):
    id: int
    check_in_id: int
    user_id: int
    user: UserOut
    timestamp: datetime.datetime
    
    model_config = {"from_attributes": True}


# ==================================================
# 点赞 (Like) 相关的模型
# ==================================================

class LikeCreate(BaseModel):
    check_in_id: int


class Like(BaseModel):
    id: int
    check_in_id: int
    user_id: int
    user: UserOut
    timestamp: datetime.datetime
    
    model_config = {"from_attributes": True}


# ==================================================
# 仪表盘 (Dashboard) 聚合模型
# ==================================================

class DailyCheckInStatus(BaseModel): # 这是一个小的数据单元，用来描述 某一个任务在当天的状态 。它里面包含了：这个任务本身的信息。你今天是否为这个任务打过卡 (如果打了，这里就是 CheckIn 对象，否则是 None )。你的伴侣今天是否为这个任务打过卡。
    """单个任务在今日的打卡状态"""
    task: Task
    user_checked_in: Optional[CheckIn] = None
    partner_checked_in: Optional[CheckIn] = None


class DailyDashboard(BaseModel):
    date: date
    tasks_status: list[DailyCheckInStatus]


# 得分申请相关模型
class ScoreRequestBase(BaseModel):
    points: int
    reason: str


class ScoreRequestCreate(ScoreRequestBase):
    pass


class ScoreRequest(ScoreRequestBase):
    id: int
    requester_id: int
    target_id: int
    status: str  # pending, approved, rejected
    timestamp: datetime.datetime
    requester: UserOut
    target: UserOut
    
    model_config = {"from_attributes": True}


class ScoreRequestResponse(BaseModel):
    action: str  # approve 或 reject

# 这个设计的妙处在于 ：手机 App 的主页只需要调用一次 /checkins/today 接口，就能拿到渲染整个页面所需的所有数据，而不需要为了获取不同任务、不同人的打卡状态而发送多次请求。这极大地提升了前端的加载速度和用户体验。