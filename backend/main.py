from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, date
from jose import JWTError, jwt
from typing import List
import os
import shutil
import datetime
import magic
import pytz
from . import crud, models, schemas, auth
from .database import engine, get_db
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# 创建数据库表
# 会基于上述模型自动创建 users 表（如果尚未存在）。
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="HeartBeat App for Couples")

# 允许前端跨域访问（包括预检请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# --- 静态文件服务 ---
# 挂载 static 目录，使得 /static/uploads/filename.jpg 可以通过 URL 访问
UPLOAD_DIR = "static/uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
app.mount("/static", StaticFiles(directory="static"), name="static")
# 这是实现图片访问的关键。它告诉 FastAPI，任何以 /static/ 开头的 URL 请求，都应该去服务器的 static 文件夹下查找对应的文件。这样，我们保存在 static/uploads 目录下的图片就能通过 http://<your-domain>/static/uploads/image.jpg 这样的链接被手机 App 访问到了。

# --- 认证相关的API路由 ---

@app.post("/auth/register", response_model=schemas.UserOut, tags=["Auth"]) # 这是一个“装饰器”，它告诉 FastAPI：下面这个 register_user 函数是用来处理发送到 /auth/register 这个 URL 的 POST 请求的。
# response_model:这是一个强大的特性。它规定了 这个接口成功时返回的 JSON 数据必须符合 schemas.UserOut 的格式。
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    # - 函数最后返回的是一个 models.User 数据库对象（包含了 hashed_password ）。
    # - FastAPI 会利用我们之前讨论的 from_attributes = True 配置，自动将 models.User 对象转换为 schemas.UserOut 对象。
    # - 这个转换过程会 自动过滤掉 hashed_password ，只保留 id , username , partner_id ，确保了密码哈希值不会泄露给客户端。
    return crud.create_user(db=db, user=user)

@app.post("/auth/token", response_model=schemas.Token, tags=["Auth"]) # 这个接口是整个认证系统的入口。当用户在登录页面输入用户名和密码点击登录时，前端就会调用这个接口。
async def login_for_access_token(# 注意这里我们用了 async 关键字。虽然在这个函数内部没有执行 await 操作，但 FastAPI 的很多内部机制是异步的，使用 async def 是推荐的最佳实践，能获得更好的性能。
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db) # 是 FastAPI 提供的一个特殊依赖类。它不是从 JSON 请求体里读取数据，而是专门用来处理标准的 application/x-www-form-urlencoded 格式的表单数据，这是 OAuth2 规范中“密码模式”的标准要求。它告诉 FastAPI：“我期望的请求体格式是 username=someuser&password=somepass 这样的字符串，而不是 JSON。”
):# Depends() 会自动解析这种格式的数据，并把 username 和 password 填充到 form_data 对象中，我们就可以通过 form_data.username 和 form_data.password 来访问它们。
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建 Access Token
    # - Access Token 为了安全，有效期很短。如果它过期了，难道要让用户每 30 分钟就重新登录一次吗？这体验太差了。
    # - Refresh Token 就是为了解决这个问题。它是一个 长时效 （例如 7 天）的令牌，它的 唯一作用 就是用来“换取”新的 Access Token。
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # 创建 Refresh Token
    refresh_token_expires = timedelta(days=auth.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = auth.create_refresh_token(
        data={"sub": user.username}, expires_delta=refresh_token_expires
    )
    # - 我们调用了一个新的 CRUD 函数 update_user_refresh_token ，将刚刚生成的 refresh_token 字符串 保存到该用户的数据库记录中 。
    # - 为什么要保存它？ 这是为了安全。当用户稍后拿着 Refresh Token 来换取新 Access Token 时，我们不仅要验证这个 Refresh Token 本身是否有效，还要验证它 是否和数据库里存的那个完全一致 。这可以防止令牌泄露后被滥用，并且允许我们通过从数据库中删除它来“吊销”用户的登录会话。
    # 将新的 refresh_token 存入数据库
    crud.update_user_refresh_token(db, user, refresh_token)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
    # - 最后，将新生成的 access_token 和 refresh_token 一起返回给客户端。
    # - 客户端（前端应用）需要将这两个令牌安全地存储起来（通常在 localStorage 或 HttpOnly Cookie 中）。 

@app.post("/auth/refresh", response_model=schemas.Token, tags=["Auth"])
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # --- 第 1 步：解码令牌，验明身份 ---
        # 尝试用我们服务器的“秘密钥匙”(auth.SECRET_KEY)来打开这个令牌盒子
        payload = jwt.decode(refresh_token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        # 如果这行代码失败了（比如令牌是伪造的、过期的、被篡改的），
        # 程序会立刻跳到下面的 `except JWTError:`，然后抛出 credentials_exception，流程结束。

        # 如果解码成功，payload 就是一个字典，比如：{'sub': 'testuser', 'exp': 1678886400}
        # 从这个字典里，我们拿出 'sub' 字段的值，也就是当初存进去的用户名
        username: str | None = payload.get("sub")
        # --- 第 2 步：交叉验证，核实令牌有效性 ---
        # 根据解码出来的用户名，去数据库里查找这个用户的所有信息
        # 如果 username 是 None，user 也会是 None
        # 这是最关键的安全检查！
        # 它检查两种“坏”情况：
        # 1. user is None: 
        #    - 令牌里的用户名根本不存在于我们的数据库中（比如用户被删了）。
        #    - 或者令牌本身就没有 'sub' 字段，导致 username 是 None。
        # 2. user.refresh_token != the_refresh_token_from_client:
        #    - 用户存在，但是他数据库里存的 Refresh Token 和客户端这次发来的不一样。
        #    - 这通常意味着数据库里存的是一个更新的令牌，而客户端用的这个是旧的、已作废的。
        #    - 这可以防止令牌被盗用后，在用户自己刷新了令牌之后，攻击者还能用旧令牌继续刷新。
        user = crud.get_user_by_username(db, username=username) if username else None
        if user is None or user.refresh_token != refresh_token:
            # 只要上面两种情况发生任意一种，就说明这个请求有问题，立刻拒绝！
            raise credentials_exception
        # --- 第 3 步：颁发新令牌 (Token Rotation) ---
        # 如果代码能走到这里，说明一切验证通过，这是一个合法的“续期”请求。
        # 为了安全，我们不直接延长旧令牌，而是生成一对全新的令牌。
        # 创建新的 Access and Refresh Token
        access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = auth.create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        refresh_token_expires = timedelta(days=auth.REFRESH_TOKEN_EXPIRE_DAYS)
        new_refresh_token = auth.create_refresh_token(
            data={"sub": user.username}, expires_delta=refresh_token_expires
        )
        crud.update_user_refresh_token(db, user, new_refresh_token)

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }
    except JWTError:
        raise credentials_exception


# --- 受保护的示例路由 ---
@app.get("/users/me", response_model=schemas.UserOut, tags=["Users"]) # 返回当前已登录用户的个人信息。和注册接口一样，它确保了无论函数内部返回什么，最终给到客户端的响应都会被安全地过滤，只包含 id , username , partner_id ，绝不会泄露密码哈希等敏感信息。
async def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


# --- 新增：绑定伴侣路由 ---
@app.post("/users/bind_partner", response_model=schemas.BindResult, tags=["Users"])
async def bind_partner(
    req: schemas.PartnerBindRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    # 不能与自己绑定
    if req.invitation_code == current_user.invitation_code:
        raise HTTPException(status_code=400, detail="Cannot bind to yourself")

    partner = crud.get_user_by_invitation_code(db, invitation_code=req.invitation_code)
    if not partner:
        raise HTTPException(status_code=404, detail="Invalid invitation code")

    # 业务约束：双方必须都未有伴侣
    if current_user.partner_id is not None:
        raise HTTPException(status_code=400, detail="You already have a partner")
    if partner.partner_id is not None:
        raise HTTPException(status_code=400, detail="Partner already has a partner")

    try:
        user_a, user_b = crud.bind_partners(db, current_user, partner)
        return {"user": user_a, "partner": user_b}
    except ValueError as e:
        # 业务校验抛错
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        # 可能是数据库唯一约束冲突等
        raise HTTPException(status_code=409, detail="Binding conflict, please retry")


# ==================================================
# 任务 (Task) 和打卡 (Check-in) 相关的 API
# ==================================================

@app.post("/tasks/", response_model=schemas.Task, tags=["Tasks & Check-ins"])
def create_task(
    task: schemas.TaskCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user) # 假设只有登录用户能创建
):
    """
    创建一个新的任务。
    （在实际应用中，你可能会希望这是一个仅限管理员的操作）
    """
    return crud.create_task(db=db, task=task, creator_id=current_user.id)

@app.get("/tasks/", response_model=List[schemas.Task], tags=["Tasks & Check-ins"])
def read_tasks(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    tasks = crud.get_tasks(db, skip=skip, limit=limit)
    return tasks

@app.get("/tasks/{task_id}", response_model=schemas.Task, tags=["Tasks & Check-ins"])
def read_task(
    task_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    db_task = crud.get_task(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

@app.put("/tasks/{task_id}", response_model=schemas.Task, tags=["Tasks & Check-ins"])
def update_task(
    task_id: int, 
    task_update: schemas.TaskUpdate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    db_task = crud.update_task(db, task_id=task_id, task_update=task_update)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

@app.get("/tasks/{task_id}/checkins", response_model=List[schemas.CheckIn], tags=["Tasks & Check-ins"])
def read_checkins_for_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """获取特定任务的所有打卡记录"""
    db_task = crud.get_task(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 这里可以加入权限检查，比如只有任务的创建者或其伴侣才能查看
    
    check_ins = crud.get_checkins_by_task(db, task_id=task_id)
    return check_ins


# 这是处理打卡的核心路由
@app.post("/tasks/{task_id}/checkin", response_model=schemas.CheckIn, tags=["Tasks & Check-ins"])
async def create_check_in_for_task(
    task_id: int,
    text_content: str = Form(None),
    images: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    为当前登录用户创建一个新的打卡记录。
    - **task_id**: 关联的任务ID。
    - **text**: 打卡的文字内容 (可选)。
    - **images**: 上传的图片文件列表 (可选，最多3张)。
    """
    image_urls = []
    if images and len(images) > 0:
        # 限制最多3张图片
        if len(images) > 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="最多只能上传3张图片",
            )
        
        for image in images:
            if image.filename:  # 确保文件不为空
                # MIME type validation
                file_content = await image.read(2048)  # Read first 2KB to check type
                await image.seek(0)  # Reset file pointer

                mime_type = magic.from_buffer(file_content, mime=True)
                if not mime_type.startswith("image/"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid file type. Only images are allowed.",
                    )

                # 生成一个安全的文件名，例如用 user_id 和时间戳
                beijing_tz = pytz.timezone('Asia/Shanghai')
                timestamp = datetime.datetime.now(beijing_tz).strftime("%Y%m%d%H%M%S")
                # 为每张图片添加序号
                image_index = len(image_urls)
                file_extension = os.path.splitext(image.filename)[1]
                # 确保文件名安全，防止路径遍历攻击
                safe_filename = f"{current_user.id}_{timestamp}_{image_index}{file_extension}"
                file_path = os.path.join(UPLOAD_DIR, safe_filename)

                # 保存文件
                try:
                    with open(file_path, "wb") as buffer:
                        shutil.copyfileobj(image.file, buffer)
                finally:
                    image.file.close()
                
                # 生成可访问的 URL
                image_url = f"/static/uploads/{safe_filename}"
                image_urls.append(image_url)

    # 将多个图片URL用逗号分隔存储（简单方案）
    image_url_string = ",".join(image_urls) if image_urls else None

    check_in = crud.create_check_in(
        db=db, 
        user_id=current_user.id, 
        task_id=task_id, 
        text_content=text_content, 
        image_url=image_url_string
    )
    return check_in


@app.get("/dashboard/{date_str}", response_model=schemas.DailyDashboard, tags=["Dashboard"])
async def get_daily_dashboard(
    date_str: str, # 接收一个 YYYY-MM-DD 格式的日期字符串作为路径参数。
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    获取指定日期的每日仪表盘数据。
    包含你和你的伴侣当天所有任务的打卡状态。
    """
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # 1. 获取所有任务
    all_tasks = crud.get_tasks(db)

    # 2. 获取当前用户和伴侣的打卡记录
    my_check_ins = crud.get_check_ins_for_user_on_date(db, current_user.id, target_date)
    
    partner_check_ins = []
    partner = None
    if current_user.partner_id:
        partner = crud.get_user(db, user_id=current_user.partner_id)
        if partner:
            partner_check_ins = crud.get_check_ins_for_user_on_date(db, partner.id, target_date)

    # 3. 构建数据结构
    my_check_ins_map = {ci.task_id: ci for ci in my_check_ins}
    partner_check_ins_map = {ci.task_id: ci for ci in partner_check_ins}

    daily_statuses = []
    for task in all_tasks:
        status = schemas.DailyCheckInStatus(
            task=task,
            user_checked_in=my_check_ins_map.get(task.id),
            partner_checked_in=partner_check_ins_map.get(task.id)
        )
        daily_statuses.append(status)
        
    return schemas.DailyDashboard(date=target_date, tasks_status=daily_statuses)


# ==================================================
# 评论 (Comment) 相关的 API 端点
# ==================================================

@app.post("/checkins/{check_in_id}/comments", response_model=schemas.Comment, tags=["Comments & Likes"])
async def create_comment(
    check_in_id: int,
    comment_data: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """为指定的打卡记录创建评论"""
    # 检查打卡记录是否存在
    check_in = db.query(models.CheckIn).filter(models.CheckIn.id == check_in_id).first()
    if not check_in:
        raise HTTPException(status_code=404, detail="Check-in not found")
    
    # 检查当前用户是否有权限评论（只有绑定的伴侣可以互相评论）
    if current_user.partner_id is None:
        raise HTTPException(status_code=403, detail="You need to bind a partner to comment")
    
    # 检查这个打卡记录是否属于当前用户或其伴侣
    if check_in.user_id != current_user.id and check_in.user_id != current_user.partner_id:
        raise HTTPException(status_code=403, detail="You can only comment on your or your partner's check-ins")
    
    # 检查用户是否已经对这个打卡记录评论过（每人每个打卡记录最多一条评论）
    existing_comment = db.query(models.Comment).filter(
        models.Comment.check_in_id == check_in_id,
        models.Comment.user_id == current_user.id
    ).first()
    
    if existing_comment:
        raise HTTPException(status_code=400, detail="You have already commented on this check-in")
    
    return crud.create_comment(
        db=db, 
        user_id=current_user.id, 
        check_in_id=check_in_id, 
        content=comment_data.content
    )


@app.get("/checkins/{check_in_id}/comments", response_model=List[schemas.Comment], tags=["Comments & Likes"])
async def get_comments(
    check_in_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """获取指定打卡记录的所有评论"""
    # 检查打卡记录是否存在
    check_in = db.query(models.CheckIn).filter(models.CheckIn.id == check_in_id).first()
    if not check_in:
        raise HTTPException(status_code=404, detail="Check-in not found")
    
    # 检查权限
    if current_user.partner_id is None:
        raise HTTPException(status_code=403, detail="You need to bind a partner to view comments")
    
    if check_in.user_id != current_user.id and check_in.user_id != current_user.partner_id:
        raise HTTPException(status_code=403, detail="You can only view comments on your or your partner's check-ins")
    
    return crud.get_comments_by_check_in(db=db, check_in_id=check_in_id)


@app.delete("/comments/{comment_id}", tags=["Comments & Likes"])
async def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """删除评论（只能删除自己的评论）"""
    success = crud.delete_comment(db=db, comment_id=comment_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Comment not found or you don't have permission to delete it")
    
    return {"message": "Comment deleted successfully"}


# ==================================================
# 点赞 (Like) 相关的 API 端点
# ==================================================

@app.post("/checkins/{check_in_id}/likes", response_model=schemas.Like, tags=["Comments & Likes"])
async def create_like(
    check_in_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """为指定的打卡记录点赞"""
    # 检查打卡记录是否存在
    check_in = db.query(models.CheckIn).filter(models.CheckIn.id == check_in_id).first()
    if not check_in:
        raise HTTPException(status_code=404, detail="Check-in not found")
    
    # 检查权限
    if current_user.partner_id is None:
        raise HTTPException(status_code=403, detail="You need to bind a partner to like check-ins")
    
    if check_in.user_id != current_user.id and check_in.user_id != current_user.partner_id:
        raise HTTPException(status_code=403, detail="You can only like your or your partner's check-ins")
    
    like = crud.create_like(db=db, user_id=current_user.id, check_in_id=check_in_id)
    if like is None:
        raise HTTPException(status_code=400, detail="You have already liked this check-in")
    
    return like


@app.delete("/checkins/{check_in_id}/likes", tags=["Comments & Likes"])
async def delete_like(
    check_in_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """取消点赞"""
    success = crud.delete_like(db=db, user_id=current_user.id, check_in_id=check_in_id)
    if not success:
        raise HTTPException(status_code=404, detail="Like not found")
    
    return {"message": "Like removed successfully"}


@app.get("/checkins/{check_in_id}/likes", response_model=List[schemas.Like], tags=["Comments & Likes"])
async def get_likes(
    check_in_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """获取指定打卡记录的所有点赞"""
    # 检查打卡记录是否存在
    check_in = db.query(models.CheckIn).filter(models.CheckIn.id == check_in_id).first()
    if not check_in:
        raise HTTPException(status_code=404, detail="Check-in not found")
    
    # 检查权限
    if current_user.partner_id is None:
        raise HTTPException(status_code=403, detail="You need to bind a partner to view likes")
    
    if check_in.user_id != current_user.id and check_in.user_id != current_user.partner_id:
        raise HTTPException(status_code=403, detail="You can only view likes on your or your partner's check-ins")
    
    return crud.get_likes_by_check_in(db=db, check_in_id=check_in_id)


@app.get("/checkins/{check_in_id}/likes/count", tags=["Comments & Likes"])
async def get_like_count(
    check_in_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """获取指定打卡记录的点赞数量"""
    # 检查打卡记录是否存在
    check_in = db.query(models.CheckIn).filter(models.CheckIn.id == check_in_id).first()
    if not check_in:
        raise HTTPException(status_code=404, detail="Check-in not found")
    
    # 检查权限
    if current_user.partner_id is None:
        raise HTTPException(status_code=403, detail="You need to bind a partner to view like count")
    
    if check_in.user_id != current_user.id and check_in.user_id != current_user.partner_id:
        raise HTTPException(status_code=403, detail="You can only view like count on your or your partner's check-ins")
    
    count = crud.get_like_count_by_check_in(db=db, check_in_id=check_in_id)
    return {"count": count}


# --- 得分申请相关API ---

@app.post("/score-requests/", response_model=schemas.ScoreRequest, tags=["Score System"])
async def create_score_request(
    request_data: schemas.ScoreRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """创建得分申请"""
    # 检查用户是否有伴侣
    if not current_user.partner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must have a partner to request score points"
        )
    
    # 创建得分申请
    db_request = models.ScoreRequest(
        requester_id=current_user.id,
        target_id=current_user.partner_id,
        points=request_data.points,
        reason=request_data.reason,
        status="pending"
    )
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    
    return db_request


@app.get("/score-requests/", response_model=List[schemas.ScoreRequest], tags=["Score System"])
async def get_score_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """获取与当前用户相关的得分申请（发出的和收到的）"""
    requests = db.query(models.ScoreRequest).filter(
        (models.ScoreRequest.requester_id == current_user.id) |
        (models.ScoreRequest.target_id == current_user.id)
    ).order_by(models.ScoreRequest.timestamp.desc()).all()
    
    return requests


@app.post("/score-requests/{request_id}/respond", tags=["Score System"])
async def respond_to_score_request(
    request_id: int,
    response: schemas.ScoreRequestResponse,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """响应得分申请（同意或拒绝）"""
    # 查找申请
    score_request = db.query(models.ScoreRequest).filter(
        models.ScoreRequest.id == request_id
    ).first()
    
    if not score_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Score request not found"
        )
    
    # 检查是否是目标用户（被申请人）
    if score_request.target_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only respond to requests made to you"
        )
    
    # 检查申请状态
    if score_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This request has already been processed"
        )
    
    # 处理响应
    if response.action == "approve":
        score_request.status = "approved"
        # 给申请人加分
        requester = db.query(models.User).filter(models.User.id == score_request.requester_id).first()
        if requester:
            requester.score += score_request.points
    elif response.action == "reject":
        score_request.status = "rejected"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be 'approve' or 'reject'"
        )
    
    db.commit()
    
    return {"message": f"Request {response.action}d successfully"}