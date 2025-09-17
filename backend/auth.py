from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import pytz
from sqlalchemy.orm import Session
from . import schemas, models, crud
from .database import get_db
import os

# 尝试从 .env 加载环境变量（若安装了 python-dotenv）
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# --- 安全配置 ---
SECRET_KEY =  os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not set. Please set environment variable SECRET_KEY (e.g., in .env)"
    ) 
# JWT 签名密钥，必须保密且复杂；生产应放到环境变量，不能硬编码
# 一旦更换 SECRET_KEY，所有用旧密钥签发的 Token 立刻失效，等同于全员登出。生产环境换钥需要提前评估与公告。

ALGORITHM = "HS256" # JWT 签名算法，这里使用对称的 HS256
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # 访问令牌有效期30分钟
REFRESH_TOKEN_EXPIRE_DAYS = 30 # 刷新令牌有效期30天

# 密码哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") # 使用 passlib 的 CryptContext，方案为 bcrypt，用 bcrypt 生成/校验密码哈希。bcrypt 会自动加盐，安全性较好。保证密码只以哈希形式存储，永不保存明文

# OAuth2 an'd token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token") # 告诉 Swagger 文档如何进行密码模式的认证流程（使用 /auth/token 获取令牌）
# 告诉 FastAPI 在请求头中提取 Bearer Token；同时用于生成 Swagger 的“Authorize”入口。

# --- 密码操作 ---
def verify_password(plain_password, hashed_password):# 
    '''校验明文密码与哈希是否匹配（登录时用）'''
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    '''注册时对明文密码进行哈希处理（注册时用）'''
    return pwd_context.hash(password)



# 一个完整的 JWT 由三部分组成，用点 . 连接，像这样： Header.Payload.Signature
# 1. 1.
#    Header (头部) : 通常包含两部分信息：令牌的类型（ "typ": "JWT" ）和所使用的签名算法（例如 "alg": "HS256" ）。
# 2. 2.
#    Payload (载荷) : 这就是我们讨论的重点。它包含了所有我们想传递的“声明 (claims)”。这些声明是关于一个实体（通常是用户）和其他附加数据。
# 3. 3.
#    Signature (签名) : 对前两部分进行签名的结果，用来验证消息在传递过程中没有被篡改。

# 在我们的代码里， payload 主要包含两种标准声明（也叫“注册声明”）：
# 1. 1.
#    sub (Subject) :
#    - 含义 : 主题，即该令牌的所有者是谁。
#    - 在我们的代码里 : 我们把用户的 username 作为 sub 的值。所以，当服务器解析一个令牌时，它会查看 sub 字段来确定这是哪个用户的请求。
#    - 例子 : {"sub": "alice"}
# 2. 2.
#    exp (Expiration Time) :
#    - 含义 : 过期时间。这是一个 Unix 时间戳，定义了令牌在哪一刻之后就失效了。
#    - 在我们的代码里 : 我们用 datetime.now(timezone.utc) + timedelta(...) 计算出一个未来的时间点，然后把它放进 exp 字段。FastAPI 和 jose 库会自动处理时间戳的转换和验证。
#    - 例子 : {"exp": 1678886400}

# Payload 是公开的，不是加密的！
# 任何人拿到一个 JWT，都可以轻易地通过 Base64 解码看到 Payload 里的所有内容（比如用户名、过期时间）。
# JWT 的安全性 不依赖于隐藏数据 ，而是依赖于 签名 (Signature) 。签名保证了：
# 1. 1.
#    真实性 : 令牌确实是由你的服务器签发的（因为只有你有 SECRET_KEY ）。
# 2. 2.
#    完整性 : Payload 的内容从签发到现在没有被任何人修改过。如果有人试图修改 Payload（比如把用户名 alice 改成 admin ），签名就会失效，服务器会立刻拒绝这个令牌。
# 所以， 永远不要在 JWT 的 Payload 中存放任何敏感信息 ，比如用户的密码、银行卡号等。存放用户 ID、用户名、角色这类信息是安全的、也是设计的初衷。


# --- Token 创建 ---
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    '''生成一个"访问令牌"，它寿命短（例如 30 分钟），用于访问受保护的 API 资源。因为寿命短，即使泄露，风险也有限。'''
    # data:一个字典，你想放进令牌里的核心信息。 关键是必须包含 {"sub": "username"} ，"sub" (subject) 是 JWT 的标准字段，我们用它来标识用户。
    to_encode = data.copy() # 先复制一份 data ，避免修改原始字典。
    beijing_tz = pytz.timezone('Asia/Shanghai')
    if expires_delta:
        # expires_delta:过期时间，一个 timedelta 对象。如果不传，函数内部会使用一个默认值（访问令牌默认 15 分钟，刷新令牌默认 7 天）。
        expire = datetime.now(beijing_tz) + expires_delta # 计算出北京时区的确切过期时间点。
    else:
        expire = datetime.now(beijing_tz) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: timedelta | None = None):
    '''生成一个"刷新令牌"，它寿命长（例如 7 天或 30 天），唯一作用就是去换取新的"访问令牌"。它不应该被用来访问资源。'''
    to_encode = data.copy()
    beijing_tz = pytz.timezone('Asia/Shanghai')
    if expires_delta:
        expire = datetime.now(beijing_tz) + expires_delta
    else:
        expire = datetime.now(beijing_tz) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 简单来说，上面这两个函数就是把**“你是谁 ( sub )” 和 “你能用到什么时候 ( exp )” 这两个信息，用一把只有服务器知道的 “钥匙 ( SECRET_KEY )”**锁起来，做成一个防伪的“通行证 (JWT)”。



# --- 获取当前用户 ---
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # token: str = Depends(oauth2_scheme)：这部分是 FastAPI 依赖注入的魔法。你不需要手动传参。Depends(oauth2_scheme) 会告诉 FastAPI：“在处理这个请求前，请自动去请求头 (Header) 里寻找 Authorization 字段，提取出 Bearer <token> 中的 <token> 部分，然后把它作为 token 参数传给我的函数。”如果找不到 Authorization: Bearer ... ，FastAPI 会直接报错，连 get_current_user 的代码都不会执行。
    # db: Session = Depends(get_db)：这和我们之前用的一样，就是从依赖注入系统中获取一个数据库会话，以便我们查询用户数据。
    '''这是整个认证系统的“守门员”。它不是一个普通的函数，而是一个 FastAPI 依赖,作为一个“守卫”被安插在需要保护的 API 路由上'''
    '''检查请求中是否包含一个 有效 的访问令牌 (Access Token)，如果有效，就把这个令牌对应的 用户完整信息从数据库里捞出来，并提供给后续的业务逻辑使用'''
    '''如果令牌无效或不存在，它会直接 拒绝 请求，返回一个 401 Unauthorized 错误。'''
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = crud.get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user