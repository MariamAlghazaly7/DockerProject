import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def check_face(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_url = data.get("image_url", "")
            response = requests.post("http://ai-api:8001/predict", json={"image_url": image_url})
            return JsonResponse(response.json())
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"message": "Only POST allowed"}, status=405)
