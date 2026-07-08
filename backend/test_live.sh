#!/usr/bin/env bash
set -e

BASE="${BASE:-http://127.0.0.1:8000}"

echo "Health:"
curl -s "$BASE/health"
echo
echo

echo "Send actionable notification:"
curl -s -X POST "$BASE/android/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "dev1",
    "package_name": "com.whatsapp",
    "app_name": "WhatsApp",
    "title": "Mom",
    "body": "Can you call me when free?",
    "notification_key": "test_mom_'$(date +%s)'"
  }'
echo
echo

echo "Send noise notification:"
curl -s -X POST "$BASE/android/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "dev1",
    "package_name": "com.instagram.android",
    "app_name": "Instagram",
    "title": "Instagram",
    "body": "someone liked your reel",
    "notification_key": "test_noise_'$(date +%s)'"
  }'
echo
echo

echo "Status:"
curl -s "$BASE/status"
echo
