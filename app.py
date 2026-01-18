import os
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
import uvicorn
from pypdf import PdfReader

# =========================
# ENV VARIABLES
# =========================
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-this-secret")

# =========================
# APP INIT
# =========================
app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
)

# =========================
# GOOGLE OAUTH
# =========================
oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# =========================
# HELPERS
# =========================
def read_file(file: UploadFile):
    if file.filename.endswith(".pdf"):
        reader = PdfReader(file.file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if file.filename.endswith(".txt"):
        return file.file.read().decode("utf-8")

    return "Unsupported file type"

# =========================
# ROUTES
# =========================

@app.get("/")
async def home(request: Request):
    user = request.session.get("user")

    if not user:
        return HTMLResponse("""
            <h2>Dexora AI</h2>
            <a href="/login">Login with Google</a>
        """)

    return HTMLResponse(f"""
        <h3>Welcome {user['email']}</h3>

        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" required />
            <button type="submit">Upload File</button>
        </form>

        <br>
        <a href="/logout">Logout</a>
    """)

@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth")
async def auth(request: Request):
    token = await oauth.google.authorize_access_token(request)
    request.session["user"] = token["userinfo"]
    return RedirectResponse("/")

@app.post("/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/")

    content = read_file(file)

    return HTMLResponse(f"""
        <h3>File uploaded by {user['email']}</h3>
        <pre style="white-space:pre-wrap;">{content[:3000]}</pre>
        <br>
        <a href="/">Back</a>
    """)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")

# =========================
# RENDER START
# =========================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
