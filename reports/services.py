import requests
from django.conf import settings

def validate_waste_with_ai(base64_image: str, category: str) -> tuple[bool, str]:
    if "," in base64_image:
        base64_image = base64_image.split(",")[1]

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        # Senin tıkır tıkır çalışan modelini geri getirdik!
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
                            f"Atık Türü: {category}.\n"
                            "Aşağıdaki 2 kuralı sırasıyla kontrol et ve sadece SONUÇ|MESAJ formatında tek satır cevap ver. Başka hiçbir kelime yazma!\n\n"
                            "KURAL 1: Fotoğrafın arka planında bir ÇÖP KUTUSU veya GERİ DÖNÜŞÜM KUTUSU var mı? Eğer fotoğraf ev, oda, masa gibi bir iç mekanda çekilmişse VEYA kutu görünmüyorsa, şişeye bakma bile! Direkt şu cevabı ver:\n"
                            "HAYIR|Lütfen atığı iç mekanda değil, bir geri dönüşüm kutusunun yanında fotoğraflayın.\n\n"
                            "KURAL 2: Eğer KURAL 1 geçildiyse (arkada kutu varsa), atığa bak. Bu atık çöpte yer açmak için açıkça EZİLMİŞ, BÜKÜLMÜŞ veya YASSILAŞTIRILMIŞ mı? Eğer şişe formunu koruyorsa (ezik değilse), şu cevabı ver:\n"
                            "HAYIR|Lütfen kutuda yer açmak için plastik şişeyi ezip tekrar gönderin.\n\n"
                            "Eğer arkada kutu VARSA ve atık EZİLMİŞSE, şu cevabı ver:\n"
                            "EVET|Harika, doğaya katkın için teşekkürler!"
                        ),
                    },
                ],
            }
        ],
        "max_tokens": 150, 
        "temperature": 0.1,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]
        
        # Yapay zekadan gelen "SONUÇ|MESAJ" metnini ikiye bölüyoruz
        if "|" in text:
            sonuc, mesaj = text.split("|", 1)
            return ("EVET" in sonuc.upper(), mesaj.strip())
        
        return ("EVET" in text.upper(), "İşlem sonucu yapay zeka tarafından formatlanamadı.")
        
    except requests.exceptions.RequestException as e:
        # Eğer Groq tekrar kızarsa sebebini terminalde açıkça göreceğiz
        error_detail = e.response.text if hasattr(e, "response") and e.response is not None else str(e)
        print(f"Groq API Hatası Detayı: {error_detail}")
        return (False, "Yapay zeka analiz yapamadı, lütfen tekrar deneyin.")
    except Exception as e:
        print(f"Genel Hata: {e}")
        return (False, "Görsel analiz edilirken bir hata oluştu.")