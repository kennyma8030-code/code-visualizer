from fastapi import FastAPI
from tracer import TracerMiddleware

app = FastAPI()
app.add_middleware(TracerMiddleware)

@app.get("/")
def test():
    x = 1
    z = test1(x)
    return z
    
def test1(x):
    x += 1
    y = 2
    return x + y