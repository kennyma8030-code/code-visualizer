from fastapi import FastAPI, HTTPException
from tracer import TracerMiddleware

app = FastAPI()  # python -m uvicorn testserver:app --host 127.0.0.1 --port 8001 --reload
app.add_middleware(TracerMiddleware)


# --- plain helpers: nested calls + simple arithmetic ---
def test():
    x = 1
    z = test1(x)
    return z


def test1(x):
    x += 1
    y = 2
    return x + y


# --- recursion ---
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)


def factorial(n):
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


# --- loops, comprehensions, conditionals ---
def classify(numbers):
    buckets = {"even": [], "odd": [], "negative": []}
    for n in numbers:
        if n < 0:
            buckets["negative"].append(n)
        elif n % 2 == 0:
            buckets["even"].append(n)
        else:
            buckets["odd"].append(n)
    return buckets


def transform(numbers):
    squared = [n * n for n in numbers]
    running = []
    total = 0
    for n in squared:
        total += n
        running.append(total)
    return {"squared": squared, "running_sum": running, "total": total}


# --- a small class with methods that call each other ---
class ShoppingCart:
    def __init__(self):
        self.items = []

    def add(self, name, price, qty=1):
        self.items.append({"name": name, "price": price, "qty": qty})

    def line_total(self, item):
        return item["price"] * item["qty"]

    def subtotal(self):
        return sum(self.line_total(item) for item in self.items)

    def with_tax(self, rate=0.08):
        sub = self.subtotal()
        return round(sub * (1 + rate), 2)


def build_cart():
    cart = ShoppingCart()
    cart.add("widget", 9.99, qty=3)
    cart.add("gadget", 19.95)
    cart.add("doohickey", 4.50, qty=2)
    return cart


# --- exception paths (caught) ---
def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return None


def parse_ints(values):
    out = []
    for v in values:
        try:
            out.append(int(v))
        except (ValueError, TypeError):
            continue
    return out


# ----------------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------------
@app.get("/")
def root():
    return {"result": test()}


@app.get("/fib/{n}")
def fib_route(n: int):
    if n > 30:
        raise HTTPException(status_code=400, detail="n too large (max 30)")
    return {"n": n, "fib": fib(n), "factorial": factorial(n if n < 20 else 19)}


@app.get("/numbers")
def numbers_route():
    data = [5, -3, 8, 0, 7, -1, 4, 2, 11, -6]
    return {
        "input": data,
        "classified": classify(data),
        "transformed": transform(data),
    }


@app.get("/cart")
def cart_route():
    cart = build_cart()
    return {
        "items": cart.items,
        "subtotal": cart.subtotal(),
        "total_with_tax": cart.with_tax(),
    }


@app.get("/divide")
def divide_route(a: float = 10, b: float = 0):
    return {
        "a": a,
        "b": b,
        "result": safe_divide(a, b),
        "parsed": parse_ints(["1", "2", "x", None, "4"]),
    }


@app.get("/pipeline")
def pipeline_route():
    """Exercises several helpers in one request for a deep, varied trace."""
    cart = build_cart()
    nums = parse_ints(["10", "20", "oops", "30"])
    return {
        "fib_10": fib(10),
        "factorial_6": factorial(6),
        "cart_total": cart.with_tax(),
        "classified": classify(nums + [-2, 3]),
        "transformed": transform(nums),
        "nested": test(),
    }
