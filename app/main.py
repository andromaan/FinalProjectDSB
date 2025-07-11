from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from controllers.car_platform_controller import car_platform_router
from controllers.scraping_controller import scraping_router
from controllers.car_model_controller import car_model_router
from controllers.regression_controller import regression_router


app = FastAPI(title="Car Ranking and Price Analysis")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(car_platform_router)

app.include_router(scraping_router)

app.include_router(car_model_router)

app.include_router(regression_router)

@app.get("/", include_in_schema=False)
def redirect_to_docs():
    return RedirectResponse(url="/docs")