import requests

from django.conf import settings


def validate_waste_with_ai(base64_image: str, category: str) -> bool:
    if "," in base64_image:
        base64_image = base64_image.split(",")[1]

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            f"Kullanıcı bu fotoğrafta {category} türünde bir atık olduğunu iddia ediyor. "
                            "Fotoğrafta açıkça bu atık var mı? "
                            "Eğer fotoğrafta sadece bir insan eli, yüzü veya alakasız bir nesne varsa reddet. "
                            "Sadece EVET veya HAYIR kelimesiyle yanıt ver."
                        ),
                    },
                ],
            }
        ],
        "max_tokens": 10,
        "temperature": 0,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]
        return "EVET" in text.upper()
    except requests.exceptions.RequestException as e:
        print(f"Groq API Hatası: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(e.response.text)
        return False
    except Exception as e:
        print(f"Genel Hata: {e}")
        return False
