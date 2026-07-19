from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import hashlib
from . import models, database

models.Base.metadata.create_all(bind=database.engine)
app = FastAPI(title="Smart URL Shortener")
templates = Jinja2Templates(directory="templates")

def generate_short_code(url: str):
    return hashlib.sha256(url.encode()).hexdigest()[:8]

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/shorten")
def shorten_url(url: str, db: Session = Depends(database.get_db)):
    if not url.startswith("http"):
        url = "https://" + url
    code = generate_short_code(url)
    
    # Avoid duplicate entries
    existing = db.query(models.URL).filter(models.URL.short_code == code).first()
    if not existing:
        db_url = models.URL(target_url=url, short_code=code)
        db.add(db_url)
        db.commit()
        
    return {"short_url": f"http://127.0.0.1:8000/{code}"}

@app.get("/{short_code}")
def redirect(short_code: str, request: Request, db: Session = Depends(database.get_db)):
    url_entry = db.query(models.URL).filter(models.URL.short_code == short_code).first()
    if not url_entry:
        raise HTTPException(status_code=404, detail="URL not found")
    
    log = models.ClickLog(
        url_id=url_entry.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    db.commit()
    
    return RedirectResponse(url=url_entry.target_url)