import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from API_Layer.Routes import wallet_routes, authentication_route, transaction_history_route, bank_detail_route

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

app = FastAPI(title="Tenderly Wallet API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
    max_age=3600,
)

app.include_router(wallet_routes.router, prefix="/wallet", tags=["Wallet"])
app.include_router(authentication_route.router, prefix="/auth", tags=["Authentication"])
app.include_router(transaction_history_route.router, prefix="/transactions", tags=["Transactions History"])
app.include_router(bank_detail_route.router, prefix="/bank_details", tags=["Bank Details"])

@app.get("/")
def root():
    return {"message": "Tenderly Wallet API running"}
