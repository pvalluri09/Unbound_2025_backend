from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from datetime import datetime
import secrets, re

# ----- App & Templates -----
app = FastAPI(title="Unbound Command Gateway - Web UI")
templates = Jinja2Templates(directory="templates")

# ----- Database -----
Base = declarative_base()
DB_URL = "sqlite:///unbound.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

# ----- Models -----
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    api_key = Column(String, unique=True)
    role = Column(String)  # admin/member
    credits = Column(Integer, default=100)

class Command(Base):
    __tablename__ = "commands"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    command_text = Column(Text)
    status = Column(String)  # executed/rejected
    reason = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

class Rule(Base):
    __tablename__ = "rules"
    id = Column(Integer, primary_key=True)
    pattern = Column(String)
    action = Column(String)  # AUTO_ACCEPT / AUTO_REJECT

# ----- Initialize DB -----
def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if not db.query(User).filter_by(role="admin").first():
        admin_api = secrets.token_urlsafe(16)
        admin = User(username="admin", api_key=admin_api, role="admin", credits=1000)
        db.add(admin)
        db.commit()
        print(f"Admin created! API Key: {admin_api}")

    starter_rules = [
        (r":\(\)\{ :\|:& \};:", "AUTO_REJECT"),
        (r"rm\s+-rf\s+/", "AUTO_REJECT"),
        (r"mkfs\.", "AUTO_REJECT"),
        (r"git\s+(status|log|diff)", "AUTO_ACCEPT"),
        (r"^(ls|cat|pwd|echo)", "AUTO_ACCEPT"),
    ]
    for pattern, action in starter_rules:
        if not db.query(Rule).filter_by(pattern=pattern).first():
            db.add(Rule(pattern=pattern, action=action))
    db.commit()
    db.close()

init_db()

# ----- Dependencies -----
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_by_api(api_key: str, db: Session):
    if not api_key:
        return None
    return db.query(User).filter_by(api_key=api_key).first()

# ----- Command Execution -----
def execute_command(db: Session, user: User, command_text: str):
    rules = db.query(Rule).all()
    action = "AUTO_REJECT"
    for rule in rules:
        try:
            if re.search(rule.pattern, command_text):
                action = rule.action
                break
        except re.error:
            continue

    cmd = Command(user_id=user.id, command_text=command_text)
    if action == "AUTO_ACCEPT":
        if user.credits <= 0:
            cmd.status = "rejected"
            cmd.reason = "No credits left"
        else:
            user.credits -= 1
            cmd.status = "executed"
            cmd.reason = "Command executed successfully"
    else:
        cmd.status = "rejected"
        cmd.reason = "Blocked by rule"

    db.add(cmd)
    db.commit()
    db.refresh(user)  # refresh credits
    return cmd

# ----- Routes -----
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login/")
def login(request: Request, username: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=username).first()
    if not user:
        api_key = secrets.token_urlsafe(16)
        user = User(username=username, api_key=api_key, role="member", credits=100)
        db.add(user)
        db.commit()
        db.refresh(user)
    response = RedirectResponse("/dashboard/", status_code=302)
    response.set_cookie(key="api_key", value=user.api_key)
    return response

@app.get("/dashboard/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    api_key = request.cookies.get("api_key")
    user = get_user_by_api(api_key, db)
    if not user:
        return RedirectResponse("/")
    history = db.query(Command).filter_by(user_id=user.id).order_by(Command.id.desc()).all()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "commands": history,  # corrected variable
            "commands_left": user.credits
        }
    )

@app.post("/submit_command/")
def submit_command(request: Request, command: str = Form(...), db: Session = Depends(get_db)):
    api_key = request.cookies.get("api_key")
    user = get_user_by_api(api_key, db)
    if not user:
        return RedirectResponse("/")
    execute_command(db, user, command)
    return RedirectResponse("/dashboard/", status_code=302)

# ----- Admin Routes -----
@app.get("/admin/", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    api_key = request.cookies.get("api_key")
    user = get_user_by_api(api_key, db)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    rules = db.query(Rule).all()
    return templates.TemplateResponse("admin.html", {"request": request, "user": user, "rules": rules})

@app.post("/add_rule/")
def add_rule(request: Request, pattern: str = Form(...), action: str = Form(...), db: Session = Depends(get_db)):
    api_key = request.cookies.get("api_key")
    user = get_user_by_api(api_key, db)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        re.compile(pattern)
    except re.error:
        raise HTTPException(status_code=400, detail="Invalid regex")
    existing_rule = db.query(Rule).filter_by(pattern=pattern).first()
    if existing_rule:
        raise HTTPException(status_code=400, detail="Rule already exists")
    db.add(Rule(pattern=pattern, action=action))
    db.commit()
    return RedirectResponse("/admin/", status_code=302)
