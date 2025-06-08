from fastapi import FastAPI
from fastapi.responses import RedirectResponse

app = FastAPI()

@app.get("/hello")
def read_hello():
    return {"message": "Hello, World!"}

@app.get("/", include_in_schema=False)
def redirect_to_docs():
    return RedirectResponse(url="/docs")