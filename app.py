from fastapi import FastAPI, Body, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse
from typing import Optional

app = FastAPI()

# Store deliveries in memory
deliveries = {}
next_delivery_id = 1


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail)}
    )

from fastapi import Response

@app.delete("/deliveries/{delivery_id}", status_code=204)
def delete_delivery(delivery_id: int):
    if delivery_id not in deliveries:
        raise HTTPException(404, "Delivery not found")

    delivery = deliveries[delivery_id]

    if delivery["status"] != "created":
        raise HTTPException(409, "Cannot delete delivery")

    del deliveries[delivery_id]

    return Response(status_code=204)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid request body"}
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/deliveries", status_code=201)
def create_delivery(data: dict = Body(...)):
    global next_delivery_id

    recipient = data.get("recipient")
    address = data.get("address")

    if not isinstance(recipient, str) or not recipient.strip():
        raise HTTPException(400, "recipient must be a non-empty string")

    if not isinstance(address, str) or not address.strip():
        raise HTTPException(400, "address must be a non-empty string")

    delivery = {
        "id": next_delivery_id,
        "recipient": recipient,
        "address": address,
        "status": "created"
    }

    deliveries[next_delivery_id] = delivery
    next_delivery_id += 1

    return delivery

@app.get("/deliveries")
def list_deliveries(status: Optional[str] = None):
    valid_statuses = {"created", "in_transit", "delivered"}

    if status is not None and status not in valid_statuses:
        raise HTTPException(400, "Invalid status")

    return [
        delivery
        for delivery in deliveries.values()
        if status is None or delivery["status"] == status
    ]

@app.get("/deliveries/{delivery_id}")
def get_delivery(delivery_id: int):
    if delivery_id not in deliveries:
        raise HTTPException(404, "Delivery not found")

    return deliveries[delivery_id]

@app.patch("/deliveries/{delivery_id}/status")
def update_delivery_status(delivery_id: int, data: dict = Body(...)):
    if delivery_id not in deliveries:
        raise HTTPException(404, "Delivery not found")

    new_status = data.get("status")
    statuses = ["created", "in_transit", "delivered"]

    if new_status not in statuses:
        raise HTTPException(400, "Invalid status")

    delivery = deliveries[delivery_id]
    current_status = delivery["status"]

    current_index = statuses.index(current_status)
    new_index = statuses.index(new_status)

    if new_index != current_index + 1:
        raise HTTPException(409, "Invalid status transition")

    delivery["status"] = new_status
    return delivery