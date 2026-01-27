from fastapi import FastAPI
from API_Layer.Routes import wallet_routes, authentication_route

app = FastAPI(title="Tenderly Wallet API")

app.include_router(wallet_routes.router, prefix="/wallet", tags=["Wallet"])
app.include_router(authentication_route.router, prefix="/auth", tags=["Authentication"])


@app.get("/")
def root():
    return {"message": "Tenderly Wallet API running"}
