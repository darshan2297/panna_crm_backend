import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

def test_phase5_e2e():
    print("=== Testing Phase 5 Website Order Integration E2E ===")
    
    # 1. Gateway Health Check
    health_resp = requests.get(f"{BASE_URL}/public/orders/gateway/health")
    assert health_resp.status_code == 200, f"Health check failed: {health_resp.status_code}"
    health_data = health_resp.json()
    print("1. Gateway Health:", health_data)
    assert health_data["status"] == "online"
    assert health_data["platform"] == "WEBSITE"
    
    # 2. Place Website Order (Simulating storefront customer)
    order_payload = {
        "customer": {
            "name": "Kavita Reddy",
            "phone": "9123456780",
            "email": "kavita.reddy@example.com",
            "delivery_address": "Flat 301, Lakeview Apts, Powai, Mumbai 400076"
        },
        "items": [
            {
                "item_name": "Royal Mutton Dum Biryani",
                "portion_size": "500g",
                "quantity": 2,
                "unit_price": 449.0,
                "notes": "Extra raita please"
            },
            {
                "item_name": "Hyderabadi Chicken 65 (Boneless)",
                "portion_size": "250g",
                "quantity": 1,
                "unit_price": 249.0
            }
        ],
        "payment_method": "ONLINE_UPI",
        "delivery_fee": 50.0,
        "discount": 100.0,
        "notes": "Please deliver hot, call on arrival"
    }
    
    create_resp = requests.post(f"{BASE_URL}/public/orders", json=order_payload)
    assert create_resp.status_code == 201, f"Create order failed: {create_resp.status_code}, {create_resp.text}"
    create_data = create_resp.json()
    print("2. Created Website Order Response:", json.dumps(create_data, indent=2))
    assert create_data["success"] is True
    order_num = create_data["data"]["order_number"]
    assert order_num.startswith("PB-W-")
    assert create_data["data"]["order_status"] == "CONFIRMED"
    assert create_data["data"]["payment_status"] == "PAID"
    
    # Check math: items = (2 * 449) + 249 = 898 + 249 = 1147
    # subtotal = 1147, discount = 100, taxable = 1047, tax = 5% of 1047 = 52.35
    # total = 1047 + 52.35 + 50 = 1149.35
    print(f"Subtotal: {create_data['data']['subtotal']}, Tax: {create_data['data']['tax']}, Total: {create_data['data']['total_amount']}")
    assert create_data["data"]["total_amount"] == 1149.35
    
    # 3. Track Order Publicly
    track_resp = requests.get(f"{BASE_URL}/public/orders/track/{order_num}")
    assert track_resp.status_code == 200, f"Track order failed: {track_resp.status_code}"
    track_data = track_resp.json()
    print("3. Public Order Tracking:", json.dumps(track_data, indent=2))
    assert track_data["success"] is True
    assert track_data["data"]["customer_phone_masked"] == "912****6780"
    assert len(track_data["data"]["timeline"]) == 6
    assert track_data["data"]["timeline"][0]["completed"] is True # Placed
    assert track_data["data"]["timeline"][1]["completed"] is True # Confirmed
    
    # 4. COD Order creation & Webhook payment callback
    cod_payload = {
        "customer": {
            "name": "Devendra Joshi",
            "phone": "9819283746",
            "delivery_address": "Shop 12, Main Bazaar, Dadar West, Mumbai"
        },
        "items": [
            {
                "item_name": "Panna Special Chicken Dum Biryani",
                "portion_size": "1kg",
                "quantity": 1,
                "unit_price": 580.0
            }
        ],
        "payment_method": "COD"
    }
    cod_resp = requests.post(f"{BASE_URL}/public/orders", json=cod_payload)
    assert cod_resp.status_code == 201
    cod_order_num = cod_resp.json()["data"]["order_number"]
    assert cod_resp.json()["data"]["order_status"] == "NEW"
    assert cod_resp.json()["data"]["payment_status"] == "PENDING"
    print(f"4a. Created COD Order {cod_order_num} (Status: NEW, Payment: PENDING)")
    
    # Send payment webhook callback to convert PENDING -> PAID and NEW -> CONFIRMED
    webhook_payload = {
        "payment_status": "PAID",
        "transaction_id": "razorpay_pay_99881122",
        "payment_gateway": "RAZORPAY",
        "notes": "Customer converted to UPI scan at doorstep"
    }
    wh_resp = requests.post(f"{BASE_URL}/public/orders/{cod_order_num}/payment-webhook", json=webhook_payload)
    assert wh_resp.status_code == 200, f"Webhook failed: {wh_resp.status_code}"
    wh_data = wh_resp.json()
    print("4b. Payment Webhook Response:", json.dumps(wh_data, indent=2))
    assert wh_data["data"]["new_payment_status"] == "PAID"
    assert wh_data["data"]["order_status"] == "CONFIRMED"
    
    print("\n ALL PHASE 5 E2E TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_phase5_e2e()
