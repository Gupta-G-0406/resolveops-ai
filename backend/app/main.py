
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="ResolveOps AI API",
    description="Multi-Agent Support Investigation Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,   #Permits the frontend to send sensitive credentials
    allow_methods=["*"], #Grants permission for all standard HTTP methods (GET, POST, PUT, DELETE, etc.).
    allow_headers=["*"], #Permits all custom or standard HTTP headers to be sent in the requests.
)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "resolveops-api",
        "version": "0.1.0",
    }
