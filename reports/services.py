import google.generativeai as genai

genai.configure(api_key="AIzaSyC1y6QnTQe6dZSqcFSH2WZEkmcA3Rp30f8")


class AIVerificationService:
    """
    Fotoğraf tabanlı atık doğrulama servisi — Gemini Vision API.
    """

    def verify_waste(self, photo_base64: str, claimed_category: str) -> tuple[bool, str]:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")

            prompt = (
                f"Sen bir geri dönüşüm uzmanısın. Bu fotoğraftaki atık, "
                f"{claimed_category} kategorisine (PLASTIC, PAPER, GLASS, ORGANIC) "
                f"uygun mu? Sadece 'EVET' veya 'HAYIR' olarak cevap ver."
            )
            image_parts = [{"mime_type": "image/jpeg", "data": photo_base64}]

            response = model.generate_content([image_parts[0], prompt])

            if "EVET" in response.text.upper():
                return True, "Onaylandı"
            return False, "Reddedildi"

        except Exception as e:
            return False, str(e)
