from fastapi import FastAPI
import redis
import random
import json

app = FastAPI()
r = redis.Redis(host="redis", port=6379, decode_responses=True)

@app.get("/random")
def get_random_proxy():
    proxies = r.lrange("proxies", 0, -1)
    if not proxies:
        return {"error": "No proxy available"}
    return {"proxy": random.choice(proxies)}