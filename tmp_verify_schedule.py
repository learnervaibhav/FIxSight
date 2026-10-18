import requests

payload = {
    'slot_id': 'slot-test',
    'center_id': '3777d72a-7040-4e4c-9682-239aeaf08683',
    'vehicle_id': 'V001',
    'scheduled_time': '2026-08-05T12:00:00',
    'duration_hours': 2,
    'slot_status': 'PENDING',
}

response = requests.post('http://127.0.0.1:8000/api/service/schedule', json=payload, timeout=30)
print(response.status_code)
print(response.text)
