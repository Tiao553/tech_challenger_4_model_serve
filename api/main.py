from fastapi import FastAPI
from app.api import router
from mangum import Mangum
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(root_path="/prod")

app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ou restringido para domínio específico
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

handler = Mangum(app)